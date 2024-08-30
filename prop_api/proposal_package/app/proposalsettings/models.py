import datetime as dt
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from .consts import *
from .utils import utils_grb, utils_gw

logger = logging.getLogger(__name__)


class EventGroup(BaseModel):
    id: int
    trig_id: str
    earliest_event_observed: Optional[datetime]
    latest_event_observed: Optional[datetime]
    ra: Optional[float]
    dec: Optional[float]
    ra_hms: Optional[str]
    dec_dms: Optional[str]
    pos_error: Optional[float]
    recieved_data: datetime
    source_type: Optional[str]
    ignored: bool
    event_observed: Optional[datetime]
    source_name: Optional[str]

    class Config:
        from_attributes = True


class Event(BaseModel):
    id: int
    event_group_id: EventGroup
    trig_id: Optional[str]
    self_generated_trig_id: bool
    telescope: Optional[str]
    sequence_num: Optional[int]
    event_type: Optional[str]
    role: Optional[str]
    duration: Optional[float]
    ra: Optional[float]
    dec: Optional[float]
    ra_hms: Optional[str]
    dec_dms: Optional[str]
    pos_error: Optional[float]
    recieved_data: datetime
    event_observed: Optional[datetime]
    xml_packet: str
    ignored: bool
    source_name: Optional[str]
    source_type: Optional[str]

    fermi_most_likely_index: Optional[float]
    fermi_detection_prob: Optional[float]
    swift_rate_signif: Optional[float]
    antares_ranking: Optional[int]
    hess_significance: Optional[float]

    lvc_false_alarm_rate: Optional[str]
    lvc_significant: Optional[bool]
    lvc_event_url: Optional[str]
    lvc_binary_neutron_star_probability: Optional[float]
    lvc_neutron_star_black_hole_probability: Optional[float]
    lvc_binary_black_hole_probability: Optional[float]
    lvc_terrestial_probability: Optional[float]
    lvc_includes_neutron_star_probability: Optional[float]
    lvc_retraction_message: Optional[str]
    lvc_skymap_fits: Optional[str]
    lvc_prob_density_tile: Optional[float]
    lvc_skymap_file: Optional[str]
    lvc_instruments: Optional[str]
    lvc_false_alarm_rate: Optional[str]

    class Config:
        from_attributes = True


class SourceChoices(str, Enum):
    GRB = "GRB"  # "Gamma-ray burst"
    FS = "FS"  # "Flare star"
    NU = "NU"  # "Neutrino"
    GW = "GW"  # "Gravitational wave"


class TriggerOnChoices(str, Enum):
    PRETEND_REAL = "PRETEND_REAL"  # "Real events only (Pretend Obs)"
    BOTH = "BOTH"  # "Real events (Real Obs) and test events (Pretend Obs)"
    REAL_ONLY = "REAL_ONLY"  # "Real events only (Real Obs)"


class Telescope(BaseModel):
    name: str = Field(max_length=64, description="E.g. MWA_VCS, MWA_correlate or ATCA.")
    lon: float = Field(description="Telescope longitude in degrees")
    lat: float = Field(description="Telescope latitude in degrees")
    height: float = Field(description="Telescope height above sea level in meters")

    class Config:
        extra = "forbid"  # This forbids any extra fields t


class EventTelescope(BaseModel):
    name: str = Field(
        max_length=64,
        description="Telescope that we receive Events from (e.g. SWIFT or Fermi)",
    )

    class Config:
        extra = "forbid"  # This forbids any extra fields t


class TelescopeProjectId(BaseModel):
    id: str = Field(
        max_length=125,
        description="The project ID for the telescope used to automatically schedule observations.",
    )
    password: str = Field(
        max_length=2020,
        description="The project password for the telescope used to automatically schedule observations.",
    )
    description: str = Field(
        max_length=5000, description="A brief description of the project."
    )
    atca_email: Optional[str] = Field(
        None,
        max_length=515,
        description="The email address of someone that was on the ATCA observing proposal. This is an authentication step only required for ATCA.",
    )
    telescope: Telescope

    class Config:
        extra = "forbid"  # This forbids any extra fields t


