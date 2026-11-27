"""Tests of the code units of a run, the named units and the constants in code units."""

import math
import sys
from dataclasses import FrozenInstanceError, fields
from typing import Any

import pytest

from mhdpy.infrastructure import constants
from mhdpy.infrastructure.units import NAMED_UNITS, NamedUnit, Units


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


class TestNamedUnits:
    """Tests that the table holds the named units with their values in cgs, and that factors convert into code units."""

    def test_table(self) -> None:
        """Checks UNIT04.

        The table holds the named units of the grid, the floors, cooling, conduction and the production problem.
        """

        ## the dimension of each, by the exponents of mass, length, time and temperature
        dimensions = {
            "cm":           (0, 1, 0, 0),
            "pc":           (0, 1, 0, 0),
            "s":            (0, 0, 1, 0),
            "yr":           (0, 0, 1, 0),
            "Myr":          (0, 0, 1, 0),
            "cm/s":         (0, 1, -1, 0),
            "km/s":         (0, 1, -1, 0),
            "g/cm^3":       (1, -3, 0, 0),
            "cm^-3":        (0, -3, 0, 0),
            "K":            (0, 0, 0, 1),
            "erg/cm^3":     (1, -1, -2, 0),
        }
        for name, dimension in dimensions.items():
            assert NAMED_UNITS[name].dimension == dimension

        ## the value in cgs of each, the astronomical ones left to UNIT05
        values = {"cm": 1, "s": 1, "cm/s": 1, "km/s": 1e5, "g/cm^3": 1, "cm^-3": 1, "K": 1, "erg/cm^3": 1}
        for name, value in values.items():
            assert NAMED_UNITS[name].value == value


    def test_astronomical(self) -> None:
        """Checks UNIT05.

        The parsec, the year and the megayear take their values in cgs from the constants.
        """

        assert NAMED_UNITS["pc"].value == constants.PARSEC
        assert NAMED_UNITS["yr"].value == constants.JULIAN_YEAR
        ## a million Julian years, which the float holds exactly
        assert NAMED_UNITS["Myr"].value == 1e6 * constants.JULIAN_YEAR


    def test_factor(self) -> None:
        """Checks UNIT06.

        The factor of a named unit is its value in cgs divided by the code unit of its dimension.
        """

        ## powers of two, whose products and quotients are exact
        units = Units(mass = 2.0, length = 4.0, time = 8.0)

        ## the code unit of velocity is 4 / 8 cm/s, so that 1 km/s is 2e5 of them
        assert units.factor("km/s") == 2e5
        ## that of density 2 / 4**3 g/cm^3, so that 1 g/cm^3 is 32 of them
        assert units.factor("g/cm^3") == 32.0
        ## that of pressure 2 / (4 * 8**2) erg/cm^3, so that 1 erg/cm^3 is 128 of them
        assert units.factor("erg/cm^3") == 128.0
        ## the kelvin is the code unit of temperature
        assert units.factor("K") == 1.0

        ## a parsec in code units of a parsec is 1, as the value divided by itself
        assert Units(length = constants.PARSEC).factor("pc") == 1.0


    def test_unknown_unit(self) -> None:
        """Checks UNIT07.

        A name that the table does not hold is refused with a ValueError that names the units of the table.
        """

        ## a misspelt unit
        with pytest.raises(ValueError) as error:
            Units().factor("km/sec")

        ## the message lists the units of the table
        assert ", ".join(NAMED_UNITS) in str(error.value)


class TestConstants:
    """Tests that Boltzmann's constant and the three masses come in code units."""

    def test_constants(self) -> None:
        """Checks UNIT08.

        Each constant is its value in cgs divided by the code unit of its dimension.
        """

        ## powers of two, whose products and quotients are exact
        units = Units(mass = 2.0, length = 4.0, time = 8.0)

        ## erg/K has the code unit 2 * 4**2 / 8**2 = 1/2 erg/K
        assert units.boltzmann == 2 * constants.BOLTZMANN

        ## a mass has the code unit 2 g
        assert units.proton_mass == constants.PROTON_MASS / 2
        assert units.electron_mass == constants.ELECTRON_MASS / 2
        assert units.atomic_mass_unit == constants.ATOMIC_MASS_UNIT / 2


