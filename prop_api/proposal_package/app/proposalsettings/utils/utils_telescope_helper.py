import datetime as dt
import logging
from datetime import datetime, timedelta
from math import floor

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.table import Table
from astropy.time import Time
from astropy.utils.data import download_file

# ATCAUser, Observations
from .utils_telescope import (getMWAPointingsFromSkymapFile,
                              getMWARaDecFromAltAz, isClosePosition)

logger = logging.getLogger(__name__)

json_logger = logging.getLogger('django_json')

GRB = "GRB"
FS = "FS"
NU = "NU"
GW = "GW"
SOURCE_CHOICES = (
    (GRB, "Gamma-ray burst"),
    (FS, "Flare star"),
    (NU, "Neutrino"),
    (GW, "Gravitational wave"),
)

TRIGGER_ON = (
    ("PRETEND_REAL", "Real events only (Pretend Obs)"),
    ("BOTH", "Real events (Real Obs) and test events (Pretend Obs)"),
    ("REAL_ONLY", "Real events only (Real Obs)"),
)


def round_to_nearest_modulo_8(number):
    """Rounds a number to the nearest modulo of 8."""
    remainder = number % 8
    if remainder >= 4:
        rounded_number = number + (8 - remainder)
    else:
        rounded_number = number - remainder
    return rounded_number


def dump_mwa_buffer():
    return True


def get_default_sub_arrays(ps):
    """Get default sub arrays based on proposal settings."""
    return {
        "dec": [
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_NE,
                az=ps.telescope_settings.mwa_sub_az_NE,
                time=Time.now(),
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_NW,
                az=ps.telescope_settings.mwa_sub_az_NW,
                time=Time.now(),
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_SE,
                az=ps.telescope_settings.mwa_sub_az_SE,
                time=Time.now(),
            )[1].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_SW,
                az=ps.telescope_settings.mwa_sub_az_SW,
                time=Time.now(),
            )[1].value,
        ],
        "ra": [
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_NE,
                az=ps.telescope_settings.mwa_sub_az_NE,
                time=Time.now(),
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_NW,
                az=ps.telescope_settings.mwa_sub_az_NW,
                time=Time.now(),
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_SE,
                az=ps.telescope_settings.mwa_sub_az_SE,
                time=Time.now(),
            )[0].value,
            getMWARaDecFromAltAz(
                alt=ps.telescope_settings.mwa_sub_alt_SW,
                az=ps.telescope_settings.mwa_sub_az_SW,
                time=Time.now(),
            )[0].value,
        ],
    }


def get_skymap_pointings_from_cache(skymap_fits):
    skymap = Table.read(skymap_fits)
    (skymap, time, pointings) = getMWAPointingsFromSkymapFile(skymap)
    return skymap, pointings


def get_skymap_pointings(skymap_fits):
    """Download and process skymap FITS file to get pointings."""
    event_filename = download_file(skymap_fits, cache=True)
    skymap = Table.read(event_filename)
    (skymap, time, pointings) = getMWAPointingsFromSkymapFile(skymap)
    return skymap, pointings


def should_repoint(current_arrays_ra, current_arrays_dec, pointings):
    """Determine whether repointing is necessary based on the new skymap."""
    repoint = False

    pointings_dec = []
    pointings_ra = []
    for res in pointings:
        pointings_ra.append(res[3])
        pointings_dec.append(res[4])

        repoint = True
        for index, val in enumerate(current_arrays_dec):
            print(f"index: {index}")
            ra1 = current_arrays_ra[index] * u.deg
            dec1 = current_arrays_dec[index] * u.deg
            ra2 = res[3]
            dec2 = res[4]

            if isClosePosition(ra1, dec1, ra2, dec2):
                repoint = False

    print(f"DEBUG - current_arrays_dec : {current_arrays_dec}")
    print(f"DEBUG - pointings_dec : {pointings_dec}")
    print(f"DEBUG - current_arrays_ra : {current_arrays_ra}")
    print(f"DEBUG - pointings_ra : {pointings_ra}")

    return repoint


def generate_sub_arrays_from_skymap(pointings):
    """Generate sub arrays from skymap pointings."""
    return {
        "dec": [pointings[i][4].value for i in range(4)],
        "ra": [pointings[i][3].value for i in range(4)],
    }


