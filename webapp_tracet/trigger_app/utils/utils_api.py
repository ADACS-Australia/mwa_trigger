import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import requests
from django.conf import settings
from requests.exceptions import RequestException
from trigger_app.models.proposal import ProposalSettings
from trigger_app.models.telescope import (EventTelescope, Telescope,
                                          TelescopeProjectID)
from trigger_app.schemas import (EventGroupSchema, EventSchema,
                                 ProposalDecisionSchema, PydProposalSettings,
                                 SkyCoordSchema)

logger = logging.getLogger(__name__)

def get_access_token(username: str, password: str):
    url = f"{settings.LOGIC_API_URL}/api/token/pair"
    
    # Define the payload with user credentials
    payload = {
        "username": username,
        "password": password
    }
    
    # Make a POST request to the login endpoint
    response = requests.post(url, json=payload)
    
    # If login is successful, return the access token
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access")  # Get the access token from the response
        return access_token
    else:
        return None
    
def update_access_token(new_token: str):
    """
    Updates the global ACCESS_TOKEN with a new value.
    """
    # Update the global settings variable
    settings.ACCESS_TOKEN = new_token
    print(f"Access token updated: {settings.ACCESS_TOKEN}")
    
    
class APISession:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        })
        # self.refresh_token()

    def refresh_token(self):
        new_token = get_access_token(settings.AUTH_USERNAME, settings.AUTH_PASSWORD)
        if new_token:
            self.session.headers["Authorization"] = f"Bearer {new_token}"
            update_access_token(new_token)

    def request(self, method: str, endpoint: str, **kwargs):
        url = f"{settings.LOGIC_API_URL}/api/{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            if response.status_code == 401:
                self.refresh_token()
                response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except RequestException as e:
            print(f"Request failed: {str(e)}")
            raise

# Create a global session instance
api_session = None

def initialize_api_session():
    global api_session
    if api_session is None:
        api_session = APISession()

def get_api_session():
    global api_session
    if api_session is None:
        initialize_api_session()
    return api_session


def make_trig_obs_request(context: Dict[str, Any], voevents: List[Any]) -> tuple:

    prop_dec_data_str = ProposalDecisionSchema.from_orm(
        context["prop_dec"]
    ).json()
    voevents_data_str = [
        json.loads(EventSchema.from_orm(voevent).json()) for voevent in voevents
    ]

    payload = {
        "prop_dec": json.loads(prop_dec_data_str),
        "voevents": voevents_data_str,
        "decision_reason_log": context["decision_reason_log"],
        "reason": context["reason"],
        "event_id": context["event_id"],
    }

    try:
        response = api_session.request("POST", "trigger_observation/", json=payload)
        api_response = response.json()

        return api_response["decision"], api_response["decision_reason_log"]

    except Exception as e:
        error_message = f"Error in make_trig_obs_request: {str(e)}"
        
        return None, None


def get_prop_settings_from_api(order_by: str = "id") -> Optional[dict]:
    try:
        response = api_session.request("GET", "proposalsettings/")
        
        if response.status_code != 200:
            logger.error(f"Request unsuccessful. Status code: {response.status_code}")
            return None
        
        return response

    except Exception as e:
        logger.error(f"Error in get_prop_settings_from_api: {str(e)}")
        return None

def make_process_all_proposals_request(context: Dict[str, Any]) -> Dict[str, Any]:
    prop_decs_data_str = [
        json.loads(ProposalDecisionSchema.from_orm(prop_dec).json()) 
        for prop_dec in context["prop_decs"]
    ]
    
    voevents_data_str = [
        json.loads(EventSchema.from_orm(voevent).json()) 
        for voevent in context["voevents"]
    ]
    
    event_data_str = json.loads(EventSchema.from_orm(context["event"]).json())
    
    event_group_data_str = json.loads(EventGroupSchema.from_orm(context["event_group"]).json())

    payload = {
        "prop_decs": prop_decs_data_str,
        "voevents": voevents_data_str,
        "event": event_data_str,
        "event_group": event_group_data_str,
        "prop_decs_exist": context["prop_decs_exist"]
    }
    
    if context.get("event_coord"):
        event_coord_data_str = json.loads(SkyCoordSchema.from_skycoord(context["event_coord"]).json())
        payload["event_coord"] = event_coord_data_str
    
    try:
        response = api_session.request("POST", "process_all_proposals/", json=payload)
        if response.status_code != 200:
            logger.error(f"Request unsuccessful. Status code: {response.status_code}")
            return None

        api_response = response.json()
        return api_response

    except Exception as e:
        error_message = f"Error in make_process_all_proposals_request: {str(e)}"
        logger.error(error_message)
        return None

# Ensure api_session is initialized at the module level
# api_session = APISession()