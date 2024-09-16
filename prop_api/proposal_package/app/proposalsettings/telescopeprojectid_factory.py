from .models import TelescopeProjectId
from .telescope_factory import TelescopeFactory


class TelescopeProjectIdFactory:
    def __init__(self, telescope_factory: TelescopeFactory):
        self.telescope_factory = telescope_factory

    @property
    def telescope_project_c002(self):

        return TelescopeProjectId(
            id="C002",
            password="MySuperSecretPassword",
            description="MWA triggering proposal that doesn't have permission to delete any existing observations",
            atca_email=None,
            telescope=self.telescope_factory.telescope_mwa_vcs,
        )

    @property
    def telescope_project_c3204(self):
        return TelescopeProjectId(
            id="C3204",
            password="MySuperSecretPassword",
            description="Token for Short GRB ATCA triggering 2024APR",
            atca_email="gemma.anderson@curtin.edu.au",
            telescope=self.telescope_factory.telescope_atca,
        )

    @property
    def telescope_project_c3374(self):

        return TelescopeProjectId(
            id="C3374",
            password="MySuperSecretPassword",
            description="Token for ATCA HESS triggering program 2023APR",
            atca_email="gemma.anderson@curtin.edu.au",
            telescope=self.telescope_factory.telescope_atca,
        )

    @property
    def telescope_project_c3542(self):
        return TelescopeProjectId(
            id="C3542",
            password="MySuperSecretPassword",
            description="Token for ATCA Long GRB triggering program 2024APR",
            atca_email="gemma.anderson@curtin.edu.au",
            telescope=self.telescope_factory.telescope_atca,
        )

    @property
    def telescope_project_g0055(self):
        return TelescopeProjectId(
            id="G0055",
            password="MySuperSecretPassword",
            description="MWA GRB password for G0055",
            atca_email=None,
            telescope=self.telescope_factory.telescope_mwa_vcs,
        )

    @property
    def telescope_project_g0094(self):
        return TelescopeProjectId(
            id="G0094",
            password="MySuperSecretPassword",
            description="Password for MWA LVK GW triggering",
            atca_email=None,
            telescope=self.telescope_factory.telescope_mwa_vcs,
        )

    @property
    def telescope_projects(self):

        return [
            getattr(self, attr)
            for attr in dir(self)
            if attr.startswith("telescope_project_")
            and isinstance(getattr(self, attr), TelescopeProjectId)
        ]
