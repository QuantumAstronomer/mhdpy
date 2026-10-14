"""Tests of values with a unit: how they are written (UNI19) and converted to code units (UNI20)."""

import re

import pytest

from mhdpy.foundation import units

## A test that is planned but not written yet. Its body is pytest.fail("Not written yet."), which this marker declares
## an expected failure ("xfail"), so the suite stays green while the test is visibly unfinished: pytest reports it as
## "x" rather than as passed or failed. raises= accepts only that deliberate failure, so a stub that crashed for any
## other reason would still fail. strict=True turns a stub that unexpectedly passes into a failure, so the marker cannot
## be forgotten once the test is written. When a test is written, its marker is removed.
NOT_WRITTEN = pytest.mark.xfail(reason="not written yet", raises=pytest.fail.Exception, strict=True)

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
        value, read = units.parse(text)

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
            units.parse(text)

    @NOT_WRITTEN
    def test_half_integer_exponents(self) -> None:
        """Check that an exponent may be a half-integer written with a decimal point, such as g^0.5 (UNI19)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_every_label_is_a_unit_expression(self) -> None:
        """Check that the label of every named unit can be read as a unit expression (UNI04, UNI19).

        Its dimensions must be those of the named unit, so that the unit a file reports is a unit a user can write.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_symbols_have_their_values(self) -> None:
        """Check the value in cgs and the dimensions of every unit symbol (UNI19).

        The cgs symbols have the values of their units (cm, g, s, K are 1; dyn, erg and G follow from them), km is
        exactly 1e5 cm, and the astronomical symbols have the values of the constants of UNI11.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_unknown_symbol_is_refused(self) -> None:
        """Check that a unit symbol that is not one of UNI19 is refused, naming the symbol (UNI19).

        A misspelt symbol ("Mry") and an SI unit ("m", "kg") alike.
        """
        pytest.fail("Not written yet.")

    ## ---- How a value with a unit is converted to code units (UNI20) ----

    @NOT_WRITTEN
    def test_conversion_to_code_units(self) -> None:
        """Check that a value with a unit converts to code units for given dimensions, to within 8 ulp (UNI20).

        The reference is computed exactly, at 50 digits, from the double-precision values of the symbols and the code
        units.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_conversion_for_a_named_unit(self) -> None:
        """Check that converting for a named unit, such as density, gives the same as for its dimensions (UNI20)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_magnetic_field_uses_its_named_unit(self) -> None:
        """Check that a field in gauss converts with the code unit of the magnetic field, sqrt(4 pi) included (UNI20).

        A field of "1e-6 G" must convert to 1e-6 gauss divided by the code unit of UNI07.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_temperature_stays_in_kelvin(self) -> None:
        """Check that the temperature dimension of a value stays in kelvin (UNI20).

        A value of "1e6 K" in kelvin is 1e6, and in a unit such as erg K^-1 only the energy is converted to code units.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_dimensionless_value(self) -> None:
        """Check that a value whose expression has no dimensions converts for a dimensionless unit unchanged (UNI20)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_wrong_dimensions_are_refused(self) -> None:
        """Check that a value whose dimensions differ from those of the given unit is refused, naming both (UNI20).

        For example, "1 pc", a length, given for a time.
        """
        pytest.fail("Not written yet.")
