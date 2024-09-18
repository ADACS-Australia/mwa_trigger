import datetime as dt
import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import atca_rapid_response_api as arrApi
import requests
from astropy.time import Time
from pydantic import BaseModel, Field

from .consts import *
from .utils import utils_grb, utils_gw
from .utils import utils_telescope_atca as utils_atca
from .utils import utils_telescope_gw as utils_telgw
from .utils import utils_telescope_helper as utils_helper
from .utils import utils_telescope_nongw as utils_nongw
from .utils.utils_triggerservice import trigger

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


class BaseTelescopeSettings(BaseModel, ABC):
    # id: int
    telescope: Telescope
    # project_id: TelescopeProjectId
    # event_telescope: Optional[EventTelescope]
    # proposal_id: str = Field(
    #     max_length=16,
    #     description="A short identifier of the proposal of maximum length 16 characters.",
    # )
    # proposal_description: str = Field(
    #     max_length=513,
    #     description="A brief description of the proposal. Only needs to be enough to distinguish it from the other proposals.",
    # )
    # priority: int = Field(
    #     DEFAULT_PRIORITY,
    #     description="Set proposal processing priority (lower is better).",
    # )

    maximum_observation_time_seconds: int = Field(
        DEFAULT_MAX_OBSERVATION_TIME_SECONDS,
        description="Set maximum observation time based off event time. Setting to 0 disables this check.",
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
    # GW custom logic
    observe_significant: bool = Field(
        DEFAULT_OBSERVE_SIGNIFICANT,
        description="Only observe events with high significance (low FAR).",
    )

    # testing: Optional[TriggerOnChoices] = Field(
    #     None, description="What events will this proposal trigger on?"
    # )
    # source_type: Optional[SourceChoices] = Field(
    #     None,
    #     description="The type of source to trigger on. Must be one of ['GRB', 'NU', 'GW', 'FS'].",
    # )

    class Config:
        extra = "forbid"  # This forbids any extra fields

    @abstractmethod
    def trigger_telescope(
        self,
        context,
        **kwargs,
    ) -> Tuple[str, str, List[Union[int, str]], Optional[str]]:
        """This is an abstract method that must be implemented by subclasses."""
        pass

    @abstractmethod
    def save_observation(self, context, trigger_id, obsid=None, reason=None) -> Dict:
        """This is an abstract method that must be implemented by subclasses."""
        pass


class MWATelescopeSettings(BaseTelescopeSettings):
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
    # TODO check mwa_nobs
    mwa_nobs: float = Field(
        None,
        description="Number of observations to make.",
    )

    class Config:
        extra = "forbid"  # This forbids any extra fields t

    def trigger_telescope(
        self,
        context,
        **kwargs,
    ) -> Tuple[str, str, List[Union[int, str]], str]:
        """Check if the MWA can observe then send it off the observation.

        Parameters
        ----------
        proposal_decision_model : `django.db.models.Model`
            The Django ProposalDecision model object.
        decision_reason_log : `str`
            A log of all the decisions made so far so a user can understand why the source was(n't) observed.
        obsname : `str`
            The name of the observation.
        vcsmode : `boolean`, optional
            True to observe in VCS mode and False to observe in correlator/imaging mode. Default: False
        event_id : `int`, optional
            An Event ID that will be recorded in the decision_reason_log. Default: None.

        Returns
        -------
        result : `str`
            The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
        decision_reason_log : `str`
            The updated trigger message to include an observation specific logs.
        observations : `list`
            A list of observations that were scheduled by MWA.
        result : `object`
            Result from mwa
        """

        # return "T", decision_reason_log, [], {}
        proposal_decision_model = context["proposal_decision_model"]
        prop_settings = context["proposal_decision_model"].proposal
        decision_reason_log = context["decision_reason_log"]
        obsname = context["obsname"]
        vcsmode = context["vcsmode"]
        event_id = context["event_id"]
        mwa_sub_arrays = context["mwa_sub_arrays"]
        buffered = context["buffered"]
        pretend = context["pretend"]

        print("DEBUG - triggering MWA")
        print(f"DEBUG - proposal: {prop_settings.__dict__}")
        # Not below horizon limit so observer
        logger.info(f"Triggering MWA at UTC time {Time.now()} ...")

        # if True:
        #     return "T", decision_reason_log, [], None

        # Handle early warning events without position using sub arrays
        try:
            if (
                prop_settings.source_type == "GW"
                and buffered == True
                and vcsmode == True
            ):
                print("DEBUG - Dumping buffer")
                print("DEBUG - Using nobs = 1, exptime = 8")

                result = trigger(
                    project_id=prop_settings.project_id.id,
                    secure_key=prop_settings.project_id.password,
                    pretend=pretend,
                    creator="VOEvent_Auto_Trigger",  # TODO grab version
                    obsname=obsname,
                    nobs=1,
                    # Assume always using 24 contiguous coarse frequency channels
                    freqspecs=prop_settings.telescope_settings.mwa_freqspecs,
                    avoidsun=True,
                    inttime=prop_settings.telescope_settings.mwa_inttime,
                    freqres=prop_settings.telescope_settings.mwa_freqres,
                    exptime=8,
                    vcsmode=vcsmode,
                    buffered=buffered,
                )
                print(f"buffered result: {result}")

            elif prop_settings.source_type == "GW" and mwa_sub_arrays != None:
                print("DEBUG - Scheduling an ra/dec sub array observation")

                result = trigger(
                    project_id=prop_settings.project_id.id,
                    secure_key=prop_settings.project_id.password,
                    pretend=pretend,
                    subarray_list=["all_ne", "all_nw", "all_se", "all_sw"],
                    ra=mwa_sub_arrays["ra"],
                    dec=mwa_sub_arrays["dec"],
                    creator="VOEvent_Auto_Trigger",  # TODO grab version
                    obsname=obsname,
                    nobs=1,
                    # Assume always using 24 contiguous coarse frequency channels
                    freqspecs=prop_settings.telescope_settings.mwa_freqspecs,
                    avoidsun=True,
                    inttime=prop_settings.telescope_settings.mwa_inttime,
                    freqres=prop_settings.telescope_settings.mwa_freqres,
                    exptime=prop_settings.telescope_settings.mwa_exptime,
                    calibrator=True,
                    calexptime=prop_settings.telescope_settings.mwa_calexptime,
                    vcsmode=vcsmode,
                )
            else:
                print("DEBUG - Scheduling an ra/dec observation")

                result = trigger(
                    project_id=prop_settings.project_id.id,
                    secure_key=prop_settings.project_id.password,
                    pretend=pretend,
                    ra=proposal_decision_model.ra,
                    dec=proposal_decision_model.dec,
                    alt=proposal_decision_model.alt,
                    az=proposal_decision_model.az,
                    creator="VOEvent_Auto_Trigger",  # TODO grab version
                    obsname=obsname,
                    nobs=1,
                    # Assume always using 24 contiguous coarse frequency channels
                    freqspecs=prop_settings.telescope_settings.mwa_freqspecs,
                    avoidsun=True,
                    inttime=prop_settings.telescope_settings.mwa_inttime,
                    freqres=prop_settings.telescope_settings.mwa_freqres,
                    exptime=prop_settings.telescope_settings.mwa_exptime,
                    calibrator=True,
                    calexptime=prop_settings.telescope_settings.mwa_calexptime,
                    vcsmode=vcsmode,
                )
        except Exception as e:
            print(f"DEBUG - Error exception scheduling observation {e}")
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Exception trying to schedule event {e}\n "
            return "E", decision_reason_log, [], []

        print(f"result: {result}")
        logger.debug(f"result: {result}")
        # Check if succesful
        if result is None:
            print("DEBUG - Error: no result from scheduling observation")
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Web API error, possible server error.\n "
            return "E", decision_reason_log, [], result
        if not result["success"]:
            print("DEBUG - Error: failed to schedule observation")
            # Observation not succesful so record why
            for err_id in result["errors"]:
                decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: {result['errors'][err_id]}.\n "
            # Return an error as the trigger status
            return "E", decision_reason_log, [], result

        # Output the results
        logger.info(f"Trigger sent: {result['success']}")
        logger.info(f"Trigger params: {result['success']}")
        if "stdout" in result["schedule"].keys():
            if result["schedule"]["stdout"]:
                logger.info(f"schedule' stdout: {result['schedule']['stdout']}")
        if "stderr" in result["schedule"].keys():
            if result["schedule"]["stderr"]:
                logger.info(f"schedule' stderr: {result['schedule']['stderr']}")

        # Grab the obsids (sometimes we will send of several observations)
        obsids = []
        if "obsid_list" in result.keys() and len(result["obsid_list"]) > 0:
            obsids = result["obsid_list"]
        else:
            for r in result["schedule"]["stderr"].split("\n"):
                if r.startswith("INFO:Schedule metadata for"):
                    obsids.append(r.split(" for ")[1][:-1])
                elif r.startswith("Pretending: commands not run"):
                    obsids.append(f"P{random.randint(1000,9999)}")

        # TODO please remove it when not testing it
        # result = DEFAULT_MWA_RESPONSE

        return "T", decision_reason_log, obsids, result

    def save_observation(self, context, trigger_id, obsid=None, reason=None) -> Dict:
        """Save the observation result through the API."""
        print("DEBUG - saving MWA observation - class")

        api_url = f"http://web:8000/api/create-observation/"
        # trigger_id = str(random.randrange(10000, 99999))

        # Prepare the payload
        payload = {
            "trigger_id": str(trigger_id),
            "telescope_name": context[
                "proposal_decision_model"
            ].proposal.telescope_settings.telescope.name,
            "proposal_decision_id": context["proposal_decision_model"].id,
            "event_id": context["latestVoevent"].id,
            "reason": reason or context["reason"],
            "website_link": f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
            # "mwa_response": context.get("result") or context.get("result_buffer"),
            "request_sent_at": (
                context["request_sent_at"].isoformat()
                if context["request_sent_at"]
                else None
            ),
            "mwa_sub_arrays": (
                context.get("mwa_sub_arrays") if context.get("mwa_sub_arrays") else None
            ),
            "mwa_sky_map_pointings": (
                context.get("mwa_sky_map_pointings")
                if context.get("mwa_sky_map_pointings")
                else None
            ),
        }

        print("DEBUG - payload starts: \n")
        print(payload)
        print("DEBUG - payload ends \n")

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"Observation created: {result}")

        except requests.RequestException as e:
            print(f"Error creating observation: {e}")

        return result


