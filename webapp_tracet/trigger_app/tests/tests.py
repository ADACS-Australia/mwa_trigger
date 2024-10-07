import datetime
import time
from unittest.mock import patch

import astropy.units as u
import pytest
import pytz
import requests
from astropy.coordinates import Angle, EarthLocation, SkyCoord
from astropy.time import Time
from django.contrib.auth.models import User
from django.test import TestCase
from tracet.parse_xml import parsed_VOEvent
from yaml import Loader, load, safe_load

from ..models.event import Event, EventGroup
from ..models.observation import Observations
from ..models.proposal import ProposalDecision
from ..models.telescope import Telescope
from ..models.user import ATCAUser


def create_voevent_wrapper(trig, ra_dec, dec_alter=True):
    if dec_alter and ra_dec and trig.ra and trig.dec:
        dec = ra_dec.dec.deg
        dec_dms = ra_dec.dec.to_string(unit=u.deg, sep=":")
        ra = ra_dec.ra.deg
        ra_hms = ra_dec.ra.to_string(unit=u.hour, sep=":")
    elif ra_dec and trig.ra and trig.dec:
        dec = trig.dec
        dec_dms = trig.dec_dms
        ra = ra_dec.ra.deg
        ra_hms = ra_dec.ra.to_string(unit=u.hour, sep=":")
    else:
        ra = None
        dec = None
        dec_dms = None
        ra_hms = None
    # Checks for no event observed
    if trig.event_observed is None:
        event_observed = None
    else:
        event_observed = trig.event_observed

    Event.objects.create(
        telescope=trig.telescope,
        xml_packet=trig.packet,
        duration=trig.event_duration,
        trig_id=trig.trig_id,
        self_generated_trig_id=trig.self_generated_trig_id,
        sequence_num=trig.sequence_num,
        event_type=trig.event_type,
        antares_ranking=trig.antares_ranking,
        # Sent event up so it's always pointing at zenith
        ra=ra,
        dec=dec,
        ra_hms=ra_hms,
        dec_dms=dec_dms,
        pos_error=trig.err,
        ignored=trig.ignore,
        source_name=trig.source_name,
        source_type=trig.source_type,
        event_observed=event_observed,
        fermi_most_likely_index=trig.fermi_most_likely_index,
        fermi_detection_prob=trig.fermi_detection_prob,
        swift_rate_signif=trig.swift_rate_signif,
        lvc_false_alarm_rate=trig.lvc_false_alarm_rate,
        lvc_binary_neutron_star_probability=trig.lvc_binary_neutron_star_probability,
        lvc_neutron_star_black_hole_probability=trig.lvc_neutron_star_black_hole_probability,
        lvc_binary_black_hole_probability=trig.lvc_binary_black_hole_probability,
        lvc_terrestial_probability=trig.lvc_terrestial_probability,
        lvc_includes_neutron_star_probability=trig.lvc_includes_neutron_star_probability,
        lvc_retraction_message=trig.lvc_retraction_message,
        lvc_skymap_fits=trig.lvc_skymap_fits,
        lvc_prob_density_tile=trig.lvc_prob_density_tile,
        lvc_significant=trig.lvc_significant,
        lvc_event_url=trig.lvc_event_url,
        lvc_instruments=trig.lvc_instruments,
        role=trig.role,
    )


class test_grb_group_fermi(TestCase):
    """Tests that events in a similar position and time will be grouped as possible event associations and trigger an observation"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):

        xml_paths = [
            "../tests/test_events/group_01_01_Fermi.xml",
            "../tests/test_events/group_01_02_Fermi.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_mwa_proposal_decision(self):
        prop_dec = (
            ProposalDecision.objects.all()
            .filter(proposal__telescope__name="MWA_VCS")
            .first()
        )

        # print(
        #     f"\n\ntest_grb_group_01 MWA proposal decison:\n{decision}\n\n")
        self.assertEqual(prop_dec.decision, "T")

    def test_atca_proposal_decision(self):
        print(
            f"\n\ntest_grb_group_01 ATCA proposal decison:\n{ProposalDecision.objects.all().filter(proposal__telescope__name='ATCA').first().decision_reason}\n\n"
        )
        self.assertEqual(
            ProposalDecision.objects.all()
            .filter(proposal__telescope__name="ATCA")
            .first()
            .decision,
            "T",
        )


class test_grb_group_swift(TestCase):
    """Tests that events with the same Trigger ID will be grouped and trigger an observation"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/group_02_SWIFT_01_BAT_GRB_Pos.xml",
            "../tests/test_events/group_02_SWIFT_02_XRT_Pos.xml",
            "../tests/test_events/group_02_SWIFT_03_UVOT_Pos.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check there are three Events that were grouped as one by the trigger ID
        self.assertEqual(len(Event.objects.all()), 3)

        eventgroups = EventGroup.objects.all()
        self.assertEqual(len(eventgroups), 1)

        source_type = eventgroups.first().source_type
        source_name = eventgroups.first().source_name

        self.assertEqual(source_type, "GRB")
        self.assertEqual(source_name, "GRB 170912")

    def test_mwa_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(
            f"\n\ntest_grb_group_02 MWA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n\n"
        )
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .first()
            .decision,
            "T",
        )
        self.assertEqual(len(Observations.objects.filter(telescope="MWA_VCS")), 1)

    def test_atca_proposal_decision(self):
        print(
            f"\n\ntest_grb_group_02 ATCA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='ATCA').first().decision_reason}\n\n"
        )
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="ATCA")
            .first()
            .decision,
            "T",
        )
        self.assertEqual(len(Observations.objects.filter(telescope="ATCA")), 1)


