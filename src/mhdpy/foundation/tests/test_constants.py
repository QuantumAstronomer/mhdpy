"""Tests of the physical constants and astronomical units: requirements UNI10-UNI11.

The requirements are part of those of the unit system (docs/requirements/L0-foundation/units.md), which converts the
constants to code units; the other requirements of that document are tested in test_units.py. Each test names the
requirements it checks in its docstring.
"""

import math
from decimal import Decimal, localcontext

import numpy as np
import pytest

from mhdpy.foundation import constants, units

## pi to 50 digits, for the exact references below: the decimal module has no constant pi.
PI = Decimal("3.1415926535897932384626433832795028841971693993751")

## The measured constants of UNI10 as CODATA 2022 publishes them, in SI, each with the exact factor that converts it to
## cgs: a metre is 100 cm, a kilogram 1000 g, a joule 1e7 erg. The values are written as strings, so that the decimal
## module reads exactly the published digits rather than a double nearby.
# fmt: off
MEASURED_CONSTANTS = {
    "GRAVITATIONAL_CONSTANT": ("6.67430e-11",       "1e3"),  ## m^3 kg^-1 s^-2 -> cm^3 g^-1 s^-2
    "ATOMIC_MASS_UNIT":       ("1.66053906892e-27", "1e3"),  ## kg -> g
    "PROTON_MASS":            ("1.67262192595e-27", "1e3"),  ## kg -> g
    "ELECTRON_MASS":          ("9.1093837139e-31",  "1e3"),  ## kg -> g
}

## The constants that are exact by the definition of the SI, as it defines them, in the same form.
EXACT_CONSTANTS = {
    "SPEED_OF_LIGHT":         ("299792458",         "1e2"),  ## m s^-1 -> cm s^-1
    "PLANCK_CONSTANT":        ("6.62607015e-34",    "1e7"),  ## J s -> erg s
    "BOLTZMANN_CONSTANT":     ("1.380649e-23",      "1e7"),  ## J K^-1 -> erg K^-1
}
# fmt: on

## The atomic mass of 1H in the Atomic Mass Evaluation 2020, in units of the atomic mass unit.
HYDROGEN_ATOMIC_MASS = "1.007825031898"

## The values the IAU fixes, in SI, in the same form: the astronomical unit (IAU 2012 Resolution B2) and the nominal
## solar values (IAU 2015 Resolution B3). The solar mass is not among them: the IAU fixes the solar mass parameter
## (GM)_sun, from which the solar mass follows (see astronomical_references).
# fmt: off
IAU_CONSTANTS = {
    "ASTRONOMICAL_UNIT":      ("149597870700",      "1e2"),  ## m -> cm
    "SOLAR_MASS_PARAMETER":   ("1.3271244e20",      "1e6"),  ## m^3 s^-2 -> cm^3 s^-2
    "SOLAR_RADIUS":           ("6.957e8",           "1e2"),  ## m -> cm
    "SOLAR_LUMINOSITY":       ("3.828e26",          "1e7"),  ## W -> erg s^-1
}
# fmt: on

## The Julian year of 365.25 days of 86400 s, in seconds. The product is exact at any precision of the decimal module,
## so it can be computed here, outside the 50-digit context of the functions below.
JULIAN_YEAR = Decimal("365.25") * 86400

## The dimensions of each physical constant of UNI10 in length, mass and time, as in NAMED_UNITS of test_units.py.
## This table is the specification the conversion to code units is checked against. The kelvin is not a dimension of
## the code units, so a constant that contains it keeps it, and it does not appear here.
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


def in_cgs(published: tuple[str, str]) -> Decimal:
    """Return a published SI value in cgs, exactly: the value times its conversion factor, both read as decimals."""
    value, factor = published
    return Decimal(value) * Decimal(factor)


def exact_references() -> dict[str, Decimal]:
    """Return the exact values in cgs of the constants that are exact, by the definition of the SI or by derivation.

    c, h and k_B are exact by the definition of the SI; the Stefan-Boltzmann constant and the radiation constant follow
    from them and are exact as well.
    """
    ## 50 significant digits, as in the exact references of test_units.py, for this function only.
    with localcontext() as context:
        context.prec = 50
        c, h, k = (
            in_cgs(EXACT_CONSTANTS[name]) for name in ("SPEED_OF_LIGHT", "PLANCK_CONSTANT", "BOLTZMANN_CONSTANT")
        )
        return {
            "SPEED_OF_LIGHT": c,
            "PLANCK_CONSTANT": h,
            "BOLTZMANN_CONSTANT": k,
            "STEFAN_BOLTZMANN_CONSTANT": 2 * PI**5 * k**4 / (15 * h**3 * c**2),
            "RADIATION_CONSTANT": 8 * PI**5 * k**4 / (15 * h**3 * c**3),
        }


def astronomical_references() -> dict[str, Decimal]:
    """Return the exact values in cgs of the astronomical units of UNI11, from the IAU resolutions."""
    with localcontext() as context:
        context.prec = 50
        au = in_cgs(IAU_CONSTANTS["ASTRONOMICAL_UNIT"])
        ## IAU 2015 Resolution B2: the parsec is 648000 / pi astronomical units, 648000 / pi being the number of
        ## arcseconds in a radian. Dividing by pi is not exact, so it happens here, at 50 digits.
        parsec = 648000 / PI * au
        return {
            "ASTRONOMICAL_UNIT": au,
            "PARSEC": parsec,
            "KILOPARSEC": parsec * 10**3,
            "MEGAPARSEC": parsec * 10**6,
            ## The solar mass is the nominal (GM)_sun divided by the CODATA value of G.
            "SOLAR_MASS": (
                in_cgs(IAU_CONSTANTS["SOLAR_MASS_PARAMETER"]) / in_cgs(MEASURED_CONSTANTS["GRAVITATIONAL_CONSTANT"])
            ),
            "SOLAR_RADIUS": in_cgs(IAU_CONSTANTS["SOLAR_RADIUS"]),
            "SOLAR_LUMINOSITY": in_cgs(IAU_CONSTANTS["SOLAR_LUMINOSITY"]),
            "JULIAN_YEAR": JULIAN_YEAR,
            "MEGAYEAR": JULIAN_YEAR * 10**6,
            "GIGAYEAR": JULIAN_YEAR * 10**9,
            "KILOMETRE_PER_SECOND": Decimal("1e5"),  ## 1e5 cm per s
        }


