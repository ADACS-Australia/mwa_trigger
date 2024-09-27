import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

from django.shortcuts import get_object_or_404
from fastapi import HTTPException
from ninja import NinjaAPI, Path, Router, Schema
from ninja_jwt.authentication import JWTAuth
# proposalsettings package
from proposalsettings.eventtelescope_factory import EventTelescopeFactory
# from proposalsettings.models import (EventTelescope, ProposalSettings,
#                                      Telescope, TelescopeProjectId)
from proposalsettings.models.proposal import ProposalSettings
from proposalsettings.models.telescope import (EventTelescope, Telescope,
                                               TelescopeProjectId)
from proposalsettings.proposalsettings_factory import ProposalSettingsFactory
from proposalsettings.telescope_factory import TelescopeFactory
from proposalsettings.telescopeprojectid_factory import \
    TelescopeProjectIdFactory

from .schemas import (EventSchema, ProposalDecisionSchema,
                      ProposalObservationRequest, TriggerObservationRequest)
from .utils import utils_api

logger = logging.getLogger(__name__)
print("standart logger:", __name__)

# Get a structlog logger
json_logger = logging.getLogger('django_json')


# Initialize the Ninja API
# app = NinjaAPI()
app = Router()

# Define the API endpoint
@app.get("/telescopes/", response=List[Telescope], auth=JWTAuth())
def get_telescopes(request):
    factory = TelescopeFactory()
    return factory.telescopes


# Define the API endpoint
@app.get("/eventtelescopes/", response=List[EventTelescope], auth=JWTAuth())
def get_event_telescopes(request):
    factory = EventTelescopeFactory()
    return factory.eventtelescopes


@app.get("/eventtelescope/{name}/", response=EventTelescope, auth=JWTAuth())
def get_event_telescope_by_name(request, name: str):
    factory = EventTelescopeFactory()
    telescope = factory.get_event_telescope_by_name(name)
    if not telescope:
        raise HTTPException(status_code=404, detail="EventTelescope not found")
    return telescope


@app.get("/telescope_project_ids/", response=list[TelescopeProjectId], auth=JWTAuth())
def get_telescope_project_ids(request):
    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    print(project_id_factory)

    return project_id_factory.telescope_projects


@app.get("/proposalsettings/", response=list[ProposalSettings], auth=None)
def get_proposalsettings(request):
    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    event_telescope_factory = EventTelescopeFactory()

    proposal_settings_factory = ProposalSettingsFactory(
        telescope_factory=telescope_factory,
        event_telescope_factory=event_telescope_factory,
        project_id_factory=project_id_factory,
    )
    # json_logger.info("Logging using pythonjsonlogger!", extra={"more_data": True})

    return proposal_settings_factory.proposals


@app.get("/proposalsettings_by_id/{id}/", response=ProposalSettings, auth=None)
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


@app.post("/trigger_observation/", response={200: Dict[str, Union[bool, str]]}, auth=JWTAuth())
def api_trigger_observation(request, data: TriggerObservationRequest):

    print("DEBUG - trigger observation received")
    
    prop_dec_pyd = ProposalDecisionSchema(**data.prop_dec.dict())

    proposal = utils_api.get_proposal_object(prop_dec_pyd.proposal)
    prop_dec_pyd.proposal = proposal

    voevents_pyd = [EventSchema(**voevent.dict()) for voevent in data.voevents]
    decision_reason_log = data.decision_reason_log
    reason = data.reason
    event_id = data.event_id

    telescopes = []
    latestVoevent = voevents_pyd[0]

    # print("latestVoevent:", latestVoevent)

    json_logger.info(
        "successfull api request",
        extra={
            "function": "api_trigger_observation",
            "trig_id": prop_dec_pyd.trig_id,
            "event_id": event_id,
        },
    )

    context = {
        "proposal_decision_model": prop_dec_pyd,
        "event_id": event_id,
        "decision_reason_log": decision_reason_log,
        "reason": reason,
        "telescopes": telescopes,
        "latestVoevent": latestVoevent,
        "mwa_sub_arrays": None,
        "stop_processing": False,
        "decision": None,
        "voevents": voevents_pyd,
    }

    print("source_settings:", proposal.source_settings)
    print(
        "telescope_settings:",
        proposal.telescope_settings.telescope,
    )

    # decision, decision_reason_log = trigger_observation(context, voevents_pyd)

    decision, decision_reason_log = proposal.trigger_gen_observation(context)

    # TODO ask when decision is None
    decision = decision if decision else "I"

    return {"decision": decision, "decision_reason_log": decision_reason_log}


@app.post("/worth_observing/", response={200: Dict[str, Union[bool, str]]}, auth=JWTAuth())
def worth_observing_proposal(request, data: ProposalObservationRequest):
    # Deserialize the nested objects

    prop_dec_pyd = ProposalDecisionSchema(**data.prop_dec.dict())
    voevent_pyd = EventSchema(**data.voevent.dict())
    proposal = utils_api.get_proposal_object(prop_dec_pyd.proposal)
    prop_dec_pyd.proposal = proposal

    print("PROP DEC PYD:", prop_dec_pyd.proposal.telescope_settings)

    json_logger.info(
        "successfull worth observing api request sent",
        extra={
            "function": "worth_observing_proposal",
            "trig_id": prop_dec_pyd.trig_id,
            "event_id": voevent_pyd.id,
            "proposal_id": prop_dec_pyd.proposal.id,
        },
    )

    boolean_log_values = utils_api.proposal_worth_observing(
        prop_dec_pyd, voevent_pyd, observation_reason="First observation."
    )

    json_logger.info(
        f"successfull worth observing proposal processed",
        extra={
            "function": "worth_observing_proposal",
            "trig_id": prop_dec_pyd.trig_id,
            "event_id": voevent_pyd.id,
            "proposal_id": prop_dec_pyd.proposal.id,
        },
    )


    print("PROCESSING WORTH OBSERVING done")
    return boolean_log_values
