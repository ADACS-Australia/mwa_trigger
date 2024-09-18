import logging
from datetime import datetime

from proposalsettings.eventtelescope_factory import EventTelescopeFactory
from proposalsettings.proposalsettings_factory import ProposalSettingsFactory
from proposalsettings.telescope_factory import TelescopeFactory
from proposalsettings.telescopeprojectid_factory import TelescopeProjectIdFactory

logger = logging.getLogger(__name__)


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

        # This project observes events from this telescope
        # Check if this proposal thinks this event is worth observing
        if (
            prop_dec.proposal.source_type == "FS"
            and prop_dec.event_group_id.source_type == "FS"
        ):
            trigger_bool = True
            decision_reason_log = f"{decision_reason_log}{datetime.utcnow()}: Event ID {voevent.id}: Triggering on Flare Star {prop_dec.event_group_id.source_name}. \n"
            proj_source_bool = True

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
                voevent, dec=prop_dec.dec, decision_reason_log=decision_reason_log
            )
            proj_source_bool = True
        else:
            print("DEBUG - proposal_worth_observing - not same values")

        if not proj_source_bool:
            # Proposal does not observe this type of source so update message
            decision_reason_log = f"{decision_reason_log}{datetime.utcnow()}: Event ID {voevent.id}: This proposal does not observe {prop_dec.event_group_id.source_type}s. \n"

    else:
        # Proposal does not observe event from this telescope so update message
        decision_reason_log = f"{decision_reason_log}{datetime.utcnow()}: Event ID {voevent.id}: This proposal does not trigger on events from {voevent.telescope}. \n"

    print(trigger_bool, debug_bool, pending_bool, decision_reason_log)

    return {
        "trigger_bool": trigger_bool,
        "debug_bool": debug_bool,
        "pending_bool": pending_bool,
        "proj_source_bool": proj_source_bool,
        "decision_reason_log": decision_reason_log,
    }
