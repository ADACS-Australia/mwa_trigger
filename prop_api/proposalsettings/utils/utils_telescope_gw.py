import datetime as dt
import logging
import random
from datetime import datetime, timezone
from math import floor

from .utils_helper import *
from .utils_log import log_event

json_logger = logging.getLogger("django_json")


@log_event(log_location="end",message=f"Handled the first observation of an event.", level="debug")
def handle_first_observation(telescope_settings, context):
    "Handle the first observation of an event."

    if context["stop_processing"]:
        return context

    print("DEBUG - handle_first_observation")

    context["reason"] = (
        f"{context['latestVoevent'].trig_id} - First event so sending dump MWA buffer request to MWA"
    )
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: First event so sending dump MWA buffer request to MWA\n"

    context["buffered"] = True
    context["request_sent_at"] = datetime.now(dt.timezone.utc)

    (
        context["decision_buffer"],
        context["decision_reason_log_buffer"],
        context["obsids_buffer"],
        context["result_buffer"],
    ) = telescope_settings.trigger_telescope(context)

    print(f"obsids_buffer: {context['obsids_buffer']}")
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Saving buffer observation result.\n"


    if context["decision_buffer"].find("T") > -1:
        saved_obs_1 = telescope_settings.save_observation(
            context,
            trigger_id=context["result_buffer"]["trigger_id"]
            or random.randrange(10000, 99999),
            obsid=context["obsids_buffer"][0],
            reason="This is a buffer observation ID",
        )
        
        # TODO: ask if we should stop triggering the subsequent events
        # context["stop_processing"] = True
        
    context["reached_end"] = True

    return context


@log_event(log_location="end",message=f"Handled early warning events.", level="debug")
def handle_early_warning(telescope_settings, context):
    """Handle early warning events."""

    if context["stop_processing"]:
        return context

    ps = context["prop_dec"].proposal
    context["reason"] = (
        f"{context['latestVoevent'].trig_id} - First event is an Early Warning so ignoring skymap"
    )
    context["mwa_sub_arrays"] = get_default_sub_arrays(ps)

    timeDiff = datetime.now(timezone.utc) - context[
        "latestVoevent"
    ].event_observed.replace(tzinfo=timezone.utc)

    print(
        f"DEBUG - ps.source_settings.early_observation_time_seconds: {ps.source_settings.early_observation_time_seconds}"
    )
    print(f"DEBUG - timeDiff.total_seconds(): {timeDiff.total_seconds()}")
    
    if timeDiff.total_seconds() >= ps.source_settings.early_observation_time_seconds:
        return context

    # if timeDiff.total_seconds() < ps.source_settings.early_observation_time_seconds:
    estObsTime = round_to_nearest_modulo_8(
        ps.source_settings.early_observation_time_seconds - timeDiff.total_seconds()
    )
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Event time was {timeDiff.total_seconds()} seconds ago, early observation proposal setting is {ps.source_settings.early_observation_time_seconds} seconds so making an observation of {estObsTime} seconds.\n"
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Sending observation request to MWA.\n"
    context["request_sent_at"] = datetime.now(dt.timezone.utc)

    (
        context["decision"],
        context["decision_reason_log_obs"],
        context["obsids"],
        context["result"],
    ) = telescope_settings.trigger_telescope(context)

    
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Saving observation result.\n"


    if context["decision"].find("T") > -1:
        saved_obs_2 = telescope_settings.save_observation(
            context,
            trigger_id=context["result"]["trigger_id"]
            or random.randrange(10000, 99999),
            obsid=context["obsids"][0],
        )
        # TODO: ask if we should stop triggering the subsequent events
        # context["stop_processing"] = True
        
    context["reached_end"] = True

    return context

