"""Tests of the conversions between code units and cgs (UNI05-UNI06)."""

import math

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from mhdpy.foundation import units
from mhdpy.foundation.tests.units.reference import NAMED_UNITS, within_range


class TestConversions:
    """UNI05-UNI06: conversions are a multiplication or a division by the unit, exact up to rounding."""

    ## Run this test once for every named unit, as the tests of UNI03 and UNI04 do.
    @pytest.mark.parametrize("name", list(NAMED_UNITS))
    def test_conversion_of_numbers(self, system: units.UnitSystem, name: str) -> None:
        """Check that a number converts to cgs by multiplication with its unit and back by division (UNI05)."""
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
    def test_conversion_of_arrays(self, system: units.UnitSystem, name: str, dtype: type[np.generic]) -> None:
        """Check that arrays convert elementwise, keep their shape and come out in double precision (UNI05).

        The result must be in double precision whatever the precision of the input array.
        """
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
    def test_round_trip_from_code_units(self, system: units.UnitSystem, value: float, name: str) -> None:
        """Check that converting from code units to cgs and back reproduces a value to within 2 ulp (UNI06)."""
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
    def test_round_trip_from_cgs(self, system: units.UnitSystem, value: float, name: str) -> None:
        """Check that converting from cgs to code units and back reproduces a value to within 2 ulp (UNI06)."""
        unit = getattr(system, name)

        ## Convert the value in cgs to code units (silencing NumPy's warning for overflowing draws, as above), check
        ## that both representations lie within the range, and convert it back.
        with np.errstate(over="ignore"):
            code = value / unit
        assume(within_range(value) and within_range(code))
        back = code * unit
        assert abs(back - value) <= 2 * math.ulp(value)
