import datetime
import json
import logging
import os
from functools import partial
from operator import itemgetter

import numpy as np
import requests
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver

from .models import AlertPermission  # ProposalSettingsNoTable,
from .models import (
    TRIGGER_ON,
    Event,
    EventGroup,
    EventTelescope,
    Observations,
    ProposalDecision,
    ProposalSettings,
    Status,
    Telescope,
    TelescopeProjectID,
    UserAlerts,
)
from .schemas import EventSchema, ProposalDecisionSchema, PydProposalSettings
from .telescope_observe import trigger_observation
from .utils.utils_signals import (
    calculate_sky_coordinates,
    check_if_ignored,
    check_testing,
    create_initial_proposal_decisions,
    fetch_proposal_decisions,
    link_event_to_group,
    log_and_initialize,
    log_initial_debug_info,
    make_api_request,
    prepare_instance_data,
    process_api_response,
    process_proposal_decision_func,
    save_prop_dec,
    update_event_group,
    update_or_create_event_group,
)

logger = logging.getLogger(__name__)

# account_sid = os.environ.get("TWILIO_ACCOUNT_SID", None)
# auth_token = os.environ.get("TWILIO_AUTH_TOKEN", None)
# my_number = os.environ.get("TWILIO_PHONE_NUMBER", None)


@receiver(post_save, sender=Event)
def group_trigger(sender, instance, **kwargs):
    """Check if the latest Event has already been observered or if it is new and update the models accordingly"""
    context = log_initial_debug_info(instance)

    context = prepare_instance_data(context)

    context = update_or_create_event_group(context)

    context = link_event_to_group(context)

    context = check_if_ignored(context)
    if context is None:
        return

    context = calculate_sky_coordinates(context)

    print(context)
    # Getting proposal decisions
    context = process_all_proposals(context)


# Main processing function using context
def process_all_proposals(context):
    event_group = context["event_group"]
    instance = context["instance"]
    event_coord = context.get("event_coord")

    proposal_decisions = fetch_proposal_decisions(event_group)

    if proposal_decisions.exists():
        logger.info(
            "Loop over all proposals settings and see if it's worth reobserving"
        )

        process_proposal_decision = partial(process_proposal_decision_func)
        # Process each proposal decision
        for prop_dec in proposal_decisions:
            context["prop_dec"] = prop_dec
            context = process_proposal_decision(context)

        # Update the event group after processing
        context["event_group"] = update_event_group(event_group, instance)
    else:
        logger.info("First unignored event so create proposal decisions objects")
        context["event_group"] = create_initial_proposal_decisions(
            event_group, instance
        )

    return context


@receiver(post_save, sender=User)
def create_admin_alerts_proposal(sender, instance, **kwargs):
    if kwargs.get("created"):
        # Create an admin alert for each proposal
        proposal_settings = ProposalSettings.objects.all()

        for prop_set in proposal_settings:
            s = AlertPermission(user=instance, proposal=prop_set)
            s.save()


@receiver(post_save, sender=ProposalSettings)
def create_admin_alerts_user(sender, instance, **kwargs):
    if kwargs.get("created"):
        # Create an admin alert for each user
        users = User.objects.all()
        for user in users:
            s = AlertPermission(user=user, proposal=instance)
            s.save()


def on_startup(sender, **kwargs):
    # Create a twistd comet status object and set it to stopped until the twistd_comet_wrapper.py is called
    if Status.objects.filter(name="twistd_comet").exists():
        Status.objects.filter(name="twistd_comet").update(status=2)
    else:
        Status.objects.create(name="twistd_comet", status=2)

    if Status.objects.filter(name="kafka").exists():
        Status.objects.filter(name="kafka").update(status=2)
    else:
        Status.objects.create(name="kafka", status=2)


# Getting a signal from views.py which indicates that the server has started
startup_signal = Signal()
# Run twistd startup function
startup_signal.connect(on_startup, dispatch_uid="models-startup")