class test_atca_no_pending_on_dec_limit(TestCase):
    """Tests that events with the same Trigger ID will be grouped and trigger an observation"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api):
        xml_paths = [
            "../tests/test_events/group_02_SWIFT_01_BAT_GRB_Pos.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.dec = 20
            Event.objects.create(
                telescope=trig.telescope,
                xml_packet=trig.packet,
                duration=trig.event_duration,
                trig_id=trig.trig_id,
                self_generated_trig_id=trig.self_generated_trig_id,
                sequence_num=trig.sequence_num,
                event_type=trig.event_type,
                antares_ranking=trig.antares_ranking,
                # Sent event up so it's always pointing at zenith
                ra=trig.ra,
                dec=trig.dec,
                ra_hms=None,
                dec_dms=None,
                pos_error=trig.err,
                ignored=trig.ignore,
                source_name=trig.source_name,
                source_type=trig.source_type,
                event_observed=trig.event_observed,
                fermi_most_likely_index=trig.fermi_most_likely_index,
                fermi_detection_prob=trig.fermi_detection_prob,
                swift_rate_signif=trig.swift_rate_signif,
                lvc_false_alarm_rate=trig.lvc_false_alarm_rate,
                lvc_binary_neutron_star_probability=trig.lvc_binary_neutron_star_probability,
                lvc_neutron_star_black_hole_probability=trig.lvc_neutron_star_black_hole_probability,
                lvc_binary_black_hole_probability=trig.lvc_binary_black_hole_probability,
                lvc_terrestial_probability=trig.lvc_terrestial_probability,
                lvc_includes_neutron_star_probability=trig.lvc_includes_neutron_star_probability,
                lvc_retraction_message=trig.lvc_retraction_message,
                lvc_skymap_fits=trig.lvc_skymap_fits,
                lvc_prob_density_tile=trig.lvc_prob_density_tile,
                lvc_significant=trig.lvc_significant,
                lvc_event_url=trig.lvc_event_url,
                lvc_instruments=trig.lvc_instruments,
            )

    def test_atca_proposal_decision(self):
        print(
            f"\n\ntest_grb_group_02 ATCA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='ATCA').first().decision_reason}\n\n"
        )
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="ATCA")
            .first()
            .decision,
            "I",
        )
        self.assertEqual(len(Observations.objects.filter(telescope="ATCA")), 0)


class test_grb_group_swift_2(TestCase):
    """Tests ignored observations during an event"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        # "trigger_app/test_yamls/mwa_short_grb_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/SWIFT_BAT_Lightcurve.xml",
            "../tests/test_events/SWIFT_BAT_POS.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check there are three Events that were grouped as one by the trigger ID
        self.assertEqual(len(Event.objects.all()), 2)
        self.assertEqual(len(EventGroup.objects.all()), 1)

    def test_mwa_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(
            f"\n\ntest_grb_group_03 MWA proposal dgecison:\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n\n"
        )
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .first()
            .decision,
            "T",
        )
        self.assertEqual(len(Observations.objects.filter(telescope="MWA_VCS")), 1)

    def test_atca_proposal_decision(self):
        print(
            f"\n\ntest_grb_group_02 ATCA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='ATCA').first().decision_reason}\n\n"
        )
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="ATCA")
            .first()
            .decision,
            "T",
        )
        self.assertEqual(len(Observations.objects.filter(telescope="ATCA")), 1)


