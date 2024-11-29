import datetime as dt
import logging
from datetime import datetime

from astropy import units as u
from astropy.coordinates import SkyCoord

from ..utils import utils_api
from .utils_log import log_event

logger = logging.getLogger(__name__)
print("standart logger:", __name__)


@log_event(log_location="start", message=f"check_worth_observing started", level="info")
def check_worth_observing(context):
    """
    Check if a proposal is worth observing based on the given context.

    Args:
        context (dict): A dictionary containing proposal and event information.

    Returns:
        dict: Updated context with observation decision information.
    """
    if context["proposal_worth_observing"] is False:
        return context

    print("DEBUG - check_worth_observing")

    # make api request after saving prop_dec
    context = proposal_worth_observing(
        context=context,
    )

    if context['trigger_bool'] is None:
        return context

    # context["trigger_bool"] = boolean_log_values["trigger_bool"]
    # context["debug_bool"] = boolean_log_values["debug_bool"]
    # context["pending_bool"] = boolean_log_values["pending_bool"]
    # context["decision_reason_log"] = boolean_log_values["decision_reason_log"]

    print(
        "DEBUG - boolean_log_values:",
        context['trigger_bool'],
        context['debug_bool'],
        context['pending_bool'],
        context['decision_reason_log'],
    )

    context["trigger_decision"] = True

    context["reached_end"] = True

    return context


def proposal_worth_observing(context):
    """For a proposal sees is this voevent is worth observing. If it is will trigger an observation and send off the relevant alerts.

    Args:
        prop_dec (django.db.models.Model): The Django ProposalDecision model object.
        event (django.db.models.Model): The Django Event model object.
        observation_reason (str): The reason for this observation (e.g., "First Observation", "Repointing").

    Returns:
        dict: A dictionary containing boolean flags and decision reasons.
    """
    print("DEBUG - proposal_worth_observing")

    prop_dec = context["prop_dec"]
    event = context["event"]
    observation_reason = context["observation_reason"]

    logger.info(f"Checking that proposal {prop_dec.proposal} is worth observing.")
    # Defaults if not worth observing
    context['decision_reason_log'] = prop_dec.decision_reason
    context['trigger_bool'] = context['debug_bool'] = context['pending_bool'] = False
    context['proj_source_bool'] = False

    # trigger_bool = debug_bool = pending_bool = False
    # decision_reason_log = prop_dec.decision_reason
    # proj_source_bool = False

    # if True:
    #     prop_dec.proposal.telescope_settings.event_telescope = None
    # prop_dec.proposal.telescope_settings.event_telescope.name = "Fermi"
    # prop_dec.event_group_id.source_type = "GRB"
    print(
        "DEBUG - prop_dec.proposal.event_telescope:",
        prop_dec.proposal.event_telescope.name,
    )
    print("DEBUG - event.telescope:", event.telescope)

    stream = event.telescope.upper() + "_" + event.event_type.upper()
    if stream[-2:] == "_-":
        stream = stream[:-2]

    print("--------------------------------------------------------")
    print("DEBUG - stream: ", stream)
    print("--------------------------------------------------------")

    # Continue to next test
    if (
        prop_dec.proposal.event_telescope is None
        or str(prop_dec.proposal.event_telescope.name).strip()
        == event.telescope.strip()
    ):

        # This project observes events from this telescope
        # Check if this proposal thinks this event is worth observing
        if (
            prop_dec.proposal.source_type == "FS"
            and prop_dec.event_group_id.source_type == "FS"
        ):
            context['trigger_bool'] = True
            context['decision_reason_log'] = (
                f"{context['decision_reason_log']}{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Triggering on Flare Star {prop_dec.event_group_id.source_name}. \n"
            )
            context['proj_source_bool'] = True

        elif (
            prop_dec.proposal.source_type == prop_dec.event_group_id.source_type
            and stream in prop_dec.proposal.streams
            and prop_dec.event_group_id.source_type in ["GRB", "GW", "NU"]
        ):

            context = prop_dec.proposal.is_worth_observing(context=context)

            # context['trigger_bool'] = context_wo["trigger_bool"]
            # context['debug_bool'] = context_wo["debug_bool"]
            # context['pending_bool'] = context_wo["pending_bool"]
            # context['decision_reason_log'] = context_wo["decision_reason_log"]

            # proj_source_bool = True
            context['proj_source_bool'] = True

        else:
            print("DEBUG - proposal_worth_observing - not same values")

        if not context['proj_source_bool']:
            # Proposal does not observe this type of source so update message
            context['decision_reason_log'] = (
                f"{context['decision_reason_log']}{datetime.now(dt.timezone.utc)}: Event ID {event.id}: This proposal does not observe {prop_dec.event_group_id.source_type}s. \n"
            )

    else:
        # Proposal does not observe event from this telescope so update message
        print("DEBUG - proposal_worth_observing - event.id:", event.id)
        print("DEBUG - proposal_worth_observing - event.telescope:", event.telescope)
        context['decision_reason_log'] = (
            f"{context['decision_reason_log']}{datetime.now(dt.timezone.utc)}: Event ID {event.id}: This proposal does not trigger on events from {event.telescope}. \n"
        )

    print(
        context['trigger_bool'],
        context['debug_bool'],
        context['pending_bool'],
        context['decision_reason_log'],
    )

    return context


