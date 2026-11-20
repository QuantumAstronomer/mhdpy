"""Tests of the physical and astronomical constants."""

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