class TestDeclaration:
    """Tests that the units are the frozen declaration by which the parameters read the table units."""

    def test_table_name(self) -> None:
        """Checks UNIT11.

        The class variable table names the table units, and is no field.
        """

        assert Units.table == "units"
        ## a class variable, which the constructor does not take
        assert "table" not in [field.name for field in fields(Units)]


    def test_fields(self) -> None:
        """Checks UNIT12.

        The base units are floats that name their units in their metadata, and the table holds those units.
        """

        by_name = {field.name: field for field in fields(Units)}
        for name, unit in [("mass", "g"), ("length", "cm"), ("time", "s")]:

            ## a float, by its annotation and by its default
            assert by_name[name].type is float
            assert type(by_name[name].default) is float

            ## a unit that the table holds
            assert by_name[name].metadata["unit"] == unit
            assert unit in NAMED_UNITS

        ## the gram, the one of them that UNIT04 does not name
        assert NAMED_UNITS["g"] == NamedUnit(1.0, (1, 0, 0, 0))


    def test_frozen(self) -> None:
        """Checks UNIT13.

        The base units, a named unit and the table refuse every change once built.
        """

        ## an assignment to a field, which a frozen dataclass refuses
        with pytest.raises(FrozenInstanceError):
            setattr(Units(), "mass", 2.0)
        with pytest.raises(FrozenInstanceError):
            setattr(NAMED_UNITS["g"], "value", 2.0)

        ## a new unit in the table, which a read-only mapping refuses
        table: Any = NAMED_UNITS
        with pytest.raises(TypeError):
            table["m"] = NamedUnit(100.0, (0, 1, 0, 0))


class TestVerification:
    """Tests that the units convert without loss under cgs, and keep the temperature in kelvin under any base units."""

    def test_cgs(self) -> None:
        """Checks UNIT09.

        Under the default base units, every factor and every constant in code units is its value in cgs, exactly.
        """

        units = Units()

        ## every unit of the table, as later briefs add theirs
        for name, unit in NAMED_UNITS.items():
            assert units.factor(name) == unit.value

        assert units.boltzmann == constants.BOLTZMANN
        assert units.proton_mass == constants.PROTON_MASS
        assert units.electron_mass == constants.ELECTRON_MASS
        assert units.atomic_mass_unit == constants.ATOMIC_MASS_UNIT


    ## every combination of the base units over the ranges of UNIT10, as stacked marks run each as a case of its own
    ## the decimal logarithms of the time from -11 to 25, of the length from 0 to 25 and of the mass from -30 to 75
    @pytest.mark.parametrize("log_time", range(-11, 26, 6))
    @pytest.mark.parametrize("log_length", range(0, 26, 5))
    @pytest.mark.parametrize("log_mass", range(-30, 76, 15))
    def test_temperature(self, log_mass: int, log_length: int, log_time: int) -> None:
        """Checks UNIT10.

        The temperature m_u p / (rho k_B) in code units equals that in cgs over the ranges of base units, within 32 eps.
        """

        ## a pressure and a density of the corona of the production problem, in cgs
        pressure, density = 3e-13, 1e-27
        temperature = constants.ATOMIC_MASS_UNIT * pressure / (density * constants.BOLTZMANN)

        units = Units(mass = 10.0**log_mass, length = 10.0**log_length, time = 10.0**log_time)

        ## the same formula, from the values and the constants in code units
        code_pressure = pressure * units.factor("erg/cm^3")
        code_density = density * units.factor("g/cm^3")
        code_temperature = units.atomic_mass_unit * code_pressure / (code_density * units.boltzmann)

        ## within k eps with k = 2**5, relative to the larger of the two
        assert math.isclose(code_temperature, temperature, rel_tol = 2**5 * sys.float_info.epsilon)
