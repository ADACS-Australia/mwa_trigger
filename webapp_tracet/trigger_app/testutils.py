from django.test import TestCase
from trigger_app.utils import getMWAPointingsFromSkymapFile, isClosePosition
from astropy import units as u
from astropy.table import Table
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.time import Time

class test_skymap_parsing_to_mwa(TestCase):
    """Tests that events in a similar position and time will be grouped as possible event associations and trigger an observation
    """

                
    def setUp(self):
        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95',
                            lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = SkyCoord(az=0., alt=90., unit=(
            u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

    def test_skymap_parsing_to_mwa(self):
        print(
            f"\ntest_skymap_parsing_to_mwa")
        skymap = Table.read("trigger_app/bayestar.multiorder.fits")

        result = getMWAPointingsFromSkymapFile(skymap)
        # print(result)
        self.assertEqual(len(result), 4)

    def test_isClosePosition(self):
        # Define the first RA and Dec values
        ra1 = 120.5 * u.deg
        dec1 = 45.2 * u.deg

        # Define the second RA and Dec values
        ra2 = 130.8 * u.deg
        dec2 = 40.3 * u.deg

        result1 = isClosePosition(ra1, dec1, ra2, dec2, deg=10)

        self.assertEqual(result1, True)

        result2 = isClosePosition(ra1 + 70.0 * u.deg, dec1 - 10.0 * u.deg, ra2, dec2, deg=10)

        self.assertEqual(result2, False)
