"""Tests of the unit system: requirements UNI01-UNI18 (docs/requirements/L0-foundation/units.md).

The tests are grouped in classes that follow the groups of requirements in that document. Each test names the
requirements it checks in its docstring. The physical constants and astronomical units (UNI10-UNI11) have a module of
their own, and so do their tests: test_constants.py.
"""

import dataclasses
import itertools
import json
import math
import sys
from decimal import Decimal, localcontext

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from mhdpy.foundation import constants, units


def within_range(x: float) -> bool:
    """Return whether x lies a factor of two inside the range of normal doubles, the domain of UNI06.

    Normal doubles range in magnitude from sys.float_info.min (about 2.2e-308) to sys.float_info.max (about 1.8e308).
    At the edges of that range, a single rounding can push a result across a limit: up to infinity, or down below the
    normal numbers, where precision is lost. Keeping a factor of two away from both limits rules that out, since one
    rounding changes a value by far less than a factor of two. Zero, NaN and infinities lie outside the range as well.
    """
    return 2 * sys.float_info.min <= abs(x) <= sys.float_info.max / 2


## Tests that can only be written once later layers exist: physics modules declaring what they need (D12.1) and a
## simulation that can be set up and run (D13).
NEEDS_DRIVER = pytest.mark.skip(reason="needs physics modules and the driver of a simulation (layers L6 and above)")

## A test that is planned but not written yet. Its body is pytest.fail("Not written yet."), which this marker declares
## an expected failure ("xfail"), so the suite stays green while the test is visibly unfinished: pytest reports it as
## "x" rather than as passed or failed. raises= accepts only that deliberate failure, so a stub that crashed for any
## other reason would still fail. strict=True turns a stub that unexpectedly passes into a failure, so the marker cannot
## be forgotten once the test is written. When a test is written, its marker is removed.
NOT_WRITTEN = pytest.mark.xfail(reason="not written yet", raises=pytest.fail.Exception, strict=True)

## Code units of 1 kpc, 1e5 solar masses and 1 Myr, written out in cgs. The tests of the definition use these literal
## values so that they do not depend on the astronomical constants of the unit system itself, which are tested
## separately (UNI11).
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


