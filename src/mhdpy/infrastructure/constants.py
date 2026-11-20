"""The physical and astronomical constants in cgs, each with the value of its current source."""

import math

from typing import Final


## Boltzmann's constant in erg/K, fixed by the SI since 2019 (CONST01)
BOLTZMANN: Final = 1.380649e-16
## the mass of the proton in g, after CODATA 2022 (CONST02)
PROTON_MASS: Final = 1.67262192595e-24
## the mass of the electron in g, after CODATA 2022 (CONST03)
ELECTRON_MASS: Final = 9.1093837139e-28
## the atomic mass unit in g, after CODATA 2022 (CONST04)
ATOMIC_MASS_UNIT: Final = 1.66053906892e-24

## the astronomical unit in cm, fixed by Resolution B2 of the IAU of 2012 (CONST05)
ASTRONOMICAL_UNIT: Final = 1.495978707e13
## the parsec in cm, as Resolution B2 of the IAU of 2015 defines it (CONST06)
PARSEC: Final = 648_000 / math.pi * ASTRONOMICAL_UNIT
## the Julian year in s, of 365.25 days of 86 400 s (CONST07)
JULIAN_YEAR: Final = 365.25 * 86_400
