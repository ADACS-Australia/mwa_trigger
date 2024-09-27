import datetime as dt
import json
import logging
import os
from datetime import datetime
from functools import partial

import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
from django.conf import settings
from trigger_app.models.constants import TRIGGER_ON
from trigger_app.models.event import Event, EventGroup
from trigger_app.models.proposal import ProposalDecision, ProposalSettings
from trigger_app.schemas import EventSchema, ProposalDecisionSchema

from .utils_alerts import send_all_alerts
from .utils_api import make_propset_api_request, make_trig_obs_request

# from trigger_app.telescope_observe import trigger_observation


logger = logging.getLogger(__name__)

json_logger = logging.getLogger('django_json')


# group trigger functions
def log_initial_debug_info(event):
    logger.info("Trying to group with similar events")
    print("DEBUG - group_trigger")

    return {"event": event}


def prepare_event_data(context):
    event = context["event"]
    eventData = {
        "ra": event.ra,
        "dec": event.dec,
        "ra_hms": event.ra_hms,
        "dec_dms": event.dec_dms,
        "pos_error": event.pos_error,
        "earliest_event_observed": event.event_observed,
        "latest_event_observed": event.event_observed,
    }
    if event.source_name:
        eventData["source_name"] = event.source_name
    if event.source_type:
        eventData["source_type"] = event.source_type

    print(f"DEBUG - eventData {eventData}")
    context["eventData"] = eventData
    return context


def update_or_create_event_group(context):
    event = context["event"]
    eventData = context["eventData"]

    event_group = EventGroup.objects.update_or_create(
        trig_id=event.trig_id,
        defaults=eventData,
    )[0]
    context["event_group"] = event_group

    # Link the Event (have to update this way to prevent save() triggering this function again)
    logger.info(f"Linking event ({event.id}) to group {event_group}")
    # print(f"Linking event ({event.id}) to group {event_group}")

    return context


def link_event_to_group(context):

    event = context["event"]
    event_group = context["event_group"]

    Event.objects.filter(id=event.id).update(event_group_id=event_group)
    return context


def check_if_ignored(context):
    event = context["event"]
    if event.ignored:
        logger.info("Event ignored so do nothing")
        print(f"DEBUG - Event ignored so do nothing")

        json_logger.debug(
            "event ignored",
            extra={
                "function": "check_if_ignored",
                "event_id": event.id,
            },
        )
        return None  # Exit early if the event is ignored
    return context


def calculate_sky_coordinates(context):
    event = context["event"]
    if event.ra and event.dec:
        logger.info(f"Getting sky coordinates {event.ra} {event.dec}")
        print("DEBUG - Has ra and dec so getting sky coordinates")
        context["event_coord"] = SkyCoord(
            ra=event.ra * u.degree, dec=event.dec * u.degree
        )

    logger.info("Getting proposal decisions")
    return context


# functions used for proposal decisions loop


def fetch_proposal_decisions(event_group):
    return ProposalDecision.objects.filter(event_group_id=event_group).order_by(
        "proposal__priority"
    )


def log_decision_info(prop_dec):
    logger.info(
        f"Proposal decision (prop_dec.id, prop_dec.decision): {prop_dec.id, prop_dec.decision}"
    )
    print(
        f"DEBUG - Proposal decision (prop_dec.id, prop_dec.decision): {prop_dec.id, prop_dec.decision}"
    )
    return prop_dec


def update_event_group(event_group, event):
    if (
        event.pos_error
        and event.pos_error < event_group.pos_error
        and event.pos_error != 0.0
    ):
        event_group.ra = event.ra
        event_group.dec = event.dec
        event_group.ra_hms = event.ra_hms
        event_group.dec_dms = event.dec_dms
        event_group.pos_error = event.pos_error

    event_group.latest_event_observed = event.event_observed

    json_logger.debug(
        f"update event group - event_group.id: {event_group.id}",
        extra={
            "function": "update_event_group",
            "event_group_id": event_group.id,
        },
    )

    event_group.save()
    return event_group


