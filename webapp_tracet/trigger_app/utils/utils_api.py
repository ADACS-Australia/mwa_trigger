import requests
from trigger_app.models import (
    EventTelescope,
    ProposalSettings,
    ProposalSettingsNoTable,
    Telescope,
    TelescopeProjectID,
)
from trigger_app.schemas import PydProposalSettings


def get_prop_settings_from_api(order_by: str = "id"):
    api_url = "http://api:8000/api/proposalsettings/"
    response = requests.get(api_url)

    pyd_prop_settings = [
        PydProposalSettings(
            **{
                **prop_set_data['telescope_settings'],
                **prop_set_data['source_settings'],
            }
        )
        for prop_set_data in response.json()
    ]
    pyd_prop_settings_sorted = sorted(pyd_prop_settings, key=lambda prop: prop.id)
    if order_by == "priority":
        pyd_prop_settings_sorted = sorted(
            pyd_prop_settings, key=lambda prop: prop.priority
        )

    prop_settings = [
        ProposalSettingsNoTable(**prop.dict()) for prop in pyd_prop_settings_sorted
    ]

    return prop_settings


def get_prop_setting_from_api(id: int):

    api_url = f"http://api:8000/api/proposalsettings_by_id/{id}/"
    response = requests.get(api_url)

    pyd_instance = PydProposalSettings(
        **{
            **response.json()['telescope_settings'],
            **response.json()['source_settings'],
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
    project_id_data['telescope'], _ = Telescope.objects.get_or_create(
        name=project_id_data['telescope']['name']
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
    proposal_data['telescope'] = telescope_instance
    proposal_data['project_id'] = project_id_instance
    proposal_data['event_telescope'] = event_telescope_instance

    # Create the ProposalSettings instance
    proposal_setting = ProposalSettings.objects.create(**proposal_data)

    proposal_data['id'] = id
    proposal_data['proposal_id'] = 'test'
    return proposal_setting