class test_grb_observation_fail_atca(TestCase):
    """Tests what happens if ATCA fails to schedule an observation"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api):
        fake_atca_api.side_effect = requests.exceptions.Timeout()
        xml_paths = ["../tests/test_events/SWIFT#BAT_GRB_Pos_1163119-055.xml"]

        # NOT USED
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            try:
                create_voevent_wrapper(trig, ra_dec, False)
            except Exception:
                pass

    def test_trigger_groups(self):
        events = Event.objects.all()
        self.assertEqual(len(events), 1)
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="ATCA")
            .first()
            .decision,
            "E",
        )
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .first()
            .decision,
            "I",
        )


class test_grb_observation_fail_mwa(TestCase):
    """Tests what happens if MWA fails to schedule an observation"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    def setUp(self, fake_mwa_api):
        fake_mwa_api.side_effect = requests.exceptions.Timeout()
        xml_paths = ["../tests/test_events/SWIFT_BAT_POS.xml"]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        try:
            for xml in xml_paths:
                trig = parsed_VOEvent(xml)
                create_voevent_wrapper(trig, ra_dec, False)
        except Exception as e:
            pass

    def test_trigger_groups(self):
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .first()
            .decision,
            "E",
        )
        self.assertEqual(len(Observations.objects.filter(telescope="MWA_VCS")), 0)


class test_grb_observation_ignored_mwa(TestCase):
    """Tests ignored observations during an event"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/mwa_short_grb_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    def setUp(self, fake_mwa_api):
        xml_paths = ["../tests/test_events/Swift_BAT_GRB_Pos_fail.xml"]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec, False)

    def test_trigger_groups(self):

        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .first()
            .decision,
            "I",
        )

        self.assertEqual(len(Observations.objects.filter(telescope="MWA_VCS")), 0)


# class test_nu(TestCase):
#     """Tests that a neutrino Event will trigger an observation
#     """
#     # Load default fixtures
#     fixtures = [
#         "default_data.yaml",
#         "trigger_app/test_yamls/mwa_nu_proposal_settings.yaml",
#     ]

#     with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
#         trigger_mwa_test = safe_load(file)

#     with open('trigger_app/test_yamls/atca_test_api_response.yaml', 'r') as file:
#         atca_test_api_response = safe_load(file)

#     @patch('trigger_app.telescope_observe.trigger', return_value=trigger_mwa_test)
#     @patch('atca_rapid_response_api.api.send', return_value=atca_test_api_response)
#     def setUp(self, fake_atca_api, fake_mwa_api):
#         xml_paths = [
#             "../tests/test_events/Antares_1438351269.xml",
#             "../tests/test_events/IceCube_134191_017593623_0.xml",
#             "../tests/test_events/IceCube_134191_017593623_1.xml",
#         ]

#         # Setup current RA and Dec at zenith for the MWA
#         MWA = EarthLocation(lat='-26:42:11.95',
#                             lon='116:40:14.93', height=377.8 * u.m)
#         mwa_coord = SkyCoord(az=0., alt=90., unit=(
#             u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
#         ra_dec = mwa_coord.icrs

#         # Parse and upload the xml file group
#         for xml in xml_paths:
#             trig = parsed_VOEvent(xml)
#             create_voevent_wrapper(trig, ra_dec)

#     def test_trigger_groups(self):
#         # Check there are three Events that were grouped as one by the trigger ID
#         self.assertEqual(len(Event.objects.all()), 3)
#         self.assertEqual(len(EventGroup.objects.all()), 2)

#     def test_proposal_decision(self):
#         # Two proposals decisions made

#         self.assertEqual(len(ProposalDecision.objects.all()), 2)
#         # Both triggered

#         prop_dec1 = ProposalDecision.objects.all()[0]
#         print(
#             f"\n\ntest_nu proposal decison 1:\n{prop_dec1.decision_reason}\n\n")
#         self.assertEqual(prop_dec1.decision, 'T')

#         prop_dec2 = ProposalDecision.objects.all()[1]
#         print(
#             f"\n\ntest_nu proposal decison 1:\n{prop_dec2.decision_reason}\n\n")
#         self.assertEqual(prop_dec2.decision, 'T')


