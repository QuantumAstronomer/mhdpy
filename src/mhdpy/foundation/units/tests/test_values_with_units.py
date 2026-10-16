"""Tests of values with a unit: how they are written (UNI19) and converted to code units (UNI20)."""

import math
import re
from decimal import Decimal, localcontext
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from mhdpy.foundation.units import constants, notation
from mhdpy.foundation.units.system import SYMBOL_VALUES, UnitSystem
from mhdpy.foundation.units.tests.reference import LABELS, LENGTH, MASS, NAMED_UNITS, PI, TIME

## Examples of values with a unit, each with the number and the factors it must be read as (UNI19): a symbol on its
## own, factors with negative exponents, a temperature, a negative number, and a named cgs unit among others.
# fmt: off
READ_EXAMPLES: list[tuple[str, float, dict[str, float]]] = [
    ("10 Myr",              10.0,   {"Myr": 1}),
    ("1e-27 g cm^-3",      1e-27,   {"g": 1, "cm": -3}),
    ("1e6 K",                1e6,   {"K": 1}),
    ("-2.5 km s^-1",        -2.5,   {"km": 1, "s": -1}),
    ("3 erg cm^-2 s^-1",     3.0,   {"erg": 1, "cm": -2, "s": -1}),
    (" 10 Myr",             10.0,   {"Myr": 1}),            ## Leading white space is ignored
    ("10 Myr ",             10.0,   {"Myr": 1}),            ## Trailing white space is ignored
    ("1e-27  g   cm^-3",    1e-27,  {"g": 1, "cm": -3}),    ## Multiple spaces between factors are ignored
]

## Strings that are not values with a unit (UNI19), each refused for the reason in its comment.
MALFORMED_EXAMPLES = [
    "10",           ## a number without a unit
    "Myr",          ## a unit without a number
    "ten Myr",      ## a number that cannot be read
    "nan K",        ## not a number
    "10 g/cm^3",    ## a division sign
    "10 cm^",       ## an exponent sign without an exponent
    "10 cm^1/2",    ## an exponent written as a fraction
    "10 cm^-3.2",   ## an exponent that is not an integer or a half-integer
    "10 cm^2.0",    ## an integer exponent written with a decimal point
]
# fmt: on

## The unit symbols of UNI19, each with its value in cgs and its dimensions: the exponents of length, mass, time and
## temperature, a dimension that does not occur left out. This table is the specification the tables of the notation and
## the unit system are checked against. The cgs symbols are the units themselves (value 1), dyn, erg and G follow from
## them, km is exactly 1e5 cm, and the astronomical symbols take the values of the constants, which are tested on their
## own (UNI11).
# fmt: off
SYMBOLS: dict[str, tuple[float, dict[str, float]]] = {
    "cm":   (1.0,                         {"length":  1                                             }),
    "g":    (1.0,                         {                "mass": 1                                }),
    "s":    (1.0,                         {                             "time":  1                  }),
    "K":    (1.0,                         {                                       "temperature": 1  }),
    "dyn":  (1.0,                         {"length":  1,   "mass": 1,   "time": -2                  }),
    "erg":  (1.0,                         {"length":  2,   "mass": 1,   "time": -2                  }),
    "G":    (1.0,                         {"length": -0.5, "mass": 0.5, "time": -1                  }),
    "km":   (1e5,                         {"length":  1                                             }),
    "au":   (constants.ASTRONOMICAL_UNIT, {"length":  1                                             }),
    "pc":   (constants.PARSEC,            {"length":  1                                             }),
    "kpc":  (constants.KILOPARSEC,        {"length":  1                                             }),
    "Mpc":  (constants.MEGAPARSEC,        {"length":  1                                             }),
    "Rsun": (constants.SOLAR_RADIUS,      {"length":  1                                             }),
    "Msun": (constants.SOLAR_MASS,        {                "mass": 1                                }),
    "Lsun": (constants.SOLAR_LUMINOSITY,  {"length":  2,   "mass": 1,   "time": -3                  }),
    "yr":   (constants.JULIAN_YEAR,       {                             "time":  1                  }),
    "Myr":  (constants.MEGAYEAR,          {                             "time":  1                  }),
    "Gyr":  (constants.GIGAYEAR,          {                             "time":  1                  }),
}
# fmt: on

## The dimensions of the magnetic field in gauss, g^0.5 cm^-0.5 s^-1. The magnetic field is not among NAMED_UNITS,
## because its code unit is not a product of powers of the base units (UNI07), but its label has dimensions all the
## same.
MAGNETIC_FIELD = {"length": -0.5, "mass": 0.5, "time": -1}

