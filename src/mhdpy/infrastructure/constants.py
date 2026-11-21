"""The physical and astronomical constants in cgs, each with the value of its current source.

The module holds the constants that the first pass of mhdpy needs, each a float of double precision under a name in
capitals, typed Final, with its unit and source in the comment above it. Later briefs add the constants that they need,
as self-gravity will add the gravitational constant.

The constants belong to the infrastructure, stratum 1, and rely on the standard library alone. They are held in cgs and
converted nowhere here: the units give Boltzmann's constant and the masses in the code units of a run, and take the
parsec and the Julian year for their named units, so that no digit is repeated where it could drift. The physics uses
them where it needs a temperature, a number density or a length in parsecs.

Contents
========================================================================================================================
BOLTZMANN
    Boltzmann's constant in erg per kelvin, fixed by the SI since 2019.
PROTON_MASS
    The mass of the proton in grams, after CODATA 2022.
ELECTRON_MASS
    The mass of the electron in grams, after CODATA 2022.
ATOMIC_MASS_UNIT
    The atomic mass unit in grams, after CODATA 2022.
ASTRONOMICAL_UNIT
    The astronomical unit in centimeters, fixed by Resolution B2 of the IAU of 2012.
PARSEC
    The parsec in centimeters, as Resolution B2 of the IAU of 2015 defines it.
JULIAN_YEAR
    The Julian year in seconds, of 365.25 days of 86 400 seconds.

Its requirements are in design/requirements/infrastructure/constants.md, and docs/constants.md explains it.
"""

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