class test_fs(TestCase):
    """Tests that a flare star Event will trigger an observation"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_fs_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/HD_8537_FLARE_STAR_TEST.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check there are three Events that were grouped as one by the trigger ID
        self.assertEqual(len(Event.objects.all()), 1)
        self.assertEqual(len(EventGroup.objects.all()), 1)

    def test_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(
            f"\n\ntest_fs proposal decison:\n{ProposalDecision.objects.all().first().decision_reason}\n\n"
        )
        self.assertEqual(ProposalDecision.objects.all().first().decision, "T")
        self.assertEqual(len(Observations.objects.filter(telescope="MWA_VCS")), 1)


class test_hess_any_dur(TestCase):
    """Tests that a HESS Event will trigger an observation but only if we use a proposal with the any duration flag"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Standard proposal that shouldn't trigger
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        # Hess proposal with the any duration flag that should trigger
        "trigger_app/test_yamls/mwa_hess_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/HESS_test_event.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check event was made
        self.assertEqual(len(Event.objects.all()), 1)
        self.assertEqual(len(EventGroup.objects.all()), 1)

    def test_proposal_decision(self):
        # Test only one proposal triggered
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__event_any_duration=True)
            .first()
            .decision,
            "T",
        )
        self.assertEqual(
            ProposalDecision.objects.filter(proposal__event_any_duration=False)
            .first()
            .decision,
            "I",
        )
        self.assertEqual(len(Observations.objects.filter(telescope="MWA_VCS")), 1)
        self.assertEqual(len(Observations.objects.filter(telescope="ATCA")), 0)


class test_lvc_mwa_sub_arrays_no_repointing(TestCase):
    """Tests that on early LVC events MWA will make an observation with sub arrays" """

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Mwa proposal that has subarrays
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
        # "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    mwaApiArgs: list[dict] = []

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_1 = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_2 = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_3 = safe_load(file)

    # with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
    #     trigger_mwa_test_4 = safe_load(file)

    trigger_mwa_test_2["trigger_id"] = "22222"
    trigger_mwa_test_3["trigger_id"] = "33333"
    # trigger_mwa_test_4["trigger_id"] = "44444"

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap
    # 3rd event = normal obs using skymap if position changes
    # 4th event = normal obs using skymap if position changes

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[
            trigger_mwa_test_buffer,
            trigger_mwa_test_1,
            trigger_mwa_test_2,
            trigger_mwa_test_3,
            # trigger_mwa_test_4
        ],
    )
    def setUp(self, patched_mwa_api):
        # def setUp(self):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warningS230518h.xml",
            "../tests/test_events/LVC_real_preliminaryS230518h.xml",
            "../tests/test_events/LVC_real_initialS230518h.xml",
            # "../tests/test_events/LVC_real_update.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                seconds=360
            )
            print(trig.trig_id)
            if trig.ra and trig.dec:
                create_voevent_wrapper(trig, ra_dec)
            else:
                print("CREATE VOEVENT")
                create_voevent_wrapper(trig, ra_dec=None)
            # Sleep needed for testing vs real api
            time.sleep(3)
            args, kwargs = patched_mwa_api.call_args
            self.mwaApiArgs.append(kwargs)
            print(args)
            print(kwargs)

    def test_trigger_groups(self):
        time.sleep(15)
        # # Check event was made
        # self.assertEqual(True, True)

        # self.assertEqual(len(Event.objects.all()),3)
        # time.sleep(100)
        # # Early warning is a different event
        # self.assertEqual(len(EventGroup.objects.all()), 1)
        obs = Observations.objects.all()
        # self.assertEqual(len(obs), 4)
        print("OBS RESULTS")
        for ob in obs:
            print(ob.trigger_id)
            print(ob.reason)
        print("proposal decision")
        print(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .first()
            .decision_reason
        )
        # self.assertEqual(ProposalDecision.objects.filter(
        #     proposal__telescope__name='MWA_VCS').first().decision, 'TT')
        # self.assertEqual(ProposalDecision.objects.filter(
        #     proposal__telescope__name='ATCA').first().decision, 'I')

        # # MWA requests are correct
        # mwa_request_0 = self.mwaApiArgs[0]
        # mwa_request_1 = self.mwaApiArgs[1]
        # mwa_request_2 = self.mwaApiArgs[0]
        # mwa_request_3 = self.mwaApiArgs[1]
        # print(mwa_request_0)
        # print(mwa_request_1)
        # print(mwa_request_2)
        # print(mwa_request_3)

        # self.assertEqual(len(mwa_request_0['ra']), 4)
        # self.assertEqual(len(mwa_request_0['dec']), 4)
        # self.assertEqual(len(mwa_request_0['subarray_list']), 4)

        # self.assertEqual(len(mwa_request_1['ra']), 4)
        # self.assertEqual(len(mwa_request_1['dec']), 4)
        # self.assertEqual(len(mwa_request_1['subarray_list']), 4)


