from functools import wraps
from typing import Any, Callable, Dict, Optional

import requests
from django.conf import settings
from requests.exceptions import RequestException


def get_access_token(username: str, password: str):
    url = f"{settings.WEB_APP_URL}/api/token/pair"
    
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
        url = f"{settings.WEB_APP_URL}/api/{endpoint}"
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
api_session = APISession()        
        
def api_request(method: str, endpoint: str, payload: Dict[str, Any] = None):
    return api_session.request(method, endpoint, json=payload)


def create_observation(payload: dict):
    try:
        response = api_request("POST", "create-observation/", payload)
        return response
    except Exception as e:
        print(f"Error creating observation: {str(e)}")
        return {}


def get_latest_observation(cls, prop_dec: dict) -> Dict[str, Any]:
    try:
        telescope_id = prop_dec.proposal.telescope_settings.telescope.name
        response = api_request("GET", f"latest-observation/{telescope_id}/")
        observation_data = response.json()
        values = cls.parse_obj(observation_data)
        # print("DEBUG - get_latest_observation new:", values)
        return values
    except Exception as e:
        print(f"Error getting latest observation: {str(e)}")
        return {}
    
def update_proposal_decision(proposal_decision_id: int, decision: str, decision_reason_log: str) -> Dict[str, Any]:
    try:
        payload = {
            "decision": decision,
            "decision_reason": decision_reason_log
        }
        response = api_request("PUT", f"proposal-decision/{proposal_decision_id}/", payload)
        return response.json()
    except Exception as e:
        print(f"Error updating proposal decision: {str(e)}")
        return {}

def trigger_alerts(context: Dict[str, Any]) -> Dict[str, Any]:
    prop_dec_id = context.get("prop_dec").id
    
    if context.get("send_alerts") is None or context.get("send_alerts") is False :
        return {"message": f"No alerts fired for prop_dec_id: {prop_dec_id}"}

    payload = {
        'prop_dec_id': prop_dec_id,
        'trigger_bool': context.get("trigger_bool"),
        'debug_bool': context.get("debug_bool"),
        'pending_bool': context.get("pending_bool"),
    }

    try:
        response = api_request("POST", "trigger-alerts/", payload)
        return response.json()
    except Exception as e:
        print(f"Error triggering alerts: {str(e)}")
        return {"error": str(e)}
    
def update_event_group(context: Dict[str, Any]) -> Dict[str, Any]:
    event_group = context.get("event_group")
    prop_decs_exist = context.get("prop_decs_exist")

    if not event_group or not hasattr(event_group, 'id'):
        return {"error": "Invalid event_group in context"}

    endpoint = f"event-group/{event_group.id}/"

    if prop_decs_exist:
        payload = {
            "ra": event_group.ra,
            "dec": event_group.dec,
            "ra_hms": event_group.ra_hms,
            "dec_dms": event_group.dec_dms,
            "pos_error": event_group.pos_error,
            "latest_event_observed": event_group.latest_event_observed.isoformat()
        }
    else:
        payload = {"ignored": event_group.ignored}

    try:
        response = api_request("PUT", endpoint, payload)
        print("DEBUG - update_event_group:", response.json())
        return response.json()
    except Exception as e:
        error_message = f"Error updating EventGroup: {str(e)}"
        print(error_message)
        return {"error": error_message}