@log_event(log_location="end", message=f"make_trigger_decision completed", level="info")
def make_trigger_decision(context):
    """
    Make a trigger decision based on the proposal worth observing results.

    Args:
        context (dict): A dictionary containing proposal and event information.

    Returns:
        dict: Updated context with trigger decision information.
    """
    if context["proposal_worth_observing"] is False:
        return context

    if "trigger_decision" not in context.keys() or context["trigger_decision"] is False:
        return context

    # context["trigger_decision"] is True
    if context["trigger_bool"]:
        print("DEBUG - trigger started")
        print("DEBUG - context keys:", context.keys())
        try:
            decision, decision_reason_log = trigger_observation(
                prop_dec=context["prop_dec"],
                voevents=context["voevents"],
                decision_reason_log=context["decision_reason_log"],
                reason=context["observation_reason"],
                event_id=context["event"].id,
            )
            context["decision"] = decision
            context["decision_reason_log"] = decision_reason_log
            context["prop_dec"].decision = decision
            context["prop_dec"].decision_reason = decision_reason_log
        except Exception as e:
            logger.error(e)
            context["decision"] = "E"
            context["debug_bool"] = True

    elif context["pending_bool"]:
        print("DEBUG - pending")
        context["decision"] = "P"
    elif (
        context["event"].event_type
        and context["event"].event_type == "Retraction"
        and context["prop_dec"].decision
    ):
        print("DEBUG - retraction. desicion:", context["prop_dec"].decision)
        context["decision"] = context["prop_dec"].decision
    else:
        print("DEBUG - ignored")
        context["decision"] = "I"

    # update prop_dec
    context["prop_dec"].decision = context["decision"]
    context["prop_dec"].decision_reason = context["decision_reason_log"]

    logger.info("Sending alerts to users and admins")

    context["send_alert"] = True

    context["reached_end"] = True

    return context


@log_event(log_location="end", message=f"trigger_repointing completed", level="info")
def trigger_repointing(context):
    """
    Trigger a repointing observation based on the given context.

    Args:
        context (dict): A dictionary containing proposal and event information.

    Returns:
        dict: Updated context with repointing information.
    """
    if (
        "trigger_repointing" not in context.keys()
        or context["trigger_repointing"] is False
    ):
        return context

    prop_dec, event, repoint_message = (
        context["prop_dec"],
        context["event"],
        context["observation_reason"],
    )

    prop_dec.ra = event.ra
    prop_dec.dec = event.dec
    prop_dec.ra_hms = event.ra_hms
    prop_dec.dec_dms = event.dec_dms
    if event.pos_error != 0.0:
        prop_dec.pos_error = event.pos_error

    voevents = context["voevents"]

    print("DEBUG - reached trigger_observation")
    decision, decision_reason_log = trigger_observation(
        prop_dec=prop_dec,
        voevents=voevents,
        decision_reason_log=f"{prop_dec.decision_reason}{repoint_message} \n",
        reason=repoint_message,
        event_id=event.id,
    )
    print("DEBUG - passed trigger_observation")
    if decision == "E":
        # Error observing so send off debug
        debug_bool = True
    else:
        debug_bool = False

    prop_dec.decision = decision
    prop_dec.decision_reason = decision_reason_log

    context["prop_dec"] = prop_dec
    # prop_dec.save()

    # send off alert messages to users and admins
    context["send_alert"] = True

    context["trigger_bool"] = True
    context["debug_bool"] = debug_bool
    context["pending_bool"] = False
    # send_all_alerts(True, debug_bool, False, prop_dec)
    context["reached_end"] = True

    return context


def trigger_observation(
    prop_dec,
    voevents,
    decision_reason_log,
    reason="First Observation",
    event_id=None,
):
    """
    Trigger an observation based on the proposal decision and event information.

    Args:
        prop_dec (django.db.models.Model): The Django ProposalDecision model object.
        voevents (list): A list of VOEvent objects.
        decision_reason_log (str): The current decision reason log.
        reason (str, optional): The reason for the observation. Defaults to "First Observation".
        event_id (int, optional): The ID of the event. Defaults to None.

    Returns:
        tuple: A tuple containing the decision (str) and updated decision_reason_log (str).
    """
    # print("DEBUG - Trigger observation")

    telescopes = []
    latestVoevent = voevents[0]

    context_trig = {
        "prop_dec": prop_dec,
        "event_id": event_id,
        "decision_reason_log": decision_reason_log,
        "reason": reason,
        "telescopes": telescopes,
        "latestVoevent": latestVoevent,
        "mwa_sub_arrays": None,
        "stop_processing": False,
        "decision": None,
        "voevents": voevents,
    }

    print("DEBUG - starts trigger_gen_observation")
    context = prop_dec.proposal.trigger_gen_observation(context_trig)
    decision, decision_reason_log = context["decision"], context["decision_reason_log"]

    print("DEBUG - ends trigger_gen_observation")

    # TODO ask if we need to set decision to "I" when decision is None
    decision = decision if decision else "I"

    return decision, decision_reason_log
