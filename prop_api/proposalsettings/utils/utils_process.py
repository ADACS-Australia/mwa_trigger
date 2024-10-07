import datetime as dt
import logging
from datetime import datetime

from astropy import units as u
from astropy.coordinates import SkyCoord

from ..utils import utils_api
from .utils_log import log_event
from .utils_worth_observing import (check_worth_observing,
                                    make_trigger_decision, trigger_repointing)

logger = logging.getLogger(__name__)
print("standart logger:", __name__)


@log_event(log_location="end",message=f"update_event_group completed", level="info")
def update_event_group(context):
    
    if context["prop_decs_exist"]:
        event_group = context["event_group"]
        event = context["event"]
    
        if event.pos_error and event.pos_error < event_group.pos_error and event.pos_error != 0.0:
            event_group.ra = event.ra
            event_group.dec = event.dec
            event_group.ra_hms = event.ra_hms
            event_group.dec_dms = event.dec_dms
            event_group.pos_error = event.pos_error

        event_group.latest_event_observed = event.event_observed
        context["event_group"] = event_group
    else :
        context["event_group"].ignored = False
   
    context['reached_end'] = True
    return context

@log_event(log_location="end",message=f"process_new_proposal_decision completed", level="info")
def process_new_proposal_decision(context):
    
    context["proposal_worth_observing"] = True
    
    context['reached_end'] = True
    return context

@log_event(log_location="end",message=f"process_proposal_decision completed", level="info")
def process_proposal_decision(context):
    
    prop_dec = context["prop_dec"]
    
    print("DEBUG - prop_dec.decision:", prop_dec.decision)
    
    # TODO remove this after testing
    # prop_dec.decision = "T"
    if prop_dec.decision == "C":
        print("DEBUG - process_canceled")
        context = process_canceled_decision(context)
    elif prop_dec.decision in ["I", "E"]:
        print("DEBUG - process_ignored_or_error")
        context = process_ignored_or_error_decision(context)
    elif prop_dec.decision in ["T", "TT"]:
        print("DEBUG - process_triggered")
        context = process_trigger_decision(context)
    elif prop_dec.decision == "P":
        print("DEBUG - process_pending")
        raise ValueError("Pending decision (P) is not implemented at this stage")
        # TODO - add logic for pending
    else:
        raise ValueError(f"Invalid decision: {prop_dec.decision}")
        
    context["reached_end"] = True
    return context

@log_event(log_location="end",message=f"process_canceled_decision completed", level="info")
def process_canceled_decision(context):

    prop_dec, event = context["prop_dec"], context["event"]

    prop_dec.decision_reason += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Previous observation canceled so not observing. \n"
    logger.info('Save proposal decision (prop_dec.decision == "C")')
    
    context["prop_dec"] = prop_dec
    context["trigger"] = False
    context["proposal_worth_observing"] = False
    
    return context

@log_event(log_location="end",message=f"process_ignored_or_error_decision completed", level="info")
def process_ignored_or_error_decision(context):
    
    prop_dec, event = context["prop_dec"], context["event"]

    prop_dec.ra = event.ra
    prop_dec.dec = event.dec
    prop_dec.ra_hms = event.ra_hms
    prop_dec.dec_dms = event.dec_dms
    if event.pos_error != 0.0:
        prop_dec.pos_error = event.pos_error
        prop_dec.decision_reason += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Checking new Event. \n"

    logger.info(
        f"Not saved - proposal decision (prop_dec.decision == {prop_dec.decision})"
    )
    
    context["prop_dec"] = prop_dec
    
    context["proposal_worth_observing"] = True
    
    context["reached_end"] = True
    return context

@log_event(log_location="end",message=f"process_trigger_decision completed", level="info")
def process_trigger_decision(context):

    prop_dec, event, event_coord = (
        context["prop_dec"],
        context["event"],
        context["event_coord"],
    )

    
    if prop_dec.ra and prop_dec.dec:
        old_event_coord = SkyCoord(
            ra=prop_dec.ra * u.degree, dec=prop_dec.dec * u.degree
        )
        
        event_sep = event_coord.separation(old_event_coord).deg
        print("DEBUG - event_sep:", event_sep)
        print("DEBUG - prop_dec.proposal.telescope_settings.repointing_limit:", prop_dec.proposal.telescope_settings.repointing_limit)
        if event_sep > prop_dec.proposal.telescope_settings.repointing_limit:
            print("DEBUG - repointing")
            context["trigger_repointing"] = True
            context["trigger"] = True
            repoint_message = f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Repointing because separation ({event_sep:.4f} deg) is greater than the repointing limit ({prop_dec.proposal.telescope_settings.repointing_limit:.4f} deg)."
            
            context["observation_reason"] = repoint_message
            # return trigger_repointing(
            #     prop_dec=prop_dec, event=event, event_sep=event_sep
            # )
        else :
            print("DEBUG - not repointing")
            raise ValueError("Not repointing: Event separation is within the repointing limit. Logic is not implemented yet.")
            
    else:
        context["proposal_worth_observing"] = True
        # proposal_worth_observing(prop_dec, event)
        
    context["reached_end"] = True
    return context

# main code proposal processing code 
@log_event(log_location="end",message=f"process_all_proposals_api completed", level="info")
def process_all_proposals(context_all):
    
    event_pyd = context_all["event"]
    prop_decs_pyd = context_all["prop_decs"]
    voevents_pyd = context_all["voevents"]
    prop_decs_exist = context_all["prop_decs_exist"]
    event_group_pyd = context_all["event_group"]
    event_coord = context_all["event_coord"]
    
    for prop_dec_pyd in prop_decs_pyd:
        context = {
            "event": event_pyd,
            "prop_dec": prop_dec_pyd,
            "voevents": voevents_pyd,
            "prop_decs_exist": prop_decs_exist,
            "event_group": event_group_pyd,
            "event_coord": event_coord,
            "trigger_bool": False,
            "debug_bool": False,
            "pending_bool": False,
            "observation_reason": "First observation.",
            "proposal_worth_observing": False,
            "send_alerts": False
        }

        if context["prop_decs_exist"]:
            logger.info(
                "Loop over all proposals settings and see if it's worth reobserving"
            )
            context = process_proposal_decision(context)
        else:
            logger.info("First unignored event so create proposal decisions objects")
            context = process_new_proposal_decision(context)
        
        # TODO remove this after testing
        # context["trigger_repointing"] = True
        context = trigger_repointing(context)
        
        context = check_worth_observing(context)
        
        # TODO remove this after testing
        context["trigger_bool"] = True
        # everthing implemened below after signals.py's line 408
        context = make_trigger_decision(context)
        
        result = utils_api.update_proposal_decision(prop_dec_pyd.id, context["decision"], context["decision_reason_log"])
        
        # TODO remove this after testing
        # context["send_alerts"]=True
        result = utils_api.trigger_alerts(context) 
    
    context = update_event_group(context)
        
    context = utils_api.update_event_group(context)
    
    context["reached_end"] = True
    
    return context
    