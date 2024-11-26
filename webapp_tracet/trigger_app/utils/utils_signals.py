import datetime as dt
import logging
from datetime import datetime

from astropy import units as u
from astropy.coordinates import SkyCoord
from trigger_app.models.event import Event, EventGroup
from trigger_app.models.proposal import ProposalDecision, ProposalSettings

from .utils_api import make_trig_obs_request
from .utils_log import log_event

logger = logging.getLogger(__name__)


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

    context["reached_end"] = True
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

    context["reached_end"] = True
    return context


def link_event_to_group(context):

    event = context["event"]
    event_group = context["event_group"]

    Event.objects.filter(id=event.id).update(event_group_id=event_group)

    event = Event.objects.get(pk=event.id)
    context["event"] = event

    return context


def check_if_ignored(context):
    event = context["event"]
    if event.ignored:
        logger.info("Event ignored so do nothing")
        print(f"DEBUG - Event ignored so do nothing")

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


def update_event_group(event_group, event):
    if (
        event.pos_error is not None
        and event.pos_error < event_group.pos_error
        and event.pos_error != 0.0
    ):
        event_group.ra = event.ra
        event_group.dec = event.dec
        event_group.ra_hms = event.ra_hms
        event_group.dec_dms = event.dec_dms
        event_group.pos_error = event.pos_error

    event_group.latest_event_observed = event.event_observed

    event_group.save()
    return event_group


# proposal worth observing trigger functions


def trigger_observation(
    prop_dec,
    voevents,
    decision_reason_log,
    reason="First Observation",
    event_id=None,
):
    """Perform any comon observation checks, send off observations with the telescope's function then record observations in the Observations model.

    Parameters
    ----------
    prop_dec : `django.db.models.Model`
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
        "prop_dec": prop_dec,
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


def process_all_proposals(context):
    event_group = context["event_group"]
    event = context["event"]
    # event_coord = context.get("event_coord")

    prop_decs = fetch_proposal_decisions(event_group)

    if prop_decs.exists():
        logger.info(
            "Loop over all proposals settings and see if it's worth reobserving"
        )

        print(
            "DEBUG- Loop over all proposals settings and see if it's worth reobserving"
        )

        context["event_group"] = update_event_group(event_group, event)
        context["prop_decs"] = prop_decs
        context["prop_decs_exist"] = True
    else:

        # TODO selected only source types are same
        # proposal_settings = ProposalSettings.objects.all().order_by("priority")

        print("DEBUG - event_group.source_type: ", event_group.source_type)
        print("DEBUG - event.telescope: ", event.telescope)
        print("DEBUG - event.event_type: ", event.event_type)

        stream = event.telescope.upper() + "_" + event.event_type.upper()
        if stream[-2:] == "_-":
            stream = stream[:-2]

        print("DEBUG - stream: ", stream)
        print(
            "DEBUG - ProposalSettings.objects.filter(streams__contains=[stream]): ",
            ProposalSettings.objects.filter(streams__contains=[stream]),
        )

        proposal_settings = ProposalSettings.objects.filter(
            source_type=event_group.source_type,
            event_telescope__name=event.telescope,
            streams__contains=[stream],  #
            active=True,  # TODO use this filter when active column is added in ProposalSettings model
        ).order_by("priority")

        print("DEBUG - num of proposals : ", len(proposal_settings))

        if len(proposal_settings) == 0:
            print("DEBUG - no proposal settings found")
            return context

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
                version=prop_set.version,
            )

        prop_decs = fetch_proposal_decisions(event_group)

        context["event_group"] = update_event_group(event_group, event)
        context["prop_decs"] = prop_decs
        context["prop_decs_exist"] = False

    voevents = Event.objects.filter(trig_id=event_group.trig_id).order_by(
        "-recieved_data"
    )
    context["voevents"] = voevents

    return context
