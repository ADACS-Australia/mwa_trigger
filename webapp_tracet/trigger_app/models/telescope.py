from django.db import models


class Telescope(models.Model):
    name = models.CharField(
        max_length=64,
        verbose_name="Telescope name",
        help_text="E.g. MWA_VCS, MWA_correlate or ATCA.",
        unique=True,
    )
    lon = models.FloatField(verbose_name="Telescope longitude in degrees")
    lat = models.FloatField(verbose_name="Telescope latitude in degrees")
    height = models.FloatField(
        verbose_name="Telescope height above sea level in meters"
    )

    def __str__(self):
        return f"{self.name}"


class EventTelescope(models.Model):
    name = models.CharField(
        max_length=64,
        verbose_name="Event Telescope name",
        help_text="Telescope that we receive Events from (e.g. SWIFT or Fermi)",
        unique=True,
    )

    def __str__(self):
        return f"{self.name}"


class TelescopeProjectID(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=125,
        verbose_name="Telescope Project ID",
        help_text="The project ID for the telescope used to automatically schedule observations.",
    )
    password = models.CharField(
        max_length=2020,
        verbose_name="Telescope Project Password",
        help_text="The project password for the telescope used to automatically schedule observations.",
    )
    description = models.CharField(
        max_length=5000, help_text="A brief description of the project."
    )
    atca_email = models.CharField(
        blank=True,
        null=True,
        max_length=515,
        verbose_name="ATCA Proposal Email",
        help_text="The email address of someone that was on the ATCA observing proposal. This is an authentication step only required for ATCA.",
    )
    telescope = models.ForeignKey(
        Telescope,
        to_field="name",
        verbose_name="Telescope name",
        help_text="Telescope this proposal will observer with. If the telescope you want is not here add it on the admin page.",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.telescope}_{self.id}"