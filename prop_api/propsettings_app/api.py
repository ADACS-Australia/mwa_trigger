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
@app.get("/telescopes/", response=List[Telescope], auth=None)
def get_telescopes(request):
    """
    Retrieve a list of all telescopes.

    Returns:
        List[Telescope]: A list of all telescope objects.
    """
    factory = TelescopeFactory()
    return factory.telescopes


# Define the API endpoint
@app.get("/eventtelescopes/", response=List[EventTelescope], auth=None)
def get_event_telescopes(request):
    """
    Retrieve a list of all event telescopes.

    Returns:
        List[EventTelescope]: A list of all event telescope objects.
    """
    factory = EventTelescopeFactory()
    return factory.eventtelescopes


@app.get("/eventtelescope/{name}/", response=EventTelescope, auth=None)
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


@app.get("/telescope_project_ids/", response=list[TelescopeProjectId], auth=None)
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


@app.get(
    "/proposalsettings_update/",
    response={200: Dict[str, Union[List[ProposalSettings], List[str], str, None]]},
    auth=None,
)
def get_proposalsettings_update(request):
    """
    Retrieve a list of all proposal settings and update their code directories.

    Returns:
        list[ProposalSettings]: A list of all proposal settings objects.
    """
    import logging
    import os
    import shutil

    logger = logging.getLogger(__name__)
    errors = []

    telescope_factory = TelescopeFactory()
    project_id_factory = TelescopeProjectIdFactory(telescope_factory=telescope_factory)
    event_telescope_factory = EventTelescopeFactory()

    proposal_settings_factory = ProposalSettingsFactory(
        telescope_factory=telescope_factory,
        event_telescope_factory=event_telescope_factory,
        project_id_factory=project_id_factory,
    )

    # Process each proposal
    for prop in proposal_settings_factory.proposals:
        try:
            # Create target directory path
            target_dir = (
                f"/shared/models/prop_{prop.proposal_id.lower()}_{prop.version}"
            )
            source_dir = f"/app/proposalsettings/models/prop_{prop.proposal_id.lower()}"

            print(f"DEBUG - target_dir: {target_dir}")
            print(f"DEBUG - source_dir: {source_dir}")

            # Remove target directory if it exists
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)

            # Create fresh target directory
            os.makedirs(target_dir)

            if os.path.exists(source_dir):
                # Copy all files from source to target
                for item in os.listdir(source_dir):
                    source_item = os.path.join(source_dir, item)
                    target_item = os.path.join(target_dir, item)
                    if os.path.isfile(source_item):
                        shutil.copy2(source_item, target_item)
            else:
                raise FileNotFoundError(f"Source directory not found: {source_dir}")

        except Exception as e:
            error_msg = f"Error processing proposal {prop.proposal_id}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    if errors:
        return {
            "status": "error",
            "proposals": proposal_settings_factory.proposals,
            "errors": errors,
        }

    print("DEBUG - proposalsettings_update success")

    # return proposal_settings_factory.proposals

    return {
        "status": "success",
        "proposals": proposal_settings_factory.proposals,
        "errors": None,
    }


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
