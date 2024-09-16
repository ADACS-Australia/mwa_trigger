import logging
import os
import random
import urllib.request
from datetime import datetime, timedelta, timezone
from math import floor
from random import randint

import astropy.units as u
import atca_rapid_response_api as arrApi
import requests
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.table import Table
from astropy.time import Time
from astropy.utils.data import download_file
from django.conf import settings
from django.core.files import File

# ATCAUser, Observations
from propsettings_app.utils.utils_telescope import (
    getMWAPointingsFromSkymapFile,
    getMWARaDecFromAltAz,
    isClosePosition,
    subArrayMWAPointings,
)

from ..consts import DEFAULT_MWA_RESPONSE
from ..models import TRIGGER_ON
from ..schemas import (
    EventSchema,
    LatestObservationSchema,
    MWAResponseSchema,
    MWASubArraysSchema,
    ObservationSchema,
    ProposalDecisionSchema,
    TelescopeSchema,
)
from .utils_triggerservice import trigger

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


def check_mwa_horizon_and_prepare_context(context):

    proposal_decision_model = context["proposal_decision_model"]
    event_id = context["event_id"]
    decision_reason_log = context["decision_reason_log"]

    if (
        proposal_decision_model.proposal.telescope_settings.telescope.name.startswith(
            "MWA"
        )
        and proposal_decision_model.ra
        and proposal_decision_model.dec
    ):
        print("Checking if is above the horizon for MWA")
        # Create Earth location for the telescope
        telescope = proposal_decision_model.proposal.telescope_settings.telescope
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
            seconds=proposal_decision_model.proposal.telescope_settings.mwa_exptime
        )
        obs_source_altaz_end = obs_source.transform_to(
            AltAz(obstime=end_time, location=location)
        )
        alt_end = obs_source_altaz_end.alt.deg

        print("converted obs for horizon")

        if (
            alt_beg
            < proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit
            and alt_end
            < proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit
        ):
            horizon_message = f"{datetime.utcnow()}: Event ID {event_id}: Not triggering due to horizon limit: alt_beg {alt_beg:.4f} < {proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit:.4f} and alt_end {alt_end:.4f} < {proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit:.4f}. "
            logger.debug(horizon_message)

            context["stop_processing"] = True
            context["decision_reason_log"] = decision_reason_log + horizon_message
            context["decision"] = "I"
            return context

        elif (
            alt_beg
            < proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit
        ):
            # Warn them in the log
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Warning: The source is below the horizion limit at the start of the observation alt_beg {alt_beg:.4f}. \n"

        elif (
            alt_end
            < proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit
        ):
            # Warn them in the log
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Warning: The source will set below the horizion limit by the end of the observation alt_end {alt_end:.4f}. \n"

        # above the horizon so send off telescope specific set ups
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Above horizon so attempting to observe with {proposal_decision_model.proposal.telescope_settings.telescope.name}. \n"

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

    vcsmode = (
        proposal_decision_model.proposal.telescope_settings.telescope.name.endswith(
            "VCS"
        )
    )
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
    # print(f"latestVoevent {latestVoevent.__dict__}")
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

    # return "T", decision_reason_log, [], {}

    prop_settings = proposal_decision_model.proposal
    print("DEBUG - triggering MWA")
    print(f"DEBUG - proposal: {prop_settings.__dict__}")
    # Not below horizon limit so observer
    logger.info(f"Triggering MWA at UTC time {Time.now()} ...")

    # if True:
    #     return "T", decision_reason_log, [], None

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
                freqspecs=prop_settings.telescope_settings.mwa_freqspecs,
                avoidsun=True,
                inttime=prop_settings.telescope_settings.mwa_inttime,
                freqres=prop_settings.telescope_settings.mwa_freqres,
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
                freqspecs=prop_settings.telescope_settings.mwa_freqspecs,
                avoidsun=True,
                inttime=prop_settings.telescope_settings.mwa_inttime,
                freqres=prop_settings.telescope_settings.mwa_freqres,
                exptime=prop_settings.telescope_settings.mwa_exptime,
                calibrator=True,
                calexptime=prop_settings.telescope_settings.mwa_calexptime,
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
                freqspecs=prop_settings.telescope_settings.mwa_freqspecs,
                avoidsun=True,
                inttime=prop_settings.telescope_settings.mwa_inttime,
                freqres=prop_settings.telescope_settings.mwa_freqres,
                exptime=prop_settings.telescope_settings.mwa_exptime,
                calibrator=True,
                calexptime=prop_settings.telescope_settings.mwa_calexptime,
                vcsmode=vcsmode,
            )
    except Exception as e:
        print(f"DEBUG - Error exception scheduling observation {e}")
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

    # TODO please remove it when not testing it
    # result = DEFAULT_MWA_RESPONSE
    return "T", decision_reason_log, obsids, result