class TestDefinition:
    """UNI01-UNI04: a unit system is defined by three code units, from which every other unit derives."""

    ## Run this test once for each code unit. Each name in the list becomes a separate test case, reported for example
    ## as test_defined_by_three_code_units[mass], so a failure names the unit that was not kept.
    @pytest.mark.parametrize("name", ["length", "mass", "time"])
    def test_defined_by_three_code_units(self, name: str) -> None:
        """Check that a unit system keeps its three defining code units exactly as given (UNI01)."""
        ## Set up a unit system with the code units defined at the top of this file.
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)

        ## getattr(system, "mass") is the same as system.mass: it reads the attribute whose name is in the variable.
        ## The value read back must be exactly the value given. Exact equality of floats is right here, because no
        ## arithmetic happens in between: any difference at all means the unit system altered its input.
        assert getattr(system, name) == CODE_UNITS[name]

    ## Run this test for every combination of a code unit and an invalid value. Two parametrize decorators multiply:
    ## 3 names x 5 values = 15 test cases, each reported by its values, for example
    ## test_invalid_code_unit_is_refused[nan-mass].
    @pytest.mark.parametrize("name", ["length", "mass", "time"])
    @pytest.mark.parametrize("value", [0.0, -1.0, math.inf, -math.inf, math.nan])
    def test_invalid_code_unit_is_refused(self, name: str, value: float) -> None:
        """Check that a code unit that is not positive and finite is refused at creation (UNI01).

        Zero, negative, infinite and undefined values are all refused, with an error that names the offending unit.
        """
        ## Start from the valid code units and replace the one under test by the invalid value. The | operator merges
        ## two dictionaries; where both have the same key, the value of the right-hand one wins.
        arguments = CODE_UNITS | {name: value}

        ## Creating the unit system must raise a ValueError. The match argument is searched for in the error message,
        ## so the test also checks that the message names the offending unit: an error about "mass" when the length
        ## is wrong would fail it.
        with pytest.raises(ValueError, match=name):
            units.UnitSystem(**arguments)

    def test_unit_from_dimensions(self) -> None:
        """Check that the unit of dimensions L^a M^b T^c is the code units' product to those powers (UNI02).

        The product must agree to within 4 ulp, for integer and half-integer exponents alike.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        ## All exponents from -4 to 4 in steps of 1/2: integers and half-integers, as the requirement asks.
        exponents = [k / 2 for k in range(-8, 9)]

        ## Every combination of three exponents, 17^3 = 4913 in all. itertools.product(exponents, repeat=3) gives each
        ## triplet (length, mass, time) once. Checking them all is fast (about a second) and, unlike a random sample,
        ## cannot miss the one combination where the error is largest.
        for length, mass, time in itertools.product(exponents, repeat=3):
            ## The reference, computed independently with Python's decimal module at 50 significant digits.
            ## Decimal(LENGTH) is the exact value of the double LENGTH, and the powers and products are rounded only at
            ## the 50th digit, so the reference is exact for any comparison in double precision. localcontext() sets
            ## the precision for this block only, without affecting decimal arithmetic elsewhere.
            with localcontext() as context:
                context.prec = 50
                exact = (
                    Decimal(LENGTH) ** Decimal(length) * Decimal(MASS) ** Decimal(mass) * Decimal(TIME) ** Decimal(time)
                )
            expected = float(exact)  ## the double nearest to the exact value

            ## math.ulp(x) is the gap between x and the next larger double, the "unit in the last place". Three powers
            ## (about 1 ulp each) and two products (1/2 ulp each) give a bound of 4 ulp. The message after the comma is
            ## shown when the assert fails, and names the exponents of the failing combination.
            actual = system.unit(length=length, mass=mass, time=time)
            assert abs(actual - expected) <= 4 * math.ulp(expected), f"exponents {length}, {mass}, {time}"

    ## Run this test once for every named unit. Each key of NAMED_UNITS becomes a separate test case, reported for
    ## example as test_named_units_follow_from_dimensions[density].
    @pytest.mark.parametrize("name", list(NAMED_UNITS))
    def test_named_units_follow_from_dimensions(self, name: str) -> None:
        """Check that every named unit equals the unit computed from its dimensions, to within 4 ulp (UNI03)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        ## The named unit, read as an attribute: getattr(system, "density") is system.density.
        named = getattr(system, name)

        ## The same unit from its dimensions through the general rule of UNI02, which is tested on its own.
        from_dimensions = system.unit(**NAMED_UNITS[name])

        ## Both must agree to within 4 ulp, the tolerance of UNI02.
        assert abs(named - from_dimensions) <= 4 * math.ulp(from_dimensions)

    ## Run this test once for every named unit: those of UNI03, and the magnetic field of UNI07, whose unit is not a
    ## product of base units and so is not in NAMED_UNITS.
    @pytest.mark.parametrize("name", [*NAMED_UNITS, "magnetic_field"])
    def test_named_unit_labels(self, name: str) -> None:
        """Check that every named unit has the label of its cgs unit, as written in file headers (UNI04)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)

        ## The expected label is looked up in LABELS. A named unit missing from that table makes this lookup fail with
        ## a KeyError, so a new named unit cannot be added without deciding on its label.
        assert system.label(name) == LABELS[name]


class TestConversions:
    """UNI05-UNI06: conversions are a multiplication or a division by the unit, exact up to rounding."""

    ## Run this test once for every named unit, as the tests of UNI03 and UNI04 do.
    @pytest.mark.parametrize("name", list(NAMED_UNITS))
    def test_conversion_of_numbers(self, name: str) -> None:
        """Check that a number converts to cgs by multiplication with its unit and back by division (UNI05)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        unit = getattr(system, name)

        ## A unit is NumPy's double-precision number np.float64, a subclass of Python's float: it works wherever a
        ## float does, and it keeps arrays in double precision (see the next test).
        assert isinstance(unit, np.float64)

        ## Two code units of the quantity are two times the unit in cgs, and dividing that cgs value by the unit gives
        ## the two code units back. Multiplying or dividing by 2 only changes the exponent of a double, never its
        ## digits, so both conversions are exact and can be compared with ==.
        assert 2.0 * unit == 2.0 * float(unit)
        assert (2.0 * unit) / unit == 2.0

    ## Run this test for every combination of a named unit and the type of the input array: 13 x 3 = 39 cases. The
    ## types are single and double precision floats and 64-bit integers, as arrays of initial conditions may come.
    @pytest.mark.parametrize("name", list(NAMED_UNITS))
    @pytest.mark.parametrize("dtype", [np.float32, np.float64, np.int64])
    def test_conversion_of_arrays(self, name: str, dtype: type[np.generic]) -> None:
        """Check that arrays convert elementwise, keep their shape and come out in double precision (UNI05).

        The result must be in double precision whatever the precision of the input array.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        unit = getattr(system, name)

        ## A small two-dimensional array of values that every input type represents exactly.
        values = np.array([[1, 2, 3], [4, 5, 6]]).astype(dtype)

        ## Convert the whole array at once, to cgs and back.
        to_cgs = values * unit
        back = to_cgs / unit

        ## Both results keep the shape of the input and are double precision, whatever the input type was.
        for result in (to_cgs, back):
            assert result.shape == values.shape
            assert result.dtype == np.float64

        ## Elementwise: every element of the converted array equals the conversion of that element on its own, as a
        ## double-precision number. np.array_equal compares all elements exactly.
        expected = np.array([[float(value) * float(unit) for value in row] for row in values.tolist()])
        assert np.array_equal(to_cgs, expected)

    ## Hypothesis calls this test many times (100 by default), each time with a value and a named unit drawn from the
    ## strategies below, and searches for a combination that makes it fail. st.floats draws from the whole range of
    ## doubles, including the very large, the very small and the negative; NaN and infinities are excluded, as UNI06
    ## concerns finite values only. st.sampled_from draws one of the given names.
    @given(value=st.floats(allow_nan=False, allow_infinity=False), name=st.sampled_from(list(NAMED_UNITS)))
    def test_round_trip_from_code_units(self, value: float, name: str) -> None:
        """Check that converting from code units to cgs and back reproduces a value to within 2 ulp (UNI06)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        unit = getattr(system, name)

        ## Convert the value in code units to cgs. Hypothesis deliberately draws extreme values, and their conversion
        ## can overflow to infinity; NumPy warns when that happens. Such draws are discarded below, so the warning says
        ## nothing about the unit system: np.errstate(over="ignore") silences it for this one line only.
        with np.errstate(over="ignore"):
            cgs = value * unit

        ## UNI06 holds for values that lie within the range of normal doubles, with a factor of two to spare, in both
        ## systems (see within_range): extreme values can overflow to infinity or lose digits in the other system,
        ## where no conversion can be exact. assume() tells Hypothesis to discard such a draw and try another, instead
        ## of counting it as a failure.
        assume(within_range(value) and within_range(cgs))

        ## And back again: the result may differ from the original by at most 2 ulp, one rounding per operation.
        back = cgs / unit
        assert abs(back - value) <= 2 * math.ulp(value)

    ## The same, starting from a value in cgs.
    @given(value=st.floats(allow_nan=False, allow_infinity=False), name=st.sampled_from(list(NAMED_UNITS)))
    def test_round_trip_from_cgs(self, value: float, name: str) -> None:
        """Check that converting from cgs to code units and back reproduces a value to within 2 ulp (UNI06)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        unit = getattr(system, name)

        ## Convert the value in cgs to code units (silencing NumPy's warning for overflowing draws, as above), check
        ## that both representations lie within the range, and convert it back.
        with np.errstate(over="ignore"):
            code = value / unit
        assume(within_range(value) and within_range(code))
        back = code * unit
        assert abs(back - value) <= 2 * math.ulp(value)


class TestMagneticField:
    """UNI07: the factor 4 pi is absorbed into the magnetic field."""

    def test_magnetic_field_unit(self) -> None:
        """Check that the code unit of the magnetic field is sqrt(4 pi p_u) gauss (UNI07).

        Here p_u is the code unit of pressure. The unit must agree with an exact reference to within 4 ulp.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)

        ## The reference, computed independently at 50 significant digits as in the test of UNI02. The decimal module
        ## has no constant pi, so pi is written out to 50 digits. The code unit of pressure is M / (L T^2), and
        ## Decimal.sqrt() takes the square root at the precision of the context.
        with localcontext() as context:
            context.prec = 50
            pi = Decimal("3.1415926535897932384626433832795028841971693993751")
            pressure = Decimal(MASS) / (Decimal(LENGTH) * Decimal(TIME) ** 2)
            exact = (4 * pi * pressure).sqrt()
        expected = float(exact)  ## the double nearest to the exact value

        ## The unit computed by the unit system rounds pi, the pressure (within 4 ulp, UNI03), the product and the
        ## square root. The square root halves the relative error of its argument, so these roundings together stay
        ## within about 3 ulp; 4 ulp is the bound used throughout the unit system.
        actual = system.magnetic_field
        assert isinstance(actual, np.float64)
        assert abs(actual - expected) <= 4 * math.ulp(expected)

    ## Hypothesis draws field strengths in code units from the whole range of doubles, as in the tests of UNI06.
    @given(field=st.floats(allow_nan=False, allow_infinity=False))
    def test_magnetic_energy_density_agrees(self, field: float) -> None:
        """Check that a field's energy density is the same physical quantity in both systems (UNI07).

        B^2 / (8 pi), with B in gauss, must equal B_code^2 / 2 times the code unit of pressure, to within 4 ulp.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)

        ## Hypothesis's floats are Python floats, whose ** raises an OverflowError for results too large for a double,
        ## where NumPy returns infinity. Converting the drawn field to np.float64 makes every operation below behave
        ## like NumPy's, so an overflow is caught by the assume() further on rather than crashing the test.
        field_code = np.float64(field)

        ## Squares overflow at magnitudes above about 1e154, so far more draws overflow here than in the round trips of
        ## UNI06. NumPy's warnings about them are silenced, as the draws are discarded below.
        with np.errstate(over="ignore"):
            ## The field in gauss, by the conversion of UNI05.
            field_gauss = field_code * system.magnetic_field

            ## The magnetic energy density in erg cm^-3, computed twice: in Gaussian cgs, where the factor 4 pi
            ## appears, and in code units, where it does not, converted to cgs by the code unit of pressure.
            in_gauss = field_gauss**2 / (8 * np.pi)
            in_code_units = field_code**2 / 2 * system.pressure

        ## Only values within the range of normal doubles, in either system, count (see within_range). This also
        ## discards a field of zero, for which both sides are trivially zero.
        assume(all(within_range(x) for x in (field_code, field_gauss, in_gauss, in_code_units)))

        ## Both must describe the same energy density to within 4 ulp. Along the way, the field is rounded in its
        ## conversion and squared, which doubles its relative error; the 4 pi of the unit and the 8 pi of Gaussian
        ## units use the same rounded value of pi, so the error in pi cancels.
        assert abs(in_gauss - in_code_units) <= 4 * math.ulp(in_code_units)


class TestTemperature:
    """UNI08-UNI09: temperature converts from the ratio of pressure to density through the mean molecular weight."""

    ## Hypothesis draws a ratio of pressure to density and a mean molecular weight. The ratio spans 200 orders of
    ## magnitude in code units, far beyond any physical temperature, while every intermediate value of the conversion
    ## stays well inside the range of normal doubles; the whole range of doubles, as in the tests of UNI06, would let
    ## intermediate values underflow even where the result does not. The mean molecular weight spans 0.1 to 10, which
    ## covers fully ionised (about 0.6) to molecular gas (about 2.3) with a wide margin.
    @given(
        p_over_rho=st.floats(min_value=1e-100, max_value=1e100),
        mu=st.floats(min_value=0.1, max_value=10.0),
    )
    def test_temperature_from_pressure_over_density(self, p_over_rho: float, mu: float) -> None:
        """Check that T = mu m_H (p / rho) / k_B for a ratio p / rho in code units (UNI08).

        The mean molecular weight mu is in units of the mass of the hydrogen atom m_H.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        temperature = system.temperature(p_over_rho, mu=mu)

        ## A scalar in gives a scalar out, in double precision like every unit (UNI05).
        assert isinstance(temperature, np.float64)

        ## The reference, computed exactly at 50 digits from the same ingredients: the unit of specific energy (the
        ## unit of p / rho, tested under UNI03) and the constants k_B and m_H (tested under UNI10). This test checks
        ## the formula of UNI08, not the values that go into it.
        with localcontext() as context:
            context.prec = 50
            p_over_rho_cgs = Decimal(p_over_rho) * Decimal(system.specific_energy)
            exact = (
                Decimal(mu) * Decimal(constants.HYDROGEN_MASS) * p_over_rho_cgs / Decimal(constants.BOLTZMANN_CONSTANT)
            )
        expected = float(exact)

        ## The conversion takes four roundings, one per multiplication or division. Each is at most half an ulp of its
        ## own result, but up to one ulp of the final result, since the size of an ulp relative to a value varies by
        ## a factor of two. Four roundings therefore stay within 4 ulp.
        assert abs(temperature - expected) <= 4 * math.ulp(expected)

    ## Hypothesis draws temperatures in kelvin over the same 200 orders of magnitude, and mean molecular weights as
    ## above.
    @given(
        temperature=st.floats(min_value=1e-100, max_value=1e100),
        mu=st.floats(min_value=0.1, max_value=10.0),
    )
    def test_pressure_over_density_from_temperature(self, temperature: float, mu: float) -> None:
        """Check that the conversion from temperature to p / rho in code units inverts the first (UNI08).

        The two conversions applied one after the other must reproduce the value to within rounding.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)

        ## From temperature to p / rho in code units, and back.
        p_over_rho = system.pressure_over_density(temperature, mu=mu)
        back = system.temperature(p_over_rho, mu=mu)

        ## Each conversion takes four roundings. Two of the eight do not count: both conversions compute the same
        ## product mu m_H, which one divides by and the other multiplies with, so its rounding cancels. The unit of
        ## specific energy cancels in the same way. That leaves six roundings, within 6 ulp (see the test above).
        assert abs(back - temperature) <= 6 * math.ulp(temperature)

    ## Run this test once for each direction of the conversion; getattr picks the method by its name.
    @pytest.mark.parametrize("conversion", ["temperature", "pressure_over_density"])
    def test_mean_molecular_weight_per_cell(self, conversion: str) -> None:
        """Check that the mean molecular weight may be an array, applied cell by cell (UNI08).

        The array has the shape of the values to convert.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        convert = getattr(system, conversion)

        ## A small two-dimensional field of values, and a mean molecular weight that differs in every cell, as in gas
        ## of varying metallicity and ionisation.
        values = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        mu = np.array([[0.6, 0.7, 0.8], [1.0, 1.2, 1.3]])

        ## The whole field converted at once keeps its shape and is double precision.
        result = convert(values, mu=mu)
        assert result.shape == values.shape
        assert result.dtype == np.float64

        ## Each cell must be converted with its own mean molecular weight: every element equals the conversion of that
        ## element on its own, with the mean molecular weight of that cell. .flat runs through the elements of an
        ## array in order, zip pairs each value with its mu (strict=True refuses arrays of different sizes), and
        ## reshape gives the list of results the shape of the field again. np.array_equal compares exactly, as the
        ## same arithmetic happens in both cases.
        cells = [convert(value, mu=mu_cell) for value, mu_cell in zip(values.flat, mu.flat, strict=True)]
        expected = np.array(cells).reshape(values.shape)
        assert np.array_equal(result, expected)

    ## Run this test for each direction of the conversion and each invalid value, 2 x 5 = 10 cases, as the test of
    ## invalid code units does.
    @pytest.mark.parametrize("conversion", ["temperature", "pressure_over_density"])
    @pytest.mark.parametrize("value", [0.0, -1.0, math.inf, -math.inf, math.nan])
    def test_invalid_mean_molecular_weight_is_refused(self, conversion: str, value: float) -> None:
        """Check that a mean molecular weight that is not positive and finite is refused (UNI08)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        convert = getattr(system, conversion)

        ## The invalid value is refused on its own, and as one cell among valid ones: a single bad cell must not
        ## slip through. The error message must say what is wrong.
        with pytest.raises(ValueError, match="mean molecular weight"):
            convert(1.0, mu=value)
        with pytest.raises(ValueError, match="mean molecular weight"):
            convert(np.array([1.0, 1.0]), mu=np.array([0.6, value]))

    ## Run this test once for each direction of the conversion.
    @pytest.mark.parametrize("conversion", ["temperature", "pressure_over_density"])
    def test_default_mean_molecular_weight(self, conversion: str) -> None:
        """Check that a default mean molecular weight is used when a conversion gives none (UNI09).

        The default is the one given when the unit system was created.
        """
        ## The same unit system, once with a default mean molecular weight and once without.
        with_default = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)
        without_default = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        convert = getattr(with_default, conversion)

        ## The default is kept as given, and a unit system created without one has none.
        assert with_default.mu == 0.6
        assert without_default.mu is None

        ## A conversion without mu uses the default: exactly as if 0.6 had been given to it.
        assert convert(2.0) == convert(2.0, mu=0.6)

        ## A mu given to the conversion takes precedence over the default: the result is that of a unit system without
        ## a default, given the same mu.
        assert convert(2.0, mu=1.3) == getattr(without_default, conversion)(2.0, mu=1.3)

    ## Run this test for each invalid value, as the test of invalid code units does.
    @pytest.mark.parametrize("value", [0.0, -1.0, math.inf, -math.inf, math.nan])
    def test_invalid_default_mean_molecular_weight_is_refused(self, value: float) -> None:
        """Check that a default mean molecular weight that is not positive and finite is refused at creation (UNI09)."""
        with pytest.raises(ValueError, match="mean molecular weight"):
            units.UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=value)

    ## Run this test once for each direction of the conversion.
    @pytest.mark.parametrize("conversion", ["temperature", "pressure_over_density"])
    def test_missing_mean_molecular_weight_is_refused(self, conversion: str) -> None:
        """Check that a temperature conversion without any mean molecular weight is refused (UNI09).

        Without a value given to the conversion and without a default, no value may be assumed silently.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        convert = getattr(system, conversion)

        ## The error must say what is missing.
        with pytest.raises(ValueError, match="mean molecular weight"):
            convert(2.0)


