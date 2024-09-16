import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

from django.shortcuts import get_object_or_404
from fastapi import HTTPException
from ninja import NinjaAPI, Path, Schema

# proposalsettings package
from proposalsettings.eventtelescope_factory import EventTelescopeFactory
from proposalsettings.models import (  # GrbSourceSettings,; GWSourceSettings,; NuSourceSettings,; ProposalSettings,
    ATCATelescopeSettings,
    EventTelescope,
    GrbSourceSettings,
    GWSourceSettings,
    MWATelescopeSettings,
    NuSourceSettings,
    ProposalSettings,
    SourceChoices,
    Telescope,
    TelescopeProjectId,
    TriggerOnChoices,
)
from proposalsettings.proposalsettings_factory import ProposalSettingsFactory
from proposalsettings.telescope_factory import TelescopeFactory
from proposalsettings.telescopeprojectid_factory import TelescopeProjectIdFactory
from propsettings_app.utils.utils_telescope_observe import (
    check_mwa_horizon_and_prepare_context,
    handle_atca_observation,
    handle_early_warning,
    handle_first_observation,
    handle_gw_voevents,
    handle_non_gw_observation,
    handle_skymap_event,
    prepare_observation_context,
)
from pydantic import BaseModel, Field

# from .factories import (
#     TelescopeFactory,
#     TelescopeProjectIdFactory,
# )
# from .pydmodels import ATCATelescopeSettings, GWProposalSettings, MWATelescopeSettings
from .schemas import (
    TRIGGER_ON,
    EventGroupSchema,
    EventSchema,
    ProposalDecisionSchema,
    TelescopeProjectIDSchema,
)


class ProposalObservationRequest(Schema):
    prop_dec: ProposalDecisionSchema
    voevent: EventSchema
    observation_reason: str = "First observation"


class TriggerObservationRequest(Schema):
    prop_dec: ProposalDecisionSchema
    voevents: List[EventSchema]
    decision_reason_log: str
    reason: str = "First Observation"
    event_id: int = None


def get_proposal_object(proposal_id: int):
    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    event_telescope_factory = EventTelescopeFactory()

    proposal_settings_factory = ProposalSettingsFactory(
        telescope_factory=telescope_factory,
        event_telescope_factory=event_telescope_factory,
        project_id_factory=project_id_factory,
    )

    proposal = proposal_settings_factory.filter_proposals_by_id(proposal_id=proposal_id)

    return proposal


logger = logging.getLogger(__name__)

# Initialize the Ninja API
app = NinjaAPI()


# Define the API endpoint
@app.get("/telescopes/", response=List[Telescope])
def get_event_telescopes(request):
    factory = TelescopeFactory()
    return factory.telescopes


# Define the API endpoint
@app.get("/eventtelescopes/", response=List[EventTelescope])
def get_event_telescopes(request):
    factory = EventTelescopeFactory()
    return factory.eventtelescopes


@app.get("/eventtelescope/{name}/", response=EventTelescope)
def get_event_telescope(request, name: str):
    factory = EventTelescopeFactory()
    telescope = factory.get_event_telescope_by_name(name)
    if not telescope:
        raise HTTPException(status_code=404, detail="EventTelescope not found")
    return telescope


@app.get("/telescope_project_ids/", response=list[TelescopeProjectId])
def get_telescope_project_ids(request):
    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    print(project_id_factory)

    return project_id_factory.telescope_projects


@app.get("/proposalsettings/", response=list[ProposalSettings])
def get_proposalsettings(request):
    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    event_telescope_factory = EventTelescopeFactory()

    proposal_settings_factory = ProposalSettingsFactory(
        telescope_factory=telescope_factory,
        event_telescope_factory=event_telescope_factory,
        project_id_factory=project_id_factory,
    )

    return proposal_settings_factory.proposals


@app.get("/proposalsettings_by_id/{id}/", response=ProposalSettings)
def get_proposalsettings_by_id(request, id: int):
    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    event_telescope_factory = EventTelescopeFactory()

    proposal_settings_factory = ProposalSettingsFactory(
        telescope_factory=telescope_factory,
        event_telescope_factory=event_telescope_factory,
        project_id_factory=project_id_factory,
    )

    proposal = proposal_settings_factory.filter_proposals_by_id(proposal_id=id)

    # Handle case where proposal is not found
    if not proposal:
        return app.create_response(
            request, {"detail": "Proposal not found"}, status=404
        )

    return proposal


@app.post("/trigger_observation/", response={200: Dict[str, Union[bool, str]]})
def api_trigger_observation(request, data: TriggerObservationRequest):

    prop_dec_pyd = ProposalDecisionSchema(**data.prop_dec.dict())

    proposal = get_proposal_object(prop_dec_pyd.proposal)
    prop_dec_pyd.proposal = proposal

    voevents_pyd = [EventSchema(**voevent.dict()) for voevent in data.voevents]
    decision_reason_log = data.decision_reason_log
    reason = data.reason
    event_id = data.event_id

    decision, decision_reason_log = trigger_observation(
        prop_dec_pyd, voevents_pyd, decision_reason_log, reason, event_id
    )

    return {"decision": "T", "decision_reason_log": decision_reason_log}


