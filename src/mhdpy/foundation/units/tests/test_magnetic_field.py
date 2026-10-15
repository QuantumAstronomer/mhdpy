"""Tests of the unit of the magnetic field, with the factor 4 pi absorbed (UNI07)."""

import math
from decimal import Decimal, localcontext

import numpy as np
from hypothesis import assume, given
from hypothesis import strategies as st

from mhdpy.foundation.units.system import UnitSystem
from mhdpy.foundation.units.tests.reference import LENGTH, MASS, PI, TIME, within_range


class TestMagneticField:
    """UNI07: the factor 4 pi is absorbed into the magnetic field."""

    def test_magnetic_field_unit(self, system: UnitSystem) -> None:
        """Check that the code unit of the magnetic field is sqrt(4 pi p_u) gauss (UNI07).

        Here p_u is the code unit of pressure. The unit must agree with an exact reference to within 4 ulp.
        """
        ## The reference, computed independently at 50 significant digits as in the test of UNI02. The code unit of
        ## pressure is M / (L T^2), and Decimal.sqrt() takes the square root at the precision of the context.
        with localcontext() as context:
            context.prec = 50
            pressure = Decimal(MASS) / (Decimal(LENGTH) * Decimal(TIME) ** 2)
            exact = (4 * PI * pressure).sqrt()
        expected = float(exact)  ## the double nearest to the exact value

        ## The unit computed by the unit system rounds pi, the pressure (within 4 ulp, UNI03), the product and the
        ## square root. The square root halves the relative error of its argument, so these roundings together stay
        ## within about 3 ulp; 4 ulp is the bound used throughout the unit system.
        actual = system.magnetic_field
        assert isinstance(actual, np.float64)
        assert abs(actual - expected) <= 4 * math.ulp(expected)

    ## Hypothesis draws field strengths in code units from the whole range of doubles, as in the tests of UNI06.
    @given(field=st.floats(allow_nan=False, allow_infinity=False))
    def test_magnetic_energy_density_agrees(self, system: UnitSystem, field: float) -> None:
        """Check that a field's energy density is the same physical quantity in both systems (UNI07).

        B^2 / (8 pi), with B in gauss, must equal B_code^2 / 2 times the code unit of pressure, to within 4 ulp.
        """
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
