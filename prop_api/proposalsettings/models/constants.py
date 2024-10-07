from enum import Enum


class SourceChoices(str, Enum):
    GRB = "GRB"  # "Gamma-ray burst"
    FS = "FS"  # "Flare star"
    NU = "NU"  # "Neutrino"
    GW = "GW"  # "Gravitational wave"


class TriggerOnChoices(str, Enum):
    PRETEND_REAL = "PRETEND_REAL"  # "Real events only (Pretend Obs)"
    BOTH = "BOTH"  # "Real events (Real Obs) and test events (Pretend Obs)"
    REAL_ONLY = "REAL_ONLY"  # "Real events only (Real Obs)"