class test_lvc_mwa_sub_arrays_prelim_first(TestCase):
    """Tests that on early LVC events MWA will make an observation with sub arrays" """

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Mwa proposal that has subarrays
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
        # "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    mwaApiArgs: list[dict] = []

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_1 = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_2 = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_3 = safe_load(file)

    # with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
    #     trigger_mwa_test_4 = safe_load(file)

    trigger_mwa_test_2["trigger_id"] = "22222"
    trigger_mwa_test_3["trigger_id"] = "33333"
    # trigger_mwa_test_4["trigger_id"] = "44444"

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap
    # 3rd event = normal obs using skymap if position changes
    # 4th event = normal obs using skymap if position changes

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[
            trigger_mwa_test_buffer,
            trigger_mwa_test_1,
            trigger_mwa_test_2,
            trigger_mwa_test_3,
            # trigger_mwa_test_4
        ],
    )
    def setUp(self, patched_mwa_api):
        # def setUp(self):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warningS230518h.xml",
            # "../tests/test_events/LVC_real_preliminaryS230518h.xml",
            # "../tests/test_events/LVC_real_initialS230518h.xml",
            # "../tests/test_events/LVC_real_update.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                seconds=360
            )
            print(trig.trig_id)
            if trig.ra and trig.dec:
                create_voevent_wrapper(trig, ra_dec)
            else:
                print("CREATE VOEVENT")
                create_voevent_wrapper(trig, ra_dec=None)
            # Sleep needed for testing vs real api
            time.sleep(3)
            args, kwargs = patched_mwa_api.call_args
            self.mwaApiArgs.append(kwargs)
            print(args)
            print(kwargs)

    def test_trigger_groups(self):
        time.sleep(7)
        # # Check event was made
        # self.assertEqual(True, True)

        # self.assertEqual(len(Event.objects.all()),3)
        # time.sleep(100)
        # # Early warning is a different event
        # self.assertEqual(len(EventGroup.objects.all()), 1)
        obs = Observations.objects.all()
        # self.assertEqual(len(obs), 4)
        print("OBS RESULTS")
        for ob in obs:
            print(ob.trigger_id)
            print(ob.reason)
        print("proposal decision")
        print(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .first()
            .decision_reason
        )
        # self.assertEqual(ProposalDecision.objects.filter(
        #     proposal__telescope__name='MWA_VCS').first().decision, 'TT')
        # self.assertEqual(ProposalDecision.objects.filter(
        #     proposal__telescope__name='ATCA').first().decision, 'I')

        # # MWA requests are correct
        # mwa_request_0 = self.mwaApiArgs[0]
        # mwa_request_1 = self.mwaApiArgs[1]
        # mwa_request_2 = self.mwaApiArgs[0]
        # mwa_request_3 = self.mwaApiArgs[1]
        # print(mwa_request_0)
        # print(mwa_request_1)
        # print(mwa_request_2)
        # print(mwa_request_3)

        # self.assertEqual(len(mwa_request_0['ra']), 4)
        # self.assertEqual(len(mwa_request_0['dec']), 4)
        # self.assertEqual(len(mwa_request_0['subarray_list']), 4)

        # self.assertEqual(len(mwa_request_1['ra']), 4)
        # self.assertEqual(len(mwa_request_1['dec']), 4)
        # self.assertEqual(len(mwa_request_1['subarray_list']), 4)


