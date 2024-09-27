import json
import logging
import os
import time

import requests
from django.conf import settings
from trigger_app.models.proposal import ProposalSettings
from trigger_app.models.telescope import (EventTelescope, Telescope,
                                          TelescopeProjectID)
from trigger_app.schemas import (EventSchema, ProposalDecisionSchema,
                                 PydProposalSettings)

logger = logging.getLogger(__name__)

json_logger = logging.getLogger('django_json')

# Create a global session object
session = None

def init_session():
    global session
    session = requests.Session()  # Create the session object

    # Set default headers for the session
    session.headers.update({
        "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
        "Content-Type": "application/json",
    })

def get_session():
    """
    Returns the global session object.
    """
    return session

def update_access_token(new_token):
    """
    Updates the global ACCESS_TOKEN with a new value.
    """
    # Update the global settings variable
    settings.ACCESS_TOKEN = new_token
    print(f"Access token updated: {settings.ACCESS_TOKEN}")

def fetch_new_access_token(username, password):
    session = get_session()
    
    url = "http://api:8000/api/token/pair"
    
    # Define the payload with user credentials
    payload = {
        "username": username,
        "password": password
    }
    
    # Make a POST request to the login endpoint
    response = session.post(url, json=payload)
    
    # If login is successful, return the access token
    if response.status_code == 200:
        new_token = response.json().get("access")
        update_access_token(new_token)
        session.headers.update({"Authorization": f"Bearer {new_token}"})
        

def get_access_token(username, password):
    session = get_session()
    
    url = "http://api:8000/api/token/pair"
    
    # Define the payload with user credentials
    payload = {
        "username": username,
        "password": password
    }
    
    # Make a POST request to the login endpoint
    response = session.post(url, json=payload)
    
    # If login is successful, return the access token
    if response.status_code == 200:
        new_token = response.json().get("access")
        update_access_token(new_token)
        session.headers.update({"Authorization": f"Bearer {new_token}"})
        
        return new_token
    else :
        return None


def make_trig_obs_request(context, voevents):
    start_time = time.time()

    prop_dec_data_str = ProposalDecisionSchema.from_orm(
        context["proposal_decision_model"]
    ).json()
    voevents_data_str = [
        json.loads(EventSchema.from_orm(voevent).json()) for voevent in voevents
    ]

    # print(prop_dec_data_str)

    payload = {
        "prop_dec": json.loads(prop_dec_data_str),
        "voevents": voevents_data_str,
        "decision_reason_log": context["decision_reason_log"],
        "reason": context["reason"],
        "event_id": context["event_id"],
    }

    session = get_session()
    response = session.post("http://api:8000/api/trigger_observation/", json=payload)
    
    if response.status_code == 401:
        access_token = get_access_token(settings.AUTH_USERNAME, settings.AUTH_PASSWORD)
        
        if access_token:
            session = get_session()
            response = session.post("http://api:8000/api/trigger_observation/", json=payload)
            print("RESPONSE:", response.status_code)
    
    if response.status_code != 200:
        logger.error("Request unsuccessful")

        json_logger.error(
            "trigger observation api request - error",
            extra={
                "function": "make_api_request",
                "event_id": context["event_id"],
                "trig_id": context["proposal_decision_model"].trig_id,
            },
        )
        return None

    api_response = response.json()
    print("API RESPONSE:", api_response)

    end_time = time.time()
    print(f"API Execution time: {end_time - start_time} seconds")

    json_logger.info(
        "trigger observation api request - success",
        extra={
            "function": "make_api_request",
            "event_id": context["event_id"],
            "trig_id": context["proposal_decision_model"].trig_id,
        },
    )

    return api_response["decision"], api_response["decision_reason_log"]



