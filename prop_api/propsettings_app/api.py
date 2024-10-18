import datetime as dt
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
from proposalsettings.models.telescope import (
    EventTelescope,
    Telescope,
    TelescopeProjectId,
)
from proposalsettings.proposalsettings_factory import ProposalSettingsFactory
from proposalsettings.telescope_factory import TelescopeFactory
from proposalsettings.telescopeprojectid_factory import TelescopeProjectIdFactory
from proposalsettings.utils import utils_process

from .schemas import (
    AllProposalsProcessRequest,
    EventGroupSchema,
    EventSchema,
    ProposalDecisionSchema,
    SkyCoordSchema,
)
from .utils import utils_api

# Initialize the Ninja API
# app = NinjaAPI()
app = Router(auth=JWTAuth())


# Define the API endpoint
@app.get("/telescopes/", response=List[Telescope])
def get_telescopes(request):
    """
    Retrieve a list of all telescopes.

    Returns:
        List[Telescope]: A list of all telescope objects.
    """
    factory = TelescopeFactory()
    return factory.telescopes


# Define the API endpoint
@app.get("/eventtelescopes/", response=List[EventTelescope])
def get_event_telescopes(request):
    """
    Retrieve a list of all event telescopes.

    Returns:
        List[EventTelescope]: A list of all event telescope objects.
    """
    factory = EventTelescopeFactory()
    return factory.eventtelescopes


@app.get("/eventtelescope/{name}/", response=EventTelescope)
def get_event_telescope_by_name(request, name: str):
    """
    Retrieve an event telescope by its name.

    Args:
        name (str): The name of the event telescope.

    Returns:
        EventTelescope: The event telescope object with the specified name.

    Raises:
        HTTPException: If the event telescope is not found.
    """
    factory = EventTelescopeFactory()
    telescope = factory.get_event_telescope_by_name(name)
    if not telescope:
        raise HTTPException(status_code=404, detail="EventTelescope not found")
    return telescope


@app.get("/telescope_project_ids/", response=list[TelescopeProjectId])
def get_telescope_project_ids(request):
    """
    Retrieve a list of all telescope project IDs.

    Returns:
        list[TelescopeProjectId]: A list of all telescope project ID objects.
    """
    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    print(project_id_factory)

    return project_id_factory.telescope_projects


@app.get("/proposalsettings/", response=list[ProposalSettings], auth=None)
def get_proposalsettings(request):
    """
    Retrieve a list of all proposal settings.

    Returns:
        list[ProposalSettings]: A list of all proposal settings objects.
    """
    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    event_telescope_factory = EventTelescopeFactory()

    proposal_settings_factory = ProposalSettingsFactory(
        telescope_factory=telescope_factory,
        event_telescope_factory=event_telescope_factory,
        project_id_factory=project_id_factory,
    )

    return proposal_settings_factory.proposals


@app.get("/proposalsettings_by_id/{id}/", response=ProposalSettings, auth=None)
def get_proposalsettings_by_id(request, id: int):
    """
    Retrieve a proposal settings object by its ID.

    Args:
        id (int): The ID of the proposal settings.

    Returns:
        ProposalSettings: The proposal settings object with the specified ID.

    Raises:
        HTTPException: If the proposal settings are not found.
    """
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


@app.post("/process_all_proposals/", response={200: Dict[str, Union[bool, str]]})
def api_process_all_proposals(request, data: AllProposalsProcessRequest):
    """
    Process all proposals based on the provided data.

    Args:
        data (AllProposalsProcessRequest): The request data containing proposal decisions,
                                           events, and other related information.

    Returns:
        Dict[str, Union[bool, str]]: A dictionary containing the processing result.

    """
    print("DEBUG - all proposals process request received")

    prop_decs_pyd = [
        ProposalDecisionSchema(**prop_dec.dict()) for prop_dec in data.prop_decs
    ]

    prop_decs_pyd_tmp = []
    for prop_dec_pyd in prop_decs_pyd:
        proposal = utils_api.get_proposal_object(prop_dec_pyd.proposal)
        prop_dec_pyd.proposal = proposal
        prop_decs_pyd_tmp.append(prop_dec_pyd)

    prop_decs_pyd = prop_decs_pyd_tmp

    voevents_pyd = [EventSchema(**voevent.dict()) for voevent in data.voevents]

    event_pyd = EventSchema(**data.event.dict())

    event_group_pyd = EventGroupSchema(**data.event_group.dict())

    if data.event_coord:
        event_coord = SkyCoordSchema(**data.event_coord.dict()).to_skycoord()
    else:
        event_coord = None

    context_all = {
        "event": event_pyd,
        "prop_decs": prop_decs_pyd,
        "voevents": voevents_pyd,
        "prop_decs_exist": data.prop_decs_exist,
        "event_group": event_group_pyd,
        "event_coord": event_coord,
    }

    context = utils_process.process_all_proposals(context_all)

    return {"message": "success"}
