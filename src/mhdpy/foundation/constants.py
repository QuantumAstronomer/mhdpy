"""Physical constants and astronomical units of mhdpy, in cgs.

One table of constants, from cited sources, serves every module, so that no two modules can use different values of
the same constant. The unit system (``units.py``) converts them to code units. The requirements are UNI10 and UNI11 in
``docs/requirements/L0-foundation/units.md``, tested in the accompanying test module ``tests/test_constants.py``.

Every constant is the double-precision number nearest to its value in cgs: the value its source publishes, or, for a
constant derived from published values (such as the parsec or the solar mass), the value derived from them exactly.
Constants are therefore written as literals, with their source and derivation in the comment above them; computing them
here in double precision would add rounding errors of its own. Each is NumPy's double-precision number np.float64,
like the units, so that conversions stay in double precision.
"""

import numpy as np

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = [
    "ASTRONOMICAL_UNIT",
    "ATOMIC_MASS_UNIT",
    "BOLTZMANN_CONSTANT",
    "DIMENSIONS",
    "ELECTRON_MASS",
    "GIGAYEAR",
    "GRAVITATIONAL_CONSTANT",
    "HYDROGEN_MASS",
    "JULIAN_YEAR",
    "KILOMETRE_PER_SECOND",
    "KILOPARSEC",
    "MEGAPARSEC",
    "MEGAYEAR",
    "PARSEC",
    "PLANCK_CONSTANT",
    "PROTON_MASS",
    "RADIATION_CONSTANT",
    "SOLAR_LUMINOSITY",
    "SOLAR_MASS",
    "SOLAR_RADIUS",
    "SOURCES",
    "SPEED_OF_LIGHT",
    "STEFAN_BOLTZMANN_CONSTANT",
]

## The sources of all values in this module, as one line of text, for the records of unit systems in outputs and restart
## files (UNI14). A file that states its sources can be interpreted exactly even after these values have been revised.
SOURCES = "CODATA 2022; AME 2020; IAU 2012 Resolution B2; IAU 2015 Resolutions B2 and B3"

## ---- Physical constants (UNI10), CODATA 2022 unless stated otherwise ----
## The SI values in the comments are as published; the conversion to cgs is exact (1 m = 100 cm, 1 kg = 1000 g,
## 1 J = 1e7 erg, 1 W = 1e7 erg/s).

## The speed of light, exact by the definition of the SI: 299792458 m/s.
SPEED_OF_LIGHT = np.float64(2.99792458e10)  ## cm s^-1

## The gravitational constant: 6.67430(15)e-11 m^3 kg^-1 s^-2.
GRAVITATIONAL_CONSTANT = np.float64(6.67430e-8)  ## cm^3 g^-1 s^-2

## Boltzmann's constant, exact by the definition of the SI: 1.380649e-23 J/K.
BOLTZMANN_CONSTANT = np.float64(1.380649e-16)  ## erg K^-1

## Planck's constant, exact by the definition of the SI: 6.62607015e-34 J s.
PLANCK_CONSTANT = np.float64(6.62607015e-27)  ## erg s

## The atomic mass unit (unified atomic mass unit): 1.66053906892(52)e-27 kg.
ATOMIC_MASS_UNIT = np.float64(1.66053906892e-24)  ## g

## The mass of the hydrogen atom: the atomic mass of 1H of the Atomic Mass Evaluation 2020, 1.007825031898(14) u, times
## the atomic mass unit above.
HYDROGEN_MASS = np.float64(1.673532840102174e-24)  ## g

## The proton mass: 1.67262192595(52)e-27 kg.
PROTON_MASS = np.float64(1.67262192595e-24)  ## g

## The electron mass: 9.1093837139(28)e-31 kg.
ELECTRON_MASS = np.float64(9.1093837139e-28)  ## g

## The Stefan-Boltzmann constant, exact since it follows from exact constants: 2 pi^5 k_B^4 / (15 h^3 c^2).
STEFAN_BOLTZMANN_CONSTANT = np.float64(5.670374419184429e-5)  ## erg cm^-2 s^-1 K^-4

