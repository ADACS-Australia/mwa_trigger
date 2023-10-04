import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from datetime import timedelta, datetime

import random
import urllib.request
from trigger_app.utils import getMWAPointingsFromSkymapFile, getMWARaDecFromAltAz, isClosePosition, subArrayMWAPointings
from astropy.table import Table
import atca_rapid_response_api as arrApi
from astropy.utils.data import download_file
from tracet.triggerservice import trigger
from .models import Observations, Event, TRIGGER_ON
from django.core.files import File 

import logging
logger = logging.getLogger(__name__)

def dump_mwa_buffer():
    return True

def trigger_observation(
    proposal_decision_model,
    decision_reason_log,
    reason="First Observation",
    event_id=None,
):
    """Perform any comon observation checks, send off observations with the telescope's function then record observations in the Observations model.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    reason : `str`, optional
        The reason for this observation. The default is "First Observation" but other potential reasons are "Repointing".
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    decision_reason_log : `str`
        The updated trigger message to include an observation specific logs.
    """
    print("Trigger observation")
    trigger_real_pretend = TRIGGER_ON[0][0]
    trigger_both = TRIGGER_ON[1][0]
    trigger_real = TRIGGER_ON[2][0]
    voevents = Event.objects.filter(
        trig_id=proposal_decision_model.trig_id).order_by('-recieved_data')
    telescopes = []
    latestVoevent = voevents[0]
    # Check if source is above the horizon for MWA
    if proposal_decision_model.proposal.telescope.name.startswith("MWA") and proposal_decision_model.ra and proposal_decision_model.dec:
        print("Checking if is above the horizon for MWA")
        # Create Earth location for the telescope
        telescope = proposal_decision_model.proposal.telescope
        location = EarthLocation(
            lon=telescope.lon * u.deg,
            lat=telescope.lat * u.deg,
            height=telescope.height * u.m
        )
        print('obtained earth location')

        obs_source = SkyCoord(
            proposal_decision_model.ra,
            proposal_decision_model.dec,
            # equinox='J2000',
            unit=(u.deg, u.deg)
        )
        print('obtained obs source location')
        # Convert from RA/Dec to Alt/Az
        obs_source_altaz_beg = obs_source.transform_to(
            AltAz(obstime=Time.now(), location=location))
        alt_beg = obs_source_altaz_beg.alt.deg
        # Calculate alt at end of obs
        end_time = Time.now() + timedelta(seconds=proposal_decision_model.proposal.mwa_exptime)
        obs_source_altaz_end = obs_source.transform_to(
            AltAz(obstime=end_time, location=location))
        alt_end = obs_source_altaz_end.alt.deg

        print('converted obs for horizon')

        if alt_beg < proposal_decision_model.proposal.mwa_horizon_limit and alt_end < proposal_decision_model.proposal.mwa_horizon_limit:
            horizon_message = f"{datetime.utcnow()}: Event ID {event_id}: Not triggering due to horizon limit: alt_beg {alt_beg:.4f} < {proposal_decision_model.proposal.mwa_horizon_limit:.4f} and alt_end {alt_end:.4f} < {proposal_decision_model.proposal.mwa_horizon_limit:.4f}. "
            logger.debug(horizon_message)
            return 'I', decision_reason_log + horizon_message
        
        elif alt_beg < proposal_decision_model.proposal.mwa_horizon_limit:
            # Warn them in the log
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Warning: The source is below the horizion limit at the start of the observation alt_beg {alt_beg:.4f}. \n"
        
        elif alt_end < proposal_decision_model.proposal.mwa_horizon_limit:
            # Warn them in the log
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Warning: The source will set below the horizion limit by the end of the observation alt_end {alt_end:.4f}. \n"

        # above the horizon so send off telescope specific set ups
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Above horizon so attempting to observe with {proposal_decision_model.proposal.telescope.name}. \n"
        
        logger.debug(
            f"Triggered observation at an elevation of {alt_beg} to elevation of {alt_end}")
      
    mwa_sub_arrays = None

    if proposal_decision_model.proposal.telescope.name.startswith("MWA"):

   
        # If telescope ends in VCS then this proposal is for observing in VCS mode
        vcsmode = proposal_decision_model.proposal.telescope.name.endswith(
            "VCS")
        if(vcsmode):
            print("VCS Mode")

        # Create an observation name
        # Collect event telescopes
  

        print(proposal_decision_model.trig_id)

        for voevent in voevents:
            telescopes.append(voevent.telescope)
        # Make sure they are unique and seperate with a _
        telescopes = "_".join(list(set(telescopes)))
        obsname = f'{telescopes}_{proposal_decision_model.trig_id}'

        buffered = False

        pretend = True
        repoint = None

        print(f"proposal_decision_model.proposal.testing {proposal_decision_model.proposal.testing}")
        print(f"latestVoevent {latestVoevent.__dict__}")
        if(latestVoevent.role == 'test' and proposal_decision_model.proposal.testing != trigger_both):
            raise Exception("Invalid event observation and proposal setting")
                
        if proposal_decision_model.proposal.testing == trigger_both and latestVoevent.role != 'test':
            pretend = False
        if proposal_decision_model.proposal.testing == trigger_real and latestVoevent.role != 'test':
            pretend = False
        print(f"pretend: {pretend}")

     
        if proposal_decision_model.proposal.source_type == 'GW' and len(voevents) == 1:
            # Dump out the last ~3 mins of MWA buffer to try and catch event
            print(f"DEBUG - DISABLED dumping MWA buffer")
            # reason = f"{latestVoevent.trig_id} - First event so dumping MWA buffer "
            # buffered = True
            # decision_buffer, decision_reason_log_buffer, obsids_buffer, result_buffer = trigger_mwa_observation(
            #     proposal_decision_model,
            #     decision_reason_log,
            #     obsname="buffered"+obsname,
            #     vcsmode=vcsmode,
            #     event_id=event_id,
            #     mwa_sub_arrays=mwa_sub_arrays,
            #     buffered=buffered,
            #     pretend=pretend
            # )
            # print(f"obsids_buffer: {obsids_buffer}")

        if proposal_decision_model.proposal.source_type == 'GW' and len(voevents) > 1 and latestVoevent.lvc_skymap_fits != None:
            print(f"DEBUG - checking to update position")
            print(f"DEBUG - proposal_decision_model.__dict__ {proposal_decision_model.__dict__}")

            latestObs = Observations.objects.filter(
                telescope=proposal_decision_model.proposal.telescope
            ).order_by('-created_at').first()
            
            print(f"DEBUG - latestObs {latestObs}")

            if(latestObs.mwa_sub_arrays is not None):
                print(f"DEBUG - skymap_fits_fits: {latestVoevent.lvc_skymap_fits}")
                try:
                    skymap = Table.read(latestVoevent.lvc_skymap_fits)
                    
                    (skymap, time, pointings) = getMWAPointingsFromSkymapFile(skymap)
                    print(pointings)
                    current_arrays_dec = latestObs.mwa_sub_arrays['dec']
                    current_arrays_ra = latestObs.mwa_sub_arrays['ra']

                    repoint = False
                  
                    pointings_dec = []
                    pointings_ra = []
                    for res in pointings:
                        pointings_ra.append(res[3])
                        pointings_dec.append(res[4])

                        repoint = True
                        for index, val  in enumerate(current_arrays_dec):
                            print(f"index: {index}")
                            ra1 = current_arrays_ra[index] *u.deg
                            dec1 = current_arrays_dec[index] *u.deg
                            ra2 = res[3]
                            dec2 = res[4]

                            if(isClosePosition(ra1,dec1,ra2,dec2)):
                                repoint = False
                    print(f'repoint: {repoint}')
                    print(current_arrays_dec)
                    print(pointings_dec)
                    print(current_arrays_ra)  
                    print(pointings_ra)    
                    if repoint:
                        reason = f"{latestVoevent.trig_id} - Updating observation positions based on event."
                        mwa_sub_arrays = {
                            'dec': [
                                pointings[0][4].value,
                                pointings[1][4].value,
                                pointings[2][4].value,
                                pointings[3][4].value,
                            ],
                            'ra': [
                                pointings[0][3].value,
                                pointings[1][3].value,
                                pointings[2][3].value,
                                pointings[3][3].value,
                            ]
                        }
                    else:
                        decision_reason_log+=f"{datetime.utcnow()}: Event ID {event_id}: Repointing is {repoint} \n"
                        return "T", decision_reason_log
                except Exception as e:
                    print(e)
                    logger.error("Error getting MWA pointings from skymap")
                    logger.error(e)
            else:
                print(f"DEBUG - no sub arrays on obs")
        

        elif proposal_decision_model.proposal.source_type == 'GW' and latestVoevent.lvc_skymap_fits != None and latestVoevent.event_type != 'EarlyWarning':
            print(f"DEBUG - skymap_fits_fits: {latestVoevent.lvc_skymap_fits}")
            try:
                event_filename = download_file(latestVoevent.lvc_skymap_fits, 
                               cache=True)
                skymap = Table.read(event_filename)
                # alt=[ps.mwa_sub_alt_NE, ps.mwa_sub_alt_NW, ps.mwa_sub_alt_SE, ps.mwa_sub_alt_SW],
                # az=[ps.mwa_sub_az_NE, ps.mwa_sub_az_NW, ps.mwa_sub_az_SE, ps.mwa_sub_az_SW],
                (skymap, time, pointings) = getMWAPointingsFromSkymapFile(skymap)
                print(pointings)
                
                mwa_sub_arrays = {
                    'dec': [
                        pointings[0][4].value,
                        pointings[1][4].value,
                        pointings[2][4].value,
                        pointings[3][4].value,
                    ],
                    'ra': [
                        pointings[0][3].value,
                        pointings[1][3].value,
                        pointings[2][3].value,
                        pointings[3][3].value,
                    ]
                }
                reason = f"{latestVoevent.trig_id} - Event has position so using skymap pointings"

            except Exception as e:
                print(e)
                logger.error("Error getting MWA pointings from skymap")
                logger.error(e)

        elif proposal_decision_model.proposal.source_type == 'GW' and latestVoevent.event_type == 'EarlyWarning':
            ps = proposal_decision_model.proposal
 
            print(f"DEBUG - ps {ps.__dict__}")

            sub1 = getMWARaDecFromAltAz(alt=ps.mwa_sub_alt_NE, az=ps.mwa_sub_az_NE, time = Time.now())
            sub2 = getMWARaDecFromAltAz(alt=ps.mwa_sub_alt_NW, az=ps.mwa_sub_az_NW, time = Time.now())
            sub3 = getMWARaDecFromAltAz(alt=ps.mwa_sub_alt_SE, az=ps.mwa_sub_az_SE, time = Time.now())
            sub4 = getMWARaDecFromAltAz(alt=ps.mwa_sub_alt_SW, az=ps.mwa_sub_az_SW, time = Time.now())

            print(f"DEBUG - sub1[1].value { sub1[1].value }")

            mwa_sub_arrays = {
                'dec': [
                    sub1[1].value,
                    sub2[1].value,
                    sub3[1].value,
                    sub4[1].value,
                ],
                'ra': [
                    sub1[0].value,
                    sub2[0].value,
                    sub3[0].value,
                    sub4[0].value,
                ]
            }

            reason = f"{latestVoevent.trig_id} - Event is an early warning so using default sub arrays"

            # Only schedule a 15 min obs
            proposal_decision_model.proposal.mwa_nobs = 1
            proposal_decision_model.proposal.mwa_exptime = 904

        elif proposal_decision_model.proposal.source_type == 'GW' and latestVoevent.lvc_skymap_fits == None:
            
            ps = proposal_decision_model.proposal
            print(f"DEBUG - ps {ps.__dict__}")
            sub1 = getMWARaDecFromAltAz(alt=ps.mwa_sub_alt_NE, az=ps.mwa_sub_az_NE, time = Time.now() )
            sub2 = getMWARaDecFromAltAz(alt=ps.mwa_sub_alt_NW, az=ps.mwa_sub_az_NW, time = Time.now())
            sub3 = getMWARaDecFromAltAz(alt=ps.mwa_sub_alt_SE, az=ps.mwa_sub_az_SE, time = Time.now())
            sub4 = getMWARaDecFromAltAz(alt=ps.mwa_sub_alt_SW, az=ps.mwa_sub_az_SW, time = Time.now())
            print(type(sub1[1]))
            print(f"DEBUG - sub1[1].value { sub1[1].value }")

            mwa_sub_arrays = {
                'dec': [
                    sub1[1].value,
                    sub2[1].value,
                    sub3[1].value,
                    sub4[1].value,
                ],
                'ra': [
                    sub1[0].value,
                    sub2[0].value,
                    sub3[0].value,
                    sub4[0].value,
                ]
            }

            reason = f"{latestVoevent.trig_id} - Event has no positional data so using default sub arrays"

            # Only schedule a 60 min obs if no position
            proposal_decision_model.proposal.mwa_nobs = 1
            proposal_decision_model.proposal.mwa_exptime = 3600        
            print(f"DEBUG - mwa_sub_arrays: {str(mwa_sub_arrays)}")

        print(f"vcsmode: {vcsmode}")
        # Check if you can observe and if so send off MWA observation

        decision, decision_reason_log, obsids, result = trigger_mwa_observation(
            proposal_decision_model,
            decision_reason_log,
            obsname,
            vcsmode=vcsmode,
            event_id=event_id,
            mwa_sub_arrays=mwa_sub_arrays,
            pretend=pretend
        )

        # print(decision, decision_reason_log, obsids)
        # decision_buffer, decision_reason_log_buffer, obsids_buffer
   
        print(f"buffered: {buffered}")
        print(f"mwa_sub_arrays: {mwa_sub_arrays}")
        if buffered:
            print(f"Debug -  Saving buffer observation")
            print(f"result_buffer id: {result_buffer['trigger_id']}")
            decision_reason_log=f"{decision_reason_log}{datetime.utcnow()}: Event ID {event_id}: Making a buffer observation. \n"
            obsids=obsids_buffer + obsids
            saved_obs_1 = Observations.objects.create(
                trigger_id=result_buffer['trigger_id'] or random.randrange(10000, 99999),
                telescope=proposal_decision_model.proposal.telescope,
                proposal_decision_id=proposal_decision_model,
                reason=f"This is a buffer observation ID",
                website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsids_buffer[0]}",
                mwa_sub_arrays=mwa_sub_arrays,
                event=latestVoevent,
                mwa_response=result_buffer
            )
            print(saved_obs_1)
        if repoint is True:
            reason = "This is a repointing observation"
            decision_reason_log=f"{decision_reason_log}{datetime.utcnow()}: Event ID {event_id}: Repointing. \n"

        print(f"result id: {result['trigger_id']}")

        if repoint is not False and latestVoevent.lvc_skymap_fits != None and mwa_sub_arrays != None:
            filepath = subArrayMWAPointings(skymap=skymap, time=time, name=latestVoevent.trig_id, pointings=pointings)
            print(f"Debug -  Saving SKYMAP sub array observation")
            decision_reason_log=f"{decision_reason_log}{datetime.utcnow()}: Event ID {event_id}: Making a SKYMAP sub array observation. \n"
            saved_obs_2 = Observations.objects.create(
                trigger_id=result['trigger_id'] or random.randrange(10000, 99999),
                telescope=proposal_decision_model.proposal.telescope,
                proposal_decision_id=proposal_decision_model,
                reason=reason,
                website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsids[0]}",
                mwa_sub_arrays=mwa_sub_arrays,
                mwa_sky_map_pointings=f"mwa_pointings/{filepath}",
                event=latestVoevent,
                mwa_response=result
            )

            print(saved_obs_2)
                
        # Create new obsid model
        elif repoint is not False: 
            print(f"Debug -  Saving DEFAULT sub array observation")
            decision_reason_log=f"{decision_reason_log}{datetime.utcnow()}: Event ID {event_id}: Making a DEFAULT sub array observation. \n"
            Observations.objects.create(
                trigger_id=result['trigger_id'] or random.randrange(10000, 99999),
                telescope=proposal_decision_model.proposal.telescope,
                proposal_decision_id=proposal_decision_model,
                reason=reason,
                website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsids[0]}",
                mwa_sub_arrays=mwa_sub_arrays,
                event=latestVoevent,
                mwa_response=result
            )
    elif proposal_decision_model.proposal.telescope.name == "ATCA":
        # Check if you can observe and if so send off mwa observation
        obsname = f'{proposal_decision_model.trig_id}'
        decision, decision_reason_log, obsids = trigger_atca_observation(
            proposal_decision_model,
            decision_reason_log,
            obsname,
            event_id=event_id,
        )
        for obsid in obsids:
            # Create new obsid model
            Observations.objects.create(
                trigger_id=obsid,
                telescope=proposal_decision_model.proposal.telescope,
                proposal_decision_id=proposal_decision_model,
                reason=reason,
                event=latestVoevent,
                # TODO see if atca has a nice observation details webpage
                # website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
            )
    return decision, decision_reason_log


