import io
import os
import pathlib
import time as pytime
from typing import Any, Dict, List, Tuple, TypeVar

import astropy_healpix as ah
import ligo.skymap.plot
import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time
from matplotlib import pyplot as plt
from mhealpy import HealpixMap

filepath = pathlib.Path(__file__).resolve().parent

MWA_LAT = "-26:42:11.95"
MWA_LONG = "116:40:14.93"
MWA_HEIGHT = 377.8
MWA_SPOTS = f"{filepath}/MWA_SPOTS.txt"

MWA = EarthLocation(lat=MWA_LAT, lon=MWA_LONG, height=MWA_HEIGHT * u.m)
PointingVar = TypeVar("PointingVar")


def getMWARaDecFromAltAz(alt, az, time):
    """
    Convert altitude and azimuth coordinates to right ascension and declination for MWA.

    Args:
        alt (float): Altitude in degrees.
        az (float): Azimuth in degrees.
        time (Time): Observation time.

    Returns:
        tuple: (ra, dec, ra_dec) where:
            ra (Quantity): Right ascension in degrees.
            dec (Quantity): Declination in degrees.
            ra_dec (SkyCoord): SkyCoord object representing the ICRS coordinates.
    """
    mwa_coord = SkyCoord(
        az, alt, unit=(u.deg, u.deg), frame="altaz", obstime=time, location=MWA
    )
    ra_dec = mwa_coord.icrs
    ra = ra_dec.ra.deg * u.deg
    dec = ra_dec.dec.deg * u.deg

    return ra, dec, ra_dec


def isClosePosition(
    ra1: float, dec1: float, ra2: float, dec2: float, deg: float = 10
) -> bool:
    """
    Check if two celestial positions are within a specified angular separation.

    Args:
        ra1 (float): Right ascension of the first position in degrees.
        dec1 (float): Declination of the first position in degrees.
        ra2 (float): Right ascension of the second position in degrees.
        dec2 (float): Declination of the second position in degrees.
        deg (float, optional): Maximum angular separation in degrees. Defaults to 10.

    Returns:
        bool: True if positions are within the specified angular separation, False otherwise.
    """
    # Create SkyCoord objects for the two positions

    coord1 = SkyCoord(ra=ra1, dec=dec1, frame="icrs")
    coord2 = SkyCoord(ra=ra2, dec=dec2, frame="icrs")

    # Calculate the angular separation between the two positions
    angular_sep = coord1.separation(coord2)

    # Check if the angular separation is within 10 degrees
    if angular_sep < deg * u.deg:
        print("The positions are within 10 degrees.")
        return True
    else:
        print("The positions are more than 10 degrees apart.")
        return False


def getMWAPointingsFromSkymapFile(skymap):
    """
    Calculate MWA pointings based on a given skymap file.

    Args:
        skymap (dict): Dictionary containing skymap data.

    Returns:
        tuple: (skymap, time, pointings) where:
            skymap (dict): The input skymap.
            time (Time): Observation time (set to a fixed value).
            pointings (list): List of tuples containing pointing information.
    """
    with open(MWA_SPOTS, "r") as file:
        lines = file.readlines()
        data = []
        for line in lines:
            line = line.strip()  # Remove leading/trailing whitespace
            if line.startswith(("---", "N")) or not line:  # Skip header and empty lines
                continue
            values = line.split("|")
            n = int(values[0].strip())
            az = float(values[1].strip())
            el = float(values[2].strip())
            data.append((n, az, el))
    time = Time("2010-01-01T00:00:00")

    results = []
    for entry in data:
        (n, az, alt) = entry

        ra, dec, ra_dec = getMWARaDecFromAltAz(alt=alt, az=az, time=time)

        level, ipix = ah.uniq_to_level_ipix(skymap["UNIQ"])
        nside = ah.level_to_nside(level)
        match_ipix = ah.lonlat_to_healpix(ra, dec, nside, order="nested")
        i = np.flatnonzero(ipix == match_ipix)[0]

        res = float(skymap[i]["PROBDENSITY"] * (np.pi / 180) ** 2)
        results.append((n, az, alt, ra, dec, i, res))
        results = sorted(results, key=lambda x: -x[6])

    pointings = []
    for result in results:
        if len(pointings) >= 4:
            break

        hasClosePositionAlready = False
        for point in pointings:
            if isClosePosition(result[3], result[4], point[3], point[4]):
                hasClosePositionAlready = True

        if len(pointings) == 0 or not hasClosePositionAlready:
            pointings.append(result)

    return (skymap, time, pointings)


