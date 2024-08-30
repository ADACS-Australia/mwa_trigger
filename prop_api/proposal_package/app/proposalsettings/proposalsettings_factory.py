from .eventtelescope_factory import EventTelescopeFactory
from .models import (
    ATCAProposalSettings,
    GrbSourceSettings,
    GWSourceSettings,
    MWAProposalSettings,
    NuSourceSettings,
    ProposalSettings,
    SourceChoices,
    TriggerOnChoices,
)
from .telescope_factory import TelescopeFactory
from .telescopeprojectid_factory import TelescopeProjectIdFactory


class ProposalSettingsFactory:
    def __init__(
        self,
        telescope_factory: TelescopeFactory,
        event_telescope_factory: EventTelescopeFactory,
        project_id_factory: TelescopeProjectIdFactory,
    ):
        self.telescope_factory = telescope_factory
        self.event_telescope_factory = event_telescope_factory
        self.project_id_factory = project_id_factory

    @property
    def proposal_atca_short_grb(self):
        # Creating the instance based on the data from id=6
        telescope_settings = ATCAProposalSettings(
            id=6,
            telescope=self.telescope_factory.telescope_atca,
            project_id=self.project_id_factory.telescope_project_c3204,
            proposal_id="ATCA_short_GRB",
            proposal_description="ATCA triggers on Swift short GRBs",
            priority=4,
            event_telescope=self.event_telescope_factory.event_telescope_swift,
            maximum_position_uncertainty=0.07,
            fermi_prob=50,
            repointing_limit=0.02,
            testing=TriggerOnChoices.REAL_ONLY,  # "Real events only (Real Obs)",
            source_type=SourceChoices.GRB,
            observe_significant=True,
            atca_band_4cm=True,
            atca_band_4cm_freq1=5500.0,
            atca_band_4cm_freq2=9000.0,
            atca_min_exptime=120,
        )

        source_settings = GrbSourceSettings()

        prop_settings = ProposalSettings(
            id=6,
            proposal_id="ATCA_short_GRB",
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )

        return prop_settings

    @property
    def proposal_mwa_vcs_grb_swif(self):  # MWA_VCS_GRB_swif
        # Creating the instance based on the data from id=7
        telescope_settings = MWAProposalSettings(
            id=7,
            telescope=self.telescope_factory.telescope_mwa_vcs,
            project_id=self.project_id_factory.telescope_project_g0055,
            proposal_id="MWA_VCS_GRB_swif",
            proposal_description="MWA VCS triggering on Swift GRBs",
            priority=3,
            event_telescope=self.event_telescope_factory.event_telescope_swift,
            event_min_duration=0.0,  # Included because it differs from the default
            event_max_duration=2.1,  # Included because it differs from the default
            pending_min_duration_1=0.0,  # Included because it differs from the default
            pending_max_duration_1=0.0,  # Included because it differs from the default
            pending_min_duration_2=0.0,  # Included because it differs from the default
            pending_max_duration_2=0.0,  # Included because it differs from the default
            fermi_prob=50,
            swift_rate_signf=0,
            repointing_limit=10.0,
            testing=TriggerOnChoices.REAL_ONLY,
            source_type=SourceChoices.GRB,
            mwa_exptime=900,  # Included because it differs from the default(896)
        )

        source_settings = GrbSourceSettings()
        prop_settings = ProposalSettings(
            id=7,
            proposal_id="MWA_VCS_GRB_swif",
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposal_test2_neutrino(self):  # test2_neutrino
        # Creating the instance based on the data from id=10
        telescope_settings = MWAProposalSettings(
            id=10,
            telescope=self.telescope_factory.telescope_mwa_vcs,
            project_id=self.project_id_factory.telescope_project_c002,
            proposal_id="test2_neutrino",
            proposal_description="test neutrino",
            priority=6,
            event_telescope=self.event_telescope_factory.event_telescope_antares,
            event_min_duration=0.256,
            event_max_duration=1.024,
            pending_min_duration_1=1.025,
            pending_max_duration_1=2.056,
            pending_min_duration_2=0.128,
            pending_max_duration_2=0.255,
            fermi_prob=50,
            swift_rate_signf=0,
            repointing_limit=10.0,
            testing=TriggerOnChoices.PRETEND_REAL,
            source_type=SourceChoices.NU,
            mwa_exptime=120,  # Included because it differs from the default
            mwa_calexptime=60,  # Included because it differs from the default
            observe_significant=True,  # GW custom logic
        )

        source_settings = NuSourceSettings()
        prop_settings = ProposalSettings(
            id=10,
            proposal_id="test2_neutrino",
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposal_atca_hess_grbs(self):  # proposal_id="ATCA_HESS_GRBs",
        # Creating the instance based on the data from id=11
        telescope_settings = ATCAProposalSettings(
            id=11,
            telescope=self.telescope_factory.telescope_atca,
            project_id=self.project_id_factory.telescope_project_c3374,
            proposal_id="ATCA_HESS_GRBs",
            proposal_description="ATCA rapid-response triggering on HESS-detected GRBs",
            priority=6,
            event_telescope=self.event_telescope_factory.event_telescope_hess,
            event_min_duration=0.256,
            event_max_duration=1.024,
            pending_min_duration_1=1.025,
            pending_max_duration_1=2.056,
            pending_min_duration_2=0.128,
            pending_max_duration_2=0.255,
            maximum_position_uncertainty=0.07,
            fermi_prob=50,
            swift_rate_signf=0,
            repointing_limit=0.02,
            testing=TriggerOnChoices.PRETEND_REAL,
            source_type=SourceChoices.GRB,
            observe_significant=True,
        )

        source_settings = GrbSourceSettings()
        prop_settings = ProposalSettings(
            id=11,
            proposal_id="ATCA_HESS_GRBs",
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposal_atca_long_grb(self):  # proposal_id="ATCA_long_GRB"
        # Creating the instance based on the data from id=12
        telescope_settings = ATCAProposalSettings(
            id=12,
            telescope=self.telescope_factory.telescope_atca,
            project_id=self.project_id_factory.telescope_project_c3542,
            proposal_id="ATCA_long_GRB",
            proposal_description="This is the triggering proposal for the large ATCA Long GRB program",
            priority=6,
            event_telescope=self.event_telescope_factory.event_telescope_swift,
            event_min_duration=2.056,
            event_max_duration=10000.0,
            pending_min_duration_1=0.0,
            pending_max_duration_1=2.055,
            pending_min_duration_2=0.0,
            pending_max_duration_2=0.0,
            maximum_position_uncertainty=0.1,
            testing=TriggerOnChoices.REAL_ONLY,
            source_type=SourceChoices.GRB,
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
            proposal_id="ATCA_long_GRB",
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposal_mwa_gw_bns(self):
        # Creating the instance based on the data from id=13
        telescope_settings = MWAProposalSettings(
            id=13,
            telescope=self.telescope_factory.telescope_mwa_vcs,
            project_id=self.project_id_factory.telescope_project_g0094,
            proposal_id="MWA_GW_BNS",
            proposal_description="MWA triggering on LIGO-Virgo-KAGRA BNS GW events detected during O4 using a multi-beam approach and the VCS",
            priority=1,
            event_telescope=self.event_telescope_factory.event_telescope_lvc,
            maximum_position_uncertainty=0.05,
            fermi_prob=50,
            repointing_limit=10.0,
            testing=TriggerOnChoices.BOTH,
            source_type=SourceChoices.GW,
            observe_significant=True,
            start_observation_at_high_sensitivity=True,
            # MWA specific settings
            mwa_freqspecs="93,24",
            mwa_exptime=7200,
        )

        source_settings = GWSourceSettings()
        prop_settings = ProposalSettings(
            id=13,
            proposal_id="MWA_G W_BNS",
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )

        return prop_settings

    @property
    def proposal_mwa_gw_nshh(self):
        # Creating the instance based on the data from id=14
        telescope_settings = MWAProposalSettings(
            id=14,
            telescope=self.telescope_factory.telescope_mwa_vcs,
            project_id=self.project_id_factory.telescope_project_g0094,
            proposal_id="MWA_GW_NSBH",
            proposal_description="MWA triggering on LIGO-Virgo-KAGRA BNS GW events detected during O4 using a multi-beam approach and the VCS",
            priority=3,  # Non-default value
            event_telescope=self.event_telescope_factory.event_telescope_lvc,
            event_min_duration=0.512,  # Non-default value
            event_max_duration=10000.0,  # Non-default value
            pending_min_duration_1=1.0,  # Non-default value
            pending_max_duration_1=1000.0,  # Non-default value
            pending_min_duration_2=0.0,  # Non-default value
            pending_max_duration_2=0.0,  # Non-default value
            maximum_position_uncertainty=0.07,  # Non-default value
            fermi_prob=60,  # Non-default value
            swift_rate_signf=5.0,  # Non-default value
            repointing_limit=5.0,  # Non-default value
            testing=TriggerOnChoices.REAL_ONLY,  # Non-default value
            source_type=SourceChoices.GW,  # Non-default value
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
            proposal_id="MWA_GW_NSBH",
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )
        return prop_settings

    @property
    def proposals(self):
        valid_classes = (ProposalSettings,)
        return [
            getattr(self, attr)
            for attr in dir(self)
            if attr.startswith("proposal_")
            and isinstance(getattr(self, attr), valid_classes)
        ]

    def filter_proposals_by_id(self, proposal_id: int):
        for proposal in self.proposals:
            if proposal.id == proposal_id:
                return proposal
        return None
