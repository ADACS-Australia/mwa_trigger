
import logging

import django_filters
import voeventparse as vp
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import InvalidPage, Paginator
from django.db import models as dj_model
from django.forms import DateTimeInput
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from rest_framework import status
from rest_framework.authentication import (BasicAuthentication,
                                           SessionAuthentication)
from rest_framework.decorators import (api_view, authentication_classes,
                                       permission_classes)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from tracet import parse_xml

from .. import forms, models, serializers

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.level = logging.INFO

class EventFilter(django_filters.FilterSet):
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

    event_observed_after = django_filters.DateTimeFilter(
        field_name="event_observed",
        lookup_expr="gte",
        widget=DateTimeInput(attrs={"type": "datetime-local"}),
    )
    event_observed_before = django_filters.DateTimeFilter(
        field_name="event_observed",
        lookup_expr="lte",
        widget=DateTimeInput(attrs={"type": "datetime-local"}),
    )

    duration__lte = django_filters.NumberFilter(
        field_name="duration", lookup_expr="lte"
    )
    duration__gte = django_filters.NumberFilter(
        field_name="duration", lookup_expr="gte"
    )

    ra__lte = django_filters.NumberFilter(field_name="ra", lookup_expr="lte")
    ra__gte = django_filters.NumberFilter(field_name="ra", lookup_expr="gte")

    dec__lte = django_filters.NumberFilter(field_name="dec", lookup_expr="lte")
    dec__gte = django_filters.NumberFilter(field_name="dec", lookup_expr="gte")

    pos_error__lte = django_filters.NumberFilter(
        field_name="pos_error", lookup_expr="lte"
    )
    pos_error__gte = django_filters.NumberFilter(
        field_name="pos_error", lookup_expr="gte"
    )

    fermi_detection_prob__lte = django_filters.NumberFilter(
        field_name="fermi_detection_prob", lookup_expr="lte"
    )
    fermi_detection_prob__gte = django_filters.NumberFilter(
        field_name="fermi_detection_prob", lookup_expr="gte"
    )

    swift_rate_signif__lte = django_filters.NumberFilter(
        field_name="swift_rate_signif", lookup_expr="lte"
    )
    swift_rate_signif__gte = django_filters.NumberFilter(
        field_name="swift_rate_signif", lookup_expr="gte"
    )

    telescopes = django_filters.AllValuesMultipleFilter(field_name="telescope")

    class Meta:
        model = models.event.Event

        # Django-filter cannot hanlde django FileField so exclude from filters
        fields = (
            "recieved_data_after",
            "recieved_data_before",
            "event_observed_after",
            "event_observed_before",
            "duration__lte",
            "duration__gte",
            "ra__lte",
            "ra__gte",
            "dec__lte",
            "dec__gte",
            "pos_error__lte",
            "pos_error__gte",
            "fermi_detection_prob__lte",
            "fermi_detection_prob__gte",
            "swift_rate_signif__lte",
            "swift_rate_signif__gte",
            "ignored",
            "event_group_id__source_type",
            "trig_id",
            "telescope",
            "event_group_id__source_name",
            "sequence_num",
            "event_type",
            "telescopes",
        )
        filter_overrides = {
            dj_model.CharField: {
                "filter_class": django_filters.CharFilter,
                "extra": lambda f: {
                    "lookup_expr": "icontains",
                },
            },
        }


def EventList(request):
    # Apply filters
    f = EventFilter(
        request.GET, queryset=models.event.Event.objects.all().filter(role="observation")
    )
    events = f.qs

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

    # Get position error units
    poserr_unit = request.GET.get("poserr_unit", "deg")

    # Paginate
    page = request.GET.get("page", 1)
    paginator = Paginator(events, 100)
    try:
        events = paginator.page(page)
    except InvalidPage:
        # if the page contains no results (EmptyPage exception) or
        # the page number is not an integer (PageNotAnInteger exception)
        # return the first page
        events = paginator.page(1)

    min_rec = (
        models.event.Event.objects.filter().order_by("recieved_data").first().recieved_data
    )
    min_obs = (
        models.event.Event.objects.filter().order_by("event_observed").first().event_observed
    )

    has_filter = any(field in request.GET for field in set(f.get_fields()))
    return render(
        request,
        "trigger_app/voevent_list.html",
        {
            "filter": f,
            "page_obj": events,
            "poserr_unit": poserr_unit,
            "has_filter": has_filter,
            "min_rec": str(min_rec),
            "min_obs": str(min_obs),
        },
    )


