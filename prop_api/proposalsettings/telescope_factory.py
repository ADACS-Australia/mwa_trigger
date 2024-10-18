from .models.telescope import Telescope


class TelescopeFactory:
    """
    A factory class for creating and managing Telescope objects.

    This class provides properties for various telescope configurations and a method
    to retrieve all available telescopes.
    """

    @property
    def telescope_mwa_vcs(self):
        return Telescope(name="MWA_VCS", lon=116.671, lat=-26.7033, height=377.827)

    @property
    def telescope_mwa_correlate(self):
        return Telescope(
            name="MWA_correlate", lon=116.671, lat=-26.7033, height=377.827
        )

    @property
    def telescope_atca(self):
        return Telescope(name="ATCA", lon=149.550278, lat=-30.312778, height=237.0)

    @property
    def telescopes(self):
        """
        Returns a list of all available Telescope objects.

        This method dynamically generates a list of all Telescope objects
        by iterating through the class attributes that start with "telescope_".

        Returns:
            list: A list of Telescope objects.
        """
        return [
            getattr(self, attr)
            for attr in dir(self)
            if attr.startswith("telescope_")
            and isinstance(getattr(self, attr), Telescope)
        ]
