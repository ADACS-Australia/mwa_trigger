import json
import os

import requests
from django.conf import settings


def get_access_token(username, password):
    url = "http://web:8000/api/token/pair"
    
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
    
def update_access_token(new_token):
    """
    Updates the global ACCESS_TOKEN with a new value.
    """
    # Update the global settings variable
    settings.ACCESS_TOKEN = new_token
    print(f"Access token updated: {settings.ACCESS_TOKEN}")
    
    
def create_observation(payload):
    url = "http://web:8000/api/create-observation/"
    
    # access_token = os.getenv("ACCESS_TOKEN")
    # auth_username = os.getenv("AUTH_USERNAME")
    # auth_password = os.getenv("AUTH_PASSWORD")
    
    access_token = settings.ACCESS_TOKEN
    auth_username = settings.AUTH_USERNAME
    auth_password = settings.AUTH_PASSWORD
    
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 401:
        access_token = get_access_token(auth_username, auth_password)
        update_access_token(access_token)
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            response = requests.post(url, json=payload, headers=headers)
            
    return response

def get_latest_observation(cls, proposal_decision_model):
    """Retrieve the latest observation for the given telescope via API."""
    telescope_id = proposal_decision_model.proposal.telescope_settings.telescope.name
    api_url = f"http://web:8000/api/latest-observation/{telescope_id}/"
    
    # access_token = os.getenv("ACCESS_TOKEN")
    # auth_username = os.getenv("AUTH_USERNAME")
    # auth_password = os.getenv("AUTH_PASSWORD")
    
    access_token = settings.ACCESS_TOKEN
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        # "JWT-Refresh-Token": refresh_token  # Custom header for refresh token
    }    

    try:
        response = requests.get(api_url, headers=headers)
    
        print("RESPONSE:", response.status_code)
        
        if response.status_code == 401:
            auth_username = settings.AUTH_USERNAME
            auth_password = settings.AUTH_PASSWORD
            access_token = get_access_token(auth_username, auth_password)
            update_access_token(access_token)
            
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                response = requests.get(api_url, headers=headers)
                print("RESPONSE:", response.status_code)
                
        response.raise_for_status()  # Raises an HTTPError for bad responses
        observation_data = response.json()

        # Create and return a Pydantic instance
        values = cls.parse_obj(observation_data)

        return values
    except requests.RequestException as e:
        print(f"Error fetching latest observation: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing observation data: {e}")
        return None