import django_filters
from django.contrib.auth.decorators import login_required
from django.core.paginator import InvalidPage, Paginator
from django.forms import DateTimeInput
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .. import models
from ..utils import utils_alerts
from ..utils.utils_signals import trigger_observation


class ProposalDecisionFilter(django_filters.FilterSet):
    # DateTimeFromToRangeFilter raises exceptions in debugger for missing _before and _after keys

    recieved_data_after = django_filters.DateTimeFilter(
        field_name="recieved_data",
        lookup_expr="gte",
        widget=DateTimeInput(attrs={"type": "datetime-local"}),
    )
    recieved_data_before = django_filters.DateTimeFilter(
        field_name="recieved_data",
        lookup_expr="lte",
        widget=DateTimeInput(attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = models.proposal.ProposalDecision
        fields = "__all__"


def ProposalDecisionList(request):
    # Apply filters
    f = ProposalDecisionFilter(
        request.GET, queryset=models.proposal.ProposalDecision.objects.all()
    )
    ProposalDecision = f.qs

    # Get position error units
    poserr_unit = request.GET.get("poserr_unit", "deg")

    # Paginate
    page = request.GET.get("page", 1)
    paginator = Paginator(ProposalDecision, 100)
    try:
        ProposalDecision = paginator.page(page)
    except InvalidPage:
        # if the page contains no results (EmptyPage exception) or
        # the page number is not an integer (PageNotAnInteger exception)
        # return the first page
        ProposalDecision = paginator.page(1)

    strip_time_stamp(ProposalDecision)
    min_dec = (
        models.proposal.ProposalDecision.objects.filter()
        .order_by("recieved_data")
        .first()
        .recieved_data
    )

    return render(
        request,
        "trigger_app/proposal_decision_list.html",
        {
            "filter": f,
            "page_obj": ProposalDecision,
            "poserr_unit": poserr_unit,
            "min_dec": min_dec,
        },
    )
    

def ProposalDecision_details(request, id):
    prop_dec = models.proposal.ProposalDecision.objects.get(id=id)

    # Work out all the telescopes that observed the event
    events = models.event.Event.objects.filter(event_group_id=prop_dec.event_group_id)
    telescopes = []
    event_types = []

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
    for event in events:
        telescopes.append(event.telescope)
        event_types.append(event.event_type)
    # Make sure they are unique and put each on a new line
    telescopes = ".\n".join(list(set(telescopes)))
    event_types = " \n".join(list(set(event_types)))

    observations = models.observation.Observations.objects.filter(proposal_decision_id=id)
    poserr_unit = request.GET.get("poserr_unit", "deg")

    content = {
        "prop_dec": prop_dec,
        "telescopes": telescopes,
        "events": events,
        "event_types": event_types,
        "obs": observations,
        "poserr_unit": poserr_unit,
    }
    return render(request, "trigger_app/proposal_decision_details.html", content)

@login_required
def ProposalDecision_result(request, id, decision):
    prop_dec = models.proposal.ProposalDecision.objects.get(id=id)

    if decision:
        # Decision is True (1) so trigger an observation
        voevents = models.event.Event.objects.filter(trig_id=prop_dec.trig_id).order_by(
            "-recieved_data"
        )

        obs_decision, decision_reason_log = trigger_observation(
            prop_dec,
            voevents,
            f"{prop_dec.decision_reason}User decided to trigger. ",
            reason="User triggered observation",
        )
        if obs_decision == "E":
            # Error observing so send off debug
            trigger_bool = False
            debug_bool = True
        else:
            # Succesfully observed
            trigger_bool = True
            debug_bool = False

        prop_dec.decision_reason = decision_reason_log
        prop_dec.decision = obs_decision
        prop_dec.save()
        # send off alert messages to users and admins
        utils_alerts.send_all_alerts(trigger_bool, debug_bool, False, prop_dec)
    else:
        # False (0) so just update decision
        prop_dec.decision_reason += "User decided not to trigger. "
        prop_dec.decision = "I"
        prop_dec.save()

    return HttpResponseRedirect(f"/proposal_decision_details/{id}/")


def strip_time_stamp(prop_decs):
    for prop_dec in prop_decs:
        if prop_dec.decision_reason:
            prop_dec_lines = prop_dec.decision_reason.split("\n")
            stripped_lines = []
            for line in prop_dec_lines:
                stripped_lines.append(line[28:])
            prop_dec.decision_reason = "\n".join(stripped_lines)