import datetime as dt
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

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
from . import utils_telescope_nongw as utils_nongw

logger = logging.getLogger(__name__)


class ProposalMwaVcsGrbSwif(ProposalSettings):
    """
    Represents the settings for MWA VCS Swift GRB proposal.
    This class holds data and functions related to proposal settings for triggering
    observations on Swift GRBs using the MWA Voltage Capture System.
    """

    # Class variables
    streams: List[str] = [
        "SWIFT_BAT_GRB_POS",
        "SWIFT_BAT_GRB_POS",
        "SWIFT_BAT_GRB_TEST_POS",
        "SWIFT_BAT_LIGHTCURVE",
        "SWIFT_BAT_QUICKLOOK_POS",
        "SWIFT_BAT_SCALEDMAP",
        "SWIFT_BAT_TRANS_POS",
        "SWIFT_FOM_OBS",
        "SWIFT_SC_SLEW",
        "SWIFT_UVOT_NACK_POS",
        "SWIFT_UVOT_POS",
    ]
    version: str = "1.0.0"
    id: int = 7
    proposal_id: str = "MWA_VCS_GRB_swif"
    proposal_description: str = "MWA VCS triggering on Swift GRBs"
    priority: int = 3
    testing: TriggerOnChoices = TriggerOnChoices.REAL_ONLY
    source_type: SourceChoices = SourceChoices.GRB

    # Initialize factories in correct order
    _telescope_factory = TelescopeFactory()
    _project_id_factory = TelescopeProjectIdFactory(
        telescope_factory=_telescope_factory
    )
    _event_telescope_factory = EventTelescopeFactory()

    # Instance variables with default values
    project_id: TelescopeProjectId = _project_id_factory.telescope_project_g0055
    event_telescope: EventTelescope = _event_telescope_factory.event_telescope_swift
    telescope_settings: MWATelescopeSettings = MWATelescopeSettings(
        telescope=_telescope_factory.telescope_mwa_vcs,
        event_min_duration=0.0,  # Differs from default
        event_max_duration=2.1,  # Differs from default
        pending_min_duration_1=0.0,  # Differs from default
        pending_max_duration_1=0.0,  # Differs from default
        pending_min_duration_2=0.0,  # Differs from default
        pending_max_duration_2=0.0,  # Differs from default
        fermi_prob=50,
        swift_rate_signif=0,
        repointing_limit=10.0,
        mwa_exptime=900,  # Differs from default(896)
    )

    class Config:
        extra = "forbid"

    def is_worth_observing(self, context: Dict, **kwargs) -> Dict:
        """
        Determines if an event is worth observing based on the source settings.

        Args:
            context (Dict): Dictionary containing event information and processing state.
            **kwargs: Additional keyword arguments to pass to the worth_observing method.

        Returns:
            Dict: Updated context dictionary containing:
                - trigger_bool (bool): Whether to trigger an observation
                - debug_bool (bool): Whether debug information was generated
                - pending_bool (bool): Whether the decision is pending human review
                - decision_reason_log (str): Log of decision making process
        """

        event = context["event"]
        prop_dec = context["prop_dec"]
        decision_reason_log = context['decision_reason_log']
        dec = prop_dec.dec

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
        log_location="end", message=f"Trigger observation completed", level="info"
    )
    def trigger_gen_observation(self, context: Dict, **kwargs) -> Dict:
        """
        Triggers the generation of an observation based on the event context.

        This method is called after receiving a response that an event is worth observing.
        It performs various checks and triggers observations for MWA telescope based on
        Swift GRB events using the Voltage Capture System (VCS).

        Args:
            context (Dict): A dictionary containing:
                - event: Event information from Swift
                - voevents: List of VOEvents associated with the observation
                - event_id: Unique identifier for the event
                - processing state flags
                - decision logs
            **kwargs: Additional keyword arguments.

        Returns:
            Dict: Updated context dictionary containing:
                - decision: Final decision on observation
                - decision_reason_log: Detailed log of decision process
                - stop_processing: Processing status flag
                - reached_end: Flag indicating completion
                - Additional observation-specific data based on the scenario
        """

        print(f"DEBUG - START context keys: {context.keys()}")

        context = utils_helper.check_mwa_horizon_and_prepare_context(context)

        # TODO: Remove this after testing
        # context["stop_processing"] = False
        print("DEBUG - context['stop_processing']: ", context["stop_processing"])

        if context["stop_processing"]:
            return context["decision"], context["decision_reason_log"]

        context = self.trigger_mwa_observation(
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
        message=f"Worth observing for GRB source completed",
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

        This method evaluates Swift GRB events against multiple criteria including:
        - Position uncertainty checks
        - ATCA declination limits
        - Event likelihood/significance thresholds
        - Event duration constraints

        Args:
            event (Event): The GRB event to evaluate.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                Configuration settings for the telescope, including observation parameters
            **kwargs: Additional keyword arguments including:
                - prop_dec: Proposal decision information
                - dec: Declination value
                - decision_reason_log: Ongoing log of decisions

        Returns:
            Dict: A dictionary containing:
                - trigger_bool: Whether to trigger an observation
                - debug_bool: Whether to trigger a debug alert
                - pending_bool: Whether to create a pending observation
                - decision_reason_log: A log of the decision-making process
                - stop_processing: Processing control flag
                - likely_bool: Event likelihood evaluation result
                - reached_end: Flag indicating completion
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
        message=f"Trigger MWA observation for GRB source completed",
        level="info",
    )
    def trigger_mwa_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Dict:
        """
        Trigger an MWA observation for a GRB event based on the event context and telescope settings.

        This method handles the generation of MWA observations for Swift GRB events using
        the Voltage Capture System (VCS). It processes the event context and generates
        appropriate observation parameters based on the telescope settings.

        Args:
            context (Dict): The context dictionary containing:
                - voevents: List of VOEvents associated with the observation
                - event_id: Unique identifier for the event
                - prop_dec: Proposal decision information
                - stop_processing: Processing control flag
                - decision_reason_log: Ongoing log of decisions
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                Configuration settings for the telescope, including observation parameters
            **kwargs: Additional keyword arguments

        Returns:
            Dict: Updated context dictionary containing:
                - All input context fields, potentially modified
                - reached_end: Flag indicating completion
                - Additional observation-specific data based on the scenario
        """

        voevents = context["voevents"]
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("MWA") is False:
            return context

        context = utils_helper.prepare_observation_context(
            context=context, voevents=voevents
        )

        context = utils_nongw.handle_non_gw_observation(
            telescope_settings=telescope_settings, context=context
        )

        context["reached_end"] = True

        return context
