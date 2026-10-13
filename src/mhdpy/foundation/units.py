"""The unit system of mhdpy: code units and their relation to physical units (cgs).

mhdpy solves its equations in dimensionless code units. A unit system relates them to cgs through three numbers, the
code units of length, mass and time, from which every other unit follows. The requirements this module fulfils are in
``docs/requirements/L0-foundation/units.md`` (UNI01-UNI18) and tested in the accompanying test module
``tests/test_units.py``.
"""

import math
from dataclasses import dataclass

import numpy as np

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["UnitSystem"]

## The label of each named unit's cgs unit (UNI04), for the headers of the history and the attributes of outputs (D14).
## The labels do not depend on the code units, only on the cgs units the values convert to, so one table serves every
## unit system. The leading underscore marks the table as internal; it is read through UnitSystem.label.
## The label of each named unit's cgs unit (UNI04), exactly as it is to appear in the headers of the history and the
## attributes of outputs. Units are written with their cgs names where those exist (dyn, erg), and exponents with ^.
# fmt: off
_LABELS = {
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
}
# fmt: on


## frozen=True: the fields cannot be changed after creation, which UNI12 will require; it also gives the unit system an
## equality comparison of its fields, which UNI13 builds on. kw_only=True: the fields can only be given by keyword, so
## UnitSystem(length=..., mass=..., time=...) works, while a call with positional arguments, which could silently mix
## up length, mass and time, is refused.
@dataclass(frozen=True, kw_only=True)
class UnitSystem:
    """A system of code units, defined by the code units of length, mass and time in cgs.

    Every other unit derives from these three. Each is the value of one code unit expressed in cgs, so a value in code
    units converts to cgs by multiplication with its unit (UNI05).

    Parameters
    ----------
    length : float
        The code unit of length, in cm.
    mass : float
        The code unit of mass, in g.
    time : float
        The code unit of time, in s.
    """

    length: float
    mass: float
    time: float

    def __post_init__(self) -> None:
        """Refuse code units that are not positive and finite (UNI01).

        A dataclass calls this method automatically at the end of its constructor, after the fields have been set, so
        no unit system with an invalid code unit can ever exist.
        """
        ## Check each code unit under its own name, so that the error can say which one is wrong.
        for name, value in (("length", self.length), ("mass", self.mass), ("time", self.time)):
            ## math.isfinite is False for infinities and for NaN ("not a number"), and NaN also fails every comparison,
            ## so this single condition refuses zero, negative, infinite and undefined values alike.
            if not (math.isfinite(value) and value > 0):
                raise ValueError(f"The code unit of {name} must be a positive, finite number in cgs, got {value!r}.")

            ## Store the code unit as NumPy's double-precision number np.float64 (UNI05). The value stays exactly as
            ## given (UNI01), but its type makes every conversion double precision: a single-precision array multiplied
            ## by a plain Python float stays single precision, multiplied by an np.float64 it becomes double precision.
            ## np.float64 is a subclass of Python's float, so a unit still works wherever a float does. Every unit
            ## derived from these three (UNI02) is then an np.float64 as well, since arithmetic on np.float64 gives
            ## np.float64. A frozen dataclass refuses ordinary assignment to its fields, even here; object.__setattr__
            ## is the documented way around that during construction.
            object.__setattr__(self, name, np.float64(value))

    ## The named units of UNI03. Each is a property: it is read like an attribute (system.density, without
    ## parentheses) but computed from the general rule of UNI02 each time it is read. Computing is cheap, and it means
    ## a named unit can never disagree with the unit derived from its dimensions. Properties also give type checkers
    ## and editors a real attribute to check and complete, unlike a lookup by name in a dictionary.
    @property
    def velocity(self) -> float:
        """The code unit of velocity, in cm/s."""
        return self.unit(length=1, time=-1)

    @property
    def acceleration(self) -> float:
        """The code unit of acceleration, in cm/s^2."""
        return self.unit(length=1, time=-2)

    @property
    def density(self) -> float:
        """The code unit of density, in g/cm^3."""
        return self.unit(length=-3, mass=1)

    @property
    def momentum_density(self) -> float:
        """The code unit of momentum density, in g/(cm^2 s)."""
        return self.unit(length=-2, mass=1, time=-1)

    @property
    def mass_flux(self) -> float:
        """The code unit of mass flux, in g/(cm^2 s)."""
        return self.unit(length=-2, mass=1, time=-1)

    @property
    def pressure(self) -> float:
        """The code unit of pressure, in dyn/cm^2 = g/(cm s^2)."""
        return self.unit(length=-1, mass=1, time=-2)

    @property
    def energy_density(self) -> float:
        """The code unit of energy density, in erg/cm^3 = g/(cm s^2)."""
        return self.unit(length=-1, mass=1, time=-2)

    @property
    def energy(self) -> float:
        """The code unit of energy, in erg = g cm^2/s^2."""
        return self.unit(length=2, mass=1, time=-2)

    @property
    def specific_energy(self) -> float:
        """The code unit of specific energy, in erg/g = cm^2/s^2."""
        return self.unit(length=2, time=-2)

    @property
    def energy_flux(self) -> float:
        """The code unit of energy flux, in erg/(cm^2 s) = g/(s^3)."""
        return self.unit(mass=1, time=-3)

    def unit(self, *, length: float = 0.0, mass: float = 0.0, time: float = 0.0) -> float:
        """Return the code unit, in cgs, of a quantity with dimensions length^length mass^mass time^time (UNI02).

        Any unit follows from the three code units raised to the powers of the quantity's dimensions. The exponents may
        be half-integers, as for the magnetic field (UNI07).

        Parameters
        ----------
        length, mass, time : float
            The exponents of length, mass and time in the dimensions of the quantity; 0 by default.

        Returns
        -------
        float
            The value of one code unit of the quantity in cgs.
        """
        ## The * in the signature makes the exponents keyword-only, so unit(length=-3, mass=1) reads as what it means
        ## and a call such as unit(-3, 1), whose meaning depends on the order, is refused. The default 0 leaves out a
        ## dimension: x**0 is exactly 1. Each power is accurate to about 1 ulp, the product to within 4 ulp (UNI02).
        return self.length**length * self.mass**mass * self.time**time

    def label(self, name: str) -> str:
        """Return the label of the cgs unit of a named unit, such as ``"g cm^-3"`` for ``"density"`` (UNI04).

        Parameters
        ----------
        name : str
            The name of the unit, as the name of its attribute: ``"density"`` for ``system.density``.

        Returns
        -------
        str
            The label of the unit in cgs, as it is written in the headers of the history and in outputs.
        """
        ## A lookup in the table of labels. An unknown name raises a KeyError that names it.
        return _LABELS[name]