# new event - there is no proposal decision yet
def create_initial_proposal_decisions(event_group, event):

    json_logger.debug(
        "create proposal decisions",
        extra={
            "function": "process_all_proposals",
            "event_id": event.id,
        },
    )

    # TODO selected only source types are same
    # proposal_settings = ProposalSettings.objects.all().order_by("priority")

    print("DEBUG - event_group.source_type: ", event_group.source_type)
    print("DEBUG - event.telescope: ", event.telescope)

    proposal_settings = ProposalSettings.objects.filter(
        source_type=event_group.source_type,
        event_telescope__name=event.telescope,
    ).order_by("priority")

    print("DEBUG - num of proposals : ", len(proposal_settings))

    for prop_set in proposal_settings:
        prop_dec = ProposalDecision.objects.create(
            decision_reason=f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Beginning event analysis. \n",
            proposal=prop_set,
            event_group_id=event_group,
            trig_id=event.trig_id,
            duration=event.duration,
            ra=event.ra,
            dec=event.dec,
            ra_hms=event.ra_hms,
            dec_dms=event.dec_dms,
            pos_error=event.pos_error,
        )

        proposal_worth_observing(prop_dec, event)

    event_group.ignored = False
    event_group.save()
    logger.info("Mark as unignored event")

    return event_group


def trigger_repointing(prop_dec, event, event_sep):
    prop_dec.ra = event.ra
    prop_dec.dec = event.dec
    prop_dec.ra_hms = event.ra_hms
    prop_dec.dec_dms = event.dec_dms
    if event.pos_error != 0.0:
        prop_dec.pos_error = event.pos_error

    json_logger.debug(
        f"trigger repointing",
        extra={
            "function": "trigger_repointing",
            "event_id": event.id,
            "event_group_id": prop_dec.trig_id,
        },
    )

    repoint_message = f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Repointing because separation ({event_sep:.4f} deg) is greater than the repointing limit ({prop_dec.proposal.repointing_limit:.4f} deg)."

    voevents = Event.objects.filter(trig_id=prop_dec.trig_id).order_by("-recieved_data")

    decision, decision_reason_log = trigger_observation(
        prop_dec,
        voevents,
        f"{prop_dec.decision_reason}{repoint_message} \n",
        reason=repoint_message,
        event_id=event.id,
    )

    if decision == "E":
        # Error observing so send off debug
        debug_bool = True
    else:
        debug_bool = False

    prop_dec.decision = decision
    prop_dec.decision_reason = decision_reason_log

    json_logger.debug(
        f"saving prop_dec",
        extra={
            "function": "trigger_repointing",
            "event_id": event.id,
            "event_group_id": prop_dec.trig_id,
        },
    )

    prop_dec.save()

    json_logger.debug(
        f"sending alerts",
        extra={
            "function": "trigger_repointing",
            "event_id": event.id,
            "event_group_id": prop_dec.trig_id,
        },
    )

    # send off alert messages to users and admins
    send_all_alerts(True, debug_bool, False, prop_dec)

    return prop_dec


def process_canceled_decision(context):

    prop_dec, event = context["prop_dec"], context["event"]

    json_logger.debug(
        "process canceled decision",
        extra={
            "function": "process_canceled_decision",
            "event_id": event.id,
            "trig_id": prop_dec.trig_id,
        },
    )

    prop_dec.decision_reason += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Previous observation canceled so not observing. \n"
    logger.info('Save proposal decision (prop_dec.decision == "C")')
    prop_dec.save()
    return context


def process_ignored_or_error_decision(context):

    prop_dec, event = context["prop_dec"], context["event"]

    json_logger.debug(
        "process ignored or error decision",
        extra={
            "function": "process_ignored_or_error_decision",
            "event_id": event.id,
            "trig_id": prop_dec.trig_id,
        },
    )

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
    # TODO - proc_dec not saved prop_dec.save()
    proposal_worth_observing(prop_dec, event)
    return context


