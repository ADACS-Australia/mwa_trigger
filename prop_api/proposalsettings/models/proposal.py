import datetime as dt
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Tuple

from pydantic import BaseModel, Field

from ..consts import DEFAULT_PRIORITY
from ..utils import utils_helper as utils_helper
from ..utils.utils_log import log_event
from .constants import SourceChoices, TriggerOnChoices
from .event import Event
from .sourcesettings import SourceSettings
from .telescope import EventTelescope, TelescopeProjectId
from .telescopesettings import BaseTelescopeSettings

logger = logging.getLogger(__name__)


class ProposalSettings(BaseModel):
    id: int
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

    telescope_settings: BaseTelescopeSettings
    source_settings: SourceSettings

    class Config:
        extra = "forbid"

    def is_worth_observing(self, event: Event, **kwargs):
        # Delegate to the source settings' worth_observing method
        return self.source_settings.worth_observing(
            event, self.telescope_settings, **kwargs
        )

    # @log_event(log_location="start",message=f"Trigger observation started", level="info")
    @log_event(log_location="end",message=f"Trigger observation completed", level="info")
    def trigger_gen_observation(self, context: Dict, **kwargs) -> Tuple[str, str]:

        print(f"DEBUG - START context keys: {context.keys()}")

        context = utils_helper.check_mwa_horizon_and_prepare_context(context)

        # TODO: Remove this after testing
        # context["stop_processing"] = False
        print("DEBUG - context['stop_processing']: ", context["stop_processing"])

        if context["stop_processing"]:
            return context["decision"], context["decision_reason_log"]

        context = self.source_settings.trigger_mwa_observation(
            telescope_settings=self.telescope_settings, context=context
        )

        context = self.source_settings.trigger_atca_observation(
            telescope_settings=self.telescope_settings, context=context
        )

        if (
            self.telescope_settings.telescope.name.startswith("ATCA") is False
            and self.telescope_settings.telescope.name.startswith("MWA") is False
        ):
            context["decision_reason_log"] = (
                f"{context['decision_reason_log']}{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Not making an MWA observation. \n"
            )
        
        context['reached_end'] = True
        print(f"DEBUG - END context keys: {context.keys()}")
        return context

