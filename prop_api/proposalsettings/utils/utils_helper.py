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
from .utils_calculation import (
    getMWAPointingsFromSkymapFile,
    getMWARaDecFromAltAz,
    isClosePosition,
)
from .utils_log import log_event

logger = logging.getLogger(__name__)

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
    """
    Rounds a number to the nearest modulo of 8.

    Args:
        number (int): The number to be rounded.

    Returns:
        int: The rounded number.
    """
    remainder = number % 8
    if remainder >= 4:
        rounded_number = number + (8 - remainder)
    else:
        rounded_number = number - remainder
    return rounded_number


def dump_mwa_buffer():
    """
    Dumps the MWA buffer.

    Returns:
        bool: Always returns True.
    """
    return True


def get_default_sub_arrays(ps):
    """
    Get default sub arrays based on proposal settings.

    Args:
        ps (ProposalSettings): The proposal settings object.

    Returns:
        dict: A dictionary containing 'dec' and 'ra' lists for the sub-arrays.
    """
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
    """
    Retrieve skymap pointings from a cached FITS file.

    Args:
        skymap_fits (str): Path to the cached skymap FITS file.

    Returns:
        tuple: A tuple containing the skymap and pointings.
    """
    skymap = Table.read(skymap_fits)
    (skymap, time, pointings) = getMWAPointingsFromSkymapFile(skymap)
    return skymap, pointings


def get_skymap_pointings(skymap_fits):
    """
    Download and process skymap FITS file to get pointings.

    Args:
        skymap_fits (str): URL or path to the skymap FITS file.

    Returns:
        tuple: A tuple containing the skymap and pointings.
    """
    event_filename = download_file(skymap_fits, cache=True)
    skymap = Table.read(event_filename)
    (skymap, time, pointings) = getMWAPointingsFromSkymapFile(skymap)
    return skymap, pointings


def should_repoint(current_arrays_ra, current_arrays_dec, pointings):
    """
    Determine whether repointing is necessary based on the new skymap.

    Args:
        current_arrays_ra (list): Current right ascension values of the arrays.
        current_arrays_dec (list): Current declination values of the arrays.
        pointings (list): New pointings from the skymap.

    Returns:
        bool: True if repointing is necessary, False otherwise.
    """
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
    """
    Generate sub arrays from skymap pointings.

    Args:
        pointings (list): List of pointings from the skymap.

    Returns:
        dict: A dictionary containing 'dec' and 'ra' lists for the sub-arrays.
    """
    return {
        "dec": [pointings[i][4].value for i in range(4)],
        "ra": [pointings[i][3].value for i in range(4)],
    }