## The radiation constant, exact for the same reason: 4 sigma_SB / c = 8 pi^5 k_B^4 / (15 h^3 c^3).
RADIATION_CONSTANT = np.float64(7.565733250280004e-15)  ## erg cm^-3 K^-4

## ---- Astronomical units (UNI11), following the IAU ----

## The astronomical unit, exact by IAU 2012 Resolution B2: 149597870700 m.
ASTRONOMICAL_UNIT = np.float64(1.495978707e13)  ## cm

## The parsec, exact by IAU 2015 Resolution B2: 648000 / pi astronomical units; the kiloparsec and megaparsec are 1e3
## and 1e6 parsecs. Each is the double nearest to its exact value, which a multiplication by 1e3 or 1e6 in double
## precision does not always give (it does not for the megaparsec).
PARSEC = np.float64(3.0856775814913674e18)  ## cm
KILOPARSEC = np.float64(3.0856775814913673e21)  ## cm
MEGAPARSEC = np.float64(3.085677581491367e24)  ## cm

## The solar mass, derived from the nominal solar mass parameter of IAU 2015 Resolution B3, (GM)_sun = 1.3271244e20
## m^3 s^-2, and the gravitational constant above: (GM)_sun / G. G M_sun is measured far more precisely than G itself,
## and deriving M_sun from it keeps the two consistent for self-gravity.
SOLAR_MASS = np.float64(1.9884098706980507e33)  ## g

## The nominal solar radius and luminosity of IAU 2015 Resolution B3: 6.957e8 m and 3.828e26 W.
SOLAR_RADIUS = np.float64(6.957e10)  ## cm
SOLAR_LUMINOSITY = np.float64(3.828e33)  ## erg s^-1

## The Julian year of 365.25 days of 86400 s, the year of the IAU, and the megayear and gigayear of 1e6 and 1e9 years.
JULIAN_YEAR = np.float64(3.15576e7)  ## s
MEGAYEAR = np.float64(3.15576e13)  ## s
GIGAYEAR = np.float64(3.15576e16)  ## s

## The kilometre per second, the usual unit of velocities in astrophysics.
KILOMETRE_PER_SECOND = np.float64(1e5)  ## cm s^-1

## ---- Dimensions of the physical constants (UNI10) ----

## The exponents of length, mass and time in the dimensions of each physical constant of UNI10, by which the unit
## system converts it to code units (UnitSystem.constant). A dimension that does not occur is left out. The kelvin is
## not among them: code units have no temperature dimension, so a constant containing the kelvin keeps it in code
## units. The astronomical units are not listed, as they are only needed in cgs, to define unit systems.
# fmt: off
DIMENSIONS: dict[str, dict[str, float]] = {
    "SPEED_OF_LIGHT":            {"length":  1,             "time": -1 },  ## cm s^-1
    "GRAVITATIONAL_CONSTANT":    {"length":  3, "mass": -1, "time": -2 },  ## cm^3 g^-1 s^-2
    "BOLTZMANN_CONSTANT":        {"length":  2, "mass":  1, "time": -2 },  ## erg K^-1
    "PLANCK_CONSTANT":           {"length":  2, "mass":  1, "time": -1 },  ## erg s
    "ATOMIC_MASS_UNIT":          {              "mass":  1             },  ## g
    "HYDROGEN_MASS":             {              "mass":  1             },  ## g
    "PROTON_MASS":               {              "mass":  1             },  ## g
    "ELECTRON_MASS":             {              "mass":  1             },  ## g
    "STEFAN_BOLTZMANN_CONSTANT": {              "mass":  1, "time": -3 },  ## erg cm^-2 s^-1 K^-4
    "RADIATION_CONSTANT":        {"length": -1, "mass":  1, "time": -2 },  ## erg cm^-3 K^-4
}
# fmt: on