class test_lvc_mwa_sub_arrays_with_repointing(TestCase):
    """Tests that on early LVC events MWA will make an observation with sub arrays" """

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Mwa proposal that has subarrays
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
        # "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    mwaApiArgs: list[dict] = []

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_1 = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_2 = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_3 = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test_4 = safe_load(file)

    trigger_mwa_test_2["trigger_id"] = "22222"
    trigger_mwa_test_3["trigger_id"] = "33333"
    trigger_mwa_test_4["trigger_id"] = "44444"

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap
    # 3rd event = normal obs using skymap if position changes
    # 4th event = normal obs using skymap if position changes

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[
            trigger_mwa_test_buffer,
            trigger_mwa_test_1,
            trigger_mwa_test_2,
            trigger_mwa_test_3,
            trigger_mwa_test_4,
        ],
    )
    def setUp(self, patched_mwa_api):
        # def setUp(self):
        xml_paths = [
            # "../tests/test_events/LVC_real_early_warning.xml",
            "../tests/test_events/LVC_real_initial.xml",
            # "../tests/test_events/LVC_real_preliminary.xml",
            # "../tests/test_events/LVC_real_update.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            print(trig.trig_id)
            if trig.ra and trig.dec:
                create_voevent_wrapper(trig, ra_dec)
            else:
                print("CREATE VOEVENT")
                create_voevent_wrapper(trig, ra_dec=None)
            # Sleep needed for testing vs real api
            args, kwargs = patched_mwa_api.call_args
            self.mwaApiArgs.append(kwargs)
            print(args)
            print(kwargs)

    def test_trigger_groups(self):
        # time.sleep(50)
        # # Check event was made
        # self.assertEqual(True, True)
        print(self.mwaApiArgs)
        self.assertEqual(len(Event.objects.all()), 1)
        # time.sleep(100)
        # # Early warning is a different event
        # self.assertEqual(len(EventGroup.objects.all()), 1)
        obs = Observations.objects.all()
        self.assertEqual(len(obs), 2)
        for ob in obs:
            print(ob.trigger_id)
        # self.assertEqual(ProposalDecision.objects.filter(
        #     proposal__telescope__name='MWA_VCS').first().decision, 'TT')
        # self.assertEqual(ProposalDecision.objects.filter(
        #     proposal__telescope__name='ATCA').first().decision, 'I')

        # # MWA requests are correct
        # mwa_request_0 = self.mwaApiArgs[0]
        # mwa_request_1 = self.mwaApiArgs[1]
        # mwa_request_2 = self.mwaApiArgs[0]
        # mwa_request_3 = self.mwaApiArgs[1]
        # print(mwa_request_0)
        # print(mwa_request_1)
        # print(mwa_request_2)
        # print(mwa_request_3)

        # self.assertEqual(len(mwa_request_0['ra']), 4)
        # self.assertEqual(len(mwa_request_0['dec']), 4)
        # self.assertEqual(len(mwa_request_0['subarray_list']), 4)

        # self.assertEqual(len(mwa_request_1['ra']), 4)
        # self.assertEqual(len(mwa_request_1['dec']), 4)
        # self.assertEqual(len(mwa_request_1['subarray_list']), 4)


class test_lvc_mwa_retraction(TestCase):
    """Tests that retractions are ignored (no "NO CAPTURE" supported by MWA API)" """

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Mwa proposal that has subarrays
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    # @patch('trigger_app.telescope_observe.trigger', return_value=trigger_mwa_test)
    def setUp(self):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning.xml",
            "../tests/test_events/LVC_real_retraction.xml",
        ]
        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            print(trig)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            if trig.ra and trig.dec:
                create_voevent_wrapper(trig, ra_dec)
            else:
                create_voevent_wrapper(trig, ra_dec=None)
            time.sleep(10)
            # args, kwargs = fake_mwa_api.call_args
            # print(args)
            # print(kwargs)

    def test_trigger_groups(self):
        # Check event was made
        self.assertEqual(len(Event.objects.all()), 2)

        # Early warning is a different event
        self.assertEqual(len(EventGroup.objects.all()), 1)
        # event_group = EventGroup.objects.all().first()
        # print(EventGroup.objects.all().first())
        # prop_decs = ProposalDecision.objects.filter(
        # event_group_id=event_group).first()
        # print(prop_decs.decision)
        self.assertEqual(
            len(
                ProposalDecision.objects.filter(
                    proposal__telescope__name="MWA_VCS"
                ).all()
            ),
            1,
        )

        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .last()
            .decision,
            "T",
        )


class test_lvc_mwa_retraction_single(TestCase):
    """Tests that retractions are ignored (no "NO CAPTURE" supported by MWA API)" """

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Mwa proposal that has subarrays
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    # @patch('trigger_app.telescope_observe.trigger', return_value=trigger_mwa_test)
    def setUp(self):
        xml_paths = ["../tests/test_events/LVC_real_retraction.xml"]
        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            print(trig)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            if trig.ra and trig.dec:
                create_voevent_wrapper(trig, ra_dec)
            else:
                create_voevent_wrapper(trig, ra_dec=None)
            time.sleep(10)
            # args, kwargs = fake_mwa_api.call_args
            # print(args)
            # print(kwargs)

    def test_trigger_groups(self):
        # Check event was made
        self.assertEqual(len(Event.objects.all()), 1)

        # Early warning is a different event
        self.assertEqual(len(EventGroup.objects.all()), 1)

        self.assertEqual(
            len(
                ProposalDecision.objects.filter(
                    proposal__telescope__name="MWA_VCS"
                ).all()
            ),
            1,
        )

        self.assertEqual(
            ProposalDecision.objects.filter(proposal__telescope__name="MWA_VCS")
            .last()
            .decision,
            "P",
        )


class test_lvc_burst_are_ignored(TestCase):
    """Tests that lvc burst events are ignored" """

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Mwa proposal that has subarrays
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    def setUp(self, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/LVC_real_burst.xml",
        ]
        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            print(trig)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            if trig.ra and trig.dec:
                create_voevent_wrapper(trig, ra_dec)
            else:
                create_voevent_wrapper(trig, ra_dec=None)
            time.sleep(10)

    def test_trigger_groups(self):
        # Check event was made
        self.assertEqual(len(Event.objects.all()), 1)
        self.assertEqual(Event.objects.all().first().ignored, True)