def trigger_mwa_observation(
    proposal_decision_model,
    decision_reason_log,
    obsname,
    vcsmode=False,
    event_id=None,
    mwa_sub_arrays=None,
    buffered=False,
    pretend=False
):
    """Check if the MWA can observe then send it off the observation.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    obsname : `str`
        The name of the observation.
    vcsmode : `boolean`, optional
        True to observe in VCS mode and False to observe in correlator/imaging mode. Default: False
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    decision_reason_log : `str`
        The updated trigger message to include an observation specific logs.
    observations : `list`
        A list of observations that were scheduled by MWA.
    result : `object`
        Result from mwa
    """
    prop_settings = proposal_decision_model.proposal
    print("DEBUG - triggering MWA")
    print(f"DEBUG - proposal: {prop_settings.__dict__}")
    # Not below horizon limit so observer
    logger.info(f"Triggering MWA at UTC time {Time.now()} ...")
    # Handle early warning events without position using sub arrays
    if(prop_settings.source_type == 'GW' and buffered == True and vcsmode == True):
        print("DEBUG - Dumping buffer")
        print("DEBUG - Using nobs = 1, exptime = 8")

        result = trigger(
            project_id=prop_settings.project_id.id,
            secure_key=prop_settings.project_id.password,
            pretend=pretend,
            creator='VOEvent_Auto_Trigger',  # TODO grab version
            obsname=obsname,
            nobs=1,
            # Assume always using 24 contiguous coarse frequency channels
            freqspecs=prop_settings.mwa_freqspecs,
            avoidsun=True,
            inttime=prop_settings.mwa_inttime,
            freqres=prop_settings.mwa_freqres,
            exptime=8,
            vcsmode=vcsmode,
            buffered=buffered
        )
    
    elif (prop_settings.source_type == 'GW' and mwa_sub_arrays != None):
        print("DEBUG - Scheduling an ra/dec sub array observation")

        result = trigger(
            project_id=prop_settings.project_id.id,
            secure_key=prop_settings.project_id.password,
            pretend=pretend,
            subarray_list=['all_ne', 'all_nw', 'all_se', 'all_sw'],
            ra=mwa_sub_arrays['ra'],
            dec=mwa_sub_arrays['dec'],
            creator='VOEvent_Auto_Trigger',  # TODO grab version
            obsname=obsname,
            nobs=prop_settings.mwa_nobs,
            # Assume always using 24 contiguous coarse frequency channels
            freqspecs=prop_settings.mwa_freqspecs,
            avoidsun=True,
            inttime=prop_settings.mwa_inttime,
            freqres=prop_settings.mwa_freqres,
            exptime=prop_settings.mwa_exptime,
            calibrator=True,
            calexptime=prop_settings.mwa_calexptime,
            vcsmode=vcsmode,
        )
    else:
        print("DEBUG - Scheduling an ra/dec observation")

        result = trigger(
            project_id=prop_settings.project_id.id,
            secure_key=prop_settings.project_id.password,
            pretend=pretend,
            ra=proposal_decision_model.ra,
            dec=proposal_decision_model.dec,
            alt=proposal_decision_model.alt,
            az=proposal_decision_model.az,
            creator='VOEvent_Auto_Trigger',  # TODO grab version
            obsname=obsname,
            nobs=prop_settings.mwa_nobs,
            # Assume always using 24 contiguous coarse frequency channels
            freqspecs=prop_settings.mwa_freqspecs,
            avoidsun=True,
            inttime=prop_settings.mwa_inttime,
            freqres=prop_settings.mwa_freqres,
            exptime=prop_settings.mwa_exptime,
            calibrator=True,
            calexptime=prop_settings.mwa_calexptime,
            vcsmode=vcsmode,
        )
    print(f"result: {result}")
    logger.debug(f"result: {result}")
    # Check if succesful
    if result is None:
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Web API error, possible server error.\n "
        return 'E', decision_reason_log, [], result
    if not result['success']:
        # Observation not succesful so record why
        for err_id in result['errors']:
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: {result['errors'][err_id]}.\n "
        # Return an error as the trigger status
        return 'E', decision_reason_log, [], result

    # Output the results
    logger.info(f"Trigger sent: {result['success']}")
    logger.info(f"Trigger params: {result['success']}")
    if 'stdout' in result['schedule'].keys():
        if result['schedule']['stdout']:
            logger.info(f"schedule' stdout: {result['schedule']['stdout']}")
    if 'stderr' in result['schedule'].keys():
        if result['schedule']['stderr']:
            logger.info(f"schedule' stderr: {result['schedule']['stderr']}")

    # Grab the obsids (sometimes we will send of several observations)
    obsids = []
    if 'obsid_list' in result.keys() and len(result['obsid_list']) > 0:
        obsids = result['obsid_list']
    else:
        for r in result['schedule']['stderr'].split("\n"):
            if r.startswith("INFO:Schedule metadata for"):
                obsids.append(r.split(" for ")[1][:-1])
            elif(r.startswith('Pretending: commands not run')):
                obsids.append(f"P{random.randint(1000,9999)}")
    return 'T', decision_reason_log, obsids, result


