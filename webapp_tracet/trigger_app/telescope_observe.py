import logging
import os
import random
import urllib.request
from datetime import datetime, timedelta, timezone
from math import floor

import astropy.units as u
import atca_rapid_response_api as arrApi
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.table import Table
from astropy.time import Time
from astropy.utils.data import download_file
from django.core.files import File
from tracet.triggerservice import trigger
from trigger_app.utils.utils_telescope import (
    getMWAPointingsFromSkymapFile,
    getMWARaDecFromAltAz,
    isClosePosition,
    subArrayMWAPointings,
)

from .models import TRIGGER_ON, ATCAUser, Event, Observations

logger = logging.getLogger(__name__)


def round_to_nearest_modulo_8(number):
    """Rounds a number to the nearest modulo of 8."""
    remainder = number % 8
    if remainder >= 4:
        rounded_number = number + (8 - remainder)
    else:
        rounded_number = number - remainder
    return rounded_number


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
    print("DEBUG - Trigger observation")
    trigger_real_pretend = TRIGGER_ON[0][0]
    trigger_both = TRIGGER_ON[1][0]
    trigger_real = TRIGGER_ON[2][0]
    voevents = Event.objects.filter(trig_id=proposal_decision_model.trig_id).order_by(
        "-recieved_data"
    )
    telescopes = []
    latestVoevent = voevents[0]

    telescope_name = proposal_decision_model.proposal.telescope.name
    context = {
        "proposal_decision_model": proposal_decision_model,
        "event_id": event_id,
        "decision_reason_log": decision_reason_log,
        "reason": reason,
        "telescopes": telescopes,
        "latestVoevent": latestVoevent,
    }

    context = check_mwa_horizon_and_prepare_context(context)
    # Check if source is above the horizon for MWA
    context["mwa_sub_arrays"] = None

    if context["proposal_decision_model"].proposal.telescope.name.startswith("MWA"):

        context = prepare_observation_context(context, voevents)

        if context["proposal_decision_model"].proposal.source_type == "GW":

            # Buffer dump if first event, use default array if early warning, process skymap if not early warning
            if len(voevents) == 1:
                # Dump out the last ~3 mins of MWA buffer to try and catch event
                context["reason"] = (
                    f"{context['latestVoevent'].trig_id} - First event so sending dump MWA buffer request to MWA"
                )
                context[
                    "decision_reason_log"
                ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: First event so sending dump MWA buffer request to MWA\n"

                context["buffered"] = True
                context["request_sent_at"] = datetime.utcnow()

                (
                    context["decision_buffer"],
                    context["decision_reason_log_buffer"],
                    context["obsids_buffer"],
                    context["result_buffer"],
                ) = trigger_mwa_observation(
                    context["proposal_decision_model"],
                    context["decision_reason_log"],
                    obsname=context["obsname"],
                    vcsmode=context["vcsmode"],
                    event_id=context["event_id"],
                    mwa_sub_arrays=context["mwa_sub_arrays"],
                    buffered=context["buffered"],
                    pretend=context["pretend"],
                )

                print(f"obsids_buffer: {context['obsids_buffer']}")
                context[
                    "decision_reason_log"
                ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Saving buffer observation result.\n"

                if context["decision_buffer"].find("T") > -1:
                    context = save_observation(
                        context,
                        trigger_id=context["result_buffer"]["trigger_id"]
                        or random.randrange(10000, 99999),
                        obsid=context["obsids_buffer"][0],
                        reason="This is a buffer observation ID",
                    )

                # Handle the unique case of the early warning
                if context["latestVoevent"].event_type == "EarlyWarning":
                    context = handle_early_warning(context)
                elif (
                    context["latestVoevent"].lvc_skymap_fits != None
                    and context["latestVoevent"].event_type != "EarlyWarning"
                ):
                    context = handle_skymap_event(context)

            # Repoint if there is a newer skymap with different positions
            if len(voevents) > 1 and context["latestVoevent"].lvc_skymap_fits:
                print(f"DEBUG - checking to repoint")
                context["reason"] = (
                    f"{context['latestVoevent'].trig_id} - Event has a skymap"
                )

                latest_obs = get_latest_observation(context["proposal_decision_model"])

                if latest_obs and latest_obs.mwa_sub_arrays:
                    context[
                        "decision_reason_log"
                    ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: New event has skymap \n"

                    try:
                        context = update_position_based_on_skymap(context, latest_obs)
                    except Exception as e:
                        print(e)
                        logger.error("Error getting MWA pointings from skymap")
                        logger.error(e)
                else:
                    print(f"DEBUG - no sub arrays on previous obs")
                    context[
                        "decision_reason_log"
                    ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Could not find sub array position on previous observation. \n"

            print("Decision: ", context)
        else:
            print("passed Non-GW check")
            context = handle_non_gw_observation(context)

    elif context["proposal_decision_model"].proposal.telescope.name == "ATCA":
        # Check if you can observe and if so send off mwa observation
        context = handle_atca_observation(context)
    else:
        context["decision_reason_log"] = (
            f"{context['decision_reason_log']}{datetime.utcnow()}: Event ID {context['event_id']}: Not making an MWA observation. \n"
        )

    return context["decision"], context["decision_reason_log"]


def trigger_mwa_observation(
    proposal_decision_model,
    decision_reason_log,
    obsname,
    vcsmode=False,
    event_id=None,
    mwa_sub_arrays=None,
    buffered=False,
    pretend=False,
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

    if prop_settings.project_id.password is None:
        return "T", decision_reason_log, [], None

    # Handle early warning events without position using sub arrays
    try:
        if prop_settings.source_type == "GW" and buffered == True and vcsmode == True:
            print("DEBUG - Dumping buffer")
            print("DEBUG - Using nobs = 1, exptime = 8")

            result = trigger(
                project_id=prop_settings.project_id.id,
                secure_key=prop_settings.project_id.password,
                pretend=pretend,
                creator="VOEvent_Auto_Trigger",  # TODO grab version
                obsname=obsname,
                nobs=1,
                # Assume always using 24 contiguous coarse frequency channels
                freqspecs=prop_settings.mwa_freqspecs,
                avoidsun=True,
                inttime=prop_settings.mwa_inttime,
                freqres=prop_settings.mwa_freqres,
                exptime=8,
                vcsmode=vcsmode,
                buffered=buffered,
            )
            print(f"buffered result: {result}")

        elif prop_settings.source_type == "GW" and mwa_sub_arrays != None:
            print("DEBUG - Scheduling an ra/dec sub array observation")

            result = trigger(
                project_id=prop_settings.project_id.id,
                secure_key=prop_settings.project_id.password,
                pretend=pretend,
                subarray_list=["all_ne", "all_nw", "all_se", "all_sw"],
                ra=mwa_sub_arrays["ra"],
                dec=mwa_sub_arrays["dec"],
                creator="VOEvent_Auto_Trigger",  # TODO grab version
                obsname=obsname,
                nobs=1,
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
                creator="VOEvent_Auto_Trigger",  # TODO grab version
                obsname=obsname,
                nobs=1,
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
    except Exception as e:
        print(f"DEGUB - Error exception scheduling observation {e}")
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Exception trying to schedule event {e}\n "
        return "E", decision_reason_log, [], []

    print(f"result: {result}")
    logger.debug(f"result: {result}")
    # Check if succesful
    if result is None:
        print("DEBUG - Error: no result from scheduling observation")
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Web API error, possible server error.\n "
        return "E", decision_reason_log, [], result
    if not result["success"]:
        print("DEBUG - Error: failed to schedule observation")
        # Observation not succesful so record why
        for err_id in result["errors"]:
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: {result['errors'][err_id]}.\n "
        # Return an error as the trigger status
        return "E", decision_reason_log, [], result

    # Output the results
    logger.info(f"Trigger sent: {result['success']}")
    logger.info(f"Trigger params: {result['success']}")
    if "stdout" in result["schedule"].keys():
        if result["schedule"]["stdout"]:
            logger.info(f"schedule' stdout: {result['schedule']['stdout']}")
    if "stderr" in result["schedule"].keys():
        if result["schedule"]["stderr"]:
            logger.info(f"schedule' stderr: {result['schedule']['stderr']}")

    # Grab the obsids (sometimes we will send of several observations)
    obsids = []
    if "obsid_list" in result.keys() and len(result["obsid_list"]) > 0:
        obsids = result["obsid_list"]
    else:
        for r in result["schedule"]["stderr"].split("\n"):
            if r.startswith("INFO:Schedule metadata for"):
                obsids.append(r.split(" for ")[1][:-1])
            elif r.startswith("Pretending: commands not run"):
                obsids.append(f"P{random.randint(1000,9999)}")
    return "T", decision_reason_log, obsids, result


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

    if prop_obj.project_id.password is None:
        return "T", decision_reason_log, []

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
    rapidObj = {"requestDict": rq}
    rapidObj["authenticationToken"] = prop_obj.project_id.password
    rapidObj["email"] = prop_obj.project_id.atca_email
    trigger_real_pretend = TRIGGER_ON[0][0]

    user = ATCAUser.objects.all().first()

    rapidObj["httpAuthUsername"] = user.httpAuthUsername
    rapidObj["httpAuthPassword"] = user.httpAuthPassword

    if prop_obj.testing == trigger_real_pretend:
        rapidObj["test"] = True
        rapidObj["noTimeLimit"] = True
        rapidObj["noScoreLimit"] = True

    request = arrApi.api(rapidObj)
    try:
        response = request.send()
    except Exception as r:
        logger.error(f"ATCA error message: {r}")
        decision_reason_log += (
            f"{datetime.utcnow()}: Event ID {event_id}: ATCA error message: {r}\n "
        )
        return "E", decision_reason_log, []

    # # Check for errors
    # if  (not response["authenticationToken"]["received"]) or (not response["authenticationToken"]["verified"]) or \
    #     (not response["schedule"]["received"]) or (not response["schedule"]["verified"]):
    #     decision_reason_log += f"ATCA return message: {r}\n "
    #     return 'E', decision_reason_log, []

    return "T", decision_reason_log, [response["id"]]


def check_mwa_horizon_and_prepare_context(context):

    proposal_decision_model = context["proposal_decision_model"]
    event_id = context["event_id"]
    decision_reason_log = context["decision_reason_log"]

    if (
        proposal_decision_model.proposal.telescope.name.startswith("MWA")
        and proposal_decision_model.ra
        and proposal_decision_model.dec
    ):
        print("Checking if is above the horizon for MWA")
        # Create Earth location for the telescope
        telescope = proposal_decision_model.proposal.telescope
        location = EarthLocation(
            lon=telescope.lon * u.deg,
            lat=telescope.lat * u.deg,
            height=telescope.height * u.m,
        )
        print("obtained earth location")

        obs_source = SkyCoord(
            proposal_decision_model.ra,
            proposal_decision_model.dec,
            # equinox='J2000',
            unit=(u.deg, u.deg),
        )
        print("obtained obs source location")
        # Convert from RA/Dec to Alt/Az
        obs_source_altaz_beg = obs_source.transform_to(
            AltAz(obstime=Time.now(), location=location)
        )
        alt_beg = obs_source_altaz_beg.alt.deg
        # Calculate alt at end of obs
        end_time = Time.now() + timedelta(
            seconds=proposal_decision_model.proposal.mwa_exptime
        )
        obs_source_altaz_end = obs_source.transform_to(
            AltAz(obstime=end_time, location=location)
        )
        alt_end = obs_source_altaz_end.alt.deg

        print("converted obs for horizon")

        if (
            alt_beg < proposal_decision_model.proposal.mwa_horizon_limit
            and alt_end < proposal_decision_model.proposal.mwa_horizon_limit
        ):
            horizon_message = f"{datetime.utcnow()}: Event ID {event_id}: Not triggering due to horizon limit: alt_beg {alt_beg:.4f} < {proposal_decision_model.proposal.mwa_horizon_limit:.4f} and alt_end {alt_end:.4f} < {proposal_decision_model.proposal.mwa_horizon_limit:.4f}. "
            logger.debug(horizon_message)
            return "I", decision_reason_log + horizon_message

        elif alt_beg < proposal_decision_model.proposal.mwa_horizon_limit:
            # Warn them in the log
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Warning: The source is below the horizion limit at the start of the observation alt_beg {alt_beg:.4f}. \n"

        elif alt_end < proposal_decision_model.proposal.mwa_horizon_limit:
            # Warn them in the log
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Warning: The source will set below the horizion limit by the end of the observation alt_end {alt_end:.4f}. \n"

        # above the horizon so send off telescope specific set ups
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Above horizon so attempting to observe with {proposal_decision_model.proposal.telescope.name}. \n"

        logger.debug(
            f"Triggered observation at an elevation of {alt_beg} to elevation of {alt_end}"
        )

    context["decision_reason_log"] = decision_reason_log
    context["event_id"] = event_id
    context["proposal_decision_model"] = proposal_decision_model

    return context


def prepare_observation_context(context, voevents):

    proposal_decision_model = context["proposal_decision_model"]
    telescopes = context["telescopes"]
    latestVoevent = context["latestVoevent"]

    trigger_both = TRIGGER_ON[1][0]
    trigger_real = TRIGGER_ON[2][0]

    vcsmode = proposal_decision_model.proposal.telescope.name.endswith("VCS")
    if vcsmode:
        print("VCS Mode")

    # Create an observation name
    # Collect event telescopes

    print(proposal_decision_model.trig_id)

    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and seperate with a _
    telescopes = "_".join(list(set(telescopes)))
    obsname = f"{telescopes}_{proposal_decision_model.trig_id}"

    buffered = False

    pretend = True
    repoint = None

    print(
        f"proposal_decision_model.proposal.testing {proposal_decision_model.proposal.testing}"
    )
    print(f"latestVoevent {latestVoevent.__dict__}")
    if (
        latestVoevent.role == "test"
        and proposal_decision_model.proposal.testing != trigger_both
    ):
        raise Exception("Invalid event observation and proposal setting")

    if (
        proposal_decision_model.proposal.testing == trigger_both
        and latestVoevent.role != "test"
    ):
        pretend = False
    if (
        proposal_decision_model.proposal.testing == trigger_real
        and latestVoevent.role != "test"
    ):
        pretend = False
    print(f"pretend: {pretend}")

    context["buffered"] = buffered
    context["pretend"] = pretend
    context["repoint"] = repoint
    context["vcsmode"] = vcsmode
    context["obsname"] = obsname
    context["telescopes"] = telescopes

    return context


def handle_first_event(context):
    context["reason"] = (
        f"{context['latestVoevent'].trig_id} - First event so sending dump MWA buffer request to MWA"
    )
    context[
        "decision_reason_log"
    ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: First event so sending dump MWA buffer request to MWA\n"

    context["buffered"] = True
    context["request_sent_at"] = datetime.utcnow()

    (
        context["decision_buffer"],
        context["decision_reason_log_buffer"],
        context["obsids_buffer"],
        context["result_buffer"],
    ) = trigger_mwa_observation(
        context["proposal_decision_model"],
        context["decision_reason_log"],
        obsname=context["obsname"],
        vcsmode=context["vcsmode"],
        event_id=context["event_id"],
        mwa_sub_arrays=context["mwa_sub_arrays"],
        buffered=context["buffered"],
        pretend=context["pretend"],
    )

    print(f"obsids_buffer: {context['obsids_buffer']}")
    context[
        "decision_reason_log"
    ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Saving buffer observation result.\n"

    if context["decision_buffer"].find("T") > -1:
        context = save_observation(
            context,
            trigger_id=context["result_buffer"]["trigger_id"]
            or random.randrange(10000, 99999),
            obsid=context["obsids_buffer"][0],
            reason="This is a buffer observation ID",
        )

    return context


def save_observation(context, trigger_id, obsid, reason=None):
    """Save the observation result in the Observations model."""
    Observations.objects.create(
        trigger_id=trigger_id,
        telescope=context["proposal_decision_model"].proposal.telescope,
        proposal_decision_id=context["proposal_decision_model"],
        reason=reason or context["reason"],
        mwa_sub_arrays=context["mwa_sub_arrays"],
        website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
        event=context["latestVoevent"],
        mwa_response=context.get("result") or context.get("result_buffer"),
        request_sent_at=context["request_sent_at"],
    )

    return context


def get_default_sub_arrays(ps):
    """Get default sub arrays based on proposal settings."""
    return {
        "dec": [
            getMWARaDecFromAltAz(
                alt=ps.mwa_sub_alt_NE, az=ps.mwa_sub_az_NE, time=Time.now()
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.mwa_sub_alt_NW, az=ps.mwa_sub_az_NW, time=Time.now()
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.mwa_sub_alt_SE, az=ps.mwa_sub_az_SE, time=Time.now()
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.mwa_sub_alt_SW, az=ps.mwa_sub_az_SW, time=Time.now()
            )[1].value,
        ],
        "ra": [
            getMWARaDecFromAltAz(
                alt=ps.mwa_sub_alt_NE, az=ps.mwa_sub_az_NE, time=Time.now()
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.mwa_sub_alt_NW, az=ps.mwa_sub_az_NW, time=Time.now()
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.mwa_sub_alt_SE, az=ps.mwa_sub_az_SE, time=Time.now()
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.mwa_sub_alt_SW, az=ps.mwa_sub_az_SW, time=Time.now()
            )[0].value,
        ],
    }


def handle_early_warning(context):
    """Handle early warning events."""
    ps = context["proposal_decision_model"].proposal
    context["reason"] = (
        f"{context['latestVoevent'].trig_id} - First event is an Early Warning so ignoring skymap"
    )
    context["mwa_sub_arrays"] = get_default_sub_arrays(ps)

    timeDiff = datetime.now(timezone.utc) - context["latestVoevent"].event_observed

    if timeDiff.total_seconds() < ps.early_observation_time_seconds:
        estObsTime = round_to_nearest_modulo_8(
            ps.early_observation_time_seconds - timeDiff.total_seconds()
        )
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Event time was {timeDiff.total_seconds()} seconds ago, early observation proposal setting is {ps.early_observation_time_seconds} seconds so making an observation of {estObsTime} seconds.\n"
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Sending observation request to MWA.\n"
        context["request_sent_at"] = datetime.utcnow()

        (
            context["decision"],
            context["decision_reason_log_obs"],
            context["obsids"],
            context["result"],
        ) = trigger_mwa_observation(
            context["proposal_decision_model"],
            context["decision_reason_log"],
            obsname=context["obsname"],
            vcsmode=context["vcsmode"],
            event_id=context["event_id"],
            mwa_sub_arrays=context["mwa_sub_arrays"],
            pretend=context["pretend"],
        )

        print(f"result: {context['result']}")
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Saving observation result.\n"

        if context["decision"].find("T") > -1:
            context = save_observation(
                context,
                trigger_id=context["result"]["trigger_id"]
                or random.randrange(10000, 99999),
                obsid=context["obsids"][0],
            )

    return context


def get_skymap_pointings(skymap_fits):
    """Download and process skymap FITS file to get pointings."""
    event_filename = download_file(skymap_fits, cache=True)
    skymap = Table.read(event_filename)
    (skymap, time, pointings) = getMWAPointingsFromSkymapFile(skymap)
    return skymap, pointings


def get_skymap_pointings_from_cache(skymap_fits):
    skymap = Table.read(skymap_fits)
    (skymap, time, pointings) = getMWAPointingsFromSkymapFile(skymap)
    return skymap, pointings


def generate_sub_arrays_from_skymap(pointings):
    """Generate sub arrays from skymap pointings."""
    return {
        "dec": [pointings[i][4].value for i in range(4)],
        "ra": [pointings[i][3].value for i in range(4)],
    }


def handle_skymap_event(context):
    """Handle events with skymap data."""
    context["reason"] = f"{context['latestVoevent'].trig_id} - Event contains a skymap"
    print(f"DEBUG - skymap_fits_fits: {context['latestVoevent'].lvc_skymap_fits}")

    try:
        skymap, pointings = get_skymap_pointings(
            context["latestVoevent"].lvc_skymap_fits
        )
        context["mwa_sub_arrays"] = generate_sub_arrays_from_skymap(pointings)

        time_diff = datetime.now(timezone.utc) - context["latestVoevent"].event_observed

        print(f"timediff - {time_diff}")
        print(time_diff.total_seconds())
        print(
            context["proposal_decision_model"].proposal.maximum_observation_time_seconds
        )

        if (
            time_diff.total_seconds()
            < context[
                "proposal_decision_model"
            ].proposal.maximum_observation_time_seconds
        ):
            est_obs_time = round_to_nearest_modulo_8(
                context[
                    "proposal_decision_model"
                ].proposal.maximum_observation_time_seconds
                - time_diff.total_seconds()
            )
            context["proposal_decision_model"].proposal.mwa_nobs = floor(
                est_obs_time / context["proposal_decision_model"].proposal.mwa_exptime
            )
            context[
                "decision_reason_log"
            ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Event time was {time_diff.total_seconds()} seconds ago, maximum_observation_time_seconds is {context['proposal_decision_model'].proposal.maximum_observation_time_seconds} seconds so making an observation of {est_obs_time} seconds.\n"
            context[
                "decision_reason_log"
            ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Sending sub array observation request to MWA.\n"
            context["request_sent_at"] = datetime.utcnow()

            (
                context["decision"],
                context["decision_reason_log_obs"],
                context["obsids"],
                context["result"],
            ) = trigger_mwa_observation(
                context["proposal_decision_model"],
                context["decision_reason_log"],
                obsname=context["obsname"],
                vcsmode=context["vcsmode"],
                event_id=context["event_id"],
                mwa_sub_arrays=context["mwa_sub_arrays"],
                pretend=context["pretend"],
            )

            print(f"result: {context['result']}")
            context[
                "decision_reason_log"
            ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Saving observation result.\n"

            if context["decision"].find("T") > -1:
                save_observation(
                    context,
                    trigger_id=context["result"]["trigger_id"]
                    or random.randrange(10000, 99999),
                    obsid=context["obsids"][0],
                )

        else:
            context["decision_reason_log"] = (
                f"{context['decision_reason_log']}{datetime.utcnow()}: Event ID {context['event_id']}: Event time was {time_diff.total_seconds()} seconds ago, maximum_observation_time_second is {context['proposal_decision_model'].proposal.maximum_observation_time_seconds} so not making an observation \n"
            )

    except Exception as e:
        print(e)
        logger.error("Error getting MWA pointings from skymap")
        logger.error(e)


def get_latest_observation(proposal_decision_model):
    """Retrieve the latest observation for the given telescope."""
    return (
        Observations.objects.filter(
            telescope=proposal_decision_model.proposal.telescope
        )
        .order_by("-created_at")
        .first()
    )


def update_position_based_on_skymap(context, latest_obs):
    """Update observation position based on the new skymap."""
    skymap, pointings = get_skymap_pointings_from_cache(
        context["latestVoevent"].lvc_skymap_fits
    )
    print("DEBUG - pointings : ", pointings)
    current_arrays_dec = latest_obs.mwa_sub_arrays["dec"]
    current_arrays_ra = latest_obs.mwa_sub_arrays["ra"]

    repoint = should_repoint(current_arrays_ra, current_arrays_dec, pointings)
    print(f"DEBUG - repoint: {repoint}")

    if repoint:
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: New skymap is more than 4 degrees of previous observation pointing. \n"
        context["reason"] = (
            f"{context['latestVoevent'].trig_id} - Updating observation positions based on event."
        )
        context["mwa_sub_arrays"] = generate_sub_arrays_from_skymap(pointings)

        trigger_and_save_observation(context)
    else:
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: New skymap is NOT more than 4 degrees of previous observation pointing. \n"
        return "T", context["decision_reason_log"]


def should_repoint(current_arrays_ra, current_arrays_dec, pointings):
    """Determine whether repointing is necessary based on the new skymap."""
    repoint = False

    pointings_dec = []
    pointings_ra = []
    for res in pointings:
        pointings_ra.append(res[3])
        pointings_dec.append(res[4])

        repoint = True
        for index, val in enumerate(current_arrays_dec):
            print(f"index: {index}")
            ra1 = current_arrays_ra[index] * u.deg
            dec1 = current_arrays_dec[index] * u.deg
            ra2 = res[3]
            dec2 = res[4]

            if isClosePosition(ra1, dec1, ra2, dec2):
                repoint = False

    print(f"DEBUG - current_arrays_dec : {current_arrays_dec}")
    print(f"DEBUG - pointings_dec : {pointings_dec}")
    print(f"DEBUG - current_arrays_ra : {current_arrays_ra}")
    print(f"DEBUG - pointings_ra : {pointings_ra}")

    return repoint


def trigger_and_save_observation(context):
    """Trigger an observation and save the result."""
    context[
        "decision_reason_log"
    ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Sending sub array observation request to MWA\n"
    context["request_sent_at"] = datetime.utcnow()

    (
        context["decision"],
        context["decision_reason_log_obs"],
        context["obsids"],
        context["result"],
    ) = trigger_mwa_observation(
        context["proposal_decision_model"],
        context["decision_reason_log"],
        obsname=context["obsname"],
        vcsmode=context["vcsmode"],
        event_id=context["event_id"],
        mwa_sub_arrays=context["mwa_sub_arrays"],
        pretend=context["pretend"],
    )

    print(f"result: {context['result']}")
    context[
        "decision_reason_log"
    ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Saving observation result. \n"
    context["request_sent_at"] = datetime.utcnow()

    if context["decision"].find("T") > -1:
        save_observation(
            context,
            trigger_id=context["result"]["trigger_id"]
            or random.randrange(10000, 99999),
            obsid=context["obsids"][0],
        )

    return context


def handle_non_gw_observation(context):
    """Handle the logic for non-GW observations."""
    if context["proposal_decision_model"].proposal.source_type != "GW":
        print("DEBUG - Not a GW so ignoring GW logic")

        (
            context["decision"],
            context["decision_reason_log_obs"],
            context['obsids'],
            context['result'],
        ) = trigger_mwa_observation(
            context["proposal_decision_model"],
            context["decision_reason_log"],
            obsname=context["obsname"],
            vcsmode=context["vcsmode"],
            event_id=context["event_id"],
            mwa_sub_arrays=context["mwa_sub_arrays"],
            pretend=context["pretend"],
        )

        print(f"result: {context['result']}")
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Saving observation result.\n"
        context["request_sent_at"] = datetime.utcnow()

        if context["decision"].find("T") > -1:
            save_observation(
                context,
                trigger_id=context["result"]["trigger_id"]
                or random.randrange(10000, 99999),
                obsid=context["obsids"][0],
                reason=context["reason"],
            )

    return context


def handle_atca_observation(context):
    """Handle the logic for ATCA observations."""
    if context["proposal_decision_model"].proposal.telescope.name == "ATCA":
        obsname = f"{context['proposal_decision_model'].trig_id}"
        (context["decision"], context["decision_reason_log"], context["obsids"]) = (
            trigger_atca_observation(
                context["proposal_decision_model"],
                context["decision_reason_log"],
                obsname,
                event_id=context["event_id"],
            )
        )

        context = save_atca_observations(context)

    return context


def save_atca_observations(context):
    """Save the ATCA observation results."""
    for obsid in context["obsids"]:
        Observations.objects.create(
            trigger_id=obsid,
            telescope=context["proposal_decision_model"].proposal.telescope,
            proposal_decision_id=context["proposal_decision_model"],
            reason=context["reason"],
            event=context["latestVoevent"],
            # TODO see if ATCA has a nice observation details webpage
            # website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
        )

        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Saving observation result for ATCA.\n"
        context["request_sent_at"] = datetime.utcnow()

    return context
