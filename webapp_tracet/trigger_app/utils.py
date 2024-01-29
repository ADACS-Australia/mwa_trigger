import io
import os
from astropy import units as u
import astropy_healpix as ah
from matplotlib import pyplot as plt
import ligo.skymap.plot
from mhealpy import HealpixMap
from astropy.time import Time
import time as pytime
from astropy.coordinates import SkyCoord, EarthLocation
import numpy as np
import pathlib
from matplotlib import pyplot as plt
from typing import Tuple, TypeVar, List

filepath = pathlib.Path(__file__).resolve().parent

MWA_LAT = "-26:42:11.95"
MWA_LONG = "116:40:14.93"
MWA_HEIGHT = 377.8
MWA_SPOTS = f"{filepath}/MWA_SPOTS.txt"

MWA = EarthLocation(lat=MWA_LAT, lon=MWA_LONG, height=MWA_HEIGHT * u.m)
PointingVar = TypeVar("PointingVar")


def getMWARaDecFromAltAz(alt, az, time):
    mwa_coord = SkyCoord(
        az, alt, unit=(u.deg, u.deg), frame="altaz", obstime=time, location=MWA
    )
    ra_dec = mwa_coord.icrs
    ra = ra_dec.ra.deg * u.deg
    dec = ra_dec.dec.deg * u.deg

    return ra, dec, ra_dec


def isClosePosition(ra1, dec1, ra2, dec2, deg=10):
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

    for (n, az, el) in data:
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

    for (n, az, alt, ra, dec, i, res) in pointings:
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
    return drawMWAPointings(skymap, time, name, [pointing])


def subArrayMWAPointings(
    skymap,
    time,
    name,
    pointings: Tuple[PointingVar, PointingVar, PointingVar, PointingVar],
):
    return drawMWAPointings(skymap, time, name, list(pointings))
