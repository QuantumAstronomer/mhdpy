"""The unit system of mhdpy: code units and their relation to physical units (cgs).

mhdpy solves its equations in dimensionless code units. A unit system relates them to cgs through three numbers, the
code units of length, mass and time, from which every other unit follows. The requirements this module fulfils are in
``docs/requirements/L0-foundation/units.md`` (UNI01-UNI18) and tested in the accompanying test module
``tests/test_units.py``.
"""

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from mhdpy.foundation import constants

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["UnitSystem"]

## The label of each named unit's cgs unit (UNI04), exactly as it is to appear in the headers of the history and the
## attributes of outputs (D14). Units are written with their cgs names where those exist (dyn, erg), and exponents with
## ^. The labels do not depend on the code units, only on the cgs units the values convert to, so one table serves every
## unit system. The leading underscore marks the table as internal; it is read through UnitSystem.label.
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
    "magnetic_field"    : "G",
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
    mu : float, optional
        The default mean molecular weight, used by temperature conversions that are given none (UNI09). Without it,
        every temperature conversion must be given one.
    """

    length: float
    mass: float
    time: float
    ## None, the default of the field, means that no default mean molecular weight was given: mhdpy assumes no value of
    ## its own (UNI09).
    mu: float | None = None

    def __post_init__(self) -> None:
        """Refuse code units and a default mean molecular weight that are not positive and finite (UNI01, UNI09).

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

        ## The default mean molecular weight, if one is given, is checked by the same condition as the code units and
        ## stored as an np.float64 for the same reason. A conversion that falls back on it then computes exactly as
        ## when it is given the same value itself.
        if self.mu is not None:
            if not (math.isfinite(self.mu) and self.mu > 0):
                raise ValueError(f"The default mean molecular weight must be positive and finite, got {self.mu!r}.")
            object.__setattr__(self, "mu", np.float64(self.mu))

    def _mean_molecular_weight(self, mu: npt.ArrayLike | None) -> npt.NDArray[np.float64]:
        """Return the mean molecular weight of a temperature conversion as a double-precision array (UNI08, UNI09).

        A conversion given no mean molecular weight uses the default of the unit system; without a default, it is
        refused. A mean molecular weight that is not positive and finite, in any of its elements, is refused as well.
        """
        ## A value given to the conversion takes precedence over the default. Without either, no value is assumed:
        ## the error says how to give one.
        if mu is None:
            if self.mu is None:
                raise ValueError(
                    "No mean molecular weight given: pass mu to the conversion, or give the unit system a default."
                )
            mu = self.mu

        ## np.asarray turns a scalar into an array of zero dimensions and leaves an array as it is (without copying it
        ## if it is double precision already), so one check serves scalars and arrays alike. Arithmetic with a
        ## zero-dimensional array gives back an ordinary np.float64, so a scalar stays a scalar in the result.
        mu = np.asarray(mu, dtype=np.float64)

        ## The same condition as for the code units (UNI01), applied to every element at once: np.isfinite and > give an
        ## array of True and False, & combines them element by element, and np.all requires it to hold everywhere.
        if not np.all(np.isfinite(mu) & (mu > 0)):
            raise ValueError(f"The mean molecular weight must be positive and finite, got {mu!r}.")
        return mu

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

    @property
    def magnetic_field(self) -> float:
        """The code unit of the magnetic field, in gauss: sqrt(4 pi p_u), with p_u the code unit of pressure (UNI07).

        The factor 4 pi is absorbed into the field, so the equations in code units contain no 4 pi: the magnetic
        pressure and energy density are B^2/2, where Gaussian units have B^2/(8 pi).
        """
        ## Absorbing 4 pi means B_code^2/2, in code units of pressure, must equal B^2/(8 pi) in cgs. With B = B_code * u
        ## that gives u^2 = 4 pi p_u. The factor sqrt(4 pi) is why this unit is not a product of powers of the base
        ## units (UNI02). np.sqrt keeps the result an np.float64, like every other unit (UNI05).
        return np.sqrt(4 * np.pi * self.pressure)

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

    def temperature(
        self, p_over_rho: npt.ArrayLike, *, mu: npt.ArrayLike | None = None
    ) -> np.float64 | npt.NDArray[np.float64]:
        """Return the temperature, in kelvin, of gas with the given ratio of pressure to density in code units (UNI08).

        For an ideal gas, T = mu m_H (p / rho) / k_B, with mu the mean molecular weight in units of the mass of the
        hydrogen atom m_H.

        Parameters
        ----------
        p_over_rho : float or array_like
            The ratio of pressure to density, in code units of specific energy.
        mu : float or array_like, optional
            The mean molecular weight, positive and finite: a scalar, or an array of the shape of p_over_rho that gives
            it cell by cell. Without it, the default of the unit system is used (UNI09).

        Returns
        -------
        float or numpy.ndarray
            The temperature in kelvin, in double precision, with the shape of p_over_rho.
        """
        ## p / rho has the dimensions of a specific energy, so its unit converts it to erg/g (UNI05). The factors are
        ## applied in the order of the formula; np.asarray makes a list of values work as an array does.
        p_over_rho_cgs = np.asarray(p_over_rho, dtype=np.float64) * self.specific_energy
        return self._mean_molecular_weight(mu) * constants.HYDROGEN_MASS * p_over_rho_cgs / constants.BOLTZMANN_CONSTANT

    def pressure_over_density(
        self, temperature: npt.ArrayLike, *, mu: npt.ArrayLike | None = None
    ) -> np.float64 | npt.NDArray[np.float64]:
        """Return the ratio of pressure to density, in code units, of gas at the given temperature (UNI08).

        The inverse of UnitSystem.temperature: p / rho = k_B T / (mu m_H).

        Parameters
        ----------
        temperature : float or array_like
            The temperature, in kelvin.
        mu : float or array_like, optional
            The mean molecular weight, positive and finite: a scalar, or an array of the shape of temperature that
            gives it cell by cell. Without it, the default of the unit system is used (UNI09).

        Returns
        -------
        float or numpy.ndarray
            The ratio of pressure to density in code units of specific energy, in double precision, with the shape of
            temperature.
        """
        ## The ratio in erg/g first, then converted to code units by dividing by the unit of specific energy (UNI05).
        p_over_rho_cgs = constants.BOLTZMANN_CONSTANT * np.asarray(temperature, dtype=np.float64)
        p_over_rho_cgs = p_over_rho_cgs / (self._mean_molecular_weight(mu) * constants.HYDROGEN_MASS)
        return p_over_rho_cgs / self.specific_energy