def drawMWAPointings(skymap, time, name, pointings: List[PointingVar]):
    """
    Draw MWA pointings on a skymap and save the plot as an image.

    Args:
        skymap (dict): Dictionary containing skymap data.
        time (Time): Observation time.
        name (str): Name to be used in the output file name.
        pointings (List[PointingVar]): List of pointing information.

    Returns:
        str: File name of the saved image.
    """
    plt.close("all")
    with open(MWA_SPOTS, "r") as file:
        lines = file.readlines()
        data = []
        for line in lines:
            line = line.strip()  # Remove leading/trailing whitespace
            if line.startswith(("---", "N")) or not line:  # Skip header and empty lines
                continue
            values = line.split("|")
            n = int(values[0].strip())
            az = float(values[1].strip())
            el = float(values[2].strip())
            data.append((n, az, el))
    fig = plt.figure(figsize=(12, 12), dpi=100)

    # Create a HealpixMap object from the skymap data
    m = HealpixMap(skymap["PROBDENSITY"], skymap["UNIQ"], density=True)

    # Create an axes object with a Mollweide projection
    ax = plt.axes(projection="astro mollweide")

    # Plot the HealpixMap on the axes object
    m.plot(ax=ax, cmap="cylon", alpha=0.9)

    # Plot the grid on the axes object
    # m.plot_grid(ax = plt.gca(), color = 'white', linewidth = 1);
    ax.grid()

    # Add an annotation to the axes object
    tr = ax.get_transform("world")
    ax.annotate("MWA", xy=(MWA.lon.degree, MWA.lat.degree), xycoords=tr)

    for n, az, el in data:
        (ra, dec, ra_dec) = getMWARaDecFromAltAz(el, az, time)
        ax.plot(
            ra.value,
            dec.value,
            color="green",
            marker="o",
            linestyle="dashed",
            linewidth=2,
            markersize=5,
            transform=tr,
        )

    for n, az, alt, ra, dec, i, res in pointings:
        ax.plot(
            ra,
            dec,
            color="blue",
            marker="o",
            linestyle="dashed",
            linewidth=2,
            markersize=10,
            transform=tr,
        )
        sub_array1 = plt.Circle(
            (ra.value, dec.value), 17, color="blue", fill=False, transform=tr
        )
        ax.add_patch(sub_array1)

    fileName = f"{int(pytime.time())}_{name}.png"
    # Show the plot
    filepath = os.path.join(
        pathlib.Path(__file__).resolve().parent.parent,
        "media",
        "mwa_pointings",
        fileName,
    )

    plt.savefig(filepath)
    return fileName


def singleMWAPointing(skymap, time, name, pointing: PointingVar):
    """
    Draw a single MWA pointing on a skymap.

    Args:
        skymap (dict): Dictionary containing skymap data.
        time (Time): Observation time.
        name (str): Name to be used in the output file name.
        pointing (PointingVar): Single pointing information.

    Returns:
        str: File name of the saved image.
    """
    return drawMWAPointings(skymap, time, name, [pointing])


def subArrayMWAPointings(
    skymap,
    time,
    name,
    pointings: Tuple[PointingVar, PointingVar, PointingVar, PointingVar],
):
    """
    Draw multiple MWA pointings (sub-array) on a skymap.

    Args:
        skymap (dict): Dictionary containing skymap data.
        time (Time): Observation time.
        name (str): Name to be used in the output file name.
        pointings (Tuple[PointingVar, PointingVar, PointingVar, PointingVar]): Tuple of four pointing information.

    Returns:
        str: File name of the saved image.
    """
    return drawMWAPointings(skymap, time, name, list(pointings))