class BaseProposalSettings(BaseModel, ABC):
    id: int
    telescope: Telescope
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

    maximum_observation_time_seconds: int = Field(
        DEFAULT_MAX_OBSERVATION_TIME_SECONDS,
        description="Set maximum observation time based off event time. Setting to 0 disables this check.",
    )
    priority: int = Field(
        DEFAULT_PRIORITY,
        description="Set proposal processing priority (lower is better).",
    )

    event_any_duration: bool = Field(
        DEFAULT_EVENT_ANY_DURATION,
        description="Will trigger on events with any duration, which includes if they have None.",
    )
    event_min_duration: float = Field(
        DEFAULT_EVENT_MIN_DURATION, description="Minimum event duration."
    )
    event_max_duration: float = Field(
        DEFAULT_EVENT_MAX_DURATION, description="Maximum event duration."
    )
    pending_min_duration_1: float = Field(
        DEFAULT_PENDING_MIN_DURATION_1, description="Pending minimum duration 1."
    )
    pending_max_duration_1: float = Field(
        DEFAULT_PENDING_MAX_DURATION_1, description="Pending maximum duration 1."
    )
    pending_min_duration_2: float = Field(
        DEFAULT_PENDING_MIN_DURATION_2, description="Pending minimum duration 2."
    )
    pending_max_duration_2: float = Field(
        DEFAULT_PENDING_MAX_DURATION_2, description="Pending maximum duration 2."
    )
    maximum_position_uncertainty: float = Field(
        DEFAULT_MAX_POSITION_UNCERTAINTY,
        description="A event must have less than or equal to this position uncertainty to be observed.",
    )
    fermi_prob: float = Field(
        DEFAULT_FERMI_PROB,
        description="The minimum probability to observe for Fermi sources.",
    )
    swift_rate_signf: float = Field(
        DEFAULT_SWIFT_RATE_SIGNF,
        description='The minimum "RATE_SIGNIF" to observe for SWIFT sources.',
    )
    antares_min_ranking: int = Field(
        DEFAULT_ANTARES_MIN_RANKING,
        description="The minimum rating (1 is best) to observe for Antares sources.",
    )
    repointing_limit: float = Field(
        DEFAULT_REPOINTING_LIMIT,
        description="An updated position must be at least this far away from a current observation before repointing.",
    )
    testing: Optional[TriggerOnChoices] = Field(
        None, description="What events will this proposal trigger on?"
    )
    source_type: Optional[SourceChoices] = Field(
        None,
        description="The type of source to trigger on. Must be one of ['GRB', 'NU', 'GW', 'FS'].",
    )
    # GW custom logic
    observe_significant: bool = Field(
        DEFAULT_OBSERVE_SIGNIFICANT,
        description="Only observe events with high significance (low FAR).",
    )

    class Config:
        extra = "forbid"  # This forbids any extra fields t


class MWAProposalSettings(BaseProposalSettings):
    start_observation_at_high_sensitivity: bool = Field(
        DEFAULT_START_OBSERVATION_AT_HIGH_SENSITIVITY,
        description="Without positional data, start observations with MWA sub array at high sensitivity area.",
    )
    mwa_sub_alt_NE: float = Field(
        DEFAULT_MWA_SUB_ALT_NE,
        description="Altitude in degrees for the North-East sub array.",
    )
    mwa_sub_az_NE: float = Field(
        DEFAULT_MWA_SUB_AZ_NE,
        description="Azimuth in degrees for the North-East sub array.",
    )
    mwa_sub_alt_NW: float = Field(
        DEFAULT_MWA_SUB_ALT_NW,
        description="Altitude in degrees for the North-West sub array.",
    )
    mwa_sub_az_NW: float = Field(
        DEFAULT_MWA_SUB_AZ_NW,
        description="Azimuth in degrees for the North-West sub array.",
    )
    mwa_sub_alt_SW: float = Field(
        DEFAULT_MWA_SUB_ALT_SW,
        description="Altitude in degrees for the South-West sub array.",
    )
    mwa_sub_az_SW: float = Field(
        DEFAULT_MWA_SUB_AZ_SW,
        description="Azimuth in degrees for the South-West sub array.",
    )
    mwa_sub_alt_SE: float = Field(
        DEFAULT_MWA_SUB_ALT_SE,
        description="Altitude in degrees for the South-East sub array.",
    )
    mwa_sub_az_SE: float = Field(
        DEFAULT_MWA_SUB_AZ_SE,
        description="Azimuth in degrees for the South-East sub array.",
    )
    mwa_freqspecs: str = Field(
        DEFAULT_MWA_FREQSPECS,
        max_length=260,
        description="The frequency channels IDs for the MWA to observe at.",
    )
    mwa_exptime: int = Field(
        DEFAULT_MWA_EXPTIME, description="Observation time in seconds."
    )
    mwa_calexptime: float = Field(
        DEFAULT_MWA_CALEXPTIME, description="Calibrator Observation time in seconds."
    )
    mwa_freqres: float = Field(
        DEFAULT_MWA_FREQRES,
        description="Correlator frequency resolution for observations.",
    )
    mwa_inttime: float = Field(
        DEFAULT_MWA_INTTIME,
        description="Correlator integration time for observations in seconds.",
    )
    mwa_horizon_limit: float = Field(
        DEFAULT_MWA_HORIZON_LIMIT,
        description="The minimum elevation of the source to observe (in degrees).",
    )

    class Config:
        extra = "forbid"  # This forbids any extra fields t