def save_mwa_observation(context, trigger_id, obsid, reason=None):
    """Save the observation result through the API."""
    print("DEBUG - saving MWA observation")

    api_url = f"http://web:8000/api/create-observation/"
    trigger_id = str(random.randrange(10000, 99999))

    # Prepare the payload
    payload = {
        "trigger_id": trigger_id,
        "telescope_name": context[
            "proposal_decision_model"
        ].proposal.telescope_settings.telescope.name,
        "proposal_decision_id": context["proposal_decision_model"].id,
        "event_id": context["latestVoevent"].id,
        "reason": reason or context["reason"],
        "website_link": f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
        # "mwa_response": context.get("result") or context.get("result_buffer"),
        "request_sent_at": (
            context["request_sent_at"].isoformat()
            if context["request_sent_at"]
            else None
        ),
        "mwa_sub_arrays": (
            context.get("mwa_sub_arrays") if context.get("mwa_sub_arrays") else None
        ),
        "mwa_sky_map_pointings": (
            context.get("mwa_sky_map_pointings")
            if context.get("mwa_sky_map_pointings")
            else None
        ),
    }

    print("DEBUG - payload starts: \n")
    print(payload)
    print("DEBUG - payload ends \n")

    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Observation created: {result}")

    except requests.RequestException as e:
        print(f"Error creating observation: {e}")

    return result


def handle_first_observation(context):
    "Handle the first observation of an event."
    print("DEBUG - handle_first_observation")
    if context["stop_processing"]:
        return context

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
        saved_obs_1 = save_mwa_observation(
            context,
            trigger_id=context["result_buffer"]["trigger_id"]
            or random.randrange(10000, 99999),
            obsid=context["obsids_buffer"][0],
            reason="This is a buffer observation ID",
        )
        print(saved_obs_1)
        # TODO: ask if we should stop triggering the subsequent events
        # context["stop_processing"] = True

    return context


def get_default_sub_arrays(ps):
    """Get default sub arrays based on proposal settings."""
    return {
        "dec": [
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_NE,
                az=ps.telescope_settings.mwa_sub_az_NE,
                time=Time.now(),
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_NW,
                az=ps.telescope_settings.mwa_sub_az_NW,
                time=Time.now(),
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_SE,
                az=ps.telescope_settings.mwa_sub_az_SE,
                time=Time.now(),
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_SW,
                az=ps.telescope_settings.mwa_sub_az_SW,
                time=Time.now(),
            )[1].value,
        ],
        "ra": [
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_NE,
                az=ps.telescope_settings.mwa_sub_az_NE,
                time=Time.now(),
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_NW,
                az=ps.telescope_settings.mwa_sub_az_NW,
                time=Time.now(),
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_SE,
                az=ps.telescope_settings.mwa_sub_az_SE,
                time=Time.now(),
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_SW,
                az=ps.telescope_settings.mwa_sub_az_SW,
                time=Time.now(),
            )[0].value,
        ],
    }


