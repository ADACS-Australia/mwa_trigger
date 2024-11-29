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

    version: str = "1.0.1"
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

        Args:
            event (Event): The Neutrino event to evaluate.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the telescope.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[bool, bool, bool, str]: A tuple containing:
                - trigger_bool: Whether to trigger an observation.
                - debug_bool: Whether to trigger a debug alert.
                - pending_bool: Whether to create a pending observation.
                - decision_reason_log: A log of the decision-making process.
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
    ) -> Tuple[str, str]:
        """
        Trigger an ATCA observation for a NU event.

        Args:
            context (Dict): The context containing event and observation information.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the ATCA telescope.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[str, str]: A tuple containing updated context information.
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
    ) -> Tuple[str, str]:
        """
        Trigger an MWA observation for a NU event.

        Args:
            context (Dict): The context containing event and observation information.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the MWA telescope.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[str, str]: A tuple containing updated context information.
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
