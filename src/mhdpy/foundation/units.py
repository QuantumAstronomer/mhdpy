"""The unit system of mhdpy: the relation between code units and physical units (cgs).

mhdpy computes in dimensionless code units. Every value that kernels, physics modules and the time integration work
with is a multiple of a code unit, and the equations contain no constant that belongs to a particular system of units
(D12). This has three benefits. Values of order unity keep the arithmetic well inside the range of double precision,
even for problems whose values span dozens of orders of magnitude in cgs. The verification problems of the literature
(D02), which are posed in code units, run as they are. And one problem in code units describes a whole family of
physical systems, related by a change of units.

A unit system relates code units to cgs. It is defined by three numbers, the code units of length, mass and time, from
which every other unit follows; the factor 4 pi is absorbed into the magnetic field, so that no 4 pi appears in the
equations either. It converts numbers and arrays between code units and cgs, converts between temperature and the ratio
of pressure to density through the mean molecular weight, and converts the physical constants of ``constants.py`` to
code units. It also reads values written with a unit, such as "100 pc" or "1e-27 g cm^-3", and converts them to code
units, refusing a value whose dimensions are not those expected. It cannot be changed once created, and it converts to
a record of plain values and back, bit for bit.

Within mhdpy, the unit system belongs to the foundation (layer L0) and is used at the edges of a simulation, never in
its computation. Physics modules that need physical constants, such as cooling or self-gravity, receive them converted
to code units at set-up (D12). Outputs and the history record the unit system and label their values with cgs units
(D14), and restart files record it, so that a continued run converts exactly as the original did (D13). A simulation
without a unit system is dimensionless and runs entirely in code units; with one, it computes the same state, bit for
bit (UNI15-UNI17). Physical values enter a run as parameters written with their unit, which the unit system of the run
converts (PAR09).

For example, a unit system of 1 kpc, 1e5 solar masses and 1 Myr, and some of its conversions::

    from mhdpy.foundation import constants
    from mhdpy.foundation.units import UnitSystem

    system = UnitSystem(length=constants.KILOPARSEC, mass=1e5 * constants.SOLAR_MASS, time=constants.MEGAYEAR)
    density_cgs = density * system.density          ## code units to g cm^-3
    temperature = system.temperature(pressure / density, mu=0.6)
    G = system.constant("GRAVITATIONAL_CONSTANT")   ## G in code units
    radius = system.to_code_units("100 pc", "length")  ## 0.1 in code units of length

The requirements this module fulfils are in ``docs/requirements/L0-foundation/units.md`` (UNI01-UNI20), and they are
tested in the accompanying test package ``tests/units/``, one module per group of requirements.
"""

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import NamedTuple, Self

import numpy as np
import numpy.typing as npt

from mhdpy.foundation import constants

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["SYMBOLS", "Symbol", "UnitSystem", "parse"]

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


class Symbol(NamedTuple):
    """A unit symbol of a value with a unit (UNI19): its value in cgs and its dimensions.

    The dimensions are the exponents of length, mass, time and temperature, a dimension that does not occur left out:
    ``{"length": -3, "mass": 1}`` for the dimensions of a density.
    """

    value: float
    dimensions: dict[str, float]


## The unit symbols a value may be written with (UNI19), each with its value in cgs and its dimensions. The cgs symbols
## are the units the labels are written in (UNI04), so every label can be read back: cm, g and s are the base units,
## with value 1; dyn, erg and the gauss G follow from them, and K, the kelvin, is a dimension of its own, since code
## units have no temperature dimension (UNI10). The other symbols are the astronomical units problems are posed in,
## with the values of the constants (UNI11), and km, exactly 1e5 cm, for velocities in km s^-1. SI units are left out
## on purpose, so that a value is never written half in one system and half in the other.
# fmt: off
SYMBOLS: dict[str, Symbol] = {
    "cm":   Symbol(1.0,                         {"length":  1                                           }),
    "g":    Symbol(1.0,                         {                "mass": 1                              }),
    "s":    Symbol(1.0,                         {                             "time":  1                }),
    "K":    Symbol(1.0,                         {                                       "temperature": 1}),
    "dyn":  Symbol(1.0,                         {"length":  1,   "mass": 1,   "time": -2                }),
    "erg":  Symbol(1.0,                         {"length":  2,   "mass": 1,   "time": -2                }),
    "G":    Symbol(1.0,                         {"length": -0.5, "mass": 0.5, "time": -1                }),
    "km":   Symbol(1e5,                         {"length":  1                                           }),
    "au":   Symbol(constants.ASTRONOMICAL_UNIT, {"length":  1                                           }),
    "pc":   Symbol(constants.PARSEC,            {"length":  1                                           }),
    "kpc":  Symbol(constants.KILOPARSEC,        {"length":  1                                           }),
    "Mpc":  Symbol(constants.MEGAPARSEC,        {"length":  1                                           }),
    "Rsun": Symbol(constants.SOLAR_RADIUS,      {"length":  1                                           }),
    "Msun": Symbol(constants.SOLAR_MASS,        {                "mass": 1                              }),
    "Lsun": Symbol(constants.SOLAR_LUMINOSITY,  {"length":  2,   "mass": 1,   "time": -3                }),
    "yr":   Symbol(constants.JULIAN_YEAR,       {                             "time":  1                }),
    "Myr":  Symbol(constants.MEGAYEAR,          {                             "time":  1                }),
    "Gyr":  Symbol(constants.GIGAYEAR,          {                             "time":  1                }),
}
# fmt: on

