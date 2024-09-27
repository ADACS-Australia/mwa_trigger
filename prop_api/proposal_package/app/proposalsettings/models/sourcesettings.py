
import datetime as dt
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from ..consts import *
from ..utils import utils_api, utils_grb, utils_gw
from ..utils import utils_telescope_atca as utils_atca
from ..utils import utils_telescope_gw as utils_telgw
from ..utils import utils_telescope_helper as utils_helper
from ..utils import utils_telescope_nongw as utils_nongw
from .event import Event
from .schemas import Observations
from .telescopesettings import (ATCATelescopeSettings, BaseTelescopeSettings,
                                MWATelescopeSettings)

logger = logging.getLogger(__name__)

json_logger = logging.getLogger('django_json')




# Settings for Source Type class
class SourceSettings(BaseModel, ABC):

    # class Config:
    #     extra = "forbid"  # This forbids any extra fields t

    # event: Dict, proc_dec: Dict
    @abstractmethod
    def worth_observing(
        self,
        event: Event,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> bool:
        """This is an abstract method that must be implemented by subclasses."""
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
        """This is an abstract method that must be implemented by subclasses."""
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
        """This is an abstract method that must be implemented by subclasses."""
        pass


class GWSourceSettings(SourceSettings):
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
    def worth_observing(
        self,
        event: Event,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[bool, bool, bool, str]:
        print("DEBUG - worth_observing_gw")

        proposal_decision_model = kwargs.get("proposal_decision_model")

        json_logger.info(
            "Worth observing for GW source",
            extra={
                "function": "GWSourceSettings.worth_observing",
                "event_id": event.id,
                "trig_id": proposal_decision_model.trig_id,
            },
        )

        # Initialize the context with the event and default values
        context = utils_gw.initialize_context(event, kwargs)

        # Chain the checks together, maintaining the original order
        context = utils_gw.process_false_alarm_rate(self, context)

        context = utils_gw.update_event_parameters(context)

        json_logger.debug(
            "Worth observing for GW source - after update_event_parameters",
            extra={
                "function": "GWSourceSettings.worth_observing",
                "event_id": event.id,
                "trig_id": context["trig_id"],
            },
        )
        
        # two hour check
        context = utils_gw.check_event_time(context)
        
        print("DEBUG - context after check_event_time")

        context = utils_gw.check_lvc_instruments(context)
        
        print("DEBUG - context after check_lvc_instruments")

        context = utils_gw.handle_event_types(context)

        context = utils_gw.check_probabilities(telescope_settings, self, context)

        # print("DEBUG - context", context)
        json_logger.info(
            "Worth observing for GW source - completed",
            extra={
                "function": "GWSourceSettings.worth_observing",
                "event_id": event.id,
                "trig_id": context["trig_id"],
            },
        )
        
        return (
            context["trigger_bool"],
            context["debug_bool"],
            context["pending_bool"],
            context["decision_reason_log"],
        )

    def trigger_atca_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[str, str]:

        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("ATCA") is False:
            return context

        print("DEBUG - Trigger ATCA observation for GW source")
        json_logger.debug(
            "Trigger ATCA observation for GW source",
            extra={
                "function": "GWSourceSettings.trigger_atca_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        # context = utils_tel.handle_atca_observation(context)

        context = utils_atca.handle_atca_observation_class(
            telescope_settings=telescope_settings, context=context
        )

        return context

    def trigger_mwa_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[str, str]:

        voevents = context["voevents"]
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("MWA") is False:
            return context

        print("DEBUG - Trigger MWA observation for GW source")
        
        json_logger.info(
            "Trigger MWA observation for GW source",
            extra={
                "function": "GWSourceSettings.trigger_mwa_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        context = utils_helper.prepare_observation_context(context, voevents)

        print("DEBUG - num of voevents:", len(voevents))

        json_logger.debug(
            f"num of voevents : {len(voevents)}",
            extra={
                "function": "GWSourceSettings.trigger_mwa_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        if len(voevents) == 1:
            # Dump out the last ~3 mins of MWA buffer to try and catch event
            context = utils_telgw.handle_first_observation(
                telescope_settings=telescope_settings, context=context
            )

            # Handle the unique case of the early warning
            if context["latestVoevent"].event_type == "EarlyWarning":
                print("DEBUG - MWA telescope - GW - EarlyWarning")

                json_logger.debug(
                    f"MWA telescope - GW - EarlyWarning",
                    extra={
                        "function": "GWSourceSettings.trigger_mwa_observation",
                        "trig_id": context["proposal_decision_model"].trig_id,
                        "event_id": context["event_id"],
                    },
                )

                context = utils_telgw.handle_early_warning(
                    telescope_settings=telescope_settings, context=context
                )
            elif (
                context["latestVoevent"].lvc_skymap_fits != None
                and context["latestVoevent"].event_type != "EarlyWarning"
            ):
                print("MWA telescope - GW - Skymap")

                json_logger.debug(
                    f"MWA telescope - GW - Skymap",
                    extra={
                        "function": "GWSourceSettings.trigger_mwa_observation",
                        "trig_id": context["proposal_decision_model"].trig_id,
                        "event_id": context["event_id"],
                    },
                )

                context = utils_telgw.handle_skymap_event(
                    telescope_settings=telescope_settings, context=context
                )
                print("DEBUG - MWA telescope - GW - Skymap Calculated")

        # Repoint if there is a newer skymap with different positions
        if len(voevents) > 1 and context["latestVoevent"].lvc_skymap_fits:
            print("DEBUG - MWA telescope - GW - Repoint")

            json_logger.debug(
                f"MWA telescope - GW - Repoint",
                extra={
                    "function": "GWSourceSettings.trigger_mwa_observation",
                    "trig_id": context["proposal_decision_model"].trig_id,
                    "event_id": context["event_id"],
                },
            )

            # get latest event for MWA
            print(f"DEBUG - checking to repoint")
            context["reason"] = (
                f"{context['latestVoevent'].trig_id} - Event has a skymap"
            )

            latest_obs = utils_api.get_latest_observation(Observations,context["proposal_decision_model"])

            print("latest_obs:", latest_obs)

            context = utils_telgw.handle_gw_voevents(
                telescope_settings=telescope_settings,
                context=context,
                latest_obs=latest_obs,
            )
            
        json_logger.info(
            "Trigger MWA observation for GW source completed",
            extra={
                "function": "GWSourceSettings.trigger_mwa_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        return context


class GrbSourceSettings(SourceSettings):
    # GRB settings
    # event: Dict, proc_dec: Dict
    # Final aggregation function
    def worth_observing(
        self,
        event: Event,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[bool, bool, bool, str]:
        print("DEBUG - worth_observing_grb")

        proposal_decision_model = kwargs.get("proposal_decision_model")

        json_logger.info(
            "Worth observing for Grb source",
            extra={
                "function": "GrbSourceSettings.worth_observing",
                "event_id": event.id,
                "trig_id": proposal_decision_model.trig_id,
            },
        )

        # Initialize the context with the event and default values
        context = utils_grb.initialize_context(event, kwargs)

        # Check if the event's position uncertainty is 0.0
        context = utils_grb.check_position_error(telescope_settings, context)

        # Check if the event's position uncertainty is greater than the maximum allowed
        context = utils_grb.check_large_position_error(telescope_settings, context)

        # Check if the event's declination is within the ATCA limits
        context = utils_grb.check_atca_declination_limits(telescope_settings, context)

        # Check the events likelyhood data
        context["stop_processing"] = False

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

        json_logger.info(
            "Worth observing for Grb source - completed",
            extra={
                "function": "GrbSourceSettings.worth_observing",
                "event_id": event.id,
                "trig_id": context["proposal_decision_model"].trig_id,
            },
        )
        
        return (
            context["trigger_bool"],
            context["debug_bool"],
            context["pending_bool"],
            context["decision_reason_log"],
        )

    def trigger_atca_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[str, str]:

        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("ATCA") is False:
            return context

        print("DEBUG - Trigger ATCA observation for GRB source")
        
        json_logger.info(
            f"Trigger ATCA observation for GRB source",
            extra={
                "function": "GrbSourceSettings.trigger_atca_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        # context = utils_tel.handle_atca_observation(context)

        context = utils_atca.handle_atca_observation(
            telescope_settings=telescope_settings, context=context
        )
        
        json_logger.info(
            f"Trigger ATCA observation for GRB source completed",
            extra={
                "function": "GrbSourceSettings.trigger_atca_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        return context

    def trigger_mwa_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[str, str]:

        voevents = context["voevents"]
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("MWA") is False:
            return context
        
        print("DEBUG - Trigger MWA observation for GRB source")
        
        json_logger.info(
            f"Trigger MWA observation for GRB source",
            extra={
                "function": "GrbSourceSettings.trigger_mwa_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        context = utils_helper.prepare_observation_context(
            context=context, voevents=voevents
        )

        print("passed Non - GW check")
        context = utils_nongw.handle_non_gw_observation_class(
            telescope_settings=telescope_settings, context=context
        )
        
        json_logger.info(
            f"Trigger MWA observation for GRB source completed",
            extra={
                "function": "GrbSourceSettings.trigger_mwa_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        return context


class NuSourceSettings(SourceSettings):

    # event: Dict, proc_dec: Dict
    def worth_observing(
        self,
        event: Event,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ):
        """Decide if a Neutrino Event is worth observing.

        Parameters
        ----------
        antares_ranking : `int`, optional
            The rank of antaras event. Default: None.
        telescope : `int`, optional
            The rank of telescope of the event. Default: None.
        antares_min_ranking : `int`, optional
            The minimum (inclusive) rank of antaras events. Default: 2.
        decision_reason_log : `str`
            A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".
        event_id : `int`, optional
            An Event ID that will be recorded in the decision_reason_log. Default: None.

        Returns
        -------
        trigger_bool : `boolean`
            If True an observations should be triggered.
        debug_bool : `boolean`
            If True a debug alert should be sent out.
        pending_bool : `boolean`
            If True will create a pending observation and wait for human intervention.
        decision_reason_log : `str`
            A log of all the decisions made so far so a user can understand why the source was(n't) observed.
        """

        print("DEBUG - WORTH OBSERVING NU")

        decision_reason_log = kwargs.get("decision_reason_log")
        proposal_decision_model = kwargs.get("proposal_decision_model")

        json_logger.info(
            "Worth observing for Nu source",
            extra={
                "function": "NuSourceSettings.worth_observing",
                "event_id": event.id,
                "trig_id": proposal_decision_model.trig_id,
            },
        )

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


        json_logger.info(
            "Worth observing for Nu source - completed",
            extra={
                "function": "NuSourceSettings.worth_observing",
                "event_id": event.id,
                "trig_id": proposal_decision_model.trig_id,
            },
        )
        
        return trigger_bool, debug_bool, pending_bool, decision_reason_log

    def trigger_atca_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[str, str]:

        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("ATCA") is False:
            return context

        print("DEBUG - Trigger ATCA observation for NU source")

        json_logger.info(
            f"Trigger ATCA observation for NU source",
            extra={
                "function": "NuSourceSettings.trigger_atca_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        # context = utils_tel.handle_atca_observation(context)

        context = utils_atca.handle_atca_observation(
            telescope_settings=telescope_settings, context=context
        )
        
        json_logger.info(
            f"Trigger ATCA observation for NU source completed",
            extra={
                "function": "NuSourceSettings.trigger_atca_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        return context

    def trigger_mwa_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[str, str]:
    
        voevents = context["voevents"]
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("MWA") is False:
            return context

        print("DEBUG - Trigger MWA observation for NU source")

        json_logger.info(
            f"Trigger MWA observation for NU source",
            extra={
                "function": "NuSourceSettings.trigger_mwa_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        context = utils_helper.prepare_observation_context(
            context=context, voevents=voevents
        )

        print("passed Non - GW check")
        context = utils_nongw.handle_non_gw_observation(
            telescope_settings=telescope_settings, context=context
        )
        
        json_logger.info(
            f"Trigger MWA observation for NU source completed",
            extra={
                "function": "NuSourceSettings.trigger_mwa_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        return context