def handle_early_warning(context):
    """Handle early warning events."""

    if context["stop_processing"]:
        return context

    ps = context["proposal_decision_model"].proposal
    context["reason"] = (
        f"{context['latestVoevent'].trig_id} - First event is an Early Warning so ignoring skymap"
    )
    context["mwa_sub_arrays"] = get_default_sub_arrays(ps)

    timeDiff = datetime.now(timezone.utc) - context[
        "latestVoevent"
    ].event_observed.replace(tzinfo=timezone.utc)

    # TODO: correct this logic after testing
    print(
        f"DEBUG - ps.source_settings.early_observation_time_seconds: {ps.source_settings.early_observation_time_seconds}"
    )
    print(f"DEBUG - timeDiff.total_seconds(): {timeDiff.total_seconds()}")

    if timeDiff.total_seconds() < ps.source_settings.early_observation_time_seconds:
        estObsTime = round_to_nearest_modulo_8(
            ps.source_settings.early_observation_time_seconds - timeDiff.total_seconds()
        )
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Event time was {timeDiff.total_seconds()} seconds ago, early observation proposal setting is {ps.source_settings.early_observation_time_seconds} seconds so making an observation of {estObsTime} seconds.\n"
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
            saved_obs_2 = save_mwa_observation(
                context,
                trigger_id=context["result"]["trigger_id"]
                or random.randrange(10000, 99999),
                obsid=context["obsids"][0],
            )
            # TODO: ask if we should stop triggering the subsequent events
            # context["stop_processing"] = True

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

    if context["stop_processing"]:
        return context

    context["reason"] = f"{context['latestVoevent'].trig_id} - Event contains a skymap"
    print(f"DEBUG - skymap_fits_fits: {context['latestVoevent'].lvc_skymap_fits}")

    try:
        skymap, pointings = get_skymap_pointings(
            context["latestVoevent"].lvc_skymap_fits
        )
        context["mwa_sub_arrays"] = generate_sub_arrays_from_skymap(pointings)

        time_diff = datetime.now(timezone.utc) - context[
            "latestVoevent"
        ].event_observed.replace(tzinfo=timezone.utc)

        print(f"timediff - {time_diff}")
        print(time_diff.total_seconds())
        print(
            context[
                "proposal_decision_model"
            ].proposal.telescope_settings.maximum_observation_time_seconds
        )

        if (
            time_diff.total_seconds()
            < context[
                "proposal_decision_model"
            ].proposal.telescope_settings.maximum_observation_time_seconds
        ):
            est_obs_time = round_to_nearest_modulo_8(
                context[
                    "proposal_decision_model"
                ].proposal.telescope_settings.maximum_observation_time_seconds
                - time_diff.total_seconds()
            )
            # TODO mwa_nobs was never declared in the models.py
            # if time_diff.total_seconds() < proposal.telescope_settings.maximum_observation_time_seconds
            # it should work and crushed
            context["proposal_decision_model"].proposal.telescope_settings.mwa_nobs = (
                floor(
                    est_obs_time
                    / context[
                        "proposal_decision_model"
                    ].proposal.telescope_settings.mwa_exptime
                )
            )

            print(
                f"DEBUG - mwa_nobs: {context['proposal_decision_model'].proposal.telescope_settings.mwa_nobs}"
            )

            context[
                "decision_reason_log"
            ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Event time was {time_diff.total_seconds()} seconds ago, maximum_observation_time_seconds is {context['proposal_decision_model'].proposal.telescope_settings.maximum_observation_time_seconds} seconds so making an observation of {est_obs_time} seconds.\n"
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
                saved_obs_2 = save_mwa_observation(
                    context,
                    trigger_id=context["result"]["trigger_id"]
                    or random.randrange(10000, 99999),
                    obsid=context["obsids"][0],
                )

                # TODO: ask if we should stop triggering the subsequent events
                # context["stop_processing"] = True

        else:
            context["decision_reason_log"] = (
                f"{context['decision_reason_log']}{datetime.utcnow()}: Event ID {context['event_id']}: Event time was {time_diff.total_seconds()} seconds ago, maximum_observation_time_second is {context['proposal_decision_model'].proposal.telescope_settings.maximum_observation_time_seconds} so not making an observation \n"
            )

    except Exception as e:
        print(e)
        logger.error("Error getting MWA pointings from skymap")
        logger.error(e)

    return context


def get_latest_observation(proposal_decision_model):
    """Retrieve the latest observation for the given telescope via API."""
    telescope_id = proposal_decision_model.proposal.telescope_settings.telescope.name
    api_url = f"http://web:8000/api/latest-observation/{telescope_id}/"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        observation_data = response.json()

        # Create and return a Pydantic instance
        return LatestObservationSchema.parse_obj(observation_data)
    except requests.RequestException as e:
        print(f"Error fetching latest observation: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing observation data: {e}")
        return None


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

    if context["stop_processing"]:
        return context

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
        saved_obs_2 = save_mwa_observation(
            context,
            trigger_id=context["result"]["trigger_id"]
            or random.randrange(10000, 99999),
            obsid=context["obsids"][0],
        )
        # TODO: ask if we should stop triggering the subsequent events
        # context["stop_processing"] = True

    return context


def update_position_based_on_skymap(context, latest_obs):
    """Update observation position based on the new skymap."""
    print("DEBUG - update_position_based_on_skymap : start")
    if context["stop_processing"]:
        return context

    skymap, pointings = get_skymap_pointings_from_cache(
        context["latestVoevent"].lvc_skymap_fits
    )
    print("DEBUG - pointings : ", pointings)
    print("DEBUG - latest_obs.mwa_sub_arrays : ", latest_obs.mwa_sub_arrays)

    current_arrays_dec = latest_obs.mwa_sub_arrays.dec
    current_arrays_ra = latest_obs.mwa_sub_arrays.ra

    repoint = should_repoint(current_arrays_ra, current_arrays_dec, pointings)
    print(f"DEBUG - repoint: {repoint}")

    # TODO comment when stop testing
    # repoint = True
    if repoint:
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: New skymap is more than 4 degrees of previous observation pointing. \n"
        context["reason"] = (
            f"{context['latestVoevent'].trig_id} - Updating observation positions based on event."
        )
        context["mwa_sub_arrays"] = generate_sub_arrays_from_skymap(pointings)

        context = trigger_and_save_observation(context)
    else:
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: New skymap is NOT more than 4 degrees of previous observation pointing. \n"

        # TODO : check if its right
        context["decision"] = "T"
        context["stop_processing"] = True
        # return "T", context["decision_reason_log"]

    print("DEBUG - update_position_based_on_skymap : end")
    return context


def handle_gw_voevents(context):

    if context["stop_processing"]:
        return context

    print(f"DEBUG - checking to repoint")
    context["reason"] = f"{context['latestVoevent'].trig_id} - Event has a skymap"

    latest_obs = get_latest_observation(context["proposal_decision_model"])

    print("DEBUG - latest_obs : ", latest_obs)

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

    return context


def handle_non_gw_observation(context):
    """Handle the logic for non-GW observations."""
    if context["stop_processing"]:
        return context

    if context["proposal_decision_model"].proposal.source_type != "GW":
        print("DEBUG - Not a GW so ignoring GW logic")

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
        context["request_sent_at"] = datetime.utcnow()

        if context["decision"].find("T") > -1:
            saved_obs = save_mwa_observation(
                context,
                trigger_id=context["result"]["trigger_id"]
                or random.randrange(10000, 99999),
                obsid=context["obsids"][0],
                reason=context["reason"],
            )

            # TODO: ask if we should stop triggering the subsequent events
            # context["stop_processing"] = True

    return context


############################################ ATCA #######################################################
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
        "maxExposureLength": str(
            timedelta(minutes=prop_obj.telescope_settings.atca_max_exptime)
        ),
        "minExposureLength": str(
            timedelta(minutes=prop_obj.telescope_settings.atca_min_exptime)
        ),
        "scanType": "Dwell",
        "3mm": {
            "use": prop_obj.telescope_settings.atca_band_3mm,
            "exposureLength": str(
                timedelta(minutes=prop_obj.telescope_settings.atca_band_3mm_exptime)
            ),
            "freq1": prop_obj.telescope_settings.atca_band_3mm_freq1,
            "freq2": prop_obj.telescope_settings.atca_band_3mm_freq2,
        },
        "7mm": {
            "use": prop_obj.telescope_settings.atca_band_7mm,
            "exposureLength": str(
                timedelta(minutes=prop_obj.telescope_settings.atca_band_7mm_exptime)
            ),
            "freq1": prop_obj.telescope_settings.atca_band_7mm_freq1,
            "freq2": prop_obj.telescope_settings.atca_band_7mm_freq2,
        },
        "15mm": {
            "use": prop_obj.telescope_settings.atca_band_15mm,
            "exposureLength": str(
                timedelta(minutes=prop_obj.telescope_settings.atca_band_15mm_exptime)
            ),
            "freq1": prop_obj.telescope_settings.atca_band_15mm_freq1,
            "freq2": prop_obj.telescope_settings.atca_band_15mm_freq2,
        },
        "4cm": {
            "use": prop_obj.telescope_settings.atca_band_4cm,
            "exposureLength": str(
                timedelta(minutes=prop_obj.telescope_settings.atca_band_4cm_exptime)
            ),
            "freq1": prop_obj.telescope_settings.atca_band_4cm_freq1,
            "freq2": prop_obj.telescope_settings.atca_band_4cm_freq2,
        },
        "16cm": {
            "use": prop_obj.telescope_settings.atca_band_16cm,
            "exposureLength": str(
                timedelta(minutes=prop_obj.telescope_settings.atca_band_16cm_exptime)
            ),
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

    # user = ATCAUser.objects.all().first()

    # rapidObj["httpAuthUsername"] = user.httpAuthUsername
    # rapidObj["httpAuthPassword"] = user.httpAuthPassword

    rapidObj["httpAuthUsername"] = "TestUser"
    rapidObj["httpAuthPassword"] = "TestPassword"

    rapidObj["serverProtocol"] = "http://"
    rapidObj["serverName"] = "test-api:8000"
    rapidObj["apiEndpoint"] = "/api/atca_proposal_request/"

    if prop_obj.testing == trigger_real_pretend:
        rapidObj["test"] = True
        rapidObj["noTimeLimit"] = True
        rapidObj["noScoreLimit"] = True

    print("DEBUG - rapidObj : ", rapidObj)
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


def save_atca_observation(context, trigger_id, reason=None):
    """Save the observation result through the API."""
    print("DEBUG - saving ATCA observation")

    api_url = f"http://web:8000/api/create-observation/"
    # trigger_id = str(random.randrange(10000, 99999))

    # Prepare the payload
    payload = {
        "trigger_id": trigger_id,
        "telescope_name": context[
            "proposal_decision_model"
        ].proposal.telescope_settings.telescope.name,
        "proposal_decision_id": context["proposal_decision_model"].id,
        "event_id": context["latestVoevent"].id,
        "reason": reason or context["reason"],
    }

    print("DEBUG - payload starts: \n")
    print(payload)
    print("DEBUG - payload ends \n")

    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Observation created: {result}")

    except requests.RequestException as e:
        print(f"Error creating observation: {e}")

    return result


def save_atca_observations(context):
    """Save the ATCA observation results."""
    print("DEBUG - saving ATCA observations")
    for obsid in context["obsids"]:
        saved_atca_obs = save_atca_observation(
            context,
            trigger_id=obsid,
            # TODO see if ATCA has a nice observation details webpage
            # website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
        )

        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event_id']}: Saving observation result for ATCA.\n"
        context["request_sent_at"] = datetime.utcnow()

        # TODO: ask if we should stop triggering the subsequent events
        # context["stop_processing"] = True

    return context


def handle_atca_observation(context):
    """Handle the logic for ATCA observations."""
    if context["stop_processing"]:
        return context

    if (
        context["proposal_decision_model"].proposal.telescope_settings.telescope.name
        == "ATCA"
    ):
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
