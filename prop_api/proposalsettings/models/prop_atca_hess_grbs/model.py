import datetime as dt
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

# constants
from ...consts import DEFAULT_PRIORITY

# factory classes
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

# local utils
from . import utils_grb
from . import utils_telescope_atca as utils_atca

logger = logging.getLogger(__name__)


class ProposalAtcaHessGrbs(ProposalSettings):
    """
    Represents the settings for ATCA HESS GRBs proposal.
    This class holds data and functions related to proposal settings for triggering
    observations on HESS GRB events.
    """

    # Class variables
    streams: List[str] = ["HESS_GRB_TO"]
    version: str = "1.0.0"
    id: int = 11
    proposal_id: str = "ATCA_HESS_GRBs"
    proposal_description: str = "ATCA triggers on HESS GRBs"
    priority: int = 2
    testing: TriggerOnChoices = TriggerOnChoices.REAL_ONLY
    source_type: SourceChoices = SourceChoices.GRB

    # Initialize factories in correct order
    _telescope_factory = TelescopeFactory()
    _project_id_factory = TelescopeProjectIdFactory(
        telescope_factory=_telescope_factory
    )
    _event_telescope_factory = EventTelescopeFactory()

    # Instance variables with default values
    project_id: TelescopeProjectId = _project_id_factory.telescope_project_c3204
    event_telescope: EventTelescope = _event_telescope_factory.event_telescope_hess
    telescope_settings: ATCATelescopeSettings = ATCATelescopeSettings(
        telescope=_telescope_factory.telescope_atca,
        event_min_duration=0.0,
        event_max_duration=10000.0,
        pending_min_duration_1=0.0,
        pending_max_duration_1=1000.0,
        pending_min_duration_2=0.0,
        pending_max_duration_2=0.0,
        maximum_position_uncertainty=0.07,
        fermi_prob=50,
        swift_rate_signif=5.0,
        repointing_limit=5.0,
        observe_significant=True,
        atca_band_4cm=True,
        atca_band_4cm_freq1=5500.0,
        atca_band_4cm_freq2=9000.0,
        atca_min_exptime=120,
    )

    class Config:
        extra = "forbid"

    def is_worth_observing(self, context: Dict, **kwargs) -> Dict:
        """
        Determines if an event is worth observing based on the source settings.

        Args:
            context (Dict): Dictionary containing event information and processing state
                containing event, prop_dec, and decision_reason_log.
            kwargs: Additional keyword arguments to pass to the worth_observing method.

        Returns:
            Dict: Updated context dictionary containing trigger_bool, debug_bool,
                pending_bool, and decision_reason_log.
        """
        event = context["event"]
        prop_dec = context["prop_dec"]
        decision_reason_log = context['decision_reason_log']
        dec = prop_dec.dec

        # Delegate to the source settings' worth_observing method
        context_wo = self.worth_observing(
            event,
            self.telescope_settings,
            prop_dec=prop_dec,
            dec=dec,
            decision_reason_log=decision_reason_log,
        )

        context["trigger_bool"] = context_wo["trigger_bool"]
        context["debug_bool"] = context_wo["debug_bool"]
        context["pending_bool"] = context_wo["pending_bool"]
        context["decision_reason_log"] = context_wo["decision_reason_log"]

        return context

    @log_event(
        log_location="end", message="Trigger observation completed", level="info"
    )
    def trigger_gen_observation(self, context: Dict, **kwargs) -> Dict:
        """
        Triggers the generation of an observation based on the event context.

        Args:
            context (Dict): Dictionary containing event information and processing state:
                - event: The event to evaluate
                - event_id: ID of the event
                - prop_dec: The proposal decision object
                - decision_reason_log: Log of decision reasons
                - trigger_bool: Whether to trigger an observation
                - stop_processing: Flag to control processing flow

            **kwargs: Additional keyword arguments

        Returns:
            Dict: Updated context dictionary containing:
                - decision: The final decision made
                - decision_reason_log: Updated log of the decision process
                - reached_end: Flag indicating completion
                - stop_processing: Updated processing control flag

        Note:
            This method is called after receiving a response that an event is worth observing.
            It performs various checks and triggers observations for different telescopes.
        """

        print(f"DEBUG - START context keys: {context.keys()}")

        context = utils_helper.check_mwa_horizon_and_prepare_context(context)

        # TODO: Remove this after testing
        # context["stop_processing"] = False
        print("DEBUG - context['stop_processing']: ", context["stop_processing"])

        if context["stop_processing"]:
            return context["decision"], context["decision_reason_log"]

        context = self.trigger_atca_observation(
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

    # GRB settings
    # event: Dict, proc_dec: Dict
    # Final aggregation function
    @log_event(
        log_location="end",
        message="Worth observing for GRB source completed",
        level="info",
    )
    def worth_observing(
        self,
        event: Event,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Dict:
        """
        Determine if a GRB event is worth observing based on various criteria.

        Args:
            event (Event): The GRB event to evaluate.

            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the telescope.

            **kwargs: Additional keyword arguments including prop_dec, dec,
                and decision_reason_log.

        Returns:
            Dict: Context dictionary containing observation decision data:
                trigger_bool, debug_bool, pending_bool, decision_reason_log,
                stop_processing, likely_bool, and reached_end flags.
        """
        print("DEBUG - worth_observing_grb")

        prop_dec = kwargs.get("prop_dec")

        # Initialize the context with the event and default values
        context = utils_grb.initialize_context(event, kwargs)

        # Check if the event's position uncertainty is 0.0
        context = utils_grb.check_position_error(context)

        # Check if the event's position uncertainty is greater than the maximum allowed
        context = utils_grb.check_large_position_error(self.telescope_settings, context)

        # Check if the event's declination is within the ATCA limits
        context = utils_grb.check_atca_declination_limits(
            self.telescope_settings, context
        )
        print("DEBUG - context after check_atca_declination_limits")
        # Check the events likelyhood data
        context["stop_processing"] = False
        context["likely_bool"] = False

        context = utils_grb.check_fermi_likelihood(self.telescope_settings, context)

        context = utils_grb.check_swift_significance(self.telescope_settings, context)

        context = utils_grb.check_hess_significance(self.telescope_settings, context)

        context = utils_grb.default_no_likelihood(context)

        # Check the duration of the event
        # since new if starts, initialize the stop_processing flag
        context["stop_processing"] = False

        context = utils_grb.check_any_event_duration(self.telescope_settings, context)

        context = utils_grb.check_not_any_event_duration(
            self.telescope_settings, context
        )

        context = utils_grb.check_duration_with_limits(self.telescope_settings, context)

        context["reached_end"] = True
        return context

    @log_event(
        log_location="end",
        message=f"Trigger ATCA observation for GRB source completed",
        level="info",
    )
    def trigger_atca_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Dict:
        """
        Trigger an ATCA observation for a GRB event.

        Args:
            context (Dict): The context containing event and observation information.

            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the ATCA telescope.

            **kwargs: Additional keyword arguments.

        Returns:
            Dict: Updated context dictionary containing:
                decision, decision_reason_log, reached_end, and stop_processing flags.
        """

        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("ATCA") is False:
            return context

        print("DEBUG - Trigger ATCA observation for GRB source")

        # context = utils_tel.handle_atca_observation(context)

        context = utils_atca.handle_atca_observation(
            telescope_settings=telescope_settings, context=context
        )

        context["reached_end"] = True

        return context
