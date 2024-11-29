import datetime as dt
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

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

        # Delegate to the source settings' worth_observing method
        pass

    @abstractmethod
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
        pass