@log_event(log_location="end", message=f"prepare context", level="debug")
def check_mwa_horizon_and_prepare_context(context):
    """
    Check if the MWA telescope is above the horizon and prepare the observation context.

    Args:
        context (dict): The current context dictionary.

    Returns:
        dict: The updated context dictionary.
    """
    prop_dec = context["prop_dec"]
    event_id = context["event_id"]
    decision_reason_log = context["decision_reason_log"]

    # condition to check if the telescope is MWA and if the ra and dec are not None
    # stops
    if (
        prop_dec.proposal.telescope_settings.telescope.name.startswith("MWA")
        and prop_dec.ra
        and prop_dec.dec
    ) == False:

        context["reached_end"] = True

        return context

    if (
        prop_dec.proposal.telescope_settings.telescope.name.startswith("MWA")
        and prop_dec.ra
        and prop_dec.dec
    ):

        print("Checking if is above the horizon for MWA")

        # Create Earth location for the telescope
        telescope = prop_dec.proposal.telescope_settings.telescope
        location = EarthLocation(
            lon=telescope.lon * u.deg,
            lat=telescope.lat * u.deg,
            height=telescope.height * u.m,
        )
        print("obtained earth location")

        obs_source = SkyCoord(
            prop_dec.ra,
            prop_dec.dec,
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
        print(
            "DEBUG - prop_dec.proposal.telescope_settings.mwa_exptime:",
            prop_dec.proposal.telescope_settings.mwa_exptime,
        )
        end_time = Time.now() + timedelta(
            seconds=prop_dec.proposal.telescope_settings.mwa_exptime
        )
        obs_source_altaz_end = obs_source.transform_to(
            AltAz(obstime=end_time, location=location)
        )
        alt_end = obs_source_altaz_end.alt.deg

        print("converted obs for horizon")

        print("DEBUG - alt_beg:", alt_beg)
        print("DEBUG - alt_end:", alt_end)
        print(
            "DEBUG - prop_dec.proposal.telescope_settings.mwa_horizon_limit:",
            prop_dec.proposal.telescope_settings.mwa_horizon_limit,
        )

        if (
            alt_beg < prop_dec.proposal.telescope_settings.mwa_horizon_limit
            and alt_end < prop_dec.proposal.telescope_settings.mwa_horizon_limit
        ):
            horizon_message = f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Not triggering due to horizon limit: alt_beg {alt_beg:.4f} < {prop_dec.proposal.telescope_settings.mwa_horizon_limit:.4f} and alt_end {alt_end:.4f} < {prop_dec.proposal.telescope_settings.mwa_horizon_limit:.4f}. "
            logger.debug(horizon_message)

            context["stop_processing"] = True
            context["decision_reason_log"] = decision_reason_log + horizon_message
            context["decision"] = "I"

            context["reached_end"] = True
            return context

        elif alt_beg < prop_dec.proposal.telescope_settings.mwa_horizon_limit:
            # Warn them in the log
            decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Warning: The source is below the horizion limit at the start of the observation alt_beg {alt_beg:.4f}. \n"

        elif alt_end < prop_dec.proposal.telescope_settings.mwa_horizon_limit:
            # Warn them in the log
            decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Warning: The source will set below the horizion limit by the end of the observation alt_end {alt_end:.4f}. \n"

        # above the horizon so send off telescope specific set ups
        decision_reason_log += f"{datetime.now(dt.timezone.utc)}: Event ID {event_id}: Above horizon so attempting to observe with {prop_dec.proposal.telescope_settings.telescope.name}. \n"

        logger.debug(
            f"Triggered observation at an elevation of {alt_beg} to elevation of {alt_end}"
        )

    context["decision_reason_log"] = decision_reason_log
    context["event_id"] = event_id
    context["prop_dec"] = prop_dec

    context["reached_end"] = True

    return context


@log_event(log_location="end", message=f"Prepared observation context.", level="debug")
def prepare_observation_context(context, voevents):
    """
    Prepare the observation context based on the proposal decision and VOEvents.

    Args:
        context (dict): The current context dictionary.
        voevents (list): List of VOEvent objects.

    Returns:
        dict: The updated context dictionary.
    """
    prop_dec = context["prop_dec"]
    telescopes = context["telescopes"]
    latestVoevent = context["latestVoevent"]

    trigger_both = TRIGGER_ON[1][0]
    trigger_real = TRIGGER_ON[2][0]

    vcsmode = prop_dec.proposal.telescope_settings.telescope.name.endswith("VCS")
    if vcsmode:
        print("VCS Mode")

    # Create an observation name
    # Collect event telescopes

    print(prop_dec.trig_id)

    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and seperate with a _
    telescopes = "_".join(list(set(telescopes)))
    obsname = f"{telescopes}_{prop_dec.trig_id}"

    buffered = False

    pretend = True
    repoint = None

    print(f"prop_dec.proposal.testing {prop_dec.proposal.testing}")
    # print(f"latestVoevent {latestVoevent.__dict__}")
    if latestVoevent.role == "test" and prop_dec.proposal.testing != trigger_both:

        raise Exception("Invalid event observation and proposal setting")

    if prop_dec.proposal.testing == trigger_both and latestVoevent.role != "test":
        pretend = False
    if prop_dec.proposal.testing == trigger_real and latestVoevent.role != "test":
        pretend = False
    print(f"pretend: {pretend}")

    context["buffered"] = buffered
    context["pretend"] = pretend
    context["repoint"] = repoint
    context["vcsmode"] = vcsmode
    context["obsname"] = obsname
    context["telescopes"] = telescopes

    context["reached_end"] = True

    return context
