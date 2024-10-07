import datetime as dt
import logging
from datetime import datetime

from astropy import units as u
from astropy.coordinates import SkyCoord

from ..utils import utils_api
from .utils_log import log_event

logger = logging.getLogger(__name__)
print("standart logger:", __name__)

@log_event(log_location="start",message=f"check_worth_observing started", level="info")
def check_worth_observing(context):
    
    if context["proposal_worth_observing"] is False:
        return context
    
    prop_dec = context["prop_dec"]
    event = context["event"]
    observation_reason=context["observation_reason"]
    
    print("DEBUG - check_worth_observing")

    # make api request after saving prop_dec
    boolean_log_values = proposal_worth_observing(
        prop_dec=prop_dec, event=event, observation_reason=observation_reason
    )

    if boolean_log_values is None:
        return context

    context["trigger_bool"] = boolean_log_values["trigger_bool"]
    context["debug_bool"] = boolean_log_values["debug_bool"]
    context["pending_bool"] = boolean_log_values["pending_bool"]
    context["decision_reason_log"] = boolean_log_values["decision_reason_log"]
    
    print("DEBUG - boolean_log_values:", boolean_log_values)
     
    context["trigger_decision"] = True

    context["reached_end"] = True
    
    return context

def proposal_worth_observing(
    prop_dec, event, observation_reason
):
    """For a proposal sees is this voevent is worth observing. If it is will trigger an observation and send off the relevant alerts.

    Parameters
    ----------
    prop_dec : `django.db.models.Model`
        The Django ProposalDecision model object.
    voevent : `django.db.models.Model`
        The Django Event model object.
    observation_reason : `str`, optional
        The reason for this observation. The default is "First Observation" but other potential reasons are "Repointing".
    """
    print("DEBUG - proposal_worth_observing")
    logger.info(f"Checking that proposal {prop_dec.proposal} is worth observing.")
    # Defaults if not worth observing
    trigger_bool = debug_bool = pending_bool = False
    decision_reason_log = prop_dec.decision_reason
    proj_source_bool = False

    # if True:
    #     prop_dec.proposal.telescope_settings.event_telescope = None
    # prop_dec.proposal.telescope_settings.event_telescope.name = "Fermi"
    # prop_dec.event_group_id.source_type = "GRB"
    print("DEBUG - prop_dec.proposal.event_telescope:", prop_dec.proposal.event_telescope.name)
    print("DEBUG - event.telescope:", event.telescope)
    
    # Continue to next test
    if (
        prop_dec.proposal.event_telescope is None
        or str(prop_dec.proposal.event_telescope.name).strip()
        == event.telescope.strip()
    ):
        print("Next test")
        print(prop_dec.proposal.source_type)
        print(prop_dec.event_group_id.source_type)

        # This project observes events from this telescope
        # Check if this proposal thinks this event is worth observing
        if (
            prop_dec.proposal.source_type == "FS"
            and prop_dec.event_group_id.source_type == "FS"
        ):
            trigger_bool = True
            decision_reason_log = f"{decision_reason_log}{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Triggering on Flare Star {prop_dec.event_group_id.source_name}. \n"
            proj_source_bool = True

        elif (
            prop_dec.proposal.source_type == prop_dec.event_group_id.source_type
            and prop_dec.event_group_id.source_type in ["GRB", "GW", "NU"]
        ):
            print(prop_dec.proposal.id)
            (
                trigger_bool,
                debug_bool,
                pending_bool,
                decision_reason_log,
            ) = prop_dec.proposal.is_worth_observing(
                event,
                dec=prop_dec.dec,
                decision_reason_log=decision_reason_log,
                prop_dec=prop_dec,
            )
            proj_source_bool = True

        else:
            print("DEBUG - proposal_worth_observing - not same values")

        if not proj_source_bool:
            # Proposal does not observe this type of source so update message
            decision_reason_log = f"{decision_reason_log}{datetime.now(dt.timezone.utc)}: Event ID {event.id}: This proposal does not observe {prop_dec.event_group_id.source_type}s. \n"

    else:
        # Proposal does not observe event from this telescope so update message
        print("DEBUG - proposal_worth_observing - event.id:", event.id)
        print("DEBUG - proposal_worth_observing - event.telescope:", event.telescope)
        decision_reason_log = f"{decision_reason_log}{datetime.now(dt.timezone.utc)}: Event ID {event.id}: This proposal does not trigger on events from {event.telescope}. \n"

    print(trigger_bool, debug_bool, pending_bool, decision_reason_log)

    return {
        "trigger_bool": trigger_bool,
        "debug_bool": debug_bool,
        "pending_bool": pending_bool,
        "proj_source_bool": proj_source_bool,
        "decision_reason_log": decision_reason_log,
    }

@log_event(log_location="end",message=f"make_trigger_decision completed", level="info")
def make_trigger_decision(context):
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


@log_event(log_location="end",message=f"trigger_repointing completed", level="info")
def trigger_repointing(context):
    
    if "trigger_repointing" not in context.keys() or context["trigger_repointing"] is False:
        return context
    
    prop_dec, event,repoint_message = context["prop_dec"], context["event"],context["observation_reason"]
    
    
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

