import datetime
import json
import logging
from functools import partial

import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
from trigger_app.models import (
    TRIGGER_ON,
    Event,
    EventGroup,
    ProposalDecision,
    ProposalSettings,
)
from trigger_app.schemas import EventSchema, ProposalDecisionSchema
from trigger_app.telescope_observe import trigger_observation

from .utils_alerts import send_all_alerts

logger = logging.getLogger(__name__)


# group trigger functions
def log_initial_debug_info(instance):
    logger.info("Trying to group with similar events")
    print("DEBUG - group_trigger")

    return {"instance": instance}


def prepare_instance_data(context):
    instance = context["instance"]
    instanceData = {
        "ra": instance.ra,
        "dec": instance.dec,
        "ra_hms": instance.ra_hms,
        "dec_dms": instance.dec_dms,
        "pos_error": instance.pos_error,
        "earliest_event_observed": instance.event_observed,
        "latest_event_observed": instance.event_observed,
    }
    if instance.source_name:
        instanceData["source_name"] = instance.source_name
    if instance.source_type:
        instanceData["source_type"] = instance.source_type

    print(f"DEBUG - instanceData {instanceData}")
    context["instanceData"] = instanceData
    return context


def update_or_create_event_group(context):
    instance = context["instance"]
    instanceData = context["instanceData"]

    event_group = EventGroup.objects.update_or_create(
        trig_id=instance.trig_id,
        defaults=instanceData,
    )[0]
    context["event_group"] = event_group

    # Link the Event (have to update this way to prevent save() triggering this function again)
    logger.info(f"Linking event ({instance.id}) to group {event_group}")
    print(f"Linking event ({instance.id}) to group {event_group}")

    return context


def link_event_to_group(context):

    instance = context["instance"]
    event_group = context["event_group"]

    Event.objects.filter(id=instance.id).update(event_group_id=event_group)
    return context


def check_if_ignored(context):
    instance = context["instance"]
    if instance.ignored:
        logger.info("Event ignored so do nothing")
        print(f"DEBUG - Event ignored so do nothing")
        return None  # Exit early if the event is ignored
    return context


def calculate_sky_coordinates(context):
    instance = context["instance"]
    if instance.ra and instance.dec:
        logger.info(f"Getting sky coordinates {instance.ra} {instance.dec}")
        print("DEBUG - Has ra and dec so getting sky coordinates")
        context["event_coord"] = SkyCoord(
            ra=instance.ra * u.degree, dec=instance.dec * u.degree
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
        f"Proposal decision (prop_dec.id, prop_dec.decision): {prop_dec.id, prop_dec.decision}"
    )
    return prop_dec


def update_event_group(event_group, instance):
    if (
        instance.pos_error
        and instance.pos_error < event_group.pos_error
        and instance.pos_error != 0.0
    ):
        event_group.ra = instance.ra
        event_group.dec = instance.dec
        event_group.ra_hms = instance.ra_hms
        event_group.dec_dms = instance.dec_dms
        event_group.pos_error = instance.pos_error

    event_group.latest_event_observed = instance.event_observed
    event_group.save()
    return event_group


# new event - there is no proposal decision yet
def create_initial_proposal_decisions(event_group, instance):
    proposal_settings = ProposalSettings.objects.all().order_by("priority")
    for prop_set in proposal_settings:
        prop_dec = ProposalDecision.objects.create(
            decision_reason=f"{datetime.datetime.utcnow()}: Event ID {instance.id}: Beginning event analysis. \n",
            proposal=prop_set,
            event_group_id=event_group,
            trig_id=instance.trig_id,
            duration=instance.duration,
            ra=instance.ra,
            dec=instance.dec,
            ra_hms=instance.ra_hms,
            dec_dms=instance.dec_dms,
            pos_error=instance.pos_error,
        )

        proposal_worth_observing(prop_dec, instance)

    event_group.ignored = False
    event_group.save()
    logger.info("Mark as unignored event")

    return event_group


def trigger_repointing(prop_dec, instance, event_sep):
    prop_dec.ra = instance.ra
    prop_dec.dec = instance.dec
    prop_dec.ra_hms = instance.ra_hms
    prop_dec.dec_dms = instance.dec_dms
    if instance.pos_error != 0.0:
        prop_dec.pos_error = instance.pos_error

    repoint_message = f"{datetime.datetime.utcnow()}: Event ID {instance.id}: Repointing because separation ({event_sep:.4f} deg) is greater than the repointing limit ({prop_dec.proposal.repointing_limit:.4f} deg)."
    decision, decision_reason_log = trigger_observation(
        prop_dec,
        f"{prop_dec.decision_reason}{repoint_message} \n",
        reason=repoint_message,
        event_id=instance.id,
    )

    if decision == "E":
        # Error observing so send off debug
        debug_bool = True
    else:
        debug_bool = False

    prop_dec.decision = decision
    prop_dec.decision_reason = decision_reason_log
    prop_dec.save()

    # send off alert messages to users and admins
    send_all_alerts(True, debug_bool, False, prop_dec)

    return prop_dec


