GRB = "GRB"
FS = "FS"
NU = "NU"
GW = "GW"
SOURCE_CHOICES = (
    (GRB, "Gamma-ray burst"),
    (FS, "Flare star"),
    (NU, "Neutrino"),
    (GW, "Gravitational wave"),
)

TRIGGER_ON = (
    ("PRETEND_REAL", "Real events only (Pretend Obs)"),
    ("BOTH", "Real events (Real Obs) and test events (Pretend Obs)"),
    ("REAL_ONLY", "Real events only (Real Obs)"),
)