## The two parts of a value with a unit (UNI19), as regular expressions: patterns that a string either matches or not.
## A number: an optional sign, digits with an optional decimal point (or a point followed by digits), and an optional
## exponent, as "-2.5", "1e-27" or ".5". A factor: a symbol of letters, optionally followed by ^ and an exponent that is
## an integer ("-3") or a half-integer written with a decimal point ("0.5", "-1.5"). The parentheses mark the parts the
## code reads back: (?: ...) groups without capturing, ( ... ) captures the symbol and the exponent of a factor.
_NUMBER = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_FACTOR = re.compile(r"([A-Za-z]+)(?:\^(-?\d+(?:\.5)?))?")


def parse(text: str) -> tuple[float, dict[str, float]]:
    """Return the number and the unit factors of a value with a unit, such as ``"1e-27 g cm^-3"`` (UNI19).

    A value with a unit is a number and a unit expression, separated by spaces: factors separated by spaces, each a
    unit symbol of ``SYMBOLS`` with an optional exponent, written with ``^``. Any number of spaces may separate the
    parts, and spaces around the value are ignored.

    Parameters
    ----------
    text : str
        The value with its unit.

    Returns
    -------
    number : float
        The number, as written.
    factors : dict
        Each symbol of the expression with its exponent: ``{"g": 1, "cm": -3}`` for ``"g cm^-3"``.
    """
    ## Split the value into its parts. str.split() without an argument splits at every run of spaces (or other
    ## whitespace) and ignores the spaces around the value, which carry no meaning. The first part is the number, and
    ## the others are the factors of the unit expression; there must be at least one.
    parts = text.split()
    if len(parts) < 2 or not _NUMBER.fullmatch(parts[0]):
        raise ValueError(f"A value with a unit must be a number, a space and a unit, such as '10 Myr', got {text!r}.")

    ## Read the factors one by one. fullmatch requires the whole factor to match, so "g/cm^3" is refused rather than
    ## partly read. A factor without an exponent has the exponent 1. A symbol written twice adds up its exponents, as
    ## "cm cm" is cm^2.
    factors: dict[str, float] = {}
    for factor in parts[1:]:
        match = _FACTOR.fullmatch(factor)
        if match is None:
            raise ValueError(f"{factor!r} in {text!r} is not a unit symbol with an optional exponent, such as 'cm^-3'.")
        symbol, exponent = match.groups()

        ## Only the symbols of the table are units; anything else, a misspelling or an SI unit, is refused by name.
        if symbol not in SYMBOLS:
            raise ValueError(f"Unknown unit symbol {symbol!r} in {text!r}; the symbols are {', '.join(SYMBOLS)}.")
        factors[symbol] = factors.get(symbol, 0.0) + (float(exponent) if exponent is not None else 1.0)
    return float(parts[0]), factors


def _dimensions(factors: Mapping[str, float]) -> dict[str, float]:
    """Return the dimensions of a unit expression, given as its factors, such as ``{"g": 1, "cm": -3}`` (UNI20).

    The dimensions of each symbol, multiplied by its exponent, are summed over the factors. A dimension whose exponents
    cancel, as the mass does in ``erg g^-1``, is left out, as one that does not occur.
    """
    ## Exponents are integers and half-integers, and so are their products and sums up to a quarter: all exact in
    ## double precision, so the dimensions can be compared with ==.
    dimensions: dict[str, float] = {}
    for symbol, exponent in factors.items():
        for dimension, power in SYMBOLS[symbol].dimensions.items():
            dimensions[dimension] = dimensions.get(dimension, 0.0) + power * exponent
    return {dimension: power for dimension, power in dimensions.items() if power != 0}


