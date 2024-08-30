from .models import Telescope


class TelescopeFactory:

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
        return [
            getattr(self, attr)
            for attr in dir(self)
            if attr.startswith("telescope_")
            and isinstance(getattr(self, attr), Telescope)
        ]
