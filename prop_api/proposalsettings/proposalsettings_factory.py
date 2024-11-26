from .eventtelescope_factory import EventTelescopeFactory
from .models.constants import SourceChoices, TriggerOnChoices
from .models.prop_atca_hess_grbs.model import ProposalAtcaHessGrbs
from .models.prop_atca_long_grb.model import ProposalAtcaLongGrb
from .models.prop_atca_short_grb.model import ProposalAtcaShortGrb
from .models.prop_mwa_gw_bns.model import ProposalMwaGwBns
from .models.prop_mwa_gw_nsbh.model import ProposalMwaGwNsbh
from .models.prop_mwa_vcs_grb_swif.model import ProposalMwaVcsGrbSwif
from .models.prop_test2_neutrino.model import ProposalTest2Neutrino
from .models.proposal import ProposalSettings
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
        prop = ProposalAtcaShortGrb()
        return prop

    @property
    def proposal_mwa_vcs_grb_swif(self):
        # print("proposal_mwa_vcs_grb_swif")
        prop = ProposalMwaVcsGrbSwif()
        return prop

    @property
    def proposal_test2_neutrino(self):
        # print("proposal_test2_neutrino")
        prop = ProposalTest2Neutrino()
        return prop

    @property
    def proposal_atca_hess_grb(self):
        # print("proposal_atca_hess_grb")
        prop = ProposalAtcaHessGrbs()
        return prop

    @property
    def proposal_atca_long_grb(self):
        # print("proposal_atca_long_grb")
        prop = ProposalAtcaLongGrb()
        return prop

    @property
    def proposal_mwa_gw_bns(self):
        # print("proposal_mwa_gw_bns")
        prop = ProposalMwaGwBns()
        return prop

    @property
    def proposal_mwa_gw_nshh(self):
        # print("proposal_mwa_gw_nshh")
        prop = ProposalMwaGwNsbh()
        return prop

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