class ATCAProposalSettings(BaseProposalSettings):
    # ATCA setting
    atca_band_3mm: bool = Field(
        DEFAULT_ATCA_BAND_3MM, description="Use 3mm Band (83-105 GHz)?"
    )
    atca_band_3mm_exptime: int = Field(
        DEFAULT_ATCA_BAND_3MM_EXPTIME, description="Band Exposure Time (mins)."
    )
    atca_band_3mm_freq1: Optional[int] = Field(
        DEFAULT_ATCA_BAND_3MM_FREQ1, description="Centre frequency 1 (MHz)."
    )
    atca_band_3mm_freq2: Optional[int] = Field(
        DEFAULT_ATCA_BAND_3MM_FREQ2, description="Centre frequency 2 (MHz)."
    )
    atca_band_7mm: bool = Field(
        DEFAULT_ATCA_BAND_7MM, description="Use 7mm Band (30-50 GHz)?"
    )
    atca_band_7mm_exptime: int = Field(
        DEFAULT_ATCA_BAND_7MM_EXPTIME, description="Band Exposure Time (mins)."
    )
    atca_band_7mm_freq1: Optional[int] = Field(
        DEFAULT_ATCA_BAND_7MM_FREQ1, description="Centre frequency 1 (MHz)."
    )
    atca_band_7mm_freq2: Optional[int] = Field(
        DEFAULT_ATCA_BAND_7MM_FREQ2, description="Centre frequency 2 (MHz)."
    )
    atca_band_15mm: bool = Field(
        DEFAULT_ATCA_BAND_15MM, description="Use 15mm Band (16-25 GHz)?"
    )
    atca_band_15mm_exptime: int = Field(
        DEFAULT_ATCA_BAND_15MM_EXPTIME, description="Band Exposure Time (mins)."
    )
    atca_band_15mm_freq1: Optional[int] = Field(
        DEFAULT_ATCA_BAND_15MM_FREQ1, description="Centre frequency 1 (MHz)."
    )
    atca_band_15mm_freq2: Optional[int] = Field(
        DEFAULT_ATCA_BAND_15MM_FREQ2, description="Centre frequency 2 (MHz)."
    )
    atca_band_4cm: bool = Field(
        DEFAULT_ATCA_BAND_4CM, description="Use 4cm Band (3.9-11.0 GHz)?"
    )
    atca_band_4cm_exptime: int = Field(
        DEFAULT_ATCA_BAND_4CM_EXPTIME, description="Band Exposure Time (mins)."
    )
    atca_band_4cm_freq1: Optional[int] = Field(
        DEFAULT_ATCA_BAND_4CM_FREQ1, description="Centre frequency 1 (MHz)."
    )
    atca_band_4cm_freq2: Optional[int] = Field(
        DEFAULT_ATCA_BAND_4CM_FREQ2, description="Centre frequency 2 (MHz)."
    )
    atca_band_16cm: bool = Field(
        DEFAULT_ATCA_BAND_16CM, description="Use 16cm Band (1.1-3.1 GHz)?"
    )
    atca_band_16cm_exptime: int = Field(
        DEFAULT_ATCA_BAND_16CM_EXPTIME, description="Band Exposure Time (mins)."
    )
    atca_max_exptime: int = Field(
        DEFAULT_ATCA_MAX_EXPTIME, description="Maximum Exposure Time (mins)."
    )
    atca_min_exptime: int = Field(
        DEFAULT_ATCA_MIN_EXPTIME, description="Minimum Exposure Time (mins)."
    )
    atca_prioritise_source: bool = Field(
        DEFAULT_ATCA_PRIORITISE_SOURCE,
        description="Prioritise time on source rather than time on calibrator.",
    )
    atca_dec_min_1: int = Field(
        DEFAULT_ATCA_DEC_MIN_1,
        description="Declination min limit 1 (deg). Only observe within this range.",
    )
    atca_dec_max_1: int = Field(
        DEFAULT_ATCA_DEC_MAX_1,
        description="Declination max limit 1 (deg). Only observe within this range.",
    )
    atca_dec_min_2: int = Field(
        DEFAULT_ATCA_DEC_MIN_2,
        description="Declination min limit 2 (deg). Only observe within this range.",
    )
    atca_dec_max_2: int = Field(
        DEFAULT_ATCA_DEC_MAX_2,
        description="Declination max limit 2 (deg). Only observe within this range.",
    )

    class Config:
        extra = "forbid"  # This forbids any extra fields t


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
            BaseProposalSettings, MWAProposalSettings, ATCAProposalSettings
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
            BaseProposalSettings, MWAProposalSettings, ATCAProposalSettings
        ],
        **kwargs,
    ) -> Tuple[bool, bool, bool, str]:
        print('DEBUG - worth_observing_gw')

        # Initialize the context with the event and default values
        context = utils_gw.initialize_context(event, kwargs)

        # Chain the checks together, maintaining the original order
        context = utils_gw.process_false_alarm_rate(self, context)

        context = utils_gw.update_event_parameters(context)

        # print('DEBUG - context', context)
        # two hour check
        context = utils_gw.check_event_time(context)

        context = utils_gw.check_lvc_instruments(context)

        context = utils_gw.handle_event_types(context)

        context = utils_gw.check_probabilities(telescope_settings, self, context)

        print('DEBUG - context', context)

        return (
            context['trigger_bool'],
            context['debug_bool'],
            context['pending_bool'],
            context['decision_reason_log'],
        )