def trigger_atca_observation(
    proposal_decision_model,
    decision_reason_log,
    obsname,
    event_id=None,
):
    """Check if the ATCA telescope can observe, send it off the observation and return any errors.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    obsname : `str`
        The name of the observation.
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    decision_reason_log : `str`
        The updated trigger message to include an observation specific logs.
    observations : `list`
        A list of observations that were scheduled by ATCA (currently there is no functionality to record this so will be empty).
    """
    prop_obj = proposal_decision_model.proposal
    
    # TODO add any schedule checks or observation parsing here
    print("DEBUG - trigger_atca_observation")
    # Not below horizon limit so observer
    logger.info(f"Triggering  ATCA at UTC time {Time.now()} ...")

    rq = {
        "source": prop_obj.source_type,
        "rightAscension": proposal_decision_model.ra_hms,
        "declination": proposal_decision_model.dec_dms,
        "project": prop_obj.project_id.id,
        "maxExposureLength": str(timedelta(minutes=prop_obj.atca_max_exptime)),
        "minExposureLength": str(timedelta(minutes=prop_obj.atca_min_exptime)),
        "scanType": "Dwell",
        "3mm": {
            "use": prop_obj.atca_band_3mm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_3mm_exptime)),
            "freq1": prop_obj.atca_band_3mm_freq1,
            "freq2": prop_obj.atca_band_3mm_freq2,
        },
        "7mm": {
            "use": prop_obj.atca_band_7mm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_7mm_exptime)),
            "freq1": prop_obj.atca_band_7mm_freq1,
            "freq2": prop_obj.atca_band_7mm_freq2,
        },
        "15mm": {
            "use": prop_obj.atca_band_15mm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_15mm_exptime)),
            "freq1": prop_obj.atca_band_15mm_freq1,
            "freq2": prop_obj.atca_band_15mm_freq2,
        },
        "4cm": {
            "use": prop_obj.atca_band_4cm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_4cm_exptime)),
            "freq1": prop_obj.atca_band_4cm_freq1,
            "freq2": prop_obj.atca_band_4cm_freq2,
        },
        "16cm": {
            "use": prop_obj.atca_band_16cm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_16cm_exptime)),
            # Only frequency available due to limited bandwidth
            "freq1": 2100,
            "freq2": 2100,
        },
    }

    # We have our request now, so we need to craft the service request to submit it to
    # the rapid response service.
    rapidObj = {'requestDict': rq}
    rapidObj["authenticationToken"] = prop_obj.project_id.password
    rapidObj["email"] = prop_obj.project_id.atca_email
    trigger_real_pretend = TRIGGER_ON[0][0]

    if prop_obj.testing == trigger_real_pretend:
        rapidObj["test"] = True
        rapidObj["noTimeLimit"] = True
        rapidObj["noScoreLimit"] = True

    request = arrApi.api(rapidObj)
    try:
        response = request.send()
    except Exception as r:
        logger.error(f"ATCA error message: {r}")
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: ATCA error message: {r}\n "
        return 'E', decision_reason_log, []

    # # Check for errors
    # if  (not response["authenticationToken"]["received"]) or (not response["authenticationToken"]["verified"]) or \
    #     (not response["schedule"]["received"]) or (not response["schedule"]["verified"]):
    #     decision_reason_log += f"ATCA return message: {r}\n "
    #     return 'E', decision_reason_log, []

    return 'T', decision_reason_log, [response["id"]]
