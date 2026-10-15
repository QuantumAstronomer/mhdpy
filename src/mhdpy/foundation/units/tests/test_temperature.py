"""Tests of the temperature conversions through the mean molecular weight (UNI08-UNI09)."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from mhdpy.foundation.units import constants
from mhdpy.foundation.units.system import UnitSystem
from mhdpy.foundation.units.tests.reference import LENGTH, MASS, TIME


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
    def test_temperature_from_pressure_over_density(self, system: UnitSystem, p_over_rho: float, mu: float) -> None:
        """Check that T = mu m_H (p / rho) / k_B for a ratio p / rho in code units (UNI08).

        The mean molecular weight mu is in units of the mass of the hydrogen atom m_H.
        """
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
    def test_pressure_over_density_from_temperature(self, system: UnitSystem, temperature: float, mu: float) -> None:
        """Check that the conversion from temperature to p / rho in code units inverts the first (UNI08).

        The two conversions applied one after the other must reproduce the value to within 2 ulp.
        """
        ## From temperature to p / rho in code units, and back.
        p_over_rho = system.pressure_over_density(temperature, mu=mu)
        back = system.temperature(p_over_rho, mu=mu)

        ## Both conversions use the same factor, mu m_H u / k_B, one dividing by it and the other multiplying, so its
        ## own rounding cancels. That leaves one rounding per conversion, within 2 ulp (see the test above).
        assert abs(back - temperature) <= 2 * math.ulp(temperature)

    ## Run this test once for each direction of the conversion; getattr picks the method by its name.
    @pytest.mark.parametrize("conversion", ["temperature", "pressure_over_density"])
    def test_mean_molecular_weight_per_cell(self, system: UnitSystem, conversion: str) -> None:
        """Check that the mean molecular weight may be an array, applied cell by cell (UNI08).

        The array has the shape of the values to convert.
        """
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
    def test_invalid_mean_molecular_weight_is_refused(self, system: UnitSystem, conversion: str, value: float) -> None:
        """Check that a mean molecular weight that is not positive and finite is refused (UNI08)."""
        convert = getattr(system, conversion)

        ## The invalid value is refused on its own, and as one cell among valid ones: a single bad cell must not
        ## slip through. The error message must say what is wrong.
        with pytest.raises(ValueError, match="mean molecular weight"):
            convert(1.0, mu=value)
        with pytest.raises(ValueError, match="mean molecular weight"):
            convert(np.array([1.0, 1.0]), mu=np.array([0.6, value]))

    ## Run this test once for each direction of the conversion.
    @pytest.mark.parametrize("conversion", ["temperature", "pressure_over_density"])
    def test_default_mean_molecular_weight(
        self, system: UnitSystem, system_with_default: UnitSystem, conversion: str
    ) -> None:
        """Check that a default mean molecular weight is used when a conversion gives none (UNI09).

        The default is the one given when the unit system was created.
        """
        ## The same unit system, once with a default mean molecular weight of 0.6 and once without (see conftest.py).
        convert = getattr(system_with_default, conversion)

        ## The default is kept as given, and a unit system created without one has none.
        assert system_with_default.mu == 0.6
        assert system.mu is None

        ## A conversion without mu uses the default: exactly as if 0.6 had been given to it.
        assert convert(2.0) == convert(2.0, mu=0.6)

        ## A mu given to the conversion takes precedence over the default: the result is that of a unit system without
        ## a default, given the same mu.
        assert convert(2.0, mu=1.3) == getattr(system, conversion)(2.0, mu=1.3)

    ## Run this test for each invalid value, as the test of invalid code units does.
    @pytest.mark.parametrize("value", [0.0, -1.0, math.inf, -math.inf, math.nan])
    def test_invalid_default_mean_molecular_weight_is_refused(self, value: float) -> None:
        """Check that a default mean molecular weight that is not positive and finite is refused at creation (UNI09)."""
        with pytest.raises(ValueError, match="mean molecular weight"):
            UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=value)

    ## Run this test once for each direction of the conversion.
    @pytest.mark.parametrize("conversion", ["temperature", "pressure_over_density"])
    def test_missing_mean_molecular_weight_is_refused(self, system: UnitSystem, conversion: str) -> None:
        """Check that a temperature conversion without any mean molecular weight is refused (UNI09).

        Without a value given to the conversion and without a default, no value may be assumed silently.
        """
        convert = getattr(system, conversion)

        ## The error must say what is missing.
        with pytest.raises(ValueError, match="mean molecular weight"):
            convert(2.0)