def TestEventList(request):
    # Apply filters
    f = EventFilter(
        request.GET, queryset=models.event.Event.objects.all().filter(role="test")
    )
    events = f.qs

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

    # Get position error units
    poserr_unit = request.GET.get("poserr_unit", "deg")

    # Paginate
    page = request.GET.get("page", 1)
    paginator = Paginator(events, 100)
    try:
        events = paginator.page(page)
    except InvalidPage:
        # if the page contains no results (EmptyPage exception) or
        # the page number is not an integer (PageNotAnInteger exception)
        # return the first page
        events = paginator.page(1)

    min_rec = (
        models.event.Event.objects.filter().order_by("recieved_data").first().recieved_data
    )
    min_obs = (
        models.event.Event.objects.filter().order_by("event_observed").first().event_observed
    )

    has_filter = any(field in request.GET for field in set(f.get_fields()))
    return render(
        request,
        "trigger_app/voevent_list.html",
        {
            "filter": f,
            "page_obj": events,
            "poserr_unit": poserr_unit,
            "has_filter": has_filter,
            "min_rec": str(min_rec),
            "min_obs": str(min_obs),
        },
    )

def voevent_view(request, id):
    event = models.event.Event.objects.get(id=id)
    v = vp.loads(event.xml_packet.encode())
    xml_pretty_str = vp.prettystr(v)
    return HttpResponse(xml_pretty_str, content_type="text/xml")



def parse_and_save_xml(xml):
    logger.info(f"Attempting to parse xml {xml}")
    trig = parse_xml.parsed_VOEvent(None, packet=xml)
    logger.info(f"Successfully parsed xml {trig}")
    data = {
        "telescope": trig.telescope,
        "xml_packet": xml,
        "duration": trig.event_duration,
        "trig_id": trig.trig_id,
        "self_generated_trig_id": trig.self_generated_trig_id,
        "sequence_num": trig.sequence_num,
        "event_type": trig.event_type,
        "role": trig.role,
        "ra": trig.ra,
        "dec": trig.dec,
        "ra_hms": trig.ra_hms,
        "dec_dms": trig.dec_dms,
        "pos_error": trig.err,
        "ignored": trig.ignore,
        "source_name": trig.source_name,
        "source_type": trig.source_type,
        "event_observed": trig.event_observed,
        "fermi_most_likely_index": trig.fermi_most_likely_index,
        "fermi_detection_prob": trig.fermi_detection_prob,
        "swift_rate_signif": trig.swift_rate_signif,
        "hess_significance": trig.hess_significance,
        "antares_ranking": trig.antares_ranking,
        "lvc_false_alarm_rate": trig.lvc_false_alarm_rate,
        "lvc_binary_neutron_star_probability": trig.lvc_binary_neutron_star_probability,
        "lvc_neutron_star_black_hole_probability": trig.lvc_neutron_star_black_hole_probability,
        "lvc_binary_black_hole_probability": trig.lvc_binary_black_hole_probability,
        "lvc_terrestial_probability": trig.lvc_terrestial_probability,
        "lvc_includes_neutron_star_probability": trig.lvc_includes_neutron_star_probability,
        "lvc_instruments": trig.lvc_instruments,
        "lvc_skymap_fits": trig.lvc_skymap_fits,
    }

    if trig.lvc_skymap_file:
        data["lvc_skymap_file"] = ContentFile(
            trig.lvc_skymap_file, f"{trig.trig_id}_skymap.fits"
        )

    logger.info(f"New event data {data}")

    new_event = serializers.EventSerializer(data=data)
    if new_event.is_valid():
        logger.info(f"Successfully serialized event {new_event.validated_data}")
        new_event.save()
        logger.info(f"Successfully saved event {new_event.validated_data}")
        return new_event


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def event_create(request):
    logger.info("Request to create an event received", extra={"event_create": True})
    logger.info(f"request.data:{request.data}")
    xml_string = request.data["xml_packet"]
    new_event = parse_and_save_xml(xml_string)

    if new_event:
        logger.info("Event created response given to user")
        logger.info(
            "Request to create an event received", extra={"event_create_finished": True}
        )
        return Response(new_event.data, status=status.HTTP_201_CREATED)
    else:
        logger.debug(request.data)
        logger.info(
            "Request to create an event received", extra={"event_create_finished": True}
        )
        return Response(new_event.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
def test_upload_xml(request):
    proposals = models.proposal.ProposalSettings.objects.filter(testing=False)
    if request.method == "POST":
        form = forms.TestEvent(request.POST)
        if form.is_valid():
            # Parse and submit the Event
            xml_string = str(request.POST["xml_packet"])
            logger.info(f"Test_upload_xml xml_string:{xml_string}")
            parse_and_save_xml(xml_string)
            logger.info(f"Test_upload_xml xml_string:{xml_string}")
            return HttpResponseRedirect("/")
    else:
        form = forms.TestEvent()
    return render(
        request,
        "trigger_app/test_upload_xml_form.html",
        {"form": form, "proposals": proposals},
    )