class TestPhysicalConstants:
    """UNI10-UNI11: physical constants and astronomical units from cited sources."""

    ## Run this test once for each measured constant.
    @pytest.mark.parametrize("name", list(MEASURED_CONSTANTS))
    def test_measured_constants_in_cgs(self, name: str) -> None:
        """Check the measured constants in cgs against the values of CODATA 2022 (UNI10).

        Each constant must be the double nearest to its published value, converted to cgs.
        """
        ## float() of a decimal gives the double nearest to it, so the constant must equal it exactly. Its type is
        ## np.float64, like the units, so that conversions stay in double precision.
        constant = getattr(constants, name)
        assert isinstance(constant, np.float64)
        assert constant == float(in_cgs(MEASURED_CONSTANTS[name]))

    ## Run this test once for each exact constant: the three exact by the definition of the SI and the two derived
    ## from them.
    @pytest.mark.parametrize("name", list(exact_references()))
    def test_exact_constants_in_cgs(self, name: str) -> None:
        """Check that the exact constants are the doubles nearest to their exact values in cgs (UNI10).

        The constants exact by the definition of the SI are c, h and k_B; the Stefan-Boltzmann constant and the
        radiation constant follow from them and are exact as well.
        """
        constant = getattr(constants, name)
        assert isinstance(constant, np.float64)
        assert constant == float(exact_references()[name])

    def test_hydrogen_mass(self) -> None:
        """Check the mass of the hydrogen atom against the Atomic Mass Evaluation 2020 (UNI10).

        The reference is the atomic mass of 1H in units of the atomic mass unit, times the atomic mass unit of CODATA
        2022, and the constant must be the double nearest to that product.
        """
        ## The product of two decimals of 13 and 12 digits has at most 25 digits, so at 50 digits it is exact.
        with localcontext() as context:
            context.prec = 50
            exact = Decimal(HYDROGEN_ATOMIC_MASS) * in_cgs(MEASURED_CONSTANTS["ATOMIC_MASS_UNIT"])
        assert isinstance(constants.HYDROGEN_MASS, np.float64)
        assert constants.HYDROGEN_MASS == float(exact)

    ## Run this test once for each physical constant of UNI10.
    @pytest.mark.parametrize("name", list(DIMENSIONS))
    def test_constants_in_code_units(self, name: str) -> None:
        """Check that every constant converts to code units by its dimensions (UNI10).

        A constant containing the kelvin, such as k_B, keeps it: code units have no temperature dimension.
        """
        ## Any unit system serves, since the test checks the conversion, not the values: this one of 1 kpc, 1e5 solar
        ## masses and 1 Myr.
        system = units.UnitSystem(length=constants.KILOPARSEC, mass=1e5 * constants.SOLAR_MASS, time=constants.MEGAYEAR)
        in_cgs_value = getattr(constants, name)

        ## The constant in code units, a double like every unit.
        in_code_units = system.constant(name)
        assert isinstance(in_code_units, np.float64)

        ## Converted back to cgs with the unit of its dimensions (UNI02), it must give the constant in cgs again: a
        ## value in code units times its unit is the value in cgs (UNI05). This checks the dimensions the unit system
        ## uses against the table above: a wrong exponent changes the value by orders of magnitude. The conversion and
        ## its inverse take one rounding each, so the round trip stays within 2 ulp, as in UNI06.
        back = in_code_units * system.unit(**DIMENSIONS[name])
        assert abs(back - in_cgs_value) <= 2 * math.ulp(in_cgs_value)

    ## Run this test once for each astronomical unit.
    @pytest.mark.parametrize("name", list(astronomical_references()))
    def test_astronomical_units(self, name: str) -> None:
        """Check the astronomical units in cgs against the IAU resolutions (UNI11).

        Each unit must be the double nearest to its exact value, or, for the solar mass, to the value derived from the
        nominal solar mass parameter and G.
        """
        constant = getattr(constants, name)
        assert isinstance(constant, np.float64)
        assert constant == float(astronomical_references()[name])

    def test_unit_system_from_astronomical_units(self) -> None:
        """Check that a unit system can be defined in astronomical units (UNI11).

        The example of the requirement: 1 kpc, 1e5 solar masses and 1 Myr.
        """
        system = units.UnitSystem(length=constants.KILOPARSEC, mass=1e5 * constants.SOLAR_MASS, time=constants.MEGAYEAR)
        references = astronomical_references()

        ## The kiloparsec and the megayear are kept exactly as given (UNI01), so they are the doubles nearest to their
        ## exact values, as the test above checks.
        assert system.length == float(references["KILOPARSEC"])
        assert system.time == float(references["MEGAYEAR"])

        ## 1e5 solar masses is a product in double precision: the solar mass, within half an ulp of its exact value,
        ## is multiplied by 1e5 and rounded once more. Measured in ulps of the result, that stays within 2 ulp.
        expected = float(10**5 * references["SOLAR_MASS"])
        assert abs(system.mass - expected) <= 2 * math.ulp(expected)