def trigger_observation(
    proposal_decision_model,
    voevents,
    decision_reason_log,
    reason="First Observation",
    event_id=None,
):
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

    print("source_settings:", proposal_decision_model.proposal.source_settings)
    print(
        "telescope_settings:",
        proposal_decision_model.proposal.telescope_settings.telescope,
    )

    context = check_mwa_horizon_and_prepare_context(context)

    # TODO: Remove this when we stop testing
    print("stop_processing:", context["stop_processing"])
    context["stop_processing"] = False

    if context["stop_processing"]:
        return context["decision"], context["decision_reason_log"]

    if context[
        "proposal_decision_model"
    ].proposal.telescope_settings.telescope.name.startswith("MWA"):

        print("DEBUG - MWA telescope")
        context = prepare_observation_context(context, voevents)

        if context["proposal_decision_model"].proposal.source_type == "GW":
            print("DEBUG - MWA telescope - GW")
            # Buffer dump if first event, use default array if early warning, process skymap if not early warning
            if len(voevents) == 1:
                # Dump out the last ~3 mins of MWA buffer to try and catch event
                context = handle_first_observation(context)

                # Handle the unique case of the early warning

                if context["latestVoevent"].event_type == "EarlyWarning":
                    print("DEBUG - MWA telescope - GW - EarlyWarning")
                    context = handle_early_warning(context)
                elif (
                    context["latestVoevent"].lvc_skymap_fits != None
                    and context["latestVoevent"].event_type != "EarlyWarning"
                ):
                    print("DEBUG - MWA telescope - GW - Skymap")
                    context = handle_skymap_event(context)
                    print("DEBUG - MWA telescope - GW - Skymap Calculated")

            # Repoint if there is a newer skymap with different positions
            if len(voevents) > 1 and context["latestVoevent"].lvc_skymap_fits:
                print("DEBUG - MWA telescope - GW - Repoint")
                context = handle_gw_voevents(context)

            print("Decision: ", context)
        else:
            print("passed Non-GW check")
            context = handle_non_gw_observation(context)

    elif context[
        "proposal_decision_model"
    ].proposal.telescope_settings.telescope.name.startswith("ATCA"):
        # Check if you can observe and if so send off mwa observation
        context = handle_atca_observation(context)
    else:
        context["decision_reason_log"] = (
            f"{context['decision_reason_log']}{datetime.utcnow()}: Event ID {context['event_id']}: Not making an MWA observation. \n"
        )

    return context["decision"], context["decision_reason_log"]


@app.post("/worth_observing/", response={200: Dict[str, Union[bool, str]]})
def check_proposal(request, data: ProposalObservationRequest):
    # Deserialize the nested objects

    prop_dec_pyd = ProposalDecisionSchema(**data.prop_dec.dict())
    voevent_pyd = EventSchema(**data.voevent.dict())
    proposal = get_proposal_object(prop_dec_pyd.proposal)
    prop_dec_pyd.proposal = proposal

    print("PROP DEC PYD:", prop_dec_pyd.proposal.telescope_settings)

    boolean_log_values = proposal_worth_observing(
        prop_dec_pyd, voevent_pyd, observation_reason="First observation."
    )

    print("PROCESSING WORTH OBSERVING")
    return boolean_log_values


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
    logger.info(f"Checking that proposal {prop_dec.proposal} is worth observing.")
    # Defaults if not worth observing
    trigger_bool = debug_bool = pending_bool = False
    decision_reason_log = prop_dec.decision_reason
    proj_source_bool = False

    print(prop_dec.proposal.testing)
    print(voevent.role)

    print(
        "prop_dec.proposal.event_telescope=",
        prop_dec.proposal.event_telescope.name,
    )
    print("voevent.telescope=", voevent.telescope)
    print(
        "prop_dec.proposal.source_type=",
        prop_dec.proposal.source_type,
    )
    print("prop_dec.event_group_id.source_type=", prop_dec.event_group_id.source_type)

    # if True:
    #     prop_dec.proposal.telescope_settings.event_telescope = None
    # prop_dec.proposal.telescope_settings.event_telescope.name = "Fermi"
    # prop_dec.event_group_id.source_type = "GRB"

    # Continue to next test
    if (
        prop_dec.proposal.event_telescope is None
        or str(prop_dec.proposal.event_telescope.name).strip()
        == voevent.telescope.strip()
    ):
        print("Next test")
        print(prop_dec.proposal.source_type)
        print(prop_dec.event_group_id.source_type)

        # This project observes events from this telescope
        # Check if this proposal thinks this event is worth observing
        if (
            prop_dec.proposal.source_type == "FS"
            and prop_dec.event_group_id.source_type == "FS"
        ):
            trigger_bool = True
            decision_reason_log = f"{decision_reason_log}{datetime.utcnow()}: Event ID {voevent.id}: Triggering on Flare Star {prop_dec.event_group_id.source_name}. \n"
            proj_source_bool = True

        elif (
            prop_dec.proposal.source_type == prop_dec.event_group_id.source_type
            and prop_dec.event_group_id.source_type in ["GRB", "GW", "NU"]
        ):
            print(prop_dec.proposal.id)
            (
                trigger_bool,
                debug_bool,
                pending_bool,
                decision_reason_log,
            ) = prop_dec.proposal.is_worth_observing(
                voevent, dec=prop_dec.dec, decision_reason_log=decision_reason_log
            )
            proj_source_bool = True
        else:
            print("DEBUG - proposal_worth_observing - not same values")

        if not proj_source_bool:
            # Proposal does not observe this type of source so update message
            decision_reason_log = f"{decision_reason_log}{datetime.utcnow()}: Event ID {voevent.id}: This proposal does not observe {prop_dec.event_group_id.source_type}s. \n"

    else:
        # Proposal does not observe event from this telescope so update message
        decision_reason_log = f"{decision_reason_log}{datetime.utcnow()}: Event ID {voevent.id}: This proposal does not trigger on events from {voevent.telescope}. \n"

    print(trigger_bool, debug_bool, pending_bool, decision_reason_log)

    return {
        "trigger_bool": trigger_bool,
        "debug_bool": debug_bool,
        "pending_bool": pending_bool,
        "proj_source_bool": proj_source_bool,
        "decision_reason_log": decision_reason_log,
    }