def check_mwa_horizon_and_prepare_context(context):

    proposal_decision_model = context["proposal_decision_model"]
    event_id = context["event_id"]
    decision_reason_log = context["decision_reason_log"]

    # condition to check if the telescope is MWA and if the ra and dec are not None
    # stops
    if (
        proposal_decision_model.proposal.telescope_settings.telescope.name.startswith(
            "MWA"
        )
        and proposal_decision_model.ra
        and proposal_decision_model.dec
    ) == False:
        json_logger.debug(
            "Not checking if above the horizon because the ra and dec are not set or telescope is not MWA",
            extra={
                "function": "check_mwa_horizon_and_prepare_context",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )
        return context

    if (
        proposal_decision_model.proposal.telescope_settings.telescope.name.startswith(
            "MWA"
        )
        and proposal_decision_model.ra
        and proposal_decision_model.dec
    ):

        json_logger.debug(
            "Checking if is above the horizon for MWA",
            extra={
                "function": "check_mwa_horizon_and_prepare_context",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        print("Checking if is above the horizon for MWA")

        # Create Earth location for the telescope
        telescope = proposal_decision_model.proposal.telescope_settings.telescope
        location = EarthLocation(
            lon=telescope.lon * u.deg,
            lat=telescope.lat * u.deg,
            height=telescope.height * u.m,
        )
        print("obtained earth location")

        obs_source = SkyCoord(
            proposal_decision_model.ra,
            proposal_decision_model.dec,
            # equinox='J2000',
            unit=(u.deg, u.deg),
        )
        print("obtained obs source location")
        # Convert from RA/Dec to Alt/Az
        obs_source_altaz_beg = obs_source.transform_to(
            AltAz(obstime=Time.now(), location=location)
        )
        alt_beg = obs_source_altaz_beg.alt.deg
        # Calculate alt at end of obs
        end_time = Time.now() + timedelta(
            seconds=proposal_decision_model.proposal.telescope_settings.mwa_exptime
        )
        obs_source_altaz_end = obs_source.transform_to(
            AltAz(obstime=end_time, location=location)
        )
        alt_end = obs_source_altaz_end.alt.deg

        print("converted obs for horizon")

        json_logger.debug(
            "converted obs for horizon",
            extra={
                "function": "check_mwa_horizon_and_prepare_context",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

        if (
            alt_beg
            < proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit
            and alt_end
            < proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit
        ):
            horizon_message = f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Not triggering due to horizon limit: alt_beg {alt_beg:.4f} < {proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit:.4f} and alt_end {alt_end:.4f} < {proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit:.4f}. "
            logger.debug(horizon_message)

            context["stop_processing"] = True
            context["decision_reason_log"] = decision_reason_log + horizon_message
            context["decision"] = "I"

            json_logger.debug(
                horizon_message,
                extra={
                    "function": "check_mwa_horizon_and_prepare_context",
                    "trig_id": context["proposal_decision_model"].trig_id,
                    "event_id": context["event_id"],
                },
            )

            return context

        elif (
            alt_beg
            < proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit
        ):
            # Warn them in the log
            decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Warning: The source is below the horizion limit at the start of the observation alt_beg {alt_beg:.4f}. \n"

            json_logger.debug(
                "Warning: The source is below the horizion limit at the start of the observation alt_beg {alt_beg:.4f}",
                extra={
                    "function": "check_mwa_horizon_and_prepare_context",
                    "trig_id": context["proposal_decision_model"].trig_id,
                    "event_id": context["event_id"],
                },
            )

        elif (
            alt_end
            < proposal_decision_model.proposal.telescope_settings.mwa_horizon_limit
        ):
            # Warn them in the log
            decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Warning: The source will set below the horizion limit by the end of the observation alt_end {alt_end:.4f}. \n"

            json_logger.debug(
                "Warning: The source will set below the horizion limit by the end of the observation alt_end {alt_end:.4f}",
                extra={
                    "function": "check_mwa_horizon_and_prepare_context",
                    "trig_id": context["proposal_decision_model"].trig_id,
                    "event_id": context["event_id"],
                },
            )

        # above the horizon so send off telescope specific set ups
        decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Above horizon so attempting to observe with {proposal_decision_model.proposal.telescope_settings.telescope.name}. \n"

        logger.debug(
            f"Triggered observation at an elevation of {alt_beg} to elevation of {alt_end}"
        )

        json_logger.debug(
            f"Triggered observation at an elevation of {alt_beg} to elevation of {alt_end}",
            extra={
                "function": "check_mwa_horizon_and_prepare_context",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )

    context["decision_reason_log"] = decision_reason_log
    context["event_id"] = event_id
    context["proposal_decision_model"] = proposal_decision_model

    return context


def prepare_observation_context(context, voevents):

    json_logger.debug(
        "prepare_observation_context",
        extra={
            "function": "prepare_observation_context",
            "trig_id": context["proposal_decision_model"].trig_id,
            "event_id": context["event_id"],
        },
    )

    proposal_decision_model = context["proposal_decision_model"]
    telescopes = context["telescopes"]
    latestVoevent = context["latestVoevent"]

    trigger_both = TRIGGER_ON[1][0]
    trigger_real = TRIGGER_ON[2][0]

    vcsmode = (
        proposal_decision_model.proposal.telescope_settings.telescope.name.endswith(
            "VCS"
        )
    )
    if vcsmode:
        print("VCS Mode")

    # Create an observation name
    # Collect event telescopes

    print(proposal_decision_model.trig_id)

    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and seperate with a _
    telescopes = "_".join(list(set(telescopes)))
    obsname = f"{telescopes}_{proposal_decision_model.trig_id}"

    buffered = False

    pretend = True
    repoint = None

    print(
        f"proposal_decision_model.proposal.testing {proposal_decision_model.proposal.testing}"
    )
    # print(f"latestVoevent {latestVoevent.__dict__}")
    if (
        latestVoevent.role == "test"
        and proposal_decision_model.proposal.testing != trigger_both
    ):
        json_logger.error(
            "Invalid event observation and proposal setting",
            extra={
                "function": "prepare_observation_context",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
            },
        )
        raise Exception("Invalid event observation and proposal setting")
        

    if (
        proposal_decision_model.proposal.testing == trigger_both
        and latestVoevent.role != "test"
    ):
        pretend = False
    if (
        proposal_decision_model.proposal.testing == trigger_real
        and latestVoevent.role != "test"
    ):
        pretend = False
    print(f"pretend: {pretend}")

    context["buffered"] = buffered
    context["pretend"] = pretend
    context["repoint"] = repoint
    context["vcsmode"] = vcsmode
    context["obsname"] = obsname
    context["telescopes"] = telescopes

    json_logger.debug(
        f"buffered: {buffered}, pretend: {pretend}, repoint: {repoint}, vcsmode: {vcsmode}, obsname: {obsname}, telescopes: {telescopes}",
        extra={
            "function": "prepare_observation_context",
            "trig_id": context["proposal_decision_model"].trig_id,
            "event_id": context["event_id"],
        },
    )

    return context
