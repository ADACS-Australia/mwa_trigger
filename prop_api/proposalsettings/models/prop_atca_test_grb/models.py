import datetime as dt
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from ...consts import DEFAULT_PRIORITY, streams_all_grbs
from ...eventtelescope_factory import EventTelescopeFactory
from ...telescope_factory import TelescopeFactory
from ...telescopeprojectid_factory import TelescopeProjectIdFactory

# general utils
from ...utils import utils_helper as utils_helper
from ...utils.utils_log import log_event

# source and triggerchoices and event and proposal classes in models
from ..constants import SourceChoices, TriggerOnChoices
from ..event import Event
from ..proposal import ProposalSettings
from ..telescope import EventTelescope, TelescopeProjectId
from ..telescopesettings import (
    ATCATelescopeSettings,
    BaseTelescopeSettings,
    MWATelescopeSettings,
)

logger = logging.getLogger(__name__)


class ProposalAtcaTestGrb(ProposalSettings):
    """
    Represents the settings for ATCA Test GRB proposal.
    """

    # Class variables
    streams: List[str] = [
        "SWIFT_BAT_GRB_POS",
    ]

    version: str = "1.0.0"
    id: int = 20
    proposal_id: str = "ATCA_test_GRB"
    proposal_description: str = "This is the triggering proposal for the testing"
    priority: int = DEFAULT_PRIORITY
    testing: TriggerOnChoices = TriggerOnChoices.REAL_ONLY
    source_type: SourceChoices = SourceChoices.GRB

    # Initialize factories in correct order
    _telescope_factory = TelescopeFactory()
    _project_id_factory = TelescopeProjectIdFactory(
        telescope_factory=_telescope_factory
    )
    _event_telescope_factory = EventTelescopeFactory()

    # Instance variables with default values
    project_id: TelescopeProjectId = _project_id_factory.telescope_project_c3542
    event_telescope: EventTelescope = _event_telescope_factory.event_telescope_swift
    telescope_settings: ATCATelescopeSettings = ATCATelescopeSettings(
        telescope=_telescope_factory.telescope_atca
    )

    class Config:
        extra = "forbid"

    def is_worth_observing(
        self, context: Dict, **kwargs
    ) -> Tuple[bool, bool, bool, str]:
        """
        Determines if an event is worth observing based on the source settings.

        Args:
            event (Event): The event to evaluate.
            **kwargs: Additional keyword arguments to pass to the worth_observing method.

        Returns:
            Tuple[bool, bool, bool, str]: A tuple containing:
                - bool: True if the event is worth observing, False otherwise.
                - bool: True if the event passes additional criteria.
                - bool: True if the event requires immediate action.
                - str: A message explaining the decision.
        """
        event = context["event"]

        # returning three boolean values and log text
        return {
            "trigger_bool": True,
            "debug_bool": False,
            "pending_bool": False,
            "decision_reason_log": "test",
        }

    def trigger_gen_observation(self, context: Dict, **kwargs) -> Tuple[str, str]:
        """
        Triggers the generation of an observation based on the event context.

        This method is called after receiving a response that an event is worth observing.
        It performs various checks and triggers observations for different telescopes (MWA, ATCA).

        Args:
            context (Dict): A dictionary containing the context of the event and observation.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[str, str]: A tuple containing the decision and the decision reason log.
        """
        print(f"DEBUG - START context keys: {context.keys()}")

        (context["decision"], context["decision_reason_log"], context["obsids"]) = (
            self.telescope_settings.trigger_telescope(context)
        )

        for obsid in context["obsids"]:
            saved_atca_obs = self.telescope_settings.save_observation(
                context,
                trigger_id=obsid,
                # TODO see if ATCA has a nice observation details webpage
                # website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
            )

            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Saving observation result for ATCA.\n"
            context["request_sent_at"] = datetime.now(dt.timezone.utc)

        return context
