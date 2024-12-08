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
from . import utils_telescope_atca as utils_atca
from . import utils_telescope_nongw as utils_nongw

logger = logging.getLogger(__name__)


class ProposalTest2Neutrino(ProposalSettings):
    """
    Represents the settings for Test2 Neutrino proposal.
    This class holds data and functions related to proposal settings for triggering
    observations on neutrino events for testing purposes.
    """

    # Class variables
    streams: List[str] = [
        "AMON_ICECUBE_BRONZE_EVENT",
        # "AMON_ICECUBE_CASCADE_EVENT",
        "AMON_ICECUBE_GOLD_EVENT",
    ]

    version: str = "1.0.0"
    id: int = 10
    proposal_id: str = "test2_neutrino"
    proposal_description: str = "Test proposal for neutrino events"
    priority: int = DEFAULT_PRIORITY
    testing: TriggerOnChoices = TriggerOnChoices.PRETEND_REAL
    source_type: SourceChoices = SourceChoices.NU

    # Initialize factories in correct order
    _telescope_factory = TelescopeFactory()
    _project_id_factory = TelescopeProjectIdFactory(
        telescope_factory=_telescope_factory
    )
    _event_telescope_factory = EventTelescopeFactory()

    # Instance variables with default values
    project_id: TelescopeProjectId = _project_id_factory.telescope_project_c002
    event_telescope: EventTelescope = _event_telescope_factory.event_telescope_antares
    telescope_settings: MWATelescopeSettings = MWATelescopeSettings(
        telescope=_telescope_factory.telescope_mwa_vcs,
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
        maximum_observation_time_seconds=18000,
        mwa_freqspecs="144,24",
        mwa_exptime=7200,
        mwa_calexptime=200.0,
        mwa_freqres=20.0,
        mwa_inttime=1.0,
        mwa_horizon_limit=20.0,
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
        It performs various checks and triggers observations for different telescopes (MWA, ATCA)
        based on neutrino events.

        Args:
            context (Dict): A dictionary containing:
                - event: Event information from neutrino detectors
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

    # NU settings
    # event: Dict, proc_dec: Dict
    @log_event(
        log_location="end",
        message=f"Worth observing for NU source completed",
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
        Determine if a Neutrino event is worth observing based on various criteria.

        This method evaluates neutrino events against specific criteria including:
        - Antares ranking thresholds for Antares events
        - Default triggering for non-Antares events

        Args:
            event (Event): The Neutrino event to evaluate.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the telescope.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict: Updated context dictionary containing:
                - trigger_bool (bool): Whether to trigger an observation
                - debug_bool (bool): Whether debug information was generated
                - pending_bool (bool): Whether the decision is pending human review
                - decision_reason_log (str): Log of decision making process
        """

        print("DEBUG - WORTH OBSERVING NU")

        context = {}
        decision_reason_log = kwargs.get("decision_reason_log")
        prop_dec = kwargs.get("prop_dec")

        context["prop_dec"] = prop_dec
        context["event"] = event
        context["event_id"] = event.id
        context["trig_id"] = prop_dec.trig_id

        # Setup up defaults
        trigger_bool = False
        debug_bool = False
        pending_bool = False

        if event.telescope == "Antares":
            # Check the Antares ranking
            if event.antares_ranking <= telescope_settings.antares_min_ranking:
                trigger_bool = True
                decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The Antares ranking ({event.antares_ranking}) is less than or equal to {telescope_settings.antares_min_ranking} so triggering. \n"
            else:
                debug_bool = True
                decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The Antares ranking ({event.antares_ranking}) is greater than {telescope_settings.antares_min_ranking} so not triggering. \n"
        else:
            trigger_bool = True
            decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: No thresholds for non Antares telescopes so triggering. \n"

        context["reached_end"] = True

        context["trigger_bool"] = trigger_bool
        context["debug_bool"] = debug_bool
        context["pending_bool"] = pending_bool
        context["decision_reason_log"] = decision_reason_log

        return context

    @log_event(
        log_location="end",
        message=f"Trigger ATCA observation for NU source completed",
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
        Trigger an ATCA observation for a neutrino event based on the event context and telescope settings.

        This method handles the generation of ATCA observations for neutrino events. It processes
        the event context and generates appropriate observation parameters based on the telescope settings.

        Args:
            context (Dict): The context dictionary containing:
                - event: Event information from neutrino detectors
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

        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("ATCA") is False:
            return context

        context = utils_atca.handle_atca_observation(
            telescope_settings=telescope_settings, context=context
        )

        context["reached_end"] = True

        return context

    @log_event(
        log_location="end",
        message=f"Trigger MWA observation for NU source completed",
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
        Trigger an MWA observation for a neutrino event based on the event context and telescope settings.

        This method handles the generation of MWA observations for neutrino events. It processes
        the event context and generates appropriate observation parameters based on the telescope settings.

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
