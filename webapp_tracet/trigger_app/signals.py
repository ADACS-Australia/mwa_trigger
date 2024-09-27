import logging
import time
from functools import partial

from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver

from .models.alert import AlertPermission
from .models.event import Event
from .models.proposal import ProposalSettings
from .models.status import Status
from .utils.utils_signals import (calculate_sky_coordinates, check_if_ignored,
                                  link_event_to_group, log_initial_debug_info,
                                  prepare_event_data, process_all_proposals,
                                  update_or_create_event_group)

logger = logging.getLogger(__name__)

json_logger = logging.getLogger('django_json')


@receiver(post_save, sender=Event)
def group_trigger(sender, instance, **kwargs):
    """Check if the latest Event has already been observered or if it is new and update the models accordingly"""
    json_logger.info(
        "signal triggered",
        extra={
            "function": "group_trigger",
            "event_id": instance.id,
        },
    )

    start_time = time.time()

    context = log_initial_debug_info(instance)

    context = prepare_event_data(context)

    context = update_or_create_event_group(context)

    context = link_event_to_group(context)

    context = check_if_ignored(context)
    if context is None:
        return

    json_logger.info(
        "signal not ignored",
        extra={
            "function": "group_trigger",
            "event_id": instance.id,
        },
    )

    context = calculate_sky_coordinates(context)

    # print(context)
    # Getting proposal decisions
    context = process_all_proposals(context)

    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")


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
