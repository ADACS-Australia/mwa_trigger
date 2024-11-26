import logging
import os

from django.utils import timezone
from trigger_app.models.proposal import ProposalSettings, ProposalSettingsArchive
from trigger_app.models.telescope import EventTelescope, Telescope, TelescopeProjectID
from trigger_app.schemas import PydProposalSettings
from trigger_app.utils import utils_api

logger = logging.getLogger(__name__)


def get_prop_settings_from_api_non_table(order_by: str = "id"):
    response = utils_api.get_prop_settings_from_api()

    pyd_prop_settings = [
        PydProposalSettings(**prop_set_data) for prop_set_data in response
    ]
    pyd_prop_settings_sorted = sorted(pyd_prop_settings, key=lambda prop: prop.id)
    if order_by == "priority":
        pyd_prop_settings_sorted = sorted(
            pyd_prop_settings, key=lambda prop: prop.priority
        )

    print("DEBUG - pyd_prop_settings_sorted")

    prop_settings = []
    for prop in pyd_prop_settings_sorted:
        # Create or get Telescope instance
        telescope, _ = Telescope.objects.get_or_create(
            name=prop.project_id.telescope.name,
            defaults={
                'lon': prop.project_id.telescope.lon,
                'lat': prop.project_id.telescope.lat,
                'height': prop.project_id.telescope.height,
            },
        )

        # Create or get TelescopeProjectID instance
        project_id, _ = TelescopeProjectID.objects.get_or_create(
            id=prop.project_id.id,
            defaults={
                'password': prop.project_id.password,
                'description': prop.project_id.description,
                'atca_email': prop.project_id.atca_email,
                'telescope': telescope,
            },
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
            streams=prop.streams,
            version=prop.version,
            proposal_id=prop.proposal_id,
            telescope=telescope,
            project_id=project_id,
            proposal_description=prop.proposal_description,
            priority=prop.priority,
            event_telescope=event_telescope,
            testing=prop.testing,
            source_type=prop.source_type,
            active=getattr(
                prop, 'active', True
            ),  # Set active to True if not present in API data
            code_link=f"/shared/models/prop_{prop.proposal_id.lower()}_{prop.version}",
        )
        prop_settings.append(prop_setting)

    return prop_settings


def update_proposal_settings_from_api():
    api_data = get_prop_settings_from_api_non_table()

    # Get all existing proposal IDs
    existing_proposal_ids = set(
        ProposalSettings.objects.values_list('proposal_id', flat=True)
    )

    # Create a set of proposal IDs from the API data
    api_proposal_ids = set(prop.proposal_id for prop in api_data)

    # Find proposals that are not in the API data
    inactive_proposals = existing_proposal_ids - api_proposal_ids
    existing_active_props = ProposalSettings.objects.filter(
        proposal_id__in=api_proposal_ids
    )

    # Separate proposals that need version update
    version_changed = []
    version_unchanged = []
    for prop in api_data:
        existing_prop = ProposalSettings.objects.filter(
            proposal_id=prop.proposal_id
        ).first()
        if existing_prop:
            if existing_prop.version != prop.version:
                version_changed.append(prop.proposal_id)
            else:
                version_unchanged.append(prop.proposal_id)

    print(version_changed)
    print(version_unchanged)

    # Create archive entries for proposals with version changes
    changed_data = []
    for prop_id in version_changed:
        existing_prop = ProposalSettings.objects.filter(proposal_id=prop_id).first()
        if existing_prop:
            archive_entry = ProposalSettingsArchive(
                id=existing_prop.id,
                id_version=f"{existing_prop.id}-{existing_prop.version}",
                streams=existing_prop.streams,
                version=existing_prop.version,
                proposal_id=existing_prop.proposal_id,
                telescope=existing_prop.telescope,
                project_id=existing_prop.project_id,
                proposal_description=existing_prop.proposal_description,
                priority=existing_prop.priority,
                event_telescope=existing_prop.event_telescope,
                testing=existing_prop.testing,
                source_type=existing_prop.source_type,
                active=False,
                created_at=existing_prop.created_at,
                updated_at=existing_prop.updated_at,
                code_link=existing_prop.code_link,
            )
            changed_data.append(archive_entry)

    # Bulk create archive entries
    if changed_data:
        ProposalSettingsArchive.objects.bulk_create(changed_data, ignore_conflicts=True)

    print("DEBUG - UPLOAD_USER", os.environ["UPLOAD_USER"])
    print("DEBUG - UPLOAD_PASSWORD", os.environ["UPLOAD_PASSWORD"])
    # Update or create proposals from API data
    ProposalSettings.objects.bulk_create(api_data, ignore_conflicts=True)
    ProposalSettings.objects.bulk_update(
        api_data,
        fields=[
            "streams",
            "version",
            'telescope',
            'project_id',
            'proposal_description',
            'priority',
            'event_telescope',
            'testing',
            'source_type',
            'active',
            'updated_at',
            'code_link',
        ],
    )

    # Set inactive proposals
    ProposalSettings.objects.filter(proposal_id__in=inactive_proposals).update(
        active=False,
    )

    # Set inactive proposals
    ProposalSettings.objects.filter(proposal_id__in=api_proposal_ids).update(
        updated_at=timezone.now(),
    )

    ProposalSettings.objects.filter(proposal_id__in=version_changed).update(
        created_at=timezone.now(),
    )
