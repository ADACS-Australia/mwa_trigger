import time

from django.conf import settings
from django.http import QueryDict
from django.shortcuts import render

from .. import models
from .eventgroup import EventGroupFilter, grab_decisions_for_event_groups


def home_page(request):
    comet_status = models.status.Status.objects.get(name="twistd_comet")
    kafka_status = models.status.Status.objects.get(name="kafka")

    prop_settings = models.proposal.ProposalSettings.objects.all()

    # req = QueryDict("ignored=False&source_type=GRB&telescope=SWIFT")
    req = QueryDict("ignored=False")

    start_time = time.time()

    f = EventGroupFilter(
        req,
        queryset=models.event.EventGroup.objects.distinct().filter(
            voevent__role="observation"
        ),
    )
    recent_event_groups = f.qs[:60]

    # recent_event_groups = models.event.EventGroup.objects.filter(
    #     ignored=False, voevent__role="observation"
    # )[:60]

    # Filter out ignored event groups and telescope=swift and show only the 5 most recent
    # recent_event_groups = models.EventGroup.objects.filter(
    #     ignored=False, source_type="GRB")[:20]

    recent_event_group_info, _ = grab_decisions_for_event_groups(recent_event_groups)

    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")

    # recent_event_group_info_swift = filter(
    #     lambda x: x[2] == "SWIFT", recent_event_group_info_swift
    # )

    # print([x[2] for x in recent_event_group_info_swift])

    context = {
        "twistd_comet_status": comet_status,
        "kafka_status": kafka_status,
        "settings": prop_settings,
        "remotes": ", ".join(settings.VOEVENT_REMOTES),
        "tcps": ", ".join(settings.VOEVENT_TCP),
        "recent_event_groups": list(recent_event_group_info),
    }
    return render(request, "trigger_app/home_page.html", context)
