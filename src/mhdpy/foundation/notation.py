"""The notation of units in mhdpy: how a unit is written, and what dimensions it has.

Physical values enter mhdpy as text, written with their unit: a parameter such as a cloud radius of "100 pc" or an
ambient density of "1e-27 g cm^-3" (PAR09). Values leave it with their unit as text too: the headers of the history and
the attributes of outputs label every quantity with its cgs unit, such as "g cm^-3" for a density (D14). Both use one
notation, defined here: a unit expression is one or more factors separated by spaces, each a unit symbol with an
optional exponent written with ^, so that every label mhdpy writes is also a unit a user can write (UNI19).

This module knows how units are written, not what they are worth. It holds the unit symbols with their dimensions, the
labels of the named units, a reader for values with a unit, and the dimensions of a unit expression: everything needed
to check that a value has the right dimensions, and nothing needed to convert it. The values of the symbols in cgs,
which come from the physical constants, and the conversion to code units are the unit system's (``units.py``).

The split is what lets the parameters check their declarations without the unit system (PAR21). A module declares the
unit of each numeric parameter, and the parameters check that a named unit exists and that a default such as "100 pc"
has the dimensions declared, as soon as the module is declared. The unit system, with NumPy behind it, is needed only to
convert, and is passed to the parameters by a run that has one. This module therefore depends on nothing beyond Python's
standard library (UNI18).

For example, reading a value with a unit and finding its dimensions::

    from mhdpy.foundation import notation

    number, factors = notation.parse("1e-27 g cm^-3")    ## 1e-27, {"g": 1.0, "cm": -3.0}
    notation.dimensions(factors)                         ## {"mass": 1.0, "length": -3.0}
    notation.LABELS["density"]                           ## "g cm^-3"

The requirements this module fulfils are in ``docs/requirements/L0-foundation/units.md`` (UNI04, UNI18, UNI19, UNI20),
and they are tested with the unit system, in the test package ``tests/units/``.
"""

import re
from collections.abc import Mapping

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["LABELS", "SYMBOLS", "dimensions", "parse"]

## The label of each named unit's cgs unit (UNI04), exactly as it is to appear in the headers of the history and the
## attributes of outputs (D14). Units are written with their cgs names where those exist (dyn, erg), and exponents with
## ^. The labels do not depend on the code units, only on the cgs units the values convert to, so one table serves every
## unit system. The keys are the names of the named units, as the unit system's attributes (UnitSystem.density).
# fmt: off
LABELS = {
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

## The unit symbols a value may be written with (UNI19), each with its dimensions: the exponents of length, mass, time
## and temperature, a dimension that does not occur left out. The cgs symbols are the units the labels are written in
## (UNI04), so every label can be read back: cm, g and s are the base units; dyn, erg and the gauss G follow from them,
## and K, the kelvin, is a dimension of its own, since code units have no temperature dimension (UNI10). The other
## symbols are the astronomical units problems are posed in, and km, for velocities in km s^-1. SI units are left out
## on purpose, so that a value is never written half in one system and half in the other. The value of each symbol in
## cgs is in the unit system (units.SYMBOL_VALUES).
# fmt: off
SYMBOLS: dict[str, dict[str, float]] = {
    "cm":   {"length":  1                                           },
    "g":    {                "mass": 1                              },
    "s":    {                             "time":  1                },
    "K":    {                                       "temperature": 1},
    "dyn":  {"length":  1,   "mass": 1,   "time": -2                },
    "erg":  {"length":  2,   "mass": 1,   "time": -2                },
    "G":    {"length": -0.5, "mass": 0.5, "time": -1                },
    "km":   {"length":  1                                           },
    "au":   {"length":  1                                           },
    "pc":   {"length":  1                                           },
    "kpc":  {"length":  1                                           },
    "Mpc":  {"length":  1                                           },
    "Rsun": {"length":  1                                           },
    "Msun": {                "mass": 1                              },
    "Lsun": {"length":  2,   "mass": 1,   "time": -3                },
    "yr":   {                             "time":  1                },
    "Myr":  {                             "time":  1                },
    "Gyr":  {                             "time":  1                },
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


def dimensions(factors: Mapping[str, float]) -> dict[str, float]:
    """Return the dimensions of a unit expression, given as its factors, such as ``{"g": 1, "cm": -3}`` (UNI20).

    The dimensions of each symbol, multiplied by its exponent, are summed over the factors. A dimension whose exponents
    cancel, as the mass does in ``erg g^-1``, is left out, as one that does not occur.

    Parameters
    ----------
    factors : mapping
        Each symbol of the expression with its exponent, as ``parse`` returns them.

    Returns
    -------
    dict
        The exponent of each dimension that occurs: ``{"mass": 1, "length": -3}`` for ``{"g": 1, "cm": -3}``.
    """
    ## Exponents are integers and half-integers, and so are their products and sums up to a quarter: all exact in
    ## double precision, so the dimensions can be compared with ==.
    total: dict[str, float] = {}
    for symbol, exponent in factors.items():
        for dimension, power in SYMBOLS[symbol].items():
            total[dimension] = total.get(dimension, 0.0) + power * exponent
    return {dimension: power for dimension, power in total.items() if power != 0}