def make_propset_api_request(context):
    
    prop_dec_data_str = ProposalDecisionSchema.from_orm(context["prop_dec"]).json()
    voevent_data_str = EventSchema.from_orm(context["voevent"]).json()

    payload = {
        "prop_dec": json.loads(prop_dec_data_str),
        "voevent": json.loads(voevent_data_str),
        "observation_reason": context["observation_reason"],
    }

    json_logger.info(
        "make proposal worth observing api request",
        extra={
            "function": "make_api_request",
            "event_id": context["voevent"].id,
            "trig_id": context["prop_dec"].trig_id,
        },
    )
    
    session = get_session()
    response = session.post("http://api:8000/api/worth_observing/", json=payload)

    if response.status_code == 401:
        access_token = get_access_token(settings.AUTH_USERNAME, settings.AUTH_PASSWORD)
        
        if access_token:
            session = get_session()
            response = session.post("http://api:8000/api/worth_observing/", json=payload)
            print("RESPONSE:", response.status_code)

    if response.status_code != 200:
        logger.error("Request unsuccessful")

        json_logger.error(
            "proposal worth observing api request - error",
            extra={
                "function": "make_api_request",
                "event_id": context["voevent"].id,
                "trig_id": context["prop_dec"].trig_id,
            },
        )
        return None

    json_logger.debug(
        "proposal worth observing api request - success",
        extra={
            "function": "make_api_request",
            "event_id": context["voevent"].id,
            "trig_id": context["prop_dec"].trig_id,
        },
    )

    api_response = response.json()
    context.update(
        {
            "trigger_bool": api_response["trigger_bool"],
            "debug_bool": api_response["debug_bool"],
            "pending_bool": api_response["pending_bool"],
            "decision_reason_log": api_response["decision_reason_log"],
        }
    )

    json_logger.info(
        f"api request success - trigger_bool: {context['trigger_bool']} debug_bool: {context['debug_bool']} pending_bool {context['pending_bool']}",
        extra={
            "function": "make_api_request",
            "event_id": context["voevent"].id,
            "trig_id": context["prop_dec"].trig_id,
        },
    )
    return context


def get_prop_settings_from_api(order_by: str = "id"):
    session = get_session()
    response = session.get("http://api:8000/api/proposalsettings/")
    
    if response.status_code == 401:
        access_token = get_access_token(settings.AUTH_USERNAME, settings.AUTH_PASSWORD)
        
        if access_token:
            session = get_session()
            response = session.post("http://api:8000/api/proposalsettings/")
            print("RESPONSE:", response.status_code)

    if response.status_code != 200:
        logger.error("Request unsuccessful")

        return None
    
    return response



# def get_prop_settings_from_api_non_table(order_by: str = "id"):
#     response = get_prop_settings_from_api()
#     print("RESPONSE:", response.json())

#     pyd_prop_settings = [
#         PydProposalSettings(**prop_set_data)
#         for prop_set_data in response.json()
#     ]
#     pyd_prop_settings_sorted = sorted(pyd_prop_settings, key=lambda prop: prop.id)
#     if order_by == "priority":
#         pyd_prop_settings_sorted = sorted(
#             pyd_prop_settings, key=lambda prop: prop.priority
#         )

#     prop_settings = [
#         ProposalSettingsNoTable(**prop.dict()) for prop in pyd_prop_settings_sorted
#     ]

#     return prop_settings


def get_prop_setting_from_api_with_table(id: int):

    api_url = f"http://api:8000/api/proposalsettings_by_id/{id}/"
    response = requests.get(api_url)

    pyd_instance = PydProposalSettings(
        **{
            **response.json()["telescope_settings"],
            **response.json()["source_settings"],
        }
    )

    # prop_setting = ProposalSettingsNoTable(**pyd_prop_set.dict())
    prop_setting = create_proposal_settings_from_pydantic(pyd_instance)

    return prop_setting


