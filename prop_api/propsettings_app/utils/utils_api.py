import datetime as dt
import logging
import os
from datetime import datetime

import requests
from proposalsettings.eventtelescope_factory import EventTelescopeFactory
from proposalsettings.proposalsettings_factory import ProposalSettingsFactory
from proposalsettings.telescope_factory import TelescopeFactory
from proposalsettings.telescopeprojectid_factory import \
    TelescopeProjectIdFactory

logger = logging.getLogger(__name__)

json_logger = logging.getLogger("django_json")

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
    

def get_latest_observation(cls, proposal_decision_model):
    """Retrieve the latest observation for the given telescope via API."""
    telescope_id = proposal_decision_model.proposal.telescope_settings.telescope.name
    api_url = f"http://web:8000/api/latest-observation/{telescope_id}/"
    
    access_token = os.getenv("ACCESS_TOKEN")
    auth_username = os.getenv("AUTH_USERNAME")
    auth_password = os.getenv("AUTH_PASSWORD")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        # "JWT-Refresh-Token": refresh_token  # Custom header for refresh token
    }    

    try:
        response = requests.get(api_url, headers=headers)
    
        print("RESPONSE:", response.status_code)
        
        if response.status_code == 401:
            access_token = get_access_token(auth_username, auth_password)
            
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

        json_logger.debug(
            "proposal telescope and voevent telescope are the same or proposal telescope is None",
            extra={
                "function": "proposal_worth_observing",
                "trig_id": prop_dec.trig_id,
                "event_id": voevent.id,
                "proposal_id": prop_dec.proposal.id,
            },
        )

        # This project observes events from this telescope
        # Check if this proposal thinks this event is worth observing
        if (
            prop_dec.proposal.source_type == "FS"
            and prop_dec.event_group_id.source_type == "FS"
        ):
            trigger_bool = True
            decision_reason_log = f"{decision_reason_log}{datetime.now(dt.timezone.utc)}: Event ID {voevent.id}: Triggering on Flare Star {prop_dec.event_group_id.source_name}. \n"
            proj_source_bool = True

            json_logger.debug(
                "proposal source type is FS",
                extra={
                    "function": "proposal_worth_observing",
                    "trig_id": prop_dec.trig_id,
                    "event_id": voevent.id,
                    "proposal_id": prop_dec.proposal.id,
                },
            )

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
                voevent,
                dec=prop_dec.dec,
                decision_reason_log=decision_reason_log,
                proposal_decision_model=prop_dec,
            )
            proj_source_bool = True

            json_logger.info(
                f"proposal source type is {prop_dec.proposal.source_type}",
                extra={
                    "function": "proposal_worth_observing",
                    "trig_id": prop_dec.trig_id,
                    "event_id": voevent.id,
                    "proposal_id": prop_dec.proposal.id,
                },
            )
        else:
            print("DEBUG - proposal_worth_observing - not same values")

            json_logger.debug(
                f"proposal source type is not same as event group source type",
                extra={
                    "function": "proposal_worth_observing",
                    "trig_id": prop_dec.trig_id,
                    "event_id": voevent.id,
                    "proposal_id": prop_dec.proposal.id,
                },
            )
        if not proj_source_bool:
            # Proposal does not observe this type of source so update message
            decision_reason_log = f"{decision_reason_log}{datetime.now(dt.timezone.utc)}: Event ID {voevent.id}: This proposal does not observe {prop_dec.event_group_id.source_type}s. \n"

            json_logger.debug(
                f"proposal does not observe this type of source",
                extra={
                    "function": "proposal_worth_observing",
                    "trig_id": prop_dec.trig_id,
                    "event_id": voevent.id,
                    "proposal_id": prop_dec.proposal.id,
                },
            )
    else:
        # Proposal does not observe event from this telescope so update message
        decision_reason_log = f"{decision_reason_log}{datetime.now(dt.timezone.utc)}: Event ID {voevent.id}: This proposal does not trigger on events from {voevent.telescope}. \n"

        json_logger.debug(
            f"proposal does not observe event from this telescope",
            extra={
                "function": "proposal_worth_observing",
                "trig_id": prop_dec.trig_id,
                "event_id": voevent.id,
                "proposal_id": prop_dec.proposal.id,
            },
        )

    print(trigger_bool, debug_bool, pending_bool, decision_reason_log)

    return {
        "trigger_bool": trigger_bool,
        "debug_bool": debug_bool,
        "pending_bool": pending_bool,
        "proj_source_bool": proj_source_bool,
        "decision_reason_log": decision_reason_log,
    }
