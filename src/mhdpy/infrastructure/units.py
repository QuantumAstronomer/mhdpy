"""The code units of a run, from its base units in cgs, with the named units and the constants in code units."""

import math
from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import ClassVar, Final

from mhdpy.infrastructure import constants


@dataclass(frozen = True)
class NamedUnit:
    """A unit that a declaration may name, by its value in cgs and its dimension.

    Parameters
    ====================================================================================================================
    value : float
        The value of the unit in cgs.
    dimension : tuple[int, int, int, int]
        The exponents of mass, length, time and temperature, as (0, 1, -1, 0) for a velocity.

    Implements UNIT04.
    """

    value: float
    dimension: tuple[int, int, int, int]


@dataclass(frozen = True)
class Units:
    """The code units of a run, from its base units of mass, length and time in cgs.

    Parameters
    ====================================================================================================================
    mass : float (default = 1.0)
        The code unit of mass in grams.
    length : float (default = 1.0)
        The code unit of length in centimeters.
    time : float (default = 1.0)
        The code unit of time in seconds.

    Raises
    ====================================================================================================================
    ValueError
        If a base unit is not a positive and finite number.

    Implements UNIT01 and UNIT12.
    """

    ## the table of the inputs that holds the base units (UNIT11)
    table: ClassVar[str] = "units"

    mass: float   = field(default = 1.0, metadata = {"unit": "g"})
    length: float = field(default = 1.0, metadata = {"unit": "cm"})
    time: float   = field(default = 1.0, metadata = {"unit": "s"})


    def __post_init__(self) -> None:
        """Refuse a base unit that is not a positive and finite number.

        Raises
        ================================================================================================================
        ValueError
            If a base unit is zero, negative, infinite or NaN, with a message that names the field and its value.

        Implements UNIT02.
        """

        for name, value in [("mass", self.mass), ("length", self.length), ("time", self.time)]:
            ## a NaN fails the comparison, as every comparison with it is false
            if not (value > 0 and math.isfinite(value)):
                raise ValueError(f"the base unit {name} must be positive and finite, not {value!r}")


    @cached_property
    def boltzmann(self) -> float:
        """Return Boltzmann's constant in code units, its value in erg/K divided by the code unit of erg/K.

        Implements UNIT08.
        """

        return constants.BOLTZMANN / self.code_unit((1, 2, -2, -1))


    @cached_property
    def proton_mass(self) -> float:
        """Return the mass of the proton in code units, its value in g divided by the code unit of mass.

        Implements UNIT08.
        """

        return constants.PROTON_MASS / self.code_unit((1, 0, 0, 0))


    @cached_property
    def electron_mass(self) -> float:
        """Return the mass of the electron in code units, its value in g divided by the code unit of mass.

        Implements UNIT08.
        """

        return constants.ELECTRON_MASS / self.code_unit((1, 0, 0, 0))


    @cached_property
    def atomic_mass_unit(self) -> float:
        """Return the atomic mass unit in code units, its value in g divided by the code unit of mass.

        Implements UNIT08.
        """

        return constants.ATOMIC_MASS_UNIT / self.code_unit((1, 0, 0, 0))


    def code_unit(self, dimension: tuple[int, int, int, int]) -> float:
        """Return the code unit of a dimension in cgs.

        Parameters
        ================================================================================================================
        dimension : tuple[int, int, int, int]
            The exponents (a, b, c, d) of mass, length, time and temperature, as (1, 2, -2, -1) for erg per kelvin.

        Returns
        ================================================================================================================
        float
            M0**a L0**b T0**c, the size in cgs of one code unit of that dimension, so that a value in code units,
            multiplied by it, gives the value in cgs. Mass, length and time give no scale of temperature, which
            keeps the kelvin, so that d takes no part.

        Implements UNIT03.
        """

        ## temperature keeps the kelvin, so that its exponent d takes no part
        a, b, c, _ = dimension
        return self.mass**a * self.length**b * self.time**c


    def factor(self, name: str) -> float:
        """Return the factor that converts a value given in the named unit into code units.

        The factor is the value of the unit in cgs divided by the code unit of its dimension, so that a value given in
        the unit, multiplied by it, is the value in code units. Under base units of 2 g, 4 cm and 8 s, the code unit
        of velocity is 4 / 8 cm/s, and the factor of km/s is 1e5 / (4 / 8) = 2e5.

        Parameters
        ================================================================================================================
        name : str
            The name of the unit, as the table holds it, such as km/s.

        Returns
        ================================================================================================================
        float
            The value of the unit in cgs divided by the code unit of its dimension.

        Raises
        ================================================================================================================
        ValueError
            If the table holds no unit of that name, with a message that lists the units of the table.

        Implements UNIT06 and UNIT07.
        """

        try:
            unit = NAMED_UNITS[name]
        except KeyError:
            ## a ValueError in place of the KeyError, which would name the unit alone
            raise ValueError(f"unknown unit {name!r}, the table holds {', '.join(NAMED_UNITS)}") from None
        return unit.value / self.code_unit(unit.dimension)


## the named units by their names, fixed in stratum 1 and read-only (UNIT04, UNIT05, UNIT12)
NAMED_UNITS: Final = MappingProxyType({
    "g":            NamedUnit(1.0, (1, 0, 0, 0)),
    "cm":           NamedUnit(1.0, (0, 1, 0, 0)),
    "pc":           NamedUnit(constants.PARSEC, (0, 1, 0, 0)),
    "s":            NamedUnit(1.0, (0, 0, 1, 0)),
    "yr":           NamedUnit(constants.JULIAN_YEAR, (0, 0, 1, 0)),
    "Myr":          NamedUnit(1e6 * constants.JULIAN_YEAR, (0, 0, 1, 0)),
    "cm/s":         NamedUnit(1.0, (0, 1, -1, 0)),
    "km/s":         NamedUnit(1e5, (0, 1, -1, 0)),
    "g/cm^3":       NamedUnit(1.0, (1, -3, 0, 0)),
    "cm^-3":        NamedUnit(1.0, (0, -3, 0, 0)),
    "K":            NamedUnit(1.0, (0, 0, 0, 1)),
    "erg/cm^3":     NamedUnit(1.0, (1, -1, -2, 0)),
})