class ATCATelescopeSettings(BaseTelescopeSettings):
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

    def trigger_telescope(
        self,
        context,
        **kwargs,
    ) -> Tuple[str, str, List[Union[int, str]]]:
        """Check if the ATCA telescope can observe, send it off the observation and return any errors.

        Parameters
        ----------
        proposal_decision_model : `django.db.models.Model`
            The Django ProposalDecision model object.
        decision_reason_log : `str`
            A log of all the decisions made so far so a user can understand why the source was(n't) observed.
        obsname : `str`
            The name of the observation.
        event_id : `int`, optional
            An Event ID that will be recorded in the decision_reason_log. Default: None.

        Returns
        -------
        result : `str`
            The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
        decision_reason_log : `str`
            The updated trigger message to include an observation specific logs.
        observations : `list`
            A list of observations that were scheduled by ATCA (currently there is no functionality to record this so will be empty).
        """

        proposal_decision_model = context["proposal_decision_model"]
        decision_reason_log = context["decision_reason_log"]
        event_id = context["event_id"]

        prop_obj = proposal_decision_model.proposal

        # TODO add any schedule checks or observation parsing here
        print("DEBUG - trigger_atca_observation")
        # Not below horizon limit so observer
        logger.info(f"Triggering  ATCA at UTC time {Time.now()} ...")

        rq = {
            "source": prop_obj.source_type,
            "rightAscension": proposal_decision_model.ra_hms,
            "declination": proposal_decision_model.dec_dms,
            "project": prop_obj.project_id.id,
            "maxExposureLength": str(
                timedelta(minutes=prop_obj.telescope_settings.atca_max_exptime)
            ),
            "minExposureLength": str(
                timedelta(minutes=prop_obj.telescope_settings.atca_min_exptime)
            ),
            "scanType": "Dwell",
            "3mm": {
                "use": prop_obj.telescope_settings.atca_band_3mm,
                "exposureLength": str(
                    timedelta(minutes=prop_obj.telescope_settings.atca_band_3mm_exptime)
                ),
                "freq1": prop_obj.telescope_settings.atca_band_3mm_freq1,
                "freq2": prop_obj.telescope_settings.atca_band_3mm_freq2,
            },
            "7mm": {
                "use": prop_obj.telescope_settings.atca_band_7mm,
                "exposureLength": str(
                    timedelta(minutes=prop_obj.telescope_settings.atca_band_7mm_exptime)
                ),
                "freq1": prop_obj.telescope_settings.atca_band_7mm_freq1,
                "freq2": prop_obj.telescope_settings.atca_band_7mm_freq2,
            },
            "15mm": {
                "use": prop_obj.telescope_settings.atca_band_15mm,
                "exposureLength": str(
                    timedelta(
                        minutes=prop_obj.telescope_settings.atca_band_15mm_exptime
                    )
                ),
                "freq1": prop_obj.telescope_settings.atca_band_15mm_freq1,
                "freq2": prop_obj.telescope_settings.atca_band_15mm_freq2,
            },
            "4cm": {
                "use": prop_obj.telescope_settings.atca_band_4cm,
                "exposureLength": str(
                    timedelta(minutes=prop_obj.telescope_settings.atca_band_4cm_exptime)
                ),
                "freq1": prop_obj.telescope_settings.atca_band_4cm_freq1,
                "freq2": prop_obj.telescope_settings.atca_band_4cm_freq2,
            },
            "16cm": {
                "use": prop_obj.telescope_settings.atca_band_16cm,
                "exposureLength": str(
                    timedelta(
                        minutes=prop_obj.telescope_settings.atca_band_16cm_exptime
                    )
                ),
                # Only frequency available due to limited bandwidth
                "freq1": 2100,
                "freq2": 2100,
            },
        }

        # We have our request now, so we need to craft the service request to submit it to
        # the rapid response service.
        rapidObj = {"requestDict": rq}
        rapidObj["authenticationToken"] = prop_obj.project_id.password
        rapidObj["email"] = prop_obj.project_id.atca_email
        trigger_real_pretend = utils_helper.TRIGGER_ON[0][0]

        # user = ATCAUser.objects.all().first()

        # rapidObj["httpAuthUsername"] = user.httpAuthUsername
        # rapidObj["httpAuthPassword"] = user.httpAuthPassword

        rapidObj["httpAuthUsername"] = "TestUser"
        rapidObj["httpAuthPassword"] = "TestPassword"

        rapidObj["serverProtocol"] = "http://"
        rapidObj["serverName"] = "test-api:8000"
        rapidObj["apiEndpoint"] = "/api/atca_proposal_request/"

        if prop_obj.testing == trigger_real_pretend:
            rapidObj["test"] = True
            rapidObj["noTimeLimit"] = True
            rapidObj["noScoreLimit"] = True

        print("DEBUG - rapidObj : ", rapidObj)
        request = arrApi.api(rapidObj)
        try:
            response = request.send()
        except Exception as r:
            logger.error(f"ATCA error message: {r}")
            decision_reason_log += (
                f"{datetime.utcnow()}: Event ID {event_id}: ATCA error message: {r}\n "
            )
            return "E", decision_reason_log, []

        # # Check for errors
        # if  (not response["authenticationToken"]["received"]) or (not response["authenticationToken"]["verified"]) or \
        #     (not response["schedule"]["received"]) or (not response["schedule"]["verified"]):
        #     decision_reason_log += f"ATCA return message: {r}\n "
        #     return 'E', decision_reason_log, []

        return "T", decision_reason_log, [response["id"]]

    def save_observation(self, context, trigger_id, obsid=None, reason=None) -> Dict:
        """Save the observation result through the API."""
        print("DEBUG - saving ATCA observation")

        api_url = f"http://web:8000/api/create-observation/"
        # trigger_id = str(random.randrange(10000, 99999))

        # Prepare the payload
        payload = {
            "trigger_id": str(trigger_id),
            "telescope_name": context[
                "proposal_decision_model"
            ].proposal.telescope_settings.telescope.name,
            "proposal_decision_id": context["proposal_decision_model"].id,
            "event_id": context["latestVoevent"].id,
            "reason": reason or context["reason"],
        }

        print("DEBUG - payload starts: \n")
        print(payload)
        print("DEBUG - payload ends \n")

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"Observation created: {result}")

        except requests.RequestException as e:
            print(f"Error creating observation: {e}")

        return result


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

        # Initialize the context with the event and default values
        context = utils_gw.initialize_context(event, kwargs)

        # Chain the checks together, maintaining the original order
        context = utils_gw.process_false_alarm_rate(self, context)

        context = utils_gw.update_event_parameters(context)

        # two hour check
        context = utils_gw.check_event_time(context)

        context = utils_gw.check_lvc_instruments(context)

        context = utils_gw.handle_event_types(context)

        context = utils_gw.check_probabilities(telescope_settings, self, context)

        print("DEBUG - context", context)

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
        print("DEBUG - Trigger ATCA observation for GW source")
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("ATCA") is False:
            return context

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
        print("DEBUG - Trigger MWA observation for GW source")
        voevents = context["voevents"]
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("MWA") is False:
            return context

        context = utils_helper.prepare_observation_context(context, voevents)

        print("DEBUG - num of voevents:", len(voevents))

        if len(voevents) == 1:
            # Dump out the last ~3 mins of MWA buffer to try and catch event
            context = utils_telgw.handle_first_observation(
                telescope_settings=telescope_settings, context=context
            )

            # Handle the unique case of the early warning
            if context["latestVoevent"].event_type == "EarlyWarning":
                print("DEBUG - MWA telescope - GW - EarlyWarning")
                context = utils_telgw.handle_early_warning(
                    telescope_settings=telescope_settings, context=context
                )
            elif (
                context["latestVoevent"].lvc_skymap_fits != None
                and context["latestVoevent"].event_type != "EarlyWarning"
            ):
                print("DEBUG - MWA telescope - GW - Skymap")
                context = utils_telgw.handle_skymap_event(
                    telescope_settings=telescope_settings, context=context
                )
                print("DEBUG - MWA telescope - GW - Skymap Calculated")

        # Repoint if there is a newer skymap with different positions
        if len(voevents) > 1 and context["latestVoevent"].lvc_skymap_fits:
            print("DEBUG - MWA telescope - GW - Repoint")

            # get latest event for MWA
            print(f"DEBUG - checking to repoint")
            context["reason"] = (
                f"{context['latestVoevent'].trig_id} - Event has a skymap"
            )

            latest_obs = get_latest_observation(context["proposal_decision_model"])

            print("latest_obs:", latest_obs)

            context = utils_telgw.handle_gw_voevents(
                telescope_settings=telescope_settings,
                context=context,
                latest_obs=latest_obs,
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
        print("DEBUG - Trigger ATCA observation for GRB source - New")
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("ATCA") is False:
            return context

        # context = utils_tel.handle_atca_observation(context)

        context = utils_atca.handle_atca_observation(
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
        print("DEBUG - Trigger MWA observation for GRB source")
        voevents = context["voevents"]
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("MWA") is False:
            return context

        context = utils_helper.prepare_observation_context(
            context=context, voevents=voevents
        )

        print("passed Non - GW check")
        context = utils_nongw.handle_non_gw_observation_class(
            telescope_settings=telescope_settings, context=context
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

    def trigger_atca_observation(
        self,
        context: Dict,
        telescope_settings: Union[
            BaseTelescopeSettings, MWATelescopeSettings, ATCATelescopeSettings
        ],
        **kwargs,
    ) -> Tuple[str, str]:
        print("DEBUG - Trigger ATCA observation for NU source - New")
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("ATCA") is False:
            return context

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
        print("DEBUG - Trigger MWA observation for NU source")
        voevents = context["voevents"]
        telescope_name = telescope_settings.telescope.name

        if context["stop_processing"]:
            return context

        if telescope_name.startswith("MWA") is False:
            return context

        context = utils_helper.prepare_observation_context(
            context=context, voevents=voevents
        )

        print("passed Non - GW check")
        context = utils_nongw.handle_non_gw_observation_class(
            telescope_settings=telescope_settings, context=context
        )

        return context


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

    def trigger_gen_observation(self, context: Dict, **kwargs) -> Tuple[str, str]:
        print("DEBUG - Trigger observation")

        context = utils_helper.check_mwa_horizon_and_prepare_context(context)

        # TODO: Remove this when we stop testing
        print("stop_processing:", context["stop_processing"])
        # context["stop_processing"] = False

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
                f"{context['decision_reason_log']}{datetime.utcnow()}: Event ID {context['event_id']}: Not making an MWA observation. \n"
            )

        return context["decision"], context["decision_reason_log"]


class ProposalDecision(BaseModel):
    id: int
    decision: str
    decision_reason: Optional[str]
    proposal: Optional[int]  # Assuming this is the ID of the related ProposalSettings
    event_group_id: EventGroup  # event_group: EventGroupSchema
    trig_id: Optional[str]
    duration: Optional[float]
    ra: Optional[float]
    dec: Optional[float]
    alt: Optional[float]
    az: Optional[float]
    ra_hms: Optional[str]
    dec_dms: Optional[str]
    pos_error: Optional[float]
    recieved_data: datetime

    class Config:
        from_attributes = True


class MWAResponseSimple(BaseModel):
    clear: Dict[str, Any] = None
    errors: Dict[str, Any] = None
    params: Dict[str, Any] = None
    success: bool = None
    schedule: Dict[str, Any] = None
    obsid_list: List[int] = None
    trigger_id: Union[int, str] = None


class MWASubArrays(BaseModel):
    ra: List[float]
    dec: List[float]


class TelescopeSchema(BaseModel):
    id: int
    name: str
    lon: float
    lat: float
    height: float


class Observations(BaseModel):

    telescope: TelescopeSchema
    proposal_decision_id: ProposalDecision
    event: Event
    trigger_id: str
    website_link: Optional[str] = None
    reason: Optional[str] = None
    mwa_sub_arrays: Optional[MWASubArrays] = None
    created_at: datetime
    request_sent_at: Optional[datetime] = None
    mwa_sky_map_pointings: Optional[str] = None
    mwa_response: Optional[MWAResponseSimple] = None

    class Config:
        from_attributes = True


def get_latest_observation(proposal_decision_model):
    """Retrieve the latest observation for the given telescope via API."""
    telescope_id = proposal_decision_model.proposal.telescope_settings.telescope.name
    api_url = f"http://web:8000/api/latest-observation/{telescope_id}/"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        observation_data = response.json()

        # Create and return a Pydantic instance
        values = Observations.parse_obj(observation_data)

        return values
    except requests.RequestException as e:
        print(f"Error fetching latest observation: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing observation data: {e}")
        return None
