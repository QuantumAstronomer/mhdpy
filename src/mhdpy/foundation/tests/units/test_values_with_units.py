"""Tests of values with a unit: how they are written (UNI19) and converted to code units (UNI20)."""

import pytest

## A test that is planned but not written yet. Its body is pytest.fail("Not written yet."), which this marker declares
## an expected failure ("xfail"), so the suite stays green while the test is visibly unfinished: pytest reports it as
## "x" rather than as passed or failed. raises= accepts only that deliberate failure, so a stub that crashed for any
## other reason would still fail. strict=True turns a stub that unexpectedly passes into a failure, so the marker cannot
## be forgotten once the test is written. When a test is written, its marker is removed.
NOT_WRITTEN = pytest.mark.xfail(reason="not written yet", raises=pytest.fail.Exception, strict=True)


class TestValuesWithUnits:
    """UNI19-UNI20: a value with a unit, such as "100 pc", is read and converted to code units."""

    ## ---- How a value with a unit is written (UNI19) ----

    @NOT_WRITTEN
    def test_value_with_unit_is_read(self) -> None:
        """Check that a number and a unit expression are read from a string such as "1e-27 g cm^-3" (UNI19).

        The number is read as a float, and the expression as its factors: each symbol with its exponent, 1 when none
        is written.
        """
        pytest.fail("Not written yet.")

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
    def test_malformed_value_is_refused(self) -> None:
        """Check that a string not of the form of UNI19 is refused, naming the string (UNI19).

        Among them: a number or a unit alone, two spaces, a division sign, an exponent that is not an integer or a
        half-integer, and a number that cannot be read.
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
