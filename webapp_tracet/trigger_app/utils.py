from astropy.table import QTable
from astropy import units as u
import astropy_healpix as ah
from astropy.coordinates import SkyCoord, EarthLocation
import numpy as np
from astropy.time import Time
from yaml import load, Loader, dump
import pathlib
filepath = pathlib.Path(__file__).resolve().parent

MWA_LAT = '-26:42:11.95'
MWA_LONG = '116:40:14.93'
MWA_HEIGHT = 377.8
MWA_SPOTS = f"{filepath}/MWA_SPOTS.txt"

MWA = EarthLocation(lat=MWA_LAT,
        lon=MWA_LONG, height=MWA_HEIGHT * u.m)

def getMWARaDecFromAltAz(alt, az):
    mwa_coord = SkyCoord(az, alt, unit=(u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
    ra_dec = mwa_coord.icrs
    ra = ra_dec.ra.deg * u.deg
    dec = ra_dec.dec.deg * u.deg

    print(ra)
    return ra, dec, ra_dec

def isClosePosition(ra1, dec1, ra2, dec2, deg=10):
    # Create SkyCoord objects for the two positions
    coord1 = SkyCoord(ra=ra1*u.deg, dec=dec1*u.deg, frame='icrs')
    coord2 = SkyCoord(ra=ra2*u.deg, dec=dec2*u.deg, frame='icrs')

    # Calculate the angular separation between the two positions
    angular_sep = coord1.separation(coord2)

    print(angular_sep *u.deg)

    print(deg*u.deg)
    # Check if the angular separation is within 10 degrees
    if angular_sep < deg*u.deg:
        print("The positions are within 10 degrees.")
        return True
    else:
        print("The positions are more than 10 degrees apart.")
        return False


def getMWAPointingsFromSkymapFile(skymap):
    with open(MWA_SPOTS, 'r') as file:
        lines = file.readlines()
        data = []
        for line in lines:
            line = line.strip()  # Remove leading/trailing whitespace
            if line.startswith(('---', 'N')) or not line:  # Skip header and empty lines
                continue
            values = line.split('|')
            n = int(values[0].strip())
            az = float(values[1].strip())
            el = float(values[2].strip())
            data.append((n, az, el))

    results = []
    for entry in data:
        (n, az, alt) = entry
        
        ra, dec, ra_dec = getMWARaDecFromAltAz(alt=alt, az=az)
        
        level, ipix = ah.uniq_to_level_ipix(skymap['UNIQ'])
        nside = ah.level_to_nside(level)
        match_ipix = ah.lonlat_to_healpix(ra, dec, nside, order='nested')
        i = np.flatnonzero(ipix == match_ipix)[0]
        
        res = float(skymap[i]['PROBDENSITY'] * (np.pi / 180)**2)
        results.append((n, az, alt, ra, dec, i, res))
        results = sorted(results, key=lambda x: -x[5])

    pointings = []
    for index, result in enumerate(results):
        if(index == 0):
            pointings.append(result)
        
        elif(len(pointings) < 4):
            for index, point in enumerate(pointings):
                if(not isClosePosition(result[3], result[4], point[3], point[4])):
                    pointings.append(point)  
                    return

    return pointings