@log_event(log_location="end",message=f"Handled events with skymap data.", level="debug")
def handle_skymap_event(telescope_settings, context):
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
                "prop_dec"
            ].proposal.telescope_settings.maximum_observation_time_seconds
        )

        if (
            time_diff.total_seconds()
            < context[
                "prop_dec"
            ].proposal.telescope_settings.maximum_observation_time_seconds
        ):
            est_obs_time = round_to_nearest_modulo_8(
                context[
                    "prop_dec"
                ].proposal.telescope_settings.maximum_observation_time_seconds
                - time_diff.total_seconds()
            )
        
            # if time_diff.total_seconds() < proposal.telescope_settings.maximum_observation_time_seconds
            # it should work and crushed
            context["prop_dec"].proposal.telescope_settings.mwa_nobs = (
                floor(
                    est_obs_time
                    / context[
                        "prop_dec"
                    ].proposal.telescope_settings.mwa_exptime
                )
            )

            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Event time was {time_diff.total_seconds()} seconds ago, maximum_observation_time_seconds is {context['prop_dec'].proposal.telescope_settings.maximum_observation_time_seconds} seconds so making an observation of {est_obs_time} seconds.\n"
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Sending sub array observation request to MWA.\n"
            context["request_sent_at"] = datetime.now(dt.timezone.utc)

            (
                context["decision"],
                context["decision_reason_log_obs"],
                context["obsids"],
                context["result"],
            ) = telescope_settings.trigger_telescope(context)

            # print(f"result: {context['result']}")
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Saving observation result.\n"

            if context["decision"].find("T") > -1:
                saved_obs_2 = telescope_settings.save_observation(
                    context,
                    trigger_id=context["result"]["trigger_id"]
                    or random.randrange(10000, 99999),
                    obsid=context["obsids"][0],
                )

                # TODO: ask if we should stop triggering the subsequent events
                # context["stop_processing"] = True

        else:
            context["decision_reason_log"] = (
                f"{context['decision_reason_log']}{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Event time was {time_diff.total_seconds()} seconds ago, maximum_observation_time_second is {context['prop_dec'].proposal.telescope_settings.maximum_observation_time_seconds} so not making an observation \n"
            )

    except Exception as e:
        print(e)
        logger.error("Error getting MWA pointings from skymap")
        logger.error(e)

        json_logger.error(
            f"Error getting MWA pointings from skymap",
            extra={
                "function": "handle_skymap_event",
                "trig_id": context["prop_dec"].trig_id,
                "event_id": context["event_id"],
            },
        )

    context["reached_end"] = True
    
    return context


@log_event(log_location="end",message=f"Trigger and save gw voevents.", level="debug")
def trigger_and_save_gw_voevents(telescope_settings, context):

    if context["stop_processing"]:
        return context

    if context["repoint"] is False:
        return context

    """Trigger an observation and save the result."""
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Sending sub array observation request to MWA\n"
    context["request_sent_at"] = datetime.now(dt.timezone.utc)

    (
        context["decision"],
        context["decision_reason_log_obs"],
        context["obsids"],
        context["result"],
    ) = telescope_settings.trigger_telescope(context)

    # print(f"result: {context['result']}")
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Saving observation result. \n"
    context["request_sent_at"] = datetime.now(dt.timezone.utc)


    if context["decision"].find("T") > -1:
        saved_obs_2 = telescope_settings.save_observation(
            context,
            trigger_id=context["result"]["trigger_id"]
            or random.randrange(10000, 99999),
            obsid=context["obsids"][0],
        )
        # TODO: ask if we should stop triggering the subsequent events
        # context["stop_processing"] = True

    context["reached_end"] = True
    return context

@log_event(log_location="end",message=f"Update observation position based on the new skymap.", level="debug")
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

    if repoint is False:
        context[
            "decision_reason_log"
        ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: New skymap is NOT more than 4 degrees of previous observation pointing. \n"

        # TODO : ask if its right
        context["decision"] = "T"
        context["stop_processing"] = True
        context["repoint"] = False

        context["reached_end"] = True
        return context

    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: New skymap is more than 4 degrees of previous observation pointing. \n"
    context["reason"] = (
        f"{context['latestVoevent'].trig_id} - Updating observation positions based on event."
    )
    context["mwa_sub_arrays"] = generate_sub_arrays_from_skymap(pointings)

    context["repoint"] = True

    print("DEBUG - update_position_based_on_skymap : end")
    
    context["reached_end"] = True
    
    return context

@log_event(log_location="end",message=f"Handle gw voevents.", level="debug")
def handle_gw_voevents(telescope_settings, context, latest_obs):

    if context["stop_processing"]:
        return context

    # print(f"DEBUG - checking to repoint")
    # context["reason"] = f"{context['latestVoevent'].trig_id} - Event has a skymap"
    # latest_obs = get_latest_observation(context["prop_dec"])
    # print("DEBUG - latest_obs : ", latest_obs)

    if (latest_obs and latest_obs.mwa_sub_arrays) is False:
        print(f"DEBUG - no sub arrays on previous obs")
        context[
            "decision_reason_log"
        ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Could not find sub array position on previous observation. \n"
        return context

    # (latest_obs and latest_obs.mwa_sub_arrays) is True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: New event has skymap \n"

    try:
        context = update_position_based_on_skymap(context, latest_obs)

        context = trigger_and_save_gw_voevents(
            telescope_settings=telescope_settings, context=context
        )
    except Exception as e:
        print(e)
        logger.error("Error getting MWA pointings from skymap")
        logger.error(e)

        json_logger.error(
            f"Error getting MWA pointings from skymap",
            extra={
                "function": "handle_gw_voevents",
                "trig_id": context["prop_dec"].trig_id,
                "event_id": context["event_id"],
            },
        )

    context["reached_end"] = True
    return context
