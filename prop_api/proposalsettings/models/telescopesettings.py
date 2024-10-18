"""
This module defines telescope settings classes for different telescopes.

The module contains a base class `BaseTelescopeSettings` which defines common
attributes and methods for all telescope settings. It also includes two child
classes, `MWATelescopeSettings` and `ATCATelescopeSettings`, which implement
telescope-specific settings and behaviors.

Classes:
    BaseTelescopeSettings: Abstract base class for telescope settings.
    MWATelescopeSettings: Settings specific to the Murchison Widefield Array (MWA) telescope.
    ATCATelescopeSettings: Settings specific to the Australia Telescope Compact Array (ATCA).

Each child class implements two key methods:
    - trigger_telescope: Sends a request to the real system or a test API to trigger
      an observation, depending on the environment (production or development).
    - save_observation: Saves the observation details through an API call, with
      specifics varying based on the telescope.

These classes are used to manage telescope-specific settings and handle the
process of triggering observations and saving their results in a standardized way
across different telescope systems.
"""

import datetime as dt
import logging
import os
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import atca_rapid_response_api as arrApi
import requests
from astropy.time import Time
from pydantic import BaseModel, Field

from ..config import (
    ATCA_API_ENDPOINT,
    ATCA_AUTH,
    ATCA_PROTOCOL,
    ATCA_SERVER_NAME,
    PROJECT_PASSWORDS,
)
from ..consts import *
from ..utils import utils_api
from ..utils import utils_helper as utils_helper
from ..utils.utils_log import log_event
from ..utils.utils_trigger_mwa import trigger as trigger_mwa
from .telescope import Telescope

logger = logging.getLogger(__name__)

# Get a json logger
json_logger = logging.getLogger('django_json')


