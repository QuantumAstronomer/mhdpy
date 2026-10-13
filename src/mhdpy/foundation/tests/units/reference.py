"""Reference values shared by the tests of the unit system.

The code units most tests use, the specification tables of the named units and their labels, pi to 50 digits for exact
references, and the domain of the round trips. Each test module imports what it uses; the unit systems built from these
code units are fixtures, in conftest.py.
"""

import sys
from decimal import Decimal

## pi to 50 digits, for exact references computed with the decimal module, which has no constant pi.
PI = Decimal("3.1415926535897932384626433832795028841971693993751")


def within_range(x: float) -> bool:
    """Return whether x lies a factor of two inside the range of normal doubles, the domain of UNI06.

    Normal doubles range in magnitude from sys.float_info.min (about 2.2e-308) to sys.float_info.max (about 1.8e308).
    At the edges of that range, a single rounding can push a result across a limit: up to infinity, or down below the
    normal numbers, where precision is lost. Keeping a factor of two away from both limits rules that out, since one
    rounding changes a value by far less than a factor of two. Zero, NaN and infinities lie outside the range as well.
    """
    return 2 * sys.float_info.min <= abs(x) <= sys.float_info.max / 2


## Code units of 1 kpc, 1e5 solar masses and 1 Myr, written out in cgs. The tests use these literal values so that they
## do not depend on the astronomical units of constants.py, which are tested separately (UNI11).
LENGTH = 3.0856775814913673e21
MASS = 1.988409870698051e38
TIME = 3.15576e13

## The same values by name, so that a test can look up the value a code unit was given.
CODE_UNITS = {"length": LENGTH, "mass": MASS, "time": TIME}

## The named units of UNI03 with the exponents of their dimensions in length, mass and time. A dimension that does not
## occur is left out (its exponent is 0). This table is the specification the test checks the unit system against.
# fmt: off
NAMED_UNITS: dict[str, dict[str, float]] = {
    "length":           {"length":  1                        },
    "mass":             {              "mass": 1             },
    "time":             {                         "time":  1 },
    "velocity":         {"length":  1,            "time": -1 },  ## cm s^-1
    "acceleration":     {"length":  1,            "time": -2 },  ## cm s^-2
    "density":          {"length": -3, "mass": 1             },  ## g cm^-3
    "momentum_density": {"length": -2, "mass": 1, "time": -1 },  ## g cm^-2 s^-1
    "mass_flux":        {"length": -2, "mass": 1, "time": -1 },  ## g cm^-2 s^-1
    "pressure":         {"length": -1, "mass": 1, "time": -2 },  ## dyn cm^-2 = g cm^-1 s^-2
    "energy_density":   {"length": -1, "mass": 1, "time": -2 },  ## erg cm^-3 = g cm^-1 s^-2
    "energy":           {"length":  2, "mass": 1, "time": -2 },  ## erg = g cm^2 s^-2
    "specific_energy":  {"length":  2,            "time": -2 },  ## erg g^-1 = cm^2 s^-2
    "energy_flux":      {              "mass": 1, "time": -3 },  ## erg cm^-2 s^-1 = g s^-3
}
# fmt: on

## The label of each named unit's cgs unit (UNI04), exactly as it is to appear in the headers of the history and the
## attributes of outputs. Units are written with their cgs names where those exist (dyn, erg), and exponents with ^.
# fmt: off
LABELS = {
    "length"            : "cm",
    "mass"              : "g",
    "time"              : "s",
    "velocity"          : "cm s^-1",
    "acceleration"      : "cm s^-2",
    "density"           : "g cm^-3",
    "momentum_density"  : "g cm^-2 s^-1",
    "mass_flux"         : "g cm^-2 s^-1",
    "pressure"          : "dyn cm^-2",
    "energy_density"    : "erg cm^-3",
    "energy"            : "erg",
    "specific_energy"   : "erg g^-1",
    "energy_flux"       : "erg cm^-2 s^-1",
    "magnetic_field"    : "G",
}
# fmt: on
