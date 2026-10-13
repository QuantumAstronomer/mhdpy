"""Tests of the definition of the unit system: three code units and the units derived from them (UNI01-UNI04)."""

import itertools
import math
from decimal import Decimal, localcontext

import pytest

from mhdpy.foundation import units
from mhdpy.foundation.tests.units.reference import CODE_UNITS, LABELS, LENGTH, MASS, NAMED_UNITS, TIME


class TestDefinition:
    """UNI01-UNI04: a unit system is defined by three code units, from which every other unit derives."""

    ## Run this test once for each code unit. Each name in the list becomes a separate test case, reported for example
    ## as test_defined_by_three_code_units[mass], so a failure names the unit that was not kept.
    @pytest.mark.parametrize("name", ["length", "mass", "time"])
    def test_defined_by_three_code_units(self, name: str) -> None:
        """Check that a unit system keeps its three defining code units exactly as given (UNI01)."""
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
        ## Start from the valid code units and replace the one under test by the invalid value.
        arguments = CODE_UNITS | {name: value}

        ## Creating the unit system must raise a ValueError. The match argument is searched for in the error message,
        ## so the test also checks that the message names the offending unit: an error about "mass" when the length
        ## is wrong would fail it.
        with pytest.raises(ValueError, match=name):
            units.UnitSystem(**arguments)

    def test_unit_from_dimensions(self, system: units.UnitSystem) -> None:
        """Check that the unit of dimensions L^a M^b T^c is the code units' product to those powers (UNI02).

        The product must agree to within 4 ulp, for integer and half-integer exponents alike.
        """
        ## All exponents from -4 to 4 in steps of 1/2: integers and half-integers, as the requirement asks.
        exponents = [k / 2 for k in range(-8, 9)]

        ## The reference, computed independently with Python's decimal module at 50 significant digits. Decimal(LENGTH)
        ## is the exact value of the double LENGTH, and powers and products are rounded only at the 50th digit, so the
        ## reference is exact for any comparison in double precision. localcontext() sets the precision for this block
        ## only, without affecting decimal arithmetic elsewhere. The 17 powers of each code unit are computed once,
        ## before the loop: fractional powers are slow in the decimal module, and computing them for every combination
        ## took about a second.
        with localcontext() as context:
            context.prec = 50
            powers = {name: {e: Decimal(value) ** Decimal(e) for e in exponents} for name, value in CODE_UNITS.items()}

            ## Every combination of three exponents, 17^3 = 4913 in all. itertools.product(exponents, repeat=3) gives
            ## each triplet (length, mass, time) once. Checking them all, unlike a random sample, cannot miss the one
            ## combination where the error is largest.
            for length, mass, time in itertools.product(exponents, repeat=3):
                exact = powers["length"][length] * powers["mass"][mass] * powers["time"][time]
                expected = float(exact)  ## the double nearest to the exact value

                ## math.ulp(x) is the gap between x and the next larger double, the "unit in the last place". Three
                ## powers (about 1 ulp each) and two products (1/2 ulp each) give a bound of 4 ulp. The message after
                ## the comma is shown when the assert fails, and names the exponents of the failing combination.
                actual = system.unit(length=length, mass=mass, time=time)
                assert abs(actual - expected) <= 4 * math.ulp(expected), f"exponents {length}, {mass}, {time}"

    ## Run this test once for every named unit. Each key of NAMED_UNITS becomes a separate test case, reported for
    ## example as test_named_units_follow_from_dimensions[density].
    @pytest.mark.parametrize("name", list(NAMED_UNITS))
    def test_named_units_follow_from_dimensions(self, system: units.UnitSystem, name: str) -> None:
        """Check that every named unit equals the unit computed from its dimensions, to within 4 ulp (UNI03)."""
        named = getattr(system, name)

        ## The same unit from its dimensions through the general rule of UNI02, which is tested on its own.
        from_dimensions = system.unit(**NAMED_UNITS[name])

        ## Both must agree to within 4 ulp, the tolerance of UNI02.
        assert abs(named - from_dimensions) <= 4 * math.ulp(from_dimensions)

    ## Run this test once for every named unit: those of UNI03, and the magnetic field of UNI07, whose unit is not a
    ## product of base units and so is not in NAMED_UNITS.
    @pytest.mark.parametrize("name", [*NAMED_UNITS, "magnetic_field"])
    def test_named_unit_labels(self, system: units.UnitSystem, name: str) -> None:
        """Check that every named unit has the label of its cgs unit, as written in file headers (UNI04)."""
        ## The expected label is looked up in LABELS. A named unit missing from that table makes this lookup fail with
        ## a KeyError, so a new named unit cannot be added without deciding on its label.
        assert system.label(name) == LABELS[name]