## The exponents the conversion test draws its factors with: integers and half-integers up to 1 in magnitude. With up
## to three factors, larger exponents give dimensions such as L^-6 M^-5 T^9, whose code unit loses its precision on the
## way (L^-6 M^-5 is smaller than the smallest normal double before T^9 brings it back), a limit of UNI02 rather than
## of the conversion.
EXPONENTS = [-1.0, -0.5, 0.5, 1.0]


def dimensions(factors: dict[str, float]) -> dict[str, float]:
    """Return the dimensions of a unit expression, from the table above.

    The dimensions of each symbol, multiplied by its exponent, are summed over the factors, and a dimension whose
    exponents cancel is left out, as one that does not occur.
    """
    total: dict[str, float] = {}
    for symbol, exponent in factors.items():
        for dimension, power in SYMBOLS[symbol][1].items():
            total[dimension] = total.get(dimension, 0.0) + power * exponent
    return {dimension: power for dimension, power in total.items() if power != 0}


def exact(number: float, factors: dict[str, float]) -> float:
    """Return a value with a unit in code units of its own dimensions, computed exactly and rounded once (UNI20).

    The number times the value of the expression in cgs, divided by the code unit of the expression's dimensions, all
    at 50 digits from the double-precision values of the symbols and the code units. A temperature dimension adds no
    factor, as it stays in kelvin.
    """
    found = dimensions(factors)
    with localcontext() as context:
        context.prec = 50
        cgs = Decimal(number)
        for symbol, exponent in factors.items():
            cgs *= Decimal(SYMBOLS[symbol][0]) ** Decimal(exponent)
        code_unit = (
            Decimal(LENGTH) ** Decimal(found.get("length", 0))
            * Decimal(MASS) ** Decimal(found.get("mass", 0))
            * Decimal(TIME) ** Decimal(found.get("time", 0))
        )
        return float(cgs / code_unit)


