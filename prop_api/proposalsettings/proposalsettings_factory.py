from .eventtelescope_factory import EventTelescopeFactory
from .models.constants import SourceChoices, TriggerOnChoices
from .models.proposal import ProposalSettings
from .models.sourcesettings import GrbSourceSettings, GWSourceSettings, NuSourceSettings
from .models.telescopesettings import ATCATelescopeSettings, MWATelescopeSettings
from .telescope_factory import TelescopeFactory
from .telescopeprojectid_factory import TelescopeProjectIdFactory


class ProposalSettingsFactory:
    """
    A factory class for creating and managing ProposalSettings instances.

    This class is responsible for generating various proposal settings for different
    telescopes and event types, such as GRBs, neutrinos, and gravitational waves.
    """

    def __init__(
        self,
        telescope_factory: TelescopeFactory,
        event_telescope_factory: EventTelescopeFactory,
        project_id_factory: TelescopeProjectIdFactory,
    ):
        """
        Initialize the ProposalSettingsFactory.

        Args:
            telescope_factory (TelescopeFactory): Factory for creating telescope instances.
            event_telescope_factory (EventTelescopeFactory): Factory for creating event telescope instances.
            project_id_factory (TelescopeProjectIdFactory): Factory for creating project ID instances.
        """
        self.telescope_factory = telescope_factory
        self.event_telescope_factory = event_telescope_factory
        self.project_id_factory = project_id_factory

    @property
    def proposal_atca_short_grb(self):
        """
        Create and return ProposalSettings for ATCA short GRB observations.

        Returns:
            ProposalSettings: Settings for ATCA short GRB proposal.
        """
        # Creating the instance based on the data from id=6
        telescope_settings = ATCATelescopeSettings(
            # id=6,
            telescope=self.telescope_factory.telescope_atca,
            maximum_position_uncertainty=0.07,
            fermi_prob=50,
            repointing_limit=0.02,
            observe_significant=True,
            atca_band_4cm=True,
            atca_band_4cm_freq1=5500.0,
            atca_band_4cm_freq2=9000.0,
            atca_min_exptime=120,
        )

        source_settings = GrbSourceSettings()

        prop_settings = ProposalSettings(
            id=6,
            project_id=self.project_id_factory.telescope_project_c3204,
            proposal_id="ATCA_short_GRB",
            proposal_description="ATCA triggers on Swift short GRBs",
            priority=4,
            event_telescope=self.event_telescope_factory.event_telescope_swift,
            testing=TriggerOnChoices.REAL_ONLY,  # "Real events only (Real Obs)",
            source_type=SourceChoices.GRB,
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )

        return prop_settings

    @property
    def proposal_mwa_vcs_grb_swif(self):  # MWA_VCS_GRB_swif
        # Creating the instance based on the data from id=7
        telescope_settings = MWATelescopeSettings(
            telescope=self.telescope_factory.telescope_mwa_vcs,
            event_min_duration=0.0,  # Included because it differs from the default
            event_max_duration=2.1,  # Included because it differs from the default
            pending_min_duration_1=0.0,  # Included because it differs from the default
            pending_max_duration_1=0.0,  # Included because it differs from the default
            pending_min_duration_2=0.0,  # Included because it differs from the default
            pending_max_duration_2=0.0,  # Included because it differs from the default
            fermi_prob=50,
            swift_rate_signif=0,
            repointing_limit=10.0,
            mwa_exptime=900,  # Included because it differs from the default(896)
        )

        source_settings = GrbSourceSettings()
        prop_settings = ProposalSettings(
            id=7,
            project_id=self.project_id_factory.telescope_project_g0055,
            proposal_id="MWA_VCS_GRB_swif",
            proposal_description="MWA VCS triggering on Swift GRBs",
            priority=3,
            event_telescope=self.event_telescope_factory.event_telescope_swift,
            testing=TriggerOnChoices.REAL_ONLY,
            source_type=SourceChoices.GRB,
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposal_test2_neutrino(self):  # test2_neutrino
        # Creating the instance based on the data from id=10
        telescope_settings = MWATelescopeSettings(
            telescope=self.telescope_factory.telescope_mwa_vcs,
            event_min_duration=0.256,
            event_max_duration=1.024,
            pending_min_duration_1=1.025,
            pending_max_duration_1=2.056,
            pending_min_duration_2=0.128,
            pending_max_duration_2=0.255,
            fermi_prob=50,
            swift_rate_signif=0,
            repointing_limit=10.0,
            mwa_exptime=120,  # Included because it differs from the default
            mwa_calexptime=60,  # Included because it differs from the default
            observe_significant=True,  # GW custom logic
        )

        source_settings = NuSourceSettings()
        prop_settings = ProposalSettings(
            id=10,
            project_id=self.project_id_factory.telescope_project_c002,
            proposal_id="test2_neutrino",
            proposal_description="test neutrino",
            priority=6,
            event_telescope=self.event_telescope_factory.event_telescope_antares,
            testing=TriggerOnChoices.PRETEND_REAL,
            source_type=SourceChoices.NU,
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposal_atca_hess_grbs(self):  # proposal_id="ATCA_HESS_GRBs",
        # Creating the instance based on the data from id=11
        telescope_settings = ATCATelescopeSettings(
            telescope=self.telescope_factory.telescope_atca,
            event_min_duration=0.256,
            event_max_duration=1.024,
            pending_min_duration_1=1.025,
            pending_max_duration_1=2.056,
            pending_min_duration_2=0.128,
            pending_max_duration_2=0.255,
            maximum_position_uncertainty=0.07,
            fermi_prob=50,
            swift_rate_signif=0,
            repointing_limit=0.02,
            observe_significant=True,
        )

        source_settings = GrbSourceSettings()
        prop_settings = ProposalSettings(
            id=11,
            project_id=self.project_id_factory.telescope_project_c3374,
            proposal_id="ATCA_HESS_GRBs",
            proposal_description="ATCA rapid-response triggering on HESS-detected GRBs",
            priority=6,
            event_telescope=self.event_telescope_factory.event_telescope_hess,
            testing=TriggerOnChoices.PRETEND_REAL,
            source_type=SourceChoices.GRB,
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposal_atca_long_grb(self):  # proposal_id="ATCA_long_GRB"
        # Creating the instance based on the data from id=12
        telescope_settings = ATCATelescopeSettings(
            # id=12,
            telescope=self.telescope_factory.telescope_atca,
            event_min_duration=2.056,
            event_max_duration=10000.0,
            pending_min_duration_1=0.0,
            pending_max_duration_1=2.055,
            pending_min_duration_2=0.0,
            pending_max_duration_2=0.0,
            maximum_position_uncertainty=0.1,
            observe_significant=True,
            # Non-default ATCA specific settings
            atca_band_7mm=True,
            atca_band_7mm_freq1=33000.0,
            atca_band_7mm_freq2=35000.0,
            atca_band_15mm=True,
            atca_band_15mm_freq1=16700.0,
            atca_band_15mm_freq2=21200.0,
            atca_band_4cm=True,
            atca_band_4cm_freq1=5500.0,
            atca_band_4cm_freq2=9000.0,
            atca_band_15mm_exptime=30,
            atca_band_4cm_exptime=20,
            atca_band_7mm_exptime=30,
            atca_min_exptime=120,
        )

        source_settings = GrbSourceSettings()
        prop_settings = ProposalSettings(
            id=12,
            project_id=self.project_id_factory.telescope_project_c3542,
            proposal_id="ATCA_long_GRB",
            proposal_description="This is the triggering proposal for the large ATCA Long GRB program",
            priority=6,
            event_telescope=self.event_telescope_factory.event_telescope_swift,
            testing=TriggerOnChoices.REAL_ONLY,
            source_type=SourceChoices.GRB,
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposal_mwa_gw_bns(self):
        # Creating the instance based on the data from id=13
        telescope_settings = MWATelescopeSettings(
            telescope=self.telescope_factory.telescope_mwa_vcs,
            maximum_position_uncertainty=0.05,
            fermi_prob=50,
            repointing_limit=10.0,
            observe_significant=True,
            start_observation_at_high_sensitivity=True,
            # MWA specific settings
            mwa_freqspecs="93,24",
            mwa_exptime=7200,
        )

        source_settings = GWSourceSettings()
        prop_settings = ProposalSettings(
            id=13,
            project_id=self.project_id_factory.telescope_project_g0094,
            proposal_id="MWA_GW_BNS",
            proposal_description="MWA triggering on LIGO-Virgo-KAGRA BNS GW events detected during O4 using a multi-beam approach and the VCS",
            priority=1,
            event_telescope=self.event_telescope_factory.event_telescope_lvc,
            testing=TriggerOnChoices.BOTH,
            source_type=SourceChoices.GW,
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )

        return prop_settings

    @property
    def proposal_mwa_gw_nshh(self):
        # Creating the instance based on the data from id=14
        telescope_settings = MWATelescopeSettings(
            telescope=self.telescope_factory.telescope_mwa_vcs,
            event_min_duration=0.512,  # Non-default value
            event_max_duration=10000.0,  # Non-default value
            pending_min_duration_1=1.0,  # Non-default value
            pending_max_duration_1=1000.0,  # Non-default value
            pending_min_duration_2=0.0,  # Non-default value
            pending_max_duration_2=0.0,  # Non-default value
            maximum_position_uncertainty=0.07,  # Non-default value
            fermi_prob=60,  # Non-default value
            swift_rate_signif=5.0,  # Non-default value
            repointing_limit=5.0,  # Non-default value
            observe_significant=True,  # Non-default value
            maximum_observation_time_seconds=18000,  # Non-default value
            # MWA specific settings
            mwa_freqspecs="144,24",
            mwa_exptime=7200,
            mwa_calexptime=200.0,  # Non-default value
            mwa_freqres=20.0,  # Non-default value
            mwa_inttime=1.0,  # Non-default value
            mwa_horizon_limit=20.0,  # Non-default value
        )

        source_settings = GWSourceSettings()
        prop_settings = ProposalSettings(
            id=14,
            project_id=self.project_id_factory.telescope_project_g0094,
            proposal_id="MWA_GW_NSBH",
            proposal_description="MWA triggering on LIGO-Virgo-KAGRA BNS GW events detected during O4 using a multi-beam approach and the VCS",
            priority=3,  # Non-default value
            event_telescope=self.event_telescope_factory.event_telescope_lvc,
            testing=TriggerOnChoices.REAL_ONLY,  # Non-default value
            source_type=SourceChoices.GW,  # Non-default value
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    # @property
    # def proposal_mwa_gw_bns_test(self):
    #     # Creating the instance based on the data from id=13
    #     telescope_settings = MWATelescopeSettings(
    #         telescope=self.telescope_factory.telescope_mwa_vcs,
    #         maximum_position_uncertainty=0.05,
    #         fermi_prob=50,
    #         repointing_limit=10.0,
    #         observe_significant=True,
    #         start_observation_at_high_sensitivity=True,
    #         # MWA specific settings
    #         mwa_freqspecs="93,24",
    #         mwa_exptime=7200,
    #     )

    #     source_settings = GWSourceSettings()
    #     prop_settings = ProposalSettings(
    #         id=20,
    #         project_id=self.project_id_factory.telescope_project_g0094,
    #         proposal_id="MWA_GW_BNS_TEST",
    #         proposal_description="MWA triggering on LIGO-Virgo-KAGRA BNS GW events detected during O4 using a multi-beam approach and the VCS",
    #         priority=1,
    #         event_telescope=self.event_telescope_factory.event_telescope_lvc,
    #         testing=TriggerOnChoices.BOTH,
    #         source_type=SourceChoices.GW,
    #         telescope_settings=telescope_settings,
    #         source_settings=source_settings,
    #     )
    #     return prop_settings

    #
    @property
    def proposals(self):
        """
        Get a list of all valid ProposalSettings instances.

        Returns:
            list: A list of ProposalSettings instances.
        """
        valid_classes = (ProposalSettings,)
        return [
            getattr(self, attr)
            for attr in dir(self)
            if attr.startswith("proposal_")
            and isinstance(getattr(self, attr), valid_classes)
        ]

    def filter_proposals_by_id(self, proposal_id: int):
        """
        Find and return a ProposalSettings instance by its ID.

        Args:
            proposal_id (int): The ID of the proposal to find.

        Returns:
            ProposalSettings or None: The matching ProposalSettings instance, or None if not found.
        """
        for proposal in self.proposals:
            if proposal.id == proposal_id:
                return proposal
        return None
