"""
This module defines source settings classes for different types of astronomical events.

The module contains a base class `SourceSettings` which defines common
attributes and methods for all source settings. It also includes three child
classes, `GWSourceSettings`, `GrbSourceSettings`, and `NuSourceSettings`, which
implement source-specific settings and behaviors for Gravitational Wave, Gamma-Ray Burst,
and Neutrino events respectively.

Classes:
    SourceSettings: Abstract base class for source settings.
    GWSourceSettings: Settings specific to Gravitational Wave events.
    GrbSourceSettings: Settings specific to Gamma-Ray Burst events.
    NuSourceSettings: Settings specific to Neutrino events.

Each child class implements three key methods:
    - worth_observing: Determines if an event is worth observing based on source-specific criteria.
    - trigger_atca_observation: Handles the logic for triggering an ATCA observation for the specific source type.
    - trigger_mwa_observation: Handles the logic for triggering an MWA observation for the specific source type.

These classes are used to manage source-specific settings and handle the
process of evaluating events and triggering observations in a standardized way
across different astronomical event types.
"""

import datetime as dt
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from ..consts import *
from ..utils import utils_api, utils_grb, utils_gw
from ..utils import utils_helper as utils_helper
from ..utils import utils_telescope_atca as utils_atca
from ..utils import utils_telescope_gw as utils_telgw
from ..utils import utils_telescope_nongw as utils_nongw
from ..utils.utils_log import log_event
from .event import Event
from .schemas import Observations
from .telescopesettings import (
    ATCATelescopeSettings,
    BaseTelescopeSettings,
    MWATelescopeSettings,
)

logger = logging.getLogger(__name__)


# Settings for Source Type class
class SourceSettings(BaseModel, ABC):
    """
    Abstract base class for source-specific settings.

    This class defines the interface for source-specific settings and observation logic.
    Subclasses should implement the abstract methods for different source types.
    """

    @abstractmethod
    def worth_observing(
        self,
        event: Event,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> bool:
        """
        Determine if an event is worth observing based on source-specific criteria.

        Args:
            event (Event): The event to evaluate.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the telescope.
            **kwargs: Additional keyword arguments.

        Returns:
            bool: True if the event is worth observing, False otherwise.
        """
        pass

    @abstractmethod
    def trigger_atca_observation(
        self,
        context,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> bool:
        """
        Trigger an ATCA observation based on source-specific criteria.

        Args:
            context: The context containing event and observation information.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the ATCA telescope.
            **kwargs: Additional keyword arguments.

        Returns:
            bool: True if the observation is triggered, False otherwise.
        """
        pass

    @abstractmethod
    def trigger_mwa_observation(
        self,
        context,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> bool:
        """
        Trigger an MWA observation based on source-specific criteria.

        Args:
            context: The context containing event and observation information.
            telescope_settings (Union[BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings]):
                The settings for the MWA telescope.
            **kwargs: Additional keyword arguments.

        Returns:
            bool: True if the observation is triggered, False otherwise.
        """
        pass


class GWSourceSettings(SourceSettings):
    """
    Settings and logic for Gravitational Wave (GW) source observations.

    This class contains specific parameters and methods for handling GW events,
    including probability thresholds and observation triggering logic.
    """

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

    class Config:
        extra = "forbid"  # This forbids any extra fields

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
    ) -> Tuple[bool, bool, bool, str]:
        """
        Determine if a GW event is worth observing based on various criteria.

        Args:
            event (Event): The GW event to evaluate.
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
        return (
            context["trigger_bool"],
            context["debug_bool"],
            context["pending_bool"],
            context["decision_reason_log"],
        )

    @log_event(
        log_location="end",
        message=f"Trigger ATCA observation for GW source completed",
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
        Trigger an ATCA observation for a GW event.

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


class GrbSourceSettings(SourceSettings):
    """
    Settings and logic for Gamma-Ray Burst (GRB) source observations.

    This class contains specific methods for handling GRB events,
    including observation triggering logic for different telescopes.
    """

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
    ) -> Tuple[bool, bool, bool, str]:
        """
        Determine if a GRB event is worth observing based on various criteria.

        Args:
            event (Event): The GRB event to evaluate.
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
        print("DEBUG - worth_observing_grb")

        prop_dec = kwargs.get("prop_dec")

        # Initialize the context with the event and default values
        context = utils_grb.initialize_context(event, kwargs)

        # Check if the event's position uncertainty is 0.0
        context = utils_grb.check_position_error(context)

        # Check if the event's position uncertainty is greater than the maximum allowed
        context = utils_grb.check_large_position_error(telescope_settings, context)

        # Check if the event's declination is within the ATCA limits
        context = utils_grb.check_atca_declination_limits(telescope_settings, context)
        print("DEBUG - context after check_atca_declination_limits")
        # Check the events likelyhood data
        context["stop_processing"] = False
        context["likely_bool"] = False

        context = utils_grb.check_fermi_likelihood(telescope_settings, context)

        context = utils_grb.check_swift_significance(telescope_settings, context)

        context = utils_grb.check_hess_significance(telescope_settings, context)

        context = utils_grb.default_no_likelihood(context)

        # Check the duration of the event
        # since new if starts, initialize the stop_processing flag
        context["stop_processing"] = False

        context = utils_grb.check_any_event_duration(telescope_settings, context)

        context = utils_grb.check_not_any_event_duration(telescope_settings, context)

        context = utils_grb.check_duration_with_limits(telescope_settings, context)

        context["reached_end"] = True
        return (
            context["trigger_bool"],
            context["debug_bool"],
            context["pending_bool"],
            context["decision_reason_log"],
        )

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
    ) -> Tuple[str, str]:
        """
        Trigger an ATCA observation for a GRB event.

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

        print("DEBUG - Trigger ATCA observation for GRB source")

        # context = utils_tel.handle_atca_observation(context)

        context = utils_atca.handle_atca_observation(
            telescope_settings=telescope_settings, context=context
        )

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
    ) -> Tuple[str, str]:
        """
        Trigger an MWA observation for a GRB event.

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


class NuSourceSettings(SourceSettings):
    """
    Settings and logic for Neutrino (Nu) source observations.

    This class contains specific methods for handling Neutrino events,
    including observation triggering logic for different telescopes.
    """

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
    ):
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
        return trigger_bool, debug_bool, pending_bool, decision_reason_log

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