class GrbSourceSettings(SourceSettings):
    # GRB settings
    # event: Dict, proc_dec: Dict
    # Final aggregation function
    def worth_observing(
        self,
        event: Event,
        telescope_settings: Union[
            BaseProposalSettings, MWAProposalSettings, ATCAProposalSettings
        ],
        **kwargs,
    ) -> Tuple[bool, bool, bool, str]:
        print('DEBUG - worth_observing_grb')

        # Initialize the context with the event and default values
        context = utils_grb.initialize_context(event, kwargs)

        # Check if the event's position uncertainty is 0.0
        context = utils_grb.check_position_error(telescope_settings, context)

        # Check if the event's position uncertainty is greater than the maximum allowed
        context = utils_grb.check_large_position_error(telescope_settings, context)

        # Check if the event's declination is within the ATCA limits
        context = utils_grb.check_atca_declination_limits(telescope_settings, context)

        # Check the events likelyhood data
        context['stop_processing'] = False

        context = utils_grb.check_fermi_likelihood(telescope_settings, context)

        context = utils_grb.check_swift_significance(telescope_settings, context)

        context = utils_grb.check_hess_significance(telescope_settings, context)

        context = utils_grb.default_no_likelihood(context)

        # Check the duration of the event
        # since new if starts, initialize the stop_processing flag
        context['stop_processing'] = False

        context = utils_grb.check_any_event_duration(telescope_settings, context)

        context = utils_grb.check_not_any_event_duration(telescope_settings, context)

        context = utils_grb.check_duration_with_limits(telescope_settings, context)

        return (
            context['trigger_bool'],
            context['debug_bool'],
            context['pending_bool'],
            context['decision_reason_log'],
        )


class NuSourceSettings(SourceSettings):

    # event: Dict, proc_dec: Dict
    def worth_observing(
        self,
        event: Event,
        telescope_settings: Union[
            BaseProposalSettings, MWAProposalSettings, ATCAProposalSettings
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

        print('DEBUG - WORTH OBSERVING NU')

        decision_reason_log = kwargs.get('decision_reason_log')

        # Setup up defaults
        trigger_bool = False
        debug_bool = False
        pending_bool = False

        if event.telescope == "Antares":
            # Check the Antares ranking
            if event.antares_ranking <= telescope_settings.antares_min_ranking:
                trigger_bool = True
                decision_reason_log += f"{datetime.utcnow()}: Event ID {event.id}: The Antares ranking ({event.antares_ranking}) is less than or equal to {telescope_settings.antares_min_ranking} so triggering. \n"
            else:
                debug_bool = True
                decision_reason_log += f"{datetime.utcnow()}: Event ID {event.id}: The Antares ranking ({event.antares_ranking}) is greater than {telescope_settings.antares_min_ranking} so not triggering. \n"
        else:
            trigger_bool = True
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event.id}: No thresholds for non Antares telescopes so triggering. \n"

        return trigger_bool, debug_bool, pending_bool, decision_reason_log


class ProposalSettings(BaseModel):
    id: int
    proposal_id: str
    telescope_settings: BaseProposalSettings
    source_settings: SourceSettings

    class Config:
        extra = "forbid"

    def is_worth_observing(self, event: Event, **kwargs):
        # Delegate to the source settings' worth_observing method
        return self.source_settings.worth_observing(
            event, self.telescope_settings, **kwargs
        )