## frozen=True: the fields cannot be changed after creation, as UNI12 requires; it also gives the unit system an
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
                raise ValueError(f"The code unit of {name} must be a positive, finite number in cgs, got {value}.")

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
                raise ValueError(f"The default mean molecular weight must be positive and finite, got {self.mu}.")
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

        ## The same condition as for the code units (UNI01), for every element at once: np.isfinite and > give arrays of
        ## True and False, & combines them element by element, and ~ inverts the result, marking the invalid elements.
        invalid = ~(np.isfinite(mu) & (mu > 0))
        if invalid.any():
            if mu.ndim == 0:
                raise ValueError(f"The mean molecular weight must be positive and finite, got {float(mu)}.")
            ## For an array, name the first invalid value, where it is, and how many there are, so that a single bad
            ## cell in a large field can be found. np.argwhere lists the indices of the marked elements.
            index = tuple(int(i) for i in np.argwhere(invalid)[0])
            raise ValueError(
                f"The mean molecular weight must be positive and finite, got {float(mu[index])} at index {index}, "
                f"one of {int(invalid.sum())} invalid values."
            )
        return mu

    def _kelvin_per_code_unit(self, mu: npt.ArrayLike | None) -> npt.NDArray[np.float64]:
        """Return mu m_H u / k_B: the temperature of gas whose p / rho is one code unit u of specific energy (UNI08)."""
        ## The constant factors are combined into one number first, so that an array takes one multiplication by mu
        ## and one by its values, rather than one pass per factor.
        scale = self.specific_energy * constants.HYDROGEN_MASS / constants.BOLTZMANN_CONSTANT
        return self._mean_molecular_weight(mu) * scale

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
        """Return the code unit, in cgs, of a quantity with dimensions L^length M^mass T^time (UNI02).

        L, M and T stand for length, mass and time. Any unit follows from the three code units raised to the powers of
        the quantity's dimensions. The exponents may be half-integers, as for the magnetic field (UNI07).

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
        ## That holds while the partial product L^a M^b lies within the range of normal doubles, which only dimensions
        ## far beyond those of any physical quantity leave (see the note on UNI02).
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
        ## T = (p / rho) mu m_H u / k_B: the ratio in code units times the temperature of one code unit. np.asarray
        ## makes a list of values work as an array does.
        return np.asarray(p_over_rho, dtype=np.float64) * self._kelvin_per_code_unit(mu)

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
        ## The inverse of UnitSystem.temperature: a division by the same factor.
        return np.asarray(temperature, dtype=np.float64) / self._kelvin_per_code_unit(mu)

    def constant(self, name: str) -> float:
        """Return a physical constant in code units, such as ``"GRAVITATIONAL_CONSTANT"`` (UNI10).

        The constant is converted by its dimensions in length, mass and time. A constant that contains the kelvin, such
        as Boltzmann's constant, keeps it: code units have no temperature dimension, so k_B in code units is a code
        unit of energy per kelvin.

        Parameters
        ----------
        name : str
            The name of the constant, as its name in ``mhdpy.foundation.constants``: ``"GRAVITATIONAL_CONSTANT"`` for
            ``constants.GRAVITATIONAL_CONSTANT``.

        Returns
        -------
        float
            The value of the constant in code units.
        """
        ## Look up the dimensions first: an unknown name, or an astronomical unit (which has no conversion to code
        ## units), raises a KeyError that names it. getattr(constants, name) then reads the value in cgs, as
        ## constants.GRAVITATIONAL_CONSTANT would, and dividing by its unit converts it to code units (UNI05).
        dimensions = constants.DIMENSIONS[name]
        return getattr(constants, name) / self.unit(**dimensions)

    def to_record(self) -> dict[str, float | str]:
        """Return the record of the unit system: its defining values and the sources of the constants (UNI14).

        The record consists of plain values, Python floats and strings, so that any file format can store it: the
        attributes of outputs (D14.2), restart files (D13.5). ``UnitSystem.from_record`` creates the unit system again.

        Returns
        -------
        dict
            The code units ``"length"``, ``"mass"`` and ``"time"``, the default mean molecular weight ``"mu"`` if the
            unit system has one, and the sources of the constants ``"sources"``.
        """
        ## float() turns each np.float64 into a plain Python float with exactly the same bits, so nothing is lost.
        record: dict[str, float | str] = {
            "length": float(self.length),
            "mass": float(self.mass),
            "time": float(self.time),
        }

        ## A missing default is left out rather than recorded as None: HDF5 attributes, for one, cannot hold None.
        if self.mu is not None:
            record["mu"] = float(self.mu)

        ## The sources of the constants, so that a file states which values it was made with. They are not needed
        ## to create the unit system again: the code units are in cgs and do not depend on the constants.
        record["sources"] = constants.SOURCES
        return record

    @classmethod
    def from_record(cls, record: Mapping[str, float | str]) -> Self:
        """Create a unit system from its record, as written by ``UnitSystem.to_record`` (UNI14).

        The unit system created is equal to the one recorded, with every value identical bit for bit.

        Parameters
        ----------
        record : mapping
            The record, as read from a file: ``"length"``, ``"mass"`` and ``"time"``, and ``"mu"`` if the unit system
            has a default mean molecular weight. Other entries, such as the sources of the constants, are ignored.

        Returns
        -------
        UnitSystem
            The unit system of the record.
        """
        ## A classmethod is called on the class, UnitSystem.from_record(record), and receives the class as cls, so
        ## cls(...) creates the unit system; Self in the signature is the type of that class. Creating it checks the
        ## values again (UNI01, UNI09), so a damaged record cannot give an invalid unit system. A missing code unit
        ## raises a KeyError that names it.
        mu = record.get("mu")
        return cls(
            length=float(record["length"]),
            mass=float(record["mass"]),
            time=float(record["time"]),
            mu=None if mu is None else float(mu),
        )

    def to_code_units(self, text: str, unit: str | Mapping[str, float]) -> float:
        """Return a value with a unit, such as ``"100 pc"``, in code units of the given unit (UNI20).

        The value's unit must have the dimensions of the given unit. A temperature dimension stays in kelvin, since
        code units have none (UNI10): ``"1e6 K"`` is 1e6 in code units.

        Parameters
        ----------
        text : str
            The value with its unit (UNI19).
        unit : str or mapping
            The unit to convert to: ``"dimensionless"``; the name of a unit, such as ``"density"`` or
            ``"magnetic_field"``; or dimensions, as the exponents of length, mass, time and temperature, such as
            ``{"length": 1, "time": -1}``.

        Returns
        -------
        float
            The value in code units.
        """
        number, factors = parse(text)

        ## The dimensions the value must have, and the code unit it is divided by. A named unit takes its dimensions
        ## from its label, which is a unit expression itself (UNI19), so they cannot disagree with what the label
        ## says. The label is looked up first: an unknown name raises a KeyError that names it, before getattr could
        ## find a method of the same name. Its code unit is the named unit itself, which for the magnetic field
        ## includes the factor sqrt(4 pi) (UNI07). Dimensions given as exponents take their code unit from UNI02, with
        ## no factor for temperature, and their zero exponents are left out, as _dimensions leaves them out.
        if unit == "dimensionless":
            dimensions, code_unit = {}, 1.0
        elif isinstance(unit, str):
            dimensions = _dimensions(parse(f"1 {_LABELS[unit]}")[1])
            code_unit = getattr(self, unit)
        else:
            dimensions = {dimension: power for dimension, power in unit.items() if power != 0}
            code_unit = self.unit(length=unit.get("length", 0), mass=unit.get("mass", 0), time=unit.get("time", 0))

        ## A value whose dimensions differ is refused rather than converted into a number without meaning. This also
        ## refuses a misspelt dimension, such as "lenght", which no unit expression has.
        found = _dimensions(factors)
        if found != dimensions:
            raise ValueError(f"{text!r} has the dimensions {found}, not those of {unit!r}, {dimensions}.")

        ## The value of the expression in cgs, the product of its symbols' values raised to their exponents, divided
        ## by the code unit. Dividing before multiplying by the number keeps the intermediate result of order of the
        ## ratio of the two units, so that a large or small number cannot overflow on the way. float() returns a plain
        ## Python float even when the code unit is an np.float64.
        cgs = math.prod(SYMBOLS[symbol].value ** exponent for symbol, exponent in factors.items())
        return float(number * (cgs / code_unit))