def process_trigger_decision(context):
    prop_dec, event, event_coord = (
        context["prop_dec"],
        context["event"],
        context["event_coord"],
    )

    json_logger.debug(
        "process trigger decision",
        extra={
            "function": "process_trigger_decision",
            "event_id": event.id,
            "trig_id": prop_dec.trig_id,
        },
    )

    if prop_dec.ra and prop_dec.dec:
        print("DEBUG - old event coord")
        old_event_coord = SkyCoord(
            ra=prop_dec.ra * u.degree, dec=prop_dec.dec * u.degree
        )
        event_sep = event_coord.separation(old_event_coord).deg
        if event_sep > prop_dec.proposal.repointing_limit:
            print("DEBUG - repointing")
            return trigger_repointing(
                prop_dec=prop_dec, event=event, event_sep=event_sep
            )
    else:
        proposal_worth_observing(prop_dec, event)
    return context


def process_proposal_decision_func(context):
    prop_dec = context["prop_dec"]
    log_decision_info(prop_dec)

    # Define partial functions
    process_canceled = partial(process_canceled_decision)
    process_ignored_or_error = partial(process_ignored_or_error_decision)
    process_trigger = partial(process_trigger_decision)

    if prop_dec.decision == "C":
        print("DEBUG - process_canceled")
        return process_canceled(context)
    elif prop_dec.decision in ["I", "E"]:
        print("DEBUG - process_ignored_or_error")
        return process_ignored_or_error(context)
    elif prop_dec.decision in ["T", "TT"]:
        print("DEBUG - process_triggered")
        return process_trigger(context)
    return context


# worth observing trigger functions
def log_and_initialize(prop_dec, voevent, observation_reason):

    logger.info(f"Checking that proposal {prop_dec.proposal} is worth observing.")
    return {
        "prop_dec": prop_dec,
        "voevent": voevent,
        "observation_reason": observation_reason,
        "trigger_bool": False,
        "debug_bool": False,
        "pending_bool": False,
        "decision_reason_log": prop_dec.decision_reason,
    }


def save_prop_dec(context):
    print("DEBUG - save_prop_dec - check:", context["decision_reason_log"])
    prop_dec = context["prop_dec"]
    prop_dec.decision = context["decision"]
    prop_dec.decision_reason = context["decision_reason_log"]
    prop_dec.save()
    return context


def check_testing(context):
    prop_dec, voevent = context["prop_dec"], context["voevent"]
    pretend_real = TRIGGER_ON[0][0]
    real_only = TRIGGER_ON[2][0]

    if (
        prop_dec.proposal.testing == pretend_real
        and voevent.role == "test"
        or prop_dec.proposal.testing == real_only
        and voevent.role == "test"
    ):
        context["decision"] = "I"
        context[
            "decision_reason_log"
        ] += f"Proposal setting {prop_dec.proposal.testing} does not trigger on event role {voevent.role}"
        save_prop_dec(context)
        return None

    return context


def trigger_start(context):
    try:
        voevents = Event.objects.filter(trig_id=context["prop_dec"].trig_id).order_by(
            "-recieved_data"
        )

        decision, decision_reason_log = trigger_observation(
            context["prop_dec"],
            voevents,
            context["decision_reason_log"],
            reason=context["observation_reason"],
            event_id=context["voevent"].id,
        )
        context["decision"] = decision
        context["decision_reason_log"] = decision_reason_log
    except Exception as e:
        logger.error(e)
        context["decision"] = "E"
        context["debug_bool"] = True
    return context


def process_api_response(context):
    if context["trigger_bool"]:
        print("DEBUG - trigger started")

        return trigger_start(context)
    elif context["pending_bool"]:
        print("DEBUG - pending")
        context["decision"] = "P"
    elif (
        context["voevent"].event_type
        and context["voevent"].event_type == "Retraction"
        and context["prop_dec"].decision
    ):
        print("DEBUG - retraction. desicion:", context["prop_dec"].decision)
        context["decision"] = context["prop_dec"].decision
    else:
        print("DEBUG - ignored")
        context["decision"] = "I"
    return context


