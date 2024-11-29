import datetime as dt
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from pydantic import Field

# constants
from ...consts import *

# factory classes
from ...eventtelescope_factory import EventTelescopeFactory
from ...telescope_factory import TelescopeFactory
from ...telescopeprojectid_factory import TelescopeProjectIdFactory

# general utils
from ...utils import utils_api, utils_helper
from ...utils.utils_log import log_event

# source and triggerchoices and event and proposal classes in models
from ..constants import SourceChoices, TriggerOnChoices
from ..event import Event
from ..proposal import ProposalSettings
from ..schemas import Observations
from ..telescope import EventTelescope, TelescopeProjectId
from ..telescopesettings import (
    ATCATelescopeSettings,
    BaseTelescopeSettings,
    MWATelescopeSettings,
)

# local utils
from . import utils_gw
from . import utils_telescope_gw as utils_telgw

logger = logging.getLogger(__name__)


class ProposalMwaGwNsbh(ProposalSettings):
    """
    Represents the settings for MWA GW NSBH proposal.
    This class holds data and functions related to proposal settings for triggering
    observations on LIGO-Virgo-KAGRA NSBH GW events.
    """

    # Class variables
    streams: List[str] = [
        "LVC_INITIAL",
        "LVC_M",
        "LVC_PRELIMINARY",
        "LVC_RETRACTION",
        "LVC_UPDATE",
    ]

    version: str = "1.0.0"
    id: int = 14
    proposal_id: str = "MWA_GW_NSBH"
    proposal_description: str = (
        "MWA triggering on LIGO-Virgo-KAGRA BNS GW events detected during O4 using a multi-beam approach and the VCS"
    )
    priority: int = 3
    testing: TriggerOnChoices = TriggerOnChoices.REAL_ONLY
    source_type: SourceChoices = SourceChoices.GW

    # Initialize factories in correct order
    _telescope_factory = TelescopeFactory()
    _project_id_factory = TelescopeProjectIdFactory(
        telescope_factory=_telescope_factory
    )
    _event_telescope_factory = EventTelescopeFactory()

    # GW settings
    # GW event property prob
    minimum_neutron_star_probability: float = Field(
        DEFAULT_MINIMUM_NEUTRON_STAR_PROBABILITY,
        description="Minimum probability that at least one object in the binary has a mass that is less than 3 solar masses.",
    )
    maximum_neutron_star_probability: float = Field(
        DEFAULT_MAXIMUM_NEUTRON_STAR_PROBABILITY,
        description="Maximum probability that at least one object in the binary has a mass that is less than 3 solar masses.",
    )
    early_observation_time_seconds: int = Field(
        DEFAULT_EARLY_OBSERVATION_TIME_SECONDS,
        description="This is the observation time for GW early warning and preliminary notices.",
    )
    minimum_binary_neutron_star_probability: float = Field(
        DEFAULT_MINIMUM_BINARY_NEUTRON_STAR_PROBABILITY,
        description="Minimum probability for event to be BNS.",
    )
    maximum_binary_neutron_star_probability: float = Field(
        DEFAULT_MAXIMUM_BINARY_NEUTRON_STAR_PROBABILITY,
        description="Maximum probability for event to be BNS.",
    )
    minimum_neutron_star_black_hole_probability: float = Field(
        DEFAULT_MINIMUM_NEUTRON_STAR_BLACK_HOLE_PROBABILITY,
        description="Minimum probability for event to be NSBH.",
    )
    maximum_neutron_star_black_hole_probability: float = Field(
        DEFAULT_MAXIMUM_NEUTRON_STAR_BLACK_HOLE_PROBABILITY,
        description="Maximum probability for event to be NSBH.",
    )
    minimum_binary_black_hole_probability: float = Field(
        DEFAULT_MINIMUM_BINARY_BLACK_HOLE_PROBABILITY,
        description="Minimum probability for event to be BBH.",
    )
    maximum_binary_black_hole_probability: float = Field(
        DEFAULT_MAXIMUM_BINARY_BLACK_HOLE_PROBABILITY,
        description="Maximum probability for event to be BBH.",
    )
    minimum_terrestial_probability: float = Field(
        DEFAULT_MINIMUM_TERRESTIAL_PROBABILITY,
        description="Minimum probability for event to be terrestrial.",
    )
    maximum_terrestial_probability: float = Field(
        DEFAULT_MAXIMUM_TERRESTIAL_PROBABILITY,
        description="Maximum probability for event to be terrestrial.",
    )
    maximum_false_alarm_rate: str = Field(
        DEFAULT_MAXIMUM_FALSE_ALARM_RATE,
        description="Maximum false alarm rate (FAR) to trigger.",
    )

    # hess settings
    minimum_hess_significance: float = Field(
        DEFAULT_MINIMUM_HESS_SIGNIFICANCE,
        description="Minimum significance from HESS to trigger an observation.",
    )
    maximum_hess_significance: float = Field(
        DEFAULT_MAXIMUM_HESS_SIGNIFICANCE,
        description="Maximum significance from HESS to trigger an observation.",
    )

    # Instance variables with default values
    project_id: TelescopeProjectId = _project_id_factory.telescope_project_g0094
    event_telescope: EventTelescope = _event_telescope_factory.event_telescope_lvc
    telescope_settings: MWATelescopeSettings = MWATelescopeSettings(
        telescope=_telescope_factory.telescope_mwa_vcs,
        event_min_duration=0.512,
        event_max_duration=10000.0,
        pending_min_duration_1=1.0,
        pending_max_duration_1=1000.0,
        pending_min_duration_2=0.0,
        pending_max_duration_2=0.0,
        maximum_position_uncertainty=0.07,
        fermi_prob=60,
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

    # self, event: Dict, proc_dec: Dict
    @log_event(
        log_location="end",
        message=f"Worth observing for GW source completed",
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
        Determine if a GW event is worth observing based on various criteria.

        Args:
            event (Event): The GW event to evaluate.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the telescope.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict: A dictionary containing:
                - trigger_bool: Whether to trigger an observation.
                - debug_bool: Whether to trigger a debug alert.
                - pending_bool: Whether to create a pending observation.
                - decision_reason_log: A log of the decision-making process.
        """

        print("DEBUG - worth_observing_gw")

        prop_dec = kwargs.get("prop_dec")

        # Initialize the context with the event and default values
        context = utils_gw.initialize_context(event, kwargs)

        print(f" DEBUG - worth_observing gw context keys: {context.keys()}")

        # Chain the checks together, maintaining the original order
        context = utils_gw.process_false_alarm_rate(
            context=context, maximum_false_alarm_rate=self.maximum_false_alarm_rate
        )

        context = utils_gw.update_event_parameters(context=context)

        # two hour check
        context = utils_gw.check_event_time(context)

        context = utils_gw.check_lvc_instruments(context)

        context = utils_gw.handle_event_types(context)

        context = utils_gw.check_probabilities(telescope_settings, self, context)

        context["reached_end"] = True
        return context

    @log_event(
        log_location="end",
        message=f"Trigger MWA observation for GW source completed",
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
        Trigger an MWA observation for a GW event.

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

        print("DEBUG - Trigger MWA observation for GW source")

        context = utils_helper.prepare_observation_context(context, voevents)

        if len(voevents) == 1:
            # Dump out the last ~3 mins of MWA buffer to try and catch event
            context = utils_telgw.handle_first_observation(
                telescope_settings=telescope_settings, context=context
            )

            # Handle the unique case of the early warning
            if context["latestVoevent"].event_type == "EarlyWarning":

                context = utils_telgw.handle_early_warning(
                    telescope_settings=telescope_settings, context=context
                )
            elif (
                context["latestVoevent"].lvc_skymap_fits != None
                and context["latestVoevent"].event_type != "EarlyWarning"
            ):
                context = utils_telgw.handle_skymap_event(
                    telescope_settings=telescope_settings, context=context
                )

        # Repoint if there is a newer skymap with different positions
        if len(voevents) > 1 and context["latestVoevent"].lvc_skymap_fits:
            # get latest event for MWA
            print(f"DEBUG - checking to repoint")
            context["reason"] = (
                f"{context['latestVoevent'].trig_id} - Event has a skymap"
            )

            latest_obs = utils_api.get_latest_observation(
                cls=Observations, prop_dec=context["prop_dec"]
            )

            context = utils_telgw.handle_gw_voevents(
                telescope_settings=telescope_settings,
                context=context,
                latest_obs=latest_obs,
            )

        context["reached_end"] = True

        return context
