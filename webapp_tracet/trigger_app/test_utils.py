from django.test import TestCase
from trigger_app.utils import getMWAPointingsFromSkymapFile
from astropy.table import Table

class test_skymap_parsing_to_mwa(TestCase):
    """Tests that events in a similar position and time will be grouped as possible event associations and trigger an observation
    """

                
    # def setUp(self):
        # # Setup current RA and Dec at zenith for the MWA
        # MWA = EarthLocation(lat='-26:42:11.95',
        #                     lon='116:40:14.93', height=377.8 * u.m)
        # mwa_coord = SkyCoord(az=0., alt=90., unit=(
        #     u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        # ra_dec = mwa_coord.icrs

    def test_skymap_parsing_to_mwa(self):
        print(
            f"\ntest_skymap_parsing_to_mwa")
        skymap = Table.read("trigger_app/bayestar.multiorder.fits")

        result = getMWAPointingsFromSkymapFile(skymap)
        # print(result)
        self.assertEqual(len(result), 4)