class test_early_warning_trigger_buffer_default_pointings(TestCase):
    """Tests that on early LVC events MWA will 1. Dump MWA buffer, 2. Make an observation with sub arrays at scheduled position for 15 mins." """

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Mwa proposal that has subarrays
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[trigger_mwa_test_buffer, trigger_mwa_test],
    )
    def setUp(self, fake_mwa_api):
        # def setUp(self):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning.xml",
        ]
        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        # Parse and upload the xml file group

        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            time.sleep(10)
            print(trig)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            if trig.ra and trig.dec:
                create_voevent_wrapper(trig, ra_dec)
            else:
                create_voevent_wrapper(trig, ra_dec=None)
            time.sleep(10)

            # args, kwargs = fake_mwa_api.call_args
            # print(kwargs)

    def test_trigger_groups(self):
        # Check event was made
        self.assertEqual(len(Event.objects.all()), 1)
        self.assertEqual(Event.objects.all().first().ignored, False)
        self.assertEqual(len(Observations.objects.all()), 2)


class test_ignore_single_instrument_gw(TestCase):
    """ """

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Mwa proposal that has subarrays
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
    ]
    call_args = None

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    @patch("trigger_app.telescope_observe.trigger", return_value=trigger_mwa_test)
    def setUp(self, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning_single_instrument.xml",
        ]
        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            print(trig)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            if trig.ra and trig.dec:
                create_voevent_wrapper(trig, ra_dec)
            else:
                create_voevent_wrapper(trig, ra_dec=None)

            self.call_args = fake_mwa_api.call_args

    def test_trigger_groups(self):
        # Check event was made
        self.assertEqual(len(Event.objects.all()), 1)
        self.assertEqual(Event.objects.all().first().ignored, False)
        self.assertEqual(self.call_args, None)


class test_pending_can_observe_atca(TestCase):
    """ """

    # Load default fixtures
    # "event_min_duration": 0.256
    # "event_max_duration": 1.024
    # "pending_min_duration_1": 1.025
    # "pending_max_duration_1": 2.056
    # "pending_min_duration_2": 0.128
    # "pending_max_duration_2": 0.255
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]
    call_args = None

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api):
        # def setUp(self):
        xml_paths = [
            "../tests/test_events/group_02_SWIFT_01_BAT_GRB_Pos.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_duration = 1.026
            print(trig.source_type)
            create_voevent_wrapper(trig, ra_dec)
            # self.call_args = fake_atca_api.call_args

        # setting pending to observe requires authentication
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

    def test_set_pending_then_approve(self):
        # Check event was made
        event = Event.objects.all().first()
        prop_dec = ProposalDecision.objects.all().first()

        self.assertEqual(event.ignored, False)
        self.assertEqual(prop_dec.decision, "P")
        self.assertEqual(self.call_args, None)

        response = self.client.get(f"/proposal_decision_result/{prop_dec}/1/")

        # self.assertEqual(len(Observations.objects.all()), 1)
        prop_dec_after = ProposalDecision.objects.all().first()
        print(prop_dec_after.decision_reason)
        self.assertGreaterEqual(
            prop_dec_after.decision_reason.find("ATCA error message"), 0
        )


class test_obs_testing_option_pretend_real_realevent(TestCase):
    """Tests the testing options; PRETEND_REAL"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[trigger_mwa_test_buffer, trigger_mwa_test],
    )
    def setUp(self, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning.xml",
        ]

        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        self.mwaApiArgs = []
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            try:
                create_voevent_wrapper(trig, ra_dec, False)
            except Exception:
                pass
            self.mwaApiArgs = fake_mwa_api.call_args_list

    def test_trigger_groups(self):
        events = Event.objects.all()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(Observations.objects.all()), 2)
        for call in self.mwaApiArgs:
            args, kwargs = call
            self.assertEqual(kwargs["pretend"], True)


class test_obs_testing_option_pretend_real_testevent(TestCase):
    """Tests the testing options; PRETEND_REAL"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[trigger_mwa_test_buffer, trigger_mwa_test],
    )
    def setUp(self, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning.xml",
        ]

        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        self.mwaApiArgs = []
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            trig.role = "test"
            try:
                create_voevent_wrapper(trig, ra_dec, False)
            except Exception:
                pass
            self.mwaApiArgs = fake_mwa_api.call_args_list

    def test_trigger_groups(self):
        events = Event.objects.all()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(Observations.objects.all()), 0)


