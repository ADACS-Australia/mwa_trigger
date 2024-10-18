from .config import PROJECT_PASSWORDS
from .models.telescope import TelescopeProjectId
from .telescope_factory import TelescopeFactory


class TelescopeProjectIdFactory:
    """
    A factory class for creating TelescopeProjectId objects.

    This class manages the creation of TelescopeProjectId instances for various
    telescope projects, providing a centralized way to handle project-specific
    information and configurations.
    """

    def __init__(self, telescope_factory: TelescopeFactory):
        """
        Initialize the TelescopeProjectIdFactory.

        Args:
            telescope_factory (TelescopeFactory): An instance of TelescopeFactory
                to provide telescope-specific information.
        """
        self.telescope_factory = telescope_factory

    def create_telescope_project(self, id, description, atca_email, telescope):
        """
        Create a TelescopeProjectId instance with the given parameters.

        Args:
            id (str): The project ID.
            description (str): A description of the project.
            atca_email (str): The email address for ATCA-related communications.
            telescope (Telescope): The telescope associated with the project.

        Returns:
            TelescopeProjectId: A new TelescopeProjectId instance.

        Raises:
            ValueError: If no password is found for the given project ID.
        """
        password = PROJECT_PASSWORDS.get(id)
        if not password:
            raise ValueError(f"No password found for project ID: {id}")

        return TelescopeProjectId(
            id=id,
            password=password,
            description=description,
            atca_email=atca_email,
            telescope=telescope,
        )

    @property
    def telescope_project_c002(self):
        """
        Create and return the TelescopeProjectId for project C002.

        Returns:
            TelescopeProjectId: The TelescopeProjectId instance for C002.
        """
        return self.create_telescope_project(
            id="C002",
            description="MWA triggering proposal that doesn't have permission to delete any existing observations",
            atca_email=None,
            telescope=self.telescope_factory.telescope_mwa_vcs,
        )

    @property
    def telescope_project_c3204(self):
        return self.create_telescope_project(
            id="C3204",
            description="Token for Short GRB ATCA triggering 2024APR",
            atca_email="batbold.sangi@curtin.edu.au",
            telescope=self.telescope_factory.telescope_atca,
        )

    @property
    def telescope_project_c3374(self):
        return self.create_telescope_project(
            id="C3374",
            description="Token for ATCA HESS triggering program 2023APR",
            atca_email="batbold.sangi@curtin.edu.au",
            telescope=self.telescope_factory.telescope_atca,
        )

    @property
    def telescope_project_c3542(self):
        return self.create_telescope_project(
            id="C3542",
            description="Token for ATCA Long GRB triggering program 2024APR",
            atca_email="batbold.sangi@curtin.edu.au",
            telescope=self.telescope_factory.telescope_atca,
        )

    @property
    def telescope_project_g0055(self):
        return self.create_telescope_project(
            id="G0055",
            description="MWA GRB password for G0055",
            atca_email=None,
            telescope=self.telescope_factory.telescope_mwa_vcs,
        )

    @property
    def telescope_project_g0094(self):
        return self.create_telescope_project(
            id="G0094",
            description="Password for MWA LVK GW triggering",
            atca_email=None,
            telescope=self.telescope_factory.telescope_mwa_vcs,
        )

    @property
    def telescope_projects(self):
        """
        Get a list of all TelescopeProjectId instances created by this factory.

        Returns:
            list[TelescopeProjectId]: A list of all TelescopeProjectId instances.
        """
        return [
            getattr(self, attr)
            for attr in dir(self)
            if attr.startswith("telescope_project_")
            and isinstance(getattr(self, attr), TelescopeProjectId)
        ]