class BaseTelescopeSettings(BaseModel, ABC):
    """
    Abstract base class for telescope settings.

    This class defines common attributes and methods for all telescope settings.
    It includes fields for various observation parameters and abstract methods
    for triggering telescopes and saving observations.

    Attributes:
        telescope (Telescope): The telescope associated with these settings.
        maximum_observation_time_seconds (int): Maximum observation time in seconds.
        event_any_duration (bool): Whether to trigger on events with any duration.
        event_min_duration (float): Minimum event duration.
        event_max_duration (float): Maximum event duration.
        pending_min_duration_1 (float): Pending minimum duration 1.
        pending_max_duration_1 (float): Pending maximum duration 1.
        pending_min_duration_2 (float): Pending minimum duration 2.
        pending_max_duration_2 (float): Pending maximum duration 2.
        maximum_position_uncertainty (float): Maximum allowed position uncertainty.
        fermi_prob (float): Minimum probability to observe for Fermi sources.
        swift_rate_signif (float): Minimum "RATE_SIGNIF" to observe for SWIFT sources.
        antares_min_ranking (int): Minimum rating to observe for Antares sources.
        repointing_limit (float): Minimum distance for repointing.
        observe_significant (bool): Whether to observe only high-significance events.
    """

    # id: int
    telescope: Telescope

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
    swift_rate_signif: float = Field(
        DEFAULT_SWIFT_RATE_SIGNIF,
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

    class Config:
        extra = "forbid"  # This forbids any extra fields

    @abstractmethod
    def trigger_telescope(
        self,
        context,
        **kwargs,
    ) -> Tuple[str, str, List[Union[int, str]], Optional[str]]:
        """
        Abstract method to trigger a telescope observation.

        This method should be implemented by subclasses to handle the specific
        logic for triggering an observation on the respective telescope.

        Args:
            context (dict): A dictionary containing context information for the observation.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[str, str, List[Union[int, str]], Optional[str]]: A tuple containing:
                - A string indicating the result of the trigger attempt ('T', 'I', or 'E').
                - An updated decision reason log.
                - A list of observation IDs.
                - Optional additional result information.
        """
        pass

    @abstractmethod
    def save_observation(self, context, trigger_id, obsid=None, reason=None) -> Dict:
        """
        Abstract method to save an observation.

        This method should be implemented by subclasses to handle the specific
        logic for saving an observation for the respective telescope.

        Args:
            context (dict): A dictionary containing context information for the observation.
            trigger_id (str): The ID of the trigger.
            obsid (Optional[str]): The observation ID, if available.
            reason (Optional[str]): The reason for the observation, if available.

        Returns:
            Dict: A dictionary containing the result of the save operation.
        """
        pass


class MWATelescopeSettings(BaseTelescopeSettings):
    """
    Settings specific to the Murchison Widefield Array (MWA) telescope.

    This class extends BaseTelescopeSettings with MWA-specific attributes and methods.

    Attributes:
        start_observation_at_high_sensitivity (bool): Whether to start observations at high sensitivity.
        mwa_sub_alt_NE (float): Altitude in degrees for the North-East sub array.
        mwa_sub_az_NE (float): Azimuth in degrees for the North-East sub array.
        mwa_sub_alt_NW (float): Altitude in degrees for the North-West sub array.
        mwa_sub_az_NW (float): Azimuth in degrees for the North-West sub array.
        mwa_sub_alt_SW (float): Altitude in degrees for the South-West sub array.
        mwa_sub_az_SW (float): Azimuth in degrees for the South-West sub array.
        mwa_sub_alt_SE (float): Altitude in degrees for the South-East sub array.
        mwa_sub_az_SE (float): Azimuth in degrees for the South-East sub array.
        mwa_freqspecs (str): The frequency channels IDs for the MWA to observe at.
        mwa_exptime (int): Observation time in seconds.
        mwa_calexptime (float): Calibrator Observation time in seconds.
        mwa_freqres (float): Correlator frequency resolution for observations.
        mwa_inttime (float): Correlator integration time for observations in seconds.
        mwa_horizon_limit (float): The minimum elevation of the source to observe (in degrees).
        mwa_nobs (float): Number of observations to make.
    """

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
    mwa_nobs: float = Field(
        None,
        description="Number of observations to make.",
    )

    class Config:
        extra = "forbid"  # This forbids any extra fields t

    @log_event(
        log_location="end", message=f"MWA trigger telescope completed", level="info"
    )
    def trigger_telescope(
        self,
        context,
        **kwargs,
    ) -> Tuple[str, str, List[Union[int, str]], str]:
        """
        Trigger an MWA telescope observation.

        This method handles the logic for triggering an MWA observation, including
        different scenarios such as early warning events and sub-array observations.

        Args:
            context (dict): A dictionary containing context information for the observation.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[str, str, List[Union[int, str]], str]: A tuple containing:
                - A string indicating the result of the trigger attempt ('T', 'I', or 'E').
                - An updated decision reason log.
                - A list of observation IDs.
                - The raw result from the MWA trigger operation.
        """
        # return "T", decision_reason_log, [], {}
        prop_dec = context["prop_dec"]
        prop_settings = context["prop_dec"].proposal
        decision_reason_log = context["decision_reason_log"]
        obsname = context["obsname"]
        vcsmode = context["vcsmode"]
        event_id = context["event_id"]
        mwa_sub_arrays = context["mwa_sub_arrays"]
        buffered = context["buffered"]
        pretend = context["pretend"]

        print("DEBUG - triggering MWA")
        # print(f"DEBUG - proposal: {prop_settings.__dict__}")
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

                result = trigger_mwa(
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
                # print(f"buffered result: {result}")

            elif prop_settings.source_type == "GW" and mwa_sub_arrays != None:
                print("DEBUG - Scheduling an ra/dec sub array observation")

                result = trigger_mwa(
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

                result = trigger_mwa(
                    project_id=prop_settings.project_id.id,
                    secure_key=prop_settings.project_id.password,
                    pretend=pretend,
                    ra=prop_dec.ra,
                    dec=prop_dec.dec,
                    alt=prop_dec.alt,
                    az=prop_dec.az,
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
            decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Exception trying to schedule event {e}\n "

            json_logger.error(
                "Triggering MWA observation",
                extra={
                    "function": "MWATelescopeSettings.trigger_telescope",
                    "trig_id": prop_dec.trig_id,
                    "event_id": event_id,
                },
            )

            return "E", decision_reason_log, [], []

        logger.debug(f"result: {result}")
        # Check if succesful
        if result is None:
            print("DEBUG - Error: no result from scheduling observation")
            decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Web API error, possible server error.\n "
            return "E", decision_reason_log, [], result
        if not result["success"]:
            print("DEBUG - Error: failed to schedule observation")
            # Observation not succesful so record why
            for err_id in result["errors"]:
                decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: {result['errors'][err_id]}.\n "
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

        context["reached_end"] = True

        return "T", decision_reason_log, obsids, result

    @log_event(
        log_location="end", message=f"MWA save observation completed", level="info"
    )
    def save_observation(self, context, trigger_id, obsid=None, reason=None) -> Dict:
        """
        Save an MWA observation.

        This method handles the logic for saving an MWA observation, including
        preparing the payload and making an API call to create the observation record.

        Args:
            context (dict): A dictionary containing context information for the observation.
            trigger_id (str): The ID of the trigger.
            obsid (Optional[str]): The observation ID, if available.
            reason (Optional[str]): The reason for the observation, if available.

        Returns:
            Dict: A dictionary containing the result of the save operation.
        """
        print("DEBUG - saving MWA observation")

        # Prepare the payload
        payload = {
            "trigger_id": str(trigger_id),
            "telescope_name": context[
                "prop_dec"
            ].proposal.telescope_settings.telescope.name,
            "proposal_decision_id": context["prop_dec"].id,
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

        try:
            response = utils_api.create_observation(payload)
            response.raise_for_status()
            result = response.json()

            print(f"Observation created: {result}")

        except requests.RequestException as e:
            print(f"Error creating observation: {e}")

        context["reached_end"] = True

        return result


class ATCATelescopeSettings(BaseTelescopeSettings):
    """
    Settings specific to the Australia Telescope Compact Array (ATCA).

    This class extends BaseTelescopeSettings with ATCA-specific attributes and methods.

    Attributes:
        atca_band_3mm (bool): Whether to use the 3mm Band (83-105 GHz).
        atca_band_3mm_exptime (int): 3mm Band Exposure Time (mins).
        atca_band_3mm_freq1 (Optional[int]): 3mm Band Centre frequency 1 (MHz).
        atca_band_3mm_freq2 (Optional[int]): 3mm Band Centre frequency 2 (MHz).
        atca_band_7mm (bool): Whether to use the 7mm Band (30-50 GHz).
        atca_band_7mm_exptime (int): 7mm Band Exposure Time (mins).
        atca_band_7mm_freq1 (Optional[int]): 7mm Band Centre frequency 1 (MHz).
        atca_band_7mm_freq2 (Optional[int]): 7mm Band Centre frequency 2 (MHz).
        atca_band_15mm (bool): Whether to use the 15mm Band (16-25 GHz).
        atca_band_15mm_exptime (int): 15mm Band Exposure Time (mins).
        atca_band_15mm_freq1 (Optional[int]): 15mm Band Centre frequency 1 (MHz).
        atca_band_15mm_freq2 (Optional[int]): 15mm Band Centre frequency 2 (MHz).
        atca_band_4cm (bool): Whether to use the 4cm Band (3.9-11.0 GHz).
        atca_band_4cm_exptime (int): 4cm Band Exposure Time (mins).
        atca_band_4cm_freq1 (Optional[int]): 4cm Band Centre frequency 1 (MHz).
        atca_band_4cm_freq2 (Optional[int]): 4cm Band Centre frequency 2 (MHz).
        atca_band_16cm (bool): Whether to use the 16cm Band (1.1-3.1 GHz).
        atca_band_16cm_exptime (int): 16cm Band Exposure Time (mins).
        atca_max_exptime (int): Maximum Exposure Time (mins).
        atca_min_exptime (int): Minimum Exposure Time (mins).
        atca_prioritise_source (bool): Whether to prioritise time on source rather than time on calibrator.
        atca_dec_min_1 (int): Declination min limit 1 (deg).
        atca_dec_max_1 (int): Declination max limit 1 (deg).
        atca_dec_min_2 (int): Declination min limit 2 (deg).
        atca_dec_max_2 (int): Declination max limit 2 (deg).
    """

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

    @log_event(
        log_location="end", message=f"ATCA save observation completed", level="info"
    )
    def trigger_telescope(
        self,
        context,
        **kwargs,
    ) -> Tuple[str, str, List[Union[int, str]]]:
        """
        Trigger an ATCA telescope observation.

        This method handles the logic for triggering an ATCA observation, including
        preparing the request payload and sending it to the ATCA rapid response service.

        Args:
            context (dict): A dictionary containing context information for the observation.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[str, str, List[Union[int, str]]]: A tuple containing:
                - A string indicating the result of the trigger attempt ('T', 'I', or 'E').
                - An updated decision reason log.
                - A list containing the response ID from the ATCA service.
        """

        prop_dec = context["prop_dec"]
        decision_reason_log = context["decision_reason_log"]
        event_id = context["event_id"]

        prop_obj = prop_dec.proposal

        # TODO add any schedule checks or observation parsing here
        print("DEBUG - trigger_atca_observation")
        # Not below horizon limit so observer
        logger.info(f"Triggering  ATCA at UTC time {Time.now()} ...")

        rq = {
            "source": prop_obj.source_type,
            "rightAscension": prop_dec.ra_hms,
            "declination": prop_dec.dec_dms,
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

        rapidObj["httpAuthUsername"] = ATCA_AUTH.get('username')
        rapidObj["httpAuthPassword"] = ATCA_AUTH.get('password')

        rapidObj["serverProtocol"] = ATCA_PROTOCOL
        rapidObj["serverName"] = ATCA_SERVER_NAME
        rapidObj["apiEndpoint"] = ATCA_API_ENDPOINT

        if prop_obj.testing == trigger_real_pretend:
            rapidObj["test"] = True
            rapidObj["noTimeLimit"] = True
            rapidObj["noScoreLimit"] = True

        # print("DEBUG - rapidObj : ", rapidObj)
        request = arrApi.api(rapidObj)
        try:
            response = request.send()
        except Exception as r:
            logger.error(f"ATCA error message: {r}")
            decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: ATCA error message: {r}\n "

            json_logger.error(
                "ATCA error message. decision: E ",
                extra={
                    "function": "ATCATelescopeSettings.trigger_telescope",
                    "trig_id": prop_dec.trig_id,
                    "event_id": event_id,
                },
            )

            return "E", decision_reason_log, []

        context["reached_end"] = True
        return "T", decision_reason_log, [response["id"]]

    @log_event(
        log_location="end", message=f"ATCA save observation completed", level="info"
    )
    def save_observation(self, context, trigger_id, obsid=None, reason=None) -> Dict:
        """
        Save an ATCA observation.

        This method handles the logic for saving an ATCA observation, including
        preparing the payload and making an API call to create the observation record.

        Args:
            context (dict): A dictionary containing context information for the observation.
            trigger_id (str): The ID of the trigger.
            obsid (Optional[str]): The observation ID, if available.
            reason (Optional[str]): The reason for the observation, if available.

        Returns:
            Dict: A dictionary containing the result of the save operation.
        """
        print("DEBUG - saving ATCA observation")

        # Prepare the payload
        payload = {
            "trigger_id": str(trigger_id),
            "telescope_name": context[
                "prop_dec"
            ].proposal.telescope_settings.telescope.name,
            "proposal_decision_id": context["prop_dec"].id,
            "event_id": context["latestVoevent"].id,
            "reason": reason or context["reason"],
        }

        try:
            response = utils_api.create_observation(payload)
            # response.raise_for_status()
            result = response.json()
            print(f"Observation created: {result}")

        except requests.RequestException as e:
            print(f"Error creating observation: {e}")

            json_logger.error(
                "Error creating observation",
                extra={
                    "function": "ATCATelescopeSettings.save_observation",
                    "trig_id": context["prop_dec"].trig_id,
                    "event_id": context["event_id"],
                },
            )

        context["reached_end"] = True
        return result