class test_obs_testing_option_both_real(TestCase):
    """Tests the testing options; BOTH"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings_both.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[trigger_mwa_test_buffer, trigger_mwa_test],
    )
    def setUp(self, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning.xml",
        ]

        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        self.mwaApiArgs = []
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            try:
                create_voevent_wrapper(trig, ra_dec, False)
            except Exception:
                pass
            self.mwaApiArgs = fake_mwa_api.call_args_list

    def test_trigger_groups(self):
        events = Event.objects.all()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(Observations.objects.all()), 2)
        for call in self.mwaApiArgs:
            args, kwargs = call
            self.assertEqual(kwargs["pretend"], False)


class test_obs_testing_option_both_test(TestCase):
    """Tests the testing options; BOTH"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings_both.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[trigger_mwa_test_buffer, trigger_mwa_test],
    )
    def setUp(self, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning.xml",
        ]

        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        self.mwaApiArgs = []
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            trig.role = "test"
            try:
                create_voevent_wrapper(trig, ra_dec, False)
            except Exception:
                pass
            self.mwaApiArgs = fake_mwa_api.call_args_list

    def test_trigger_groups(self):
        events = Event.objects.all()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(Observations.objects.all()), 2)
        for call in self.mwaApiArgs:
            args, kwargs = call
            self.assertEqual(kwargs["pretend"], True)


class test_obs_testing_option_real_only_realevent(TestCase):
    """Tests the testing options; REAL_ONLY"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings_real_only.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[trigger_mwa_test_buffer, trigger_mwa_test],
    )
    def setUp(self, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning.xml",
        ]

        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        self.mwaApiArgs = []
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            try:
                create_voevent_wrapper(trig, ra_dec, False)
            except Exception:
                pass
            self.mwaApiArgs = fake_mwa_api.call_args_list

    def test_trigger_groups(self):
        events = Event.objects.all()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(Observations.objects.all()), 2)
        for call in self.mwaApiArgs:
            args, kwargs = call
            self.assertEqual(kwargs["pretend"], False)


class test_obs_testing_option_real_only_testevent(TestCase):
    """Tests the testing options; REAL_ONLY"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_early_lvc_mwa_proposal_settings_real_only.yaml",
    ]

    with open("trigger_app/test_yamls/trigger_mwa_test_buffer.yaml", "r") as file:
        trigger_mwa_test_buffer = safe_load(file)

    with open("trigger_app/test_yamls/trigger_mwa_test.yaml", "r") as file:
        trigger_mwa_test = safe_load(file)

    # 1st event = buffer obs + normal obs w/ default pointings
    # 2nd event = normal obs using skymap

    @patch(
        "trigger_app.telescope_observe.trigger",
        side_effect=[trigger_mwa_test_buffer, trigger_mwa_test],
    )
    def setUp(self, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/LVC_real_early_warning.xml",
        ]

        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            trig.event_observed = datetime.datetime.now(pytz.UTC) - datetime.timedelta(
                hours=0.1
            )
            trig.role = "test"
            try:
                create_voevent_wrapper(trig, ra_dec, False)
            except Exception:
                pass

    def test_trigger_groups(self):
        events = Event.objects.all()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(Observations.objects.all()), 0)


class test_atca_http_auth(TestCase):
    """Tests atca http auth update"""

    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    with open("trigger_app/test_yamls/atca_test_api_response.yaml", "r") as file:
        atca_test_api_response = safe_load(file)

    @patch("atca_rapid_response_api.api.send", return_value=atca_test_api_response)
    def setUp(self, fake_atca_api):
        xml_paths = [
            "../tests/test_events/group_02_SWIFT_01_BAT_GRB_Pos.xml",
            "../tests/test_events/group_02_SWIFT_02_XRT_Pos.xml",
            "../tests/test_events/group_02_SWIFT_03_UVOT_Pos.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat="-26:42:11.95", lon="116:40:14.93", height=377.8 * u.m)
        mwa_coord = SkyCoord(
            az=0.0,
            alt=90.0,
            unit=(u.deg, u.deg),
            frame="altaz",
            obstime=Time.now(),
            location=MWA,
        )
        ra_dec = mwa_coord.icrs

        self.atcaApiArgs = []

        ATCAUser.objects.create(
            httpAuthUsername="atcaUserName", httpAuthPassword="atcaUserPassword"
        )

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)
            args, kwargs = fake_atca_api.call_args
            print(args)
            print(kwargs)
            self.atcaApiArgs.append(args)

    def test_trigger_groups(self):
        # Check there are three Events that were grouped as one by the trigger ID
        self.assertEqual(len(Event.objects.all()), 3)
        print(self.atcaApiArgs)
        self.assertEqual(len(Observations.objects.filter(telescope="ATCA")), 1)
