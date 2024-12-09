from django.conf import settings
from django.http import QueryDict
from django.shortcuts import render

from .. import models
from .eventgroup import EventGroupFilter, grab_decisions_for_event_groups


def home_page(request):
    comet_status = models.status.Status.objects.get(name="twistd_comet")
    kafka_status = models.status.Status.objects.get(name="kafka")

    prop_settings = models.proposal.ProposalSettings.objects.all()

    req = QueryDict("ignored=False&source_type=GRB&telescope=SWIFT")

    f = EventGroupFilter(
        req,
        queryset=models.event.EventGroup.objects.distinct().filter(
            voevent__role="observation"
        ),
    )
    recent_event_groups_swift = f.qs[:20]

    # Filter out ignored event groups and telescope=swift and show only the 5 most recent
    # recent_event_groups_swift = models.EventGroup.objects.filter(
    #     ignored=False, source_type="GRB")[:20]
    recent_event_group_info_swift, _ = grab_decisions_for_event_groups(
        recent_event_groups_swift
    )

    recent_event_group_info_swift = filter(
        lambda x: x[2] == "SWIFT", recent_event_group_info_swift
    )

    recent_event_groups_lvc = models.event.EventGroup.objects.filter(
        ignored=False, source_type="GW"
    )[:10]
    recent_event_group_info_lvc, _ = grab_decisions_for_event_groups(
        recent_event_groups_lvc
    )

    recent_event_group_info_lvc = filter(
        lambda x: x[2] == "LVC", recent_event_group_info_lvc
    )

    context = {
        "twistd_comet_status": comet_status,
        "kafka_status": kafka_status,
        "settings": prop_settings,
        "remotes": ", ".join(settings.VOEVENT_REMOTES),
        "tcps": ", ".join(settings.VOEVENT_TCP),
        "recent_event_groups_swift": list(recent_event_group_info_swift),
        "recent_event_groups_lvc": list(recent_event_group_info_lvc),
    }
    return render(request, "trigger_app/home_page.html", context)