class TestValuesWithUnits:
    """UNI19-UNI20: a value with a unit, such as "100 pc", is read and converted to code units."""

    ## ---- How a value with a unit is written (UNI19) ----

    ## Run this test once for each example of READ_EXAMPLES. ids= names each case by its string, so that a failure is
    ## reported as, for example, test_value_with_unit_is_read[1e-27 g cm^-3].
    @pytest.mark.parametrize(("text", "number", "factors"), READ_EXAMPLES, ids=[text for text, *_ in READ_EXAMPLES])
    def test_value_with_unit_is_read(self, text: str, number: float, factors: dict[str, float]) -> None:
        """Check that a number and a unit expression are read from a string such as "1e-27 g cm^-3" (UNI19).

        The number is read as a float, and the expression as its factors: each symbol with its exponent, 1 when none
        is written.
        """
        value, read = notation.parse(text)

        ## The number is read exactly as written, so == is right: float("1e-27") is the double nearest to 1e-27, as is
        ## the literal 1e-27 in the list above. It is a float even when written without a decimal point, as "10".
        assert isinstance(value, float)
        assert value == number

        ## The factors are a dictionary from each symbol to its exponent. Comparing dictionaries compares every symbol
        ## and exponent, and also that no factor is missing or added.
        assert read == factors

    ## Run this test once for each string of MALFORMED_EXAMPLES, named by the string itself.
    @pytest.mark.parametrize("text", MALFORMED_EXAMPLES, ids=MALFORMED_EXAMPLES)
    def test_malformed_value_is_refused(self, text: str) -> None:
        """Check that a string not of the form of UNI19 is refused, naming the string (UNI19).

        Among them: a number or a unit alone, a division sign, an exponent that is not an integer or a half-integer,
        and a number that cannot be read.
        """
        ## The message must contain the string as Python writes it, in quotes. match= is a regular expression, in which
        ## characters such as ^ and . have meanings of their own; re.escape makes them match literally.
        with pytest.raises(ValueError, match=re.escape(repr(text))):
            notation.parse(text)

    def test_half_integer_exponents(self) -> None:
        """Check that an exponent may be a half-integer written with a decimal point, such as g^0.5 (UNI19)."""
        ## The gauss in base units, g^0.5 cm^-0.5 s^-1, with positive and negative half-integers, and a larger one.
        ## Halves are exact in double precision, so the exponents can be compared with ==.
        assert notation.parse("1 g^0.5 cm^-0.5 s^-1") == (1.0, {"g": 0.5, "cm": -0.5, "s": -1})
        assert notation.parse("2 s^-1.5") == (2.0, {"s": -1.5})

    ## Run this test once for every named unit with a label, the magnetic field included.
    @pytest.mark.parametrize("name", list(LABELS))
    def test_every_label_is_a_unit_expression(self, system: UnitSystem, name: str) -> None:
        """Check that the label of every named unit can be read as a unit expression (UNI04, UNI19).

        Its dimensions must be those of the named unit, so that the unit a file reports is a unit a user can write.
        """
        ## A label is a unit expression without a number, so it is read with the number 1 in front.
        _, factors = notation.parse(f"1 {system.label(name)}")
        assert dimensions(factors) == {**NAMED_UNITS, "magnetic_field": MAGNETIC_FIELD}[name]

    ## Run this test once for each symbol of the table above.
    @pytest.mark.parametrize("symbol", list(SYMBOLS))
    def test_symbols_have_their_values(self, symbol: str) -> None:
        """Check the value in cgs and the dimensions of every unit symbol (UNI19).

        The cgs symbols have the values of their units (cm, g, s, K are 1; dyn, erg and G follow from them), km is
        exactly 1e5 cm, and the astronomical symbols have the values of the constants of UNI11.
        """
        value, dimensions = SYMBOLS[symbol]

        ## The notation's table of dimensions and the unit system's table of values hold the same symbols as the
        ## specification, no more and no fewer. A symbol added to one table but not another fails here, in every case.
        assert set(notation.SYMBOLS) == set(SYMBOLS)
        assert set(SYMBOL_VALUES) == set(SYMBOLS)

        ## Each value is exact: 1, 1e5 or a constant, taken over without any arithmetic, so == is right.
        assert SYMBOL_VALUES[symbol] == value
        assert notation.SYMBOLS[symbol] == dimensions

    ## Run this test for a misspelt symbol, SI units, and a known symbol in the wrong case: each string with the symbol
    ## that must be named in the message.
    @pytest.mark.parametrize(
        ("text", "symbol"), [("10 Mry", "Mry"), ("1 m", "m"), ("1 kg", "kg"), ("1 KM s^-1", "KM"), ("1 g CM^-3", "CM")]
    )
    def test_unknown_symbol_is_refused(self, text: str, symbol: str) -> None:
        """Check that a unit symbol that is not one of UNI19 is refused, naming the symbol (UNI19).

        A misspelt symbol ("Mry") and an SI unit ("m", "kg") alike.
        """
        ## The message names the unknown symbol, in quotes; the string itself is named too, but the symbol is what
        ## tells the user which part of the string to correct.
        with pytest.raises(ValueError, match=re.escape(repr(symbol))):
            notation.parse(text)

    ## ---- How a value with a unit is converted to code units (UNI20) ----

    ## Hypothesis draws a number and one to three factors, each a symbol of the table with an exponent of EXPONENTS, and
    ## the test writes the value with a unit from them, as "123.4 pc^-0.5 Msun". st.dictionaries draws each symbol at
    ## most once. The numbers lie between 1e-6 and 1e6: the number enters by a single multiplication, so its size
    ## matters little, and a sign, being exact, not at all. The ranges are chosen so that every value and every code
    ## unit lies well within the range of doubles, and no draw needs to be discarded.
    @given(
        number=st.floats(min_value=1e-6, max_value=1e6),
        factors=st.dictionaries(st.sampled_from(list(SYMBOLS)), st.sampled_from(EXPONENTS), min_size=1, max_size=3),
    )
    def test_conversion_to_code_units(self, system: UnitSystem, number: float, factors: dict[str, float]) -> None:
        """Check that a value with a unit converts to code units for given dimensions, to within 8 ulp (UNI20).

        The reference is computed exactly, at 50 digits, from the double-precision values of the symbols and the code
        units.
        """
        ## repr writes the number so that it reads back as the same double; :g writes an exponent without a trailing
        ## .0, as UNI19 requires of integers ("-1", "0.5").
        text = f"{number!r} " + " ".join(f"{symbol}^{exponent:g}" for symbol, exponent in factors.items())
        actual = system.to_code_units(text, dimensions(factors))

        ## The powers and products of the expression and of the code unit, the division and the multiplication by the
        ## number each round once. In a million random conversions the largest error was 4 ulp, half the tolerance.
        expected = exact(number, factors)
        assert abs(actual - expected) <= 8 * math.ulp(expected), text

    ## Run this test once for every named unit of UNI03.
    @pytest.mark.parametrize("name", list(NAMED_UNITS))
    def test_conversion_for_a_named_unit(self, system: UnitSystem, name: str) -> None:
        """Check that converting for a named unit, such as density, gives the same as for its dimensions (UNI20)."""
        ## A value in the unit of the label, converted once for the name and once for the dimensions. A named unit is
        ## computed from its dimensions by the same arithmetic (UNI03), so the two must agree exactly.
        text = f"2.5 {LABELS[name]}"
        assert system.to_code_units(text, name) == system.to_code_units(text, NAMED_UNITS[name])

    def test_magnetic_field_uses_its_named_unit(self, system: UnitSystem) -> None:
        """Check that a field in gauss converts with the code unit of the magnetic field, sqrt(4 pi) included (UNI20).

        A field of "1e-6 G" must convert to 1e-6 gauss divided by the code unit of UNI07.
        """
        actual = system.to_code_units("1e-6 G", "magnetic_field")

        ## The exact reference: 1e-6 gauss divided by sqrt(4 pi p_u), with p_u = M / (L T^2) the code unit of pressure,
        ## as in the test of UNI07.
        with localcontext() as context:
            context.prec = 50
            pressure = Decimal(MASS) / (Decimal(LENGTH) * Decimal(TIME) ** 2)
            expected = float(Decimal(1e-6) / (4 * PI * pressure).sqrt())
        assert abs(actual - expected) <= 8 * math.ulp(expected)

        ## Converted for the dimensions of the gauss instead, the same field comes out larger by sqrt(4 pi): the factor
        ## that the name of the unit is there to include. The tolerance allows for a few ulp in either value.
        by_dimensions = system.to_code_units("1e-6 G", MAGNETIC_FIELD)
        assert math.isclose(by_dimensions, actual * np.sqrt(4 * np.pi), rel_tol=1e-14)

    def test_temperature_stays_in_kelvin(self, system: UnitSystem) -> None:
        """Check that the temperature dimension of a value stays in kelvin (UNI20).

        A value of "1e6 K" in kelvin is 1e6, and in a unit such as erg K^-1 only the energy is converted to code units.
        """
        ## A temperature alone is not converted at all, so it comes out exactly as written.
        assert system.to_code_units("1e6 K", {"temperature": 1}) == 1e6

        ## Boltzmann's constant in erg K^-1: the erg is converted to code units of energy, the kelvin is kept.
        kelvin_dimensions = {"length": 2, "mass": 1, "time": -2, "temperature": -1}
        actual = system.to_code_units("1.380649e-16 erg K^-1", kelvin_dimensions)
        expected = exact(1.380649e-16, {"erg": 1, "K": -1})
        assert abs(actual - expected) <= 8 * math.ulp(expected)

    def test_dimensionless_value(self, system: UnitSystem) -> None:
        """Check that a value whose expression has no dimensions converts for a dimensionless unit (UNI20).

        Its value in code units is the number its expression stands for, as "2 km cm^-1" is 2e5.
        """
        ## km is exactly 1e5 cm, so this conversion is exact. Dimensions given as exponents that are all zero are the
        ## same as dimensionless.
        assert system.to_code_units("2 km cm^-1", "dimensionless") == 2e5
        assert system.to_code_units("2 km cm^-1", {"length": 0, "mass": 0, "time": 0, "temperature": 0}) == 2e5

        ## A Myr is a million years, but yr^-1 is the inverse of the year rounded to double precision, so this one is
        ## exact only to within the tolerance of UNI20.
        actual = system.to_code_units("1 Myr yr^-1", "dimensionless")
        assert abs(actual - 1e6) <= 8 * math.ulp(1e6)

    ## Run this test for each value with a unit and a given unit of other dimensions: lengths and densities given for a
    ## time and a pressure, a temperature for a dimensionless unit, and a field without the time dimension. ids=str
    ## names each case by its two values.
    @pytest.mark.parametrize(
        ("text", "unit"),
        [
            ("1 pc", "time"),
            ("1 pc", {"time": 1}),
            ("1e-27 g cm^-3", "pressure"),
            ("1e6 K", "dimensionless"),
            ("1e-6 G", {"length": -0.5, "mass": 0.5}),
        ],
        ids=str,
    )
    def test_wrong_dimensions_are_refused(self, system: UnitSystem, text: str, unit: str | dict[str, float]) -> None:
        """Check that a value whose dimensions differ from those of the given unit is refused, naming both (UNI20).

        For example, "1 pc", a length, given for a time.
        """
        ## The message names the value and the unit it was given for, each as Python writes it.
        with pytest.raises(ValueError) as refusal:
            system.to_code_units(text, unit)
        assert repr(text) in str(refusal.value)
        assert repr(unit) in str(refusal.value)

    ## Run this test for each unit of none of the three forms: a misspelt named unit, one in the wrong case, a misspelt
    ## dimension, exponents that are not multiples of a quarter or not numbers, and a number instead of a unit. Any,
    ## because these are deliberately not of the type a unit has.
    @pytest.mark.parametrize(
        "unit", ["densty", "Density", {"lenght": 1}, {"length": 0.3}, {"length": True}, {"length": "1"}, 5], ids=str
    )
    def test_invalid_unit_is_refused(self, system: UnitSystem, unit: Any) -> None:
        """Check that a unit that is not dimensionless, a named unit or dimensions is refused, naming it (UNI20).

        A misspelt name or dimension is refused as such, rather than as a value of other dimensions.
        """
        with pytest.raises(ValueError, match=re.escape(repr(unit))):
            system.to_code_units("1 pc", unit)
