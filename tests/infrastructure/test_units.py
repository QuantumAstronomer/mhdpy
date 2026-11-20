"""Tests of the code units of a run, the named units and the constants in code units."""

import math

import pytest

from mhdpy.infrastructure.units import Units


class TestCodeUnits:
    """Tests that the base units of a run give the code unit of every dimension, and that faulty ones are refused."""

    def test_base_units(self) -> None:
        """Checks UNIT01.

        The base units are the fields mass, length and time, each 1 by default.
        """

        ## by default those of cgs
        units = Units()
        assert (units.mass, units.length, units.time) == (1, 1, 1)
        ## or those of the run, each by its name
        units = Units(mass = 2.0, length = 4.0, time = 8.0)
        assert (units.mass, units.length, units.time) == (2.0, 4.0, 8.0)


    ## every faulty value for every base unit, as stacked marks run each pair as a case of its own
    ## the numbers that are no scale: zero of either sign, a negative number, both infinities and a NaN
    @pytest.mark.parametrize("value", [.0, -.0, -1., math.inf, -math.inf, math.nan])
    ## each base unit in turn, the other two kept at their defaults
    @pytest.mark.parametrize("name", ["mass", "length", "time"])
    def test_invalid_base_unit(self, name: str, value: float) -> None:
        """Checks UNIT02.

        A base unit that is not a positive and finite number is refused with a ValueError naming it and its value.
        """

        with pytest.raises(ValueError) as error:
            Units(**{name: value})

        ## the error message names the invalid base unit and its value
        assert name in str(error.value)
        assert repr(value) in str(error.value)


    def test_code_units(self) -> None:
        """Checks UNIT03.

        The code unit of a dimension (a, b, c, d) is M0**a L0**b T0**c in cgs, and the kelvin for temperature.
        """

        ## powers of two, whose products and quotients are exact
        units = Units(mass = 2.0, length = 4.0, time = 8.0)

        ## each exponent applies to its own base unit
        assert units.code_unit((1, 0, 0, 0)) == 2.0
        assert units.code_unit((0, 1, 0, 0)) == 4.0
        assert units.code_unit((0, 0, 1, 0)) == 8.0

        ## temperature keeps the kelvin
        assert units.code_unit((0, 0, 0, 1)) == 1.0

        ## erg/K, the dimension of Boltzmann's constant, 2 * 4**2 / 8**2
        assert units.code_unit((1, 2, -2, -1)) == 0.5
