
import logging

from trigger_app.models.proposal import ProposalSettings
from trigger_app.models.telescope import (EventTelescope, Telescope,
                                          TelescopeProjectID)
from trigger_app.schemas import PydProposalSettings
from trigger_app.utils import utils_api

logger = logging.getLogger(__name__)

def get_prop_settings_from_api_non_table(order_by: str = "id"):
    response = utils_api.get_prop_settings_from_api()
    
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
            active=getattr(prop, 'active', True),  # Set active to True if not present in API data
        )
        prop_settings.append(prop_setting)

    return prop_settings


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
        'event_telescope', 'testing', 'source_type',
        'active',
    ])
    
    # Set inactive proposals
    ProposalSettings.objects.filter(proposal_id__in=inactive_proposals).update(active=False)
    