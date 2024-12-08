import datetime as dt
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..consts import DEFAULT_PRIORITY
from ..utils import utils_helper as utils_helper
from ..utils.utils_log import log_event
from .constants import SourceChoices, TriggerOnChoices
from .event import Event
from .telescope import EventTelescope, TelescopeProjectId
from .telescopesettings import (
    ATCATelescopeSettings,
    BaseTelescopeSettings,
    MWATelescopeSettings,
)

logger = logging.getLogger(__name__)


class ProposalSettings(BaseModel, ABC):
    """
    Represents the settings for a proposal in the telescope observation system.

    This class holds data and functions related to proposal settings, including
    project information, event telescope details, proposal identifiers, and
    various configuration options for triggering observations.

    """

    id: int
    streams: List[str] = []
    version: str = "1.0.0"

    project_id: TelescopeProjectId
    event_telescope: Optional[EventTelescope]
    proposal_id: str = Field(
        max_length=16,
        description="A short identifier of the proposal of maximum length 16 characters.",
    )
    proposal_description: str = Field(
        max_length=513,
        description="A brief description of the proposal. Only needs to be enough to distinguish it from the other proposals.",
    )
    priority: int = Field(
        DEFAULT_PRIORITY,
        description="Set proposal processing priority (lower is better).",
    )

    testing: Optional[TriggerOnChoices] = Field(
        None, description="What events will this proposal trigger on?"
    )
    source_type: Optional[SourceChoices] = Field(
        None,
        description="The type of source to trigger on. Must be one of ['GRB', 'NU', 'GW', 'FS'].",
    )

    telescope_settings: Union[
        BaseTelescopeSettings, ATCATelescopeSettings, MWATelescopeSettings
    ]

    class Config:
        extra = "forbid"

    @abstractmethod
    def is_worth_observing(
        self, context: Dict, **kwargs
    ) -> Dict[str, Union[bool, str]]:
        """
        Evaluates whether an event meets the criteria for telescope observation.

        Args:
            context (Dict): Event context containing relevant observation parameters
            **kwargs: Additional parameters for observation evaluation

        Returns:
            Dict[str, Union[bool, str]]: Observation decision containing:
                - worth_observing (bool): Whether the event meets basic observation criteria
                - passes_criteria (bool): Whether the event passes additional filters
                - requires_immediate (bool): Whether immediate observation is needed
                - message (str): Explanation of the decision
        """
        pass

    @abstractmethod
    def trigger_gen_observation(self, context: Dict, **kwargs) -> Dict[str, str]:
        """
        Initiates telescope observation based on event parameters.

        Processes approved observation requests by configuring and triggering
        the appropriate telescope systems (MWA, ATCA) based on the event context.

        Args:
            context (Dict): Event details and observation parameters
            **kwargs: Additional configuration options

        Returns:
            Dict[str, str]: Observation outcome containing:
                - decision (str): Final observation decision
                - reason (str): Detailed explanation of the decision
        """
        pass