def create_proposal_settings_from_pydantic(
    pyd_instance: PydProposalSettings, id: int = 8
):
    # Convert nested fields
    telescope_data = pyd_instance.telescope.dict()
    project_id_data = pyd_instance.project_id.dict()
    event_telescope_data = (
        pyd_instance.event_telescope.dict() if pyd_instance.event_telescope else None
    )

    # Get or create the Telescope instance
    telescope_instance, _ = Telescope.objects.get_or_create(**telescope_data)

    # Update project_id_data to replace telescope with the actual instance
    project_id_data["telescope"], _ = Telescope.objects.get_or_create(
        name=project_id_data["telescope"]["name"]
    )

    # Get or create the TelescopeProjectID instance
    project_id_instance, _ = TelescopeProjectID.objects.get_or_create(**project_id_data)

    # Get or create the EventTelescope instance if event_telescope is provided
    event_telescope_instance = None
    if event_telescope_data:
        event_telescope_instance, _ = EventTelescope.objects.get_or_create(
            **event_telescope_data
        )

    # Prepare the data for ProposalSettings model
    proposal_data = pyd_instance.dict()
    proposal_data["telescope"] = telescope_instance
    proposal_data["project_id"] = project_id_instance
    proposal_data["event_telescope"] = event_telescope_instance

    # Create the ProposalSettings instance
    proposal_setting = ProposalSettings.objects.create(**proposal_data)

    proposal_data["id"] = id
    proposal_data["proposal_id"] = "test"
    return proposal_setting

def get_prop_settings_from_api_non_table(order_by: str = "id"):
    response = get_prop_settings_from_api()
    
    pyd_prop_settings = [
        PydProposalSettings(**prop_set_data)
        for prop_set_data in response.json()
    ]
    pyd_prop_settings_sorted = sorted(pyd_prop_settings, key=lambda prop: prop.id)
    if order_by == "priority":
        pyd_prop_settings_sorted = sorted(
            pyd_prop_settings, key=lambda prop: prop.priority
        )

    prop_settings = []
    for prop in pyd_prop_settings_sorted:
        # Create or get Telescope instance
        telescope, _ = Telescope.objects.get_or_create(
            name=prop.project_id.telescope.name,
            defaults={
                'lon': prop.project_id.telescope.lon,
                'lat': prop.project_id.telescope.lat,
                'height': prop.project_id.telescope.height
            }
        )

        # Create or get TelescopeProjectID instance
        project_id, _ = TelescopeProjectID.objects.get_or_create(
            id=prop.project_id.id,
            defaults={
                'password': prop.project_id.password,
                'description': prop.project_id.description,
                'atca_email': prop.project_id.atca_email,
                'telescope': telescope
            }
        )

        # Create or get EventTelescope instance
        event_telescope = None
        if prop.event_telescope:
            event_telescope, _ = EventTelescope.objects.get_or_create(
                name=prop.event_telescope.name
            )

        # Create ProposalSettingsNoTable instance
        prop_setting = ProposalSettings(
            id=prop.id,
            proposal_id=prop.proposal_id,
            telescope=telescope,
            project_id=project_id,
            proposal_description=prop.proposal_description,
            priority=prop.priority,
            event_telescope=event_telescope,
            testing=prop.testing,
            source_type=prop.source_type,
            repointing_limit=prop.telescope_settings['repointing_limit'],
            active=getattr(prop, 'active', True),  # Set active to True if not present in API data
        )
        prop_settings.append(prop_setting)

    return prop_settings


# def update_proposal_settings_from_api():
#     api_data = get_prop_settings_from_api_non_table()
#     ProposalSettings.objects.bulk_create(api_data, ignore_conflicts=True)
#     ProposalSettings.objects.bulk_update(api_data, fields=[
#         'telescope', 'project_id', 'proposal_description', 'priority',
#         'event_telescope', 'testing', 'source_type','repointing_limit',
#     ])

def update_proposal_settings_from_api():
    api_data = get_prop_settings_from_api_non_table()
    
    # Get all existing proposal IDs
    existing_proposal_ids = set(ProposalSettings.objects.values_list('proposal_id', flat=True))
    
    # Create a set of proposal IDs from the API data
    api_proposal_ids = set(prop.proposal_id for prop in api_data)
    
    # Find proposals that are not in the API data
    inactive_proposals = existing_proposal_ids - api_proposal_ids
    
    # Update or create proposals from API data
    ProposalSettings.objects.bulk_create(api_data, ignore_conflicts=True)
    ProposalSettings.objects.bulk_update(api_data, fields=[
        'telescope', 'project_id', 'proposal_description', 'priority',
        'event_telescope', 'testing', 'source_type', 'repointing_limit',
        'active',
    ])
    
    # Set inactive proposals
    ProposalSettings.objects.filter(proposal_id__in=inactive_proposals).update(active=False)