class TestRecords:
    """UNI12-UNI14: a unit system is fixed once created, comparable, and recorded exactly in files."""

    ## Run this test for every defining value, and for a name that is not an attribute at all.
    @pytest.mark.parametrize("name", ["length", "mass", "time", "mu", "new_attribute"])
    def test_cannot_be_changed(self, name: str) -> None:
        """Check that changing a unit system after its creation is refused (UNI12)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)

        ## setattr(system, "mass", 1.0) is the same as system.mass = 1.0, and delattr(system, "mass") as del
        ## system.mass. A frozen dataclass refuses both with a FrozenInstanceError, for its fields and for any new
        ## attribute alike.
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(system, name, 1.0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            delattr(system, name)

        ## The refused change has left the unit system as it was.
        assert system == units.UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)

    def test_equality(self) -> None:
        """Check that two unit systems are equal if and only if their defining values are equal (UNI13).

        The defining values are the three code units and the default mean molecular weight.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)

        ## Two unit systems created from the same values are equal, though they are different objects. Equal objects
        ## must also have equal hashes, so that a unit system can serve as the key of a dictionary.
        same = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)
        assert same is not system
        assert same == system
        assert hash(same) == hash(system)

        ## A difference in any one defining value makes them unequal: each code unit changed by a single ulp, the
        ## default mean molecular weight changed, and no default at all. math.nextafter(x, math.inf) is the next
        ## double above x, the smallest possible change.
        changes = [
            {"length": math.nextafter(LENGTH, math.inf)},
            {"mass": math.nextafter(MASS, math.inf)},
            {"time": math.nextafter(TIME, math.inf)},
            {"mu": 1.3},
            {"mu": None},
        ]
        for change in changes:
            ## dataclasses.replace creates a new unit system with the values of the old one, except those it is given.
            ## The new one is created, and checked, as any other: the old one stays as it is (UNI12).
            other = dataclasses.replace(system, **change)
            assert other != system, f"change {change}"

    ## Hypothesis draws code units from every positive, finite double, the very large and very small included, and a
    ## default mean molecular weight that is either absent (None) or a positive, finite double. st.one_of draws from
    ## one of the strategies it is given.
    @given(
        length=st.floats(min_value=0.0, exclude_min=True, allow_infinity=False),
        mass=st.floats(min_value=0.0, exclude_min=True, allow_infinity=False),
        time=st.floats(min_value=0.0, exclude_min=True, allow_infinity=False),
        mu=st.one_of(st.none(), st.floats(min_value=0.0, exclude_min=True, allow_infinity=False)),
    )
    def test_record_round_trip(self, length: float, mass: float, time: float, mu: float | None) -> None:
        """Check that a unit system created again from its record is equal to it (UNI14).

        Every value must be identical bit for bit.
        """
        system = units.UnitSystem(length=length, mass=mass, time=time, mu=mu)
        record = system.to_record()

        ## The record consists of plain values only, Python's own floats and strings, which any file format can
        ## store: HDF5 attributes, TOML, JSON. type() rather than isinstance(), since np.float64 is a subclass of
        ## float but not a plain value. A missing default is left out rather than recorded as None, which HDF5
        ## attributes cannot hold.
        assert all(type(value) in (float, str) for value in record.values())
        assert ("mu" in record) == (mu is not None)

        ## Write the record as text and read it back, as a file would. JSON writes each float with the shortest
        ## digits that read back as the same double, so text is no obstacle to exactness.
        stored = json.loads(json.dumps(record))

        ## The unit system created from the stored record is equal to the original (UNI13), and every defining value
        ## is identical bit for bit: float.hex() writes the exact bits of a double, sign, exponent and digits.
        restored = units.UnitSystem.from_record(stored)
        assert restored == system
        for name in ("length", "mass", "time"):
            assert float(getattr(restored, name)).hex() == float(getattr(system, name)).hex()
        if mu is not None:
            assert restored.mu is not None and float(restored.mu).hex() == float(mu).hex()

    def test_record_names_sources(self) -> None:
        """Check that the record names the sources of the constants (UNI14).

        The sources are CODATA 2022, AME 2020, and the IAU resolutions of 2012 and 2015.
        """
        record = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME).to_record()

        ## The sources are one line of text in the record, the one the constants module states. The isinstance check
        ## also tells the type checker that the value is a string, which the record's type leaves open.
        sources = record["sources"]
        assert isinstance(sources, str)
        assert sources == constants.SOURCES
        for source in ("CODATA 2022", "AME 2020", "IAU 2012", "IAU 2015"):
            assert source in sources


class TestDimensionlessSimulations:
    """UNI15-UNI17: simulations without a unit system, and the independence of results from the unit system."""

    @NEEDS_DRIVER
    def test_simulation_without_unit_system_runs(self) -> None:
        """Check that a simulation without a unit system runs, with every quantity in code units (UNI15)."""
        pytest.fail("Not written yet.")

    @NEEDS_DRIVER
    def test_module_needing_units_is_refused(self) -> None:
        """Check that a module needing physical constants is refused in a dimensionless simulation (UNI16).

        The refusal comes at set-up, before the run starts, and names the module.
        """
        pytest.fail("Not written yet.")

    @NEEDS_DRIVER
    def test_results_independent_of_unit_system(self) -> None:
        """Check that a problem posed in code units gives the same state with any unit system or none (UNI17).

        The state in code units must be identical bit for bit.
        """
        pytest.fail("Not written yet.")


class TestDependencies:
    """UNI18: the unit system needs nothing beyond the standard library and NumPy."""

    @NOT_WRITTEN
    def test_no_further_dependencies(self) -> None:
        """Check that importing the unit system imports no third-party package other than NumPy (UNI18)."""
        pytest.fail("Not written yet.")
