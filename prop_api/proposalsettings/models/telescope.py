from typing import Optional

from pydantic import BaseModel, Field


class Telescope(BaseModel):
    """
    Represents a telescope with its basic properties.
    """

    name: str = Field(max_length=64, description="E.g. MWA_VCS, MWA_correlate or ATCA.")
    lon: float = Field(description="Telescope longitude in degrees")
    lat: float = Field(description="Telescope latitude in degrees")
    height: float = Field(description="Telescope height above sea level in meters")

    class Config:
        extra = "forbid"  # This forbids any extra fields t


class EventTelescope(BaseModel):
    """
    Represents a telescope that receives events.
    """

    name: str = Field(
        max_length=64,
        description="Telescope that we receive Events from (e.g. SWIFT or Fermi)",
    )

    class Config:
        extra = "forbid"  # This forbids any extra fields t


class TelescopeProjectId(BaseModel):
    """
    Represents a telescope project with its identification and authentication details.
    """

    id: str = Field(
        max_length=125,
        description="The project ID for the telescope used to automatically schedule observations.",
    )
    password: str = Field(
        max_length=2020,
        description="The project password for the telescope used to automatically schedule observations.",
    )
    description: str = Field(
        max_length=5000, description="A brief description of the project."
    )
    atca_email: Optional[str] = Field(
        None,
        max_length=515,
        description="The email address of someone that was on the ATCA observing proposal. This is an authentication step only required for ATCA.",
    )
    telescope: Telescope

    class Config:
        extra = "forbid"  # This forbids any extra fields t
