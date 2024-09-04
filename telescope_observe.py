import logging
import random
from datetime import datetime

from utils.utils_telescope_observe import (
    check_mwa_horizon_and_prepare_context,
    handle_atca_observation,
    handle_early_warning,
    handle_non_gw_observation,
    handle_skymap_event,
    prepare_observation_context,
    save_observation,
    trigger_mwa_observation,
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