# proposal worth observing trigger functions


def proposal_worth_observing(
    prop_dec, voevent, observation_reason="First observation."
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

    json_logger.info(
        "proposal worth observing start",
        extra={
            "function": "proposal_worth_observing",
            "event_id": voevent.id,
            "trig_id": prop_dec.trig_id,
        },
    )

    context = log_and_initialize(prop_dec, voevent, observation_reason)
    print("DEBUG - log_and_initialize")
    context = check_testing(context)
    if context is None:
        json_logger.debug(
            "proposal worth observing - testing",
            extra={
                "function": "proposal_worth_observing",
                "event_id": voevent.id,
                "trig_id": prop_dec.trig_id,
            },
        )
        return

    # make api request after saving prop_dec
    # everthing implemened in api worth-observing after signals.py's line between 272 and 408
    print("DEBUG - context after check_testing")

    context = make_propset_api_request(context)
    if context is None:
        return

    # Test
    # TODO comment back
    context["trigger_bool"] = True
    print("DEBUG - please trigger_bool comment back in. Its getting True value always")
    print("DEBUG - context keys:", context.keys())

    # everthing implemened below after signals.py's line 408
    context = process_api_response(context)

    json_logger.debug(
        f"process after checking worth observing trigger_bool: {context['trigger_bool']}",
        extra={
            "function": "proposal_worth_observing",
            "event_id": voevent.id,
            "trig_id": prop_dec.trig_id,
        },
    )

    context = save_prop_dec(context)

    logger.info("Sending alerts to users and admins")
    print(
        f"\nDEBUG - send email: {context['trigger_bool']} {context['debug_bool']} {context['pending_bool']} {context['prop_dec']}\n"
    )

    send_all_alerts(
        context["trigger_bool"],
        context["debug_bool"],
        context["pending_bool"],
        context["prop_dec"],
    )


# Main processing function using context
def process_all_proposals(context):
    event_group = context["event_group"]
    event = context["event"]
    event_coord = context.get("event_coord")

    json_logger.info(
        "process all proposals",
        extra={
            "function": "process_all_proposals",
            "event_id": event.id,
        },
    )

    proposal_decisions = fetch_proposal_decisions(event_group)

    if proposal_decisions.exists():
        logger.info(
            "Loop over all proposals settings and see if it's worth reobserving"
        )

        print(
            "DEBUG- Loop over all proposals settings and see if it's worth reobserving"
        )

        json_logger.info(
            "process existing proposal decisions",
            extra={
                "function": "process_all_proposals",
                "event_id": event.id,
            },
        )

        process_proposal_decision = partial(process_proposal_decision_func)
        # Process each proposal decision

        for prop_dec in proposal_decisions:
            context["prop_dec"] = prop_dec
            context = process_proposal_decision(context)

        # Update the event group after processing
        context["event_group"] = update_event_group(event_group, event)
    else:
        logger.info("First unignored event so create proposal decisions objects")
        context["event_group"] = create_initial_proposal_decisions(
            event_group, event
        )

    return context


def trigger_observation(
    proposal_decision_model,
    voevents,
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

    telescopes = []
    latestVoevent = voevents[0]

    context = {
        "proposal_decision_model": proposal_decision_model,
        "event_id": event_id,
        "decision_reason_log": decision_reason_log,
        "reason": reason,
        "telescopes": telescopes,
        "latestVoevent": latestVoevent,
        "mwa_sub_arrays": None,
        "stop_processing": False,
        "decision": None,
    }

    context["decision"], context["decision_reason_log"] = make_trig_obs_request(
        context, voevents
    )
    return context["decision"], context["decision_reason_log"]