def process_canceled_decision(context):
    prop_dec, instance = context["prop_dec"], context["instance"]
    prop_dec.decision_reason += f"{datetime.datetime.utcnow()}: Event ID {instance.id}: Previous observation canceled so not observing. \n"
    logger.info('Save proposal decision (prop_dec.decision == "C")')
    prop_dec.save()
    return context


def process_ignored_or_error_decision(context):
    prop_dec, instance = context["prop_dec"], context["instance"]
    prop_dec.ra = instance.ra
    prop_dec.dec = instance.dec
    prop_dec.ra_hms = instance.ra_hms
    prop_dec.dec_dms = instance.dec_dms
    if instance.pos_error != 0.0:
        prop_dec.pos_error = instance.pos_error
        prop_dec.decision_reason += f"{datetime.datetime.utcnow()}: Event ID {instance.id}: Checking new Event. \n"

    logger.info(
        f"Not saved - proposal decision (prop_dec.decision == {prop_dec.decision})"
    )
    # TODO - proc_dec not saved prop_dec.save()
    proposal_worth_observing(prop_dec, instance)
    return context


def process_trigger_decision(context):
    prop_dec, instance, event_coord = (
        context["prop_dec"],
        context["instance"],
        context["event_coord"],
    )
    if prop_dec.ra and prop_dec.dec:
        old_event_coord = SkyCoord(
            ra=prop_dec.ra * u.degree, dec=prop_dec.dec * u.degree
        )
        event_sep = event_coord.separation(old_event_coord).deg
        if event_sep > prop_dec.proposal.repointing_limit:
            return trigger_repointing(context, event_sep)
    else:
        proposal_worth_observing(prop_dec, instance)
    return context


def process_proposal_decision_func(context):
    prop_dec = context["prop_dec"]
    log_decision_info(prop_dec)

    # Define partial functions
    process_canceled = partial(process_canceled_decision)
    process_ignored_or_error = partial(process_ignored_or_error_decision)
    process_trigger = partial(process_trigger_decision)

    if prop_dec.decision == "C":
        return process_canceled(context)
    elif prop_dec.decision in ["I", "E"]:
        return process_ignored_or_error(context)
    elif prop_dec.decision in ["T", "TT"]:
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


def make_api_request(context):

    prop_dec_data_str = ProposalDecisionSchema.from_orm(context["prop_dec"]).json()
    voevent_data_str = EventSchema.from_orm(context["voevent"]).json()

    payload = {
        "prop_dec": json.loads(prop_dec_data_str),
        "voevent": json.loads(voevent_data_str),
        "observation_reason": context["observation_reason"],
    }
    response = requests.post("http://api:8000/api/worth_observing/", json=payload)

    if response.status_code != 200:
        logger.error("Request unsuccessful")
        return None

    api_response = response.json()
    context.update(
        {
            "trigger_bool": api_response["trigger_bool"],
            "debug_bool": api_response["debug_bool"],
            "pending_bool": api_response["pending_bool"],
            "decision_reason_log": api_response["decision_reason_log"],
        }
    )
    return context


def trigger_start(context):
    try:
        decision, decision_reason_log = trigger_observation(
            context["prop_dec"],
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
        context["decision"] = "P"
    elif (
        context["voevent"].event_type
        and context["voevent"].event_type == "Retraction"
        and context["prop_dec"].decision
    ):
        context["decision"] = context["prop_dec"].decision
    else:
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

    context = log_and_initialize(prop_dec, voevent, observation_reason)
    context = check_testing(context)
    if context is None:
        return

    # make api request after saving prop_dec
    # everthing implemened in api worth-observing after signals.py's line between 272 and 408
    print("DEBUG - context after check_testing", context)

    context = make_api_request(context)
    if context is None:
        return

    print("DEBUG - made suggessfull request")

    # Test
    # context["trigger_bool"] = True
    # print("DEBUG - context after make_api_request", context)

    # everthing implemened below after signals.py's line 408
    context = process_api_response(context)

    context = save_prop_dec(context)

    logger.info("Sending alerts to users and admins")
    print(
        f"\nDEBUG - {context['trigger_bool']} {context['debug_bool']} {context['pending_bool']} {context['prop_dec']}\n"
    )

    send_all_alerts(
        context["trigger_bool"],
        context["debug_bool"],
        context["pending_bool"],
        context["prop_dec"],
    )
