"""Tests of the physical and astronomical constants."""

import math
import sys

from mhdpy.infrastructure import constants


class TestPhysical:
    """Tests that Boltzmann's constant and the three masses hold the values of their sources in cgs."""

    def test_boltzmann(self) -> None:
        """Checks CONST01.

        Boltzmann's constant is the value in erg/K that the SI fixes.
        """

        ## exactly, as the same digits round to the same double
        assert constants.BOLTZMANN == 1.380649e-16


    def test_proton_mass(self) -> None:
        """Checks CONST02.

        The mass of the proton is the value in g of CODATA 2022.
        """

        assert constants.PROTON_MASS == 1.67262192595e-24


    def test_electron_mass(self) -> None:
        """Checks CONST03.

        The mass of the electron is the value in g of CODATA 2022.
        """

        assert constants.ELECTRON_MASS == 9.1093837139e-28


    def test_atomic_mass_unit(self) -> None:
        """Checks CONST04.

        The atomic mass unit is the value in g of CODATA 2022.
        """

        assert constants.ATOMIC_MASS_UNIT == 1.66053906892e-24


class TestAstronomical:
    """Tests that the astronomical unit, the parsec and the Julian year hold the values of their definitions in CGS."""


    def test_astronomical_unit(self) -> None:
        """Checks CONST05.

        The astronomical unit is a float equal to 149 597 870 700 m, the length that the IAU fixes, in cm.
        """

        ## the metres of the IAU in centimetres, an integer that the float holds exactly
        assert constants.ASTRONOMICAL_UNIT == 149_597_870_700 * 100
        ## a float, as an integer would pass the comparison too
        assert type(constants.ASTRONOMICAL_UNIT) is float


    def test_parsec(self) -> None:
        """Checks CONST06.

        The parsec is a float equal to 648 000 / pi au, as the IAU defines it, to within twice the machine epsilon.
        """

        ## the definition, which other orders of the operations move by one unit in the last place
        parsec = 648_000 / math.pi * constants.ASTRONOMICAL_UNIT
        ## within twice the machine epsilon, 2**-52, relative to the larger of the two values
        assert math.isclose(constants.PARSEC, parsec, rel_tol = 2 * sys.float_info.epsilon)
        ## a float, as an integer would pass the comparison too
        assert type(constants.PARSEC) is float


    def test_julian_year(self) -> None:
        """Checks CONST07.

        The Julian year is a float equal to 365.25 days of 86 400s.
        """

        ## the seconds of the year, an integer that the float holds exactly
        assert constants.JULIAN_YEAR == 31_557_600
        ## a float, as an integer would pass the comparison too
        assert type(constants.JULIAN_YEAR) is float
