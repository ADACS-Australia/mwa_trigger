import django_filters
from django.core.paginator import InvalidPage, Paginator
from django.http import QueryDict
from django.shortcuts import render

from .. import models


class EventGroupFilter(django_filters.FilterSet):
    telescope = django_filters.ChoiceFilter(
        field_name="telescope",
        choices=(("SWIFT", "SWIFT"), ("Fermi", "Fermi"), ("LVC", "LVC")),
        method="filter_telescope",
    )

    def filter_telescope(self, queryset, name, value):
        # construct the full lookup expression.
        return queryset.filter(voevent__telescope=value)

    class Meta:
        model = models.event.EventGroup
        fields = ["ignored", "source_type", "telescope"]


def EventGroupList(request):
    # Apply filters
    req = request.GET
    if not req.dict():
        req = QueryDict("ignored=False&source_type=GRB&telescope=SWIFT")

    f = EventGroupFilter(
        req,
        queryset=models.event.EventGroup.objects.distinct().filter(
            voevent__role="observation"
        ),
    )
    eventgroups = f.qs

    prop_settings = models.proposal.ProposalSettings.objects.all()
    # Paginate
    page = request.GET.get("page", 1)
    # zip the trigger event and the tevent_telescope_list together so I can loop over both in the html
    paginator = Paginator(eventgroups, 100)
    try:
        event_group_ids_paged = paginator.page(page)
    except InvalidPage:
        event_group_ids_paged = paginator.page(1)

    recent_triggers_info, page_obj = grab_decisions_for_event_groups(
        event_group_ids_paged
    )

    return render(
        request,
        "trigger_app/event_group_list.html",
        {
            "filter": f,
            "trigger_info": recent_triggers_info,
            "settings": prop_settings,
            "page_obj": page_obj,
        },
    )


def TestEventGroupList(request):
    # Apply filters
    req = request.GET
    if not req.dict():
        req = QueryDict("ignored=False&source_type=GRB&telescope=SWIFT")

    f = EventGroupFilter(
        req,
        queryset=models.event.EventGroup.objects.distinct().filter(
            voevent__role="test"
        ),
    )
    eventgroups = f.qs

    prop_settings = models.proposal.ProposalSettings.objects.all()
    # Paginate
    page = request.GET.get("page", 1)
    # zip the trigger event and the tevent_telescope_list together so I can loop over both in the html
    paginator = Paginator(eventgroups, 100)
    try:
        event_group_ids_paged = paginator.page(page)
    except InvalidPage:
        event_group_ids_paged = paginator.page(1)

    recent_triggers_info, page_obj = grab_decisions_for_event_groups(
        event_group_ids_paged
    )

    return render(
        request,
        "trigger_app/event_group_list.html",
        {
            "filter": f,
            "trigger_info": recent_triggers_info,
            "settings": prop_settings,
            "page_obj": page_obj,
        },
    )


def EventGroup_details(request, tid):
    event_group = models.event.EventGroup.objects.get(id=tid)

    # grab telescope names
    events = models.event.Event.objects.filter(event_group_id=event_group)
    telescopes = " ".join(set(events.values_list("telescope", flat=True)))

    for event in events:
        if event.source_type == "GW":
            if event.lvc_binary_neutron_star_probability is not None:
                if event.lvc_binary_neutron_star_probability > 0.50:
                    event.classification = "BNS"
                elif event.lvc_neutron_star_black_hole_probability > 0.50:
                    event.classification = "NSBH"
                elif event.lvc_binary_black_hole_probability > 0.50:
                    event.classification = "BBH"
                elif event.lvc_terrestial_probability > 0.50:
                    event.classification = "TERE"
            else:
                event.classification = "NOPROB"
        else:
            event.classification = None

    # list all prop decisions
    prop_decs = models.proposal.ProposalDecision.objects.filter(
        event_group_id=event_group
    )

    # Grab obs if the exist
    obs = []
    for prop_dec in prop_decs:
        obs += models.observation.Observations.objects.filter(
            proposal_decision_id=prop_dec
        )
    strip_time_stamp(prop_decs)

    # Get position error units
    poserr_unit = request.GET.get("poserr_unit", "deg")

    context = {
        "event_group": event_group,
        "events": events,
        "obs": obs,
        "prop_decs": prop_decs,
        "telescopes": telescopes,
        "poserr_unit": poserr_unit,
    }

    return render(request, "trigger_app/event_group_details.html", context)


def grab_decisions_for_event_groups(event_groups):
    # For the event groups, grab all useful information like each proposal decision was

    prop_settings = models.proposal.ProposalSettings.objects.all()[:15]

    telescope_list = []
    source_name_list = []
    proposal_decision_list = []
    proposal_decision_id_list = []
    role_list = []
    stream_list = []

    for event_group in event_groups:
        event_group_events = models.event.Event.objects.filter(
            event_group_id=event_group
        ).order_by("recieved_data")

        event_group_events_not_ignored = models.event.Event.objects.filter(
            event_group_id=event_group, ignored=False
        ).order_by("recieved_data")

        telescope_list.append(
            " ".join(set(event_group_events.values_list("telescope", flat=True)))
        )

        # stream_list.append(
        #     event_group_events_not_ignored.first().event_type
        #     if event_group_events_not_ignored.exists()
        #     else ""
        # )

        stream_list.append(
            list(
                set(event_group_events_not_ignored.values_list("event_type", flat=True))
            )
            if event_group_events_not_ignored.exists()
            else []
        )

        event_with_source_name = list(
            filter(lambda x: x.source_name is not None, list(event_group_events))
        )
        if len(event_with_source_name) > 0:
            source_name_list.append(event_with_source_name[0].source_name)
        else:
            source_name_list.append(event_group_events.first().source_name)
        event_with_role = list(
            filter(lambda x: x.role is not None, list(event_group_events))
        )
        if len(event_with_role) > 0:
            role_list.append(event_with_role[0].role)
        else:
            role_list.append("unknown")
        # grab decision for each proposal
        decision_list = []
        decision_id_list = []
        for prop in prop_settings:
            this_decision = models.proposal.ProposalDecision.objects.filter(
                event_group_id=event_group, proposal=prop
            )
            if this_decision.exists():
                decision_list.append(this_decision.first().get_decision_display())
                decision_id_list.append(this_decision.first().id)
            else:
                decision_list.append("")
                decision_id_list.append("")
        proposal_decision_list.append(decision_list)
        proposal_decision_id_list.append(decision_id_list)

    # zip into something that you can iterate over in the html
    return (
        list(
            zip(
                event_groups,
                role_list,
                telescope_list,
                source_name_list,
                proposal_decision_list,
                proposal_decision_id_list,
                stream_list,
            )
        ),
        event_groups,
    )


def strip_time_stamp(prop_decs):
    for prop_dec in prop_decs:
        if prop_dec.decision_reason:
            prop_dec_lines = prop_dec.decision_reason.split("\n")
            stripped_lines = []
            for line in prop_dec_lines:
                stripped_lines.append(line[28:])
            prop_dec.decision_reason = "\n".join(stripped_lines)
