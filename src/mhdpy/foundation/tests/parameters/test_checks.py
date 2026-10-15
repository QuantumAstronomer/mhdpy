"""Tests of the checks of values against their declarations: names, types, conditions, all at once (PAR11-PAR14)."""

import pytest

from mhdpy.foundation.tests.parameters import NOT_WRITTEN


class TestChecks:
    """PAR11-PAR14: every value is checked against its declaration, and all mistakes reported, before a run starts."""

    ## ---- Unknown names (PAR11) ----

    @NOT_WRITTEN
    def test_unknown_name_is_refused(self) -> None:
        """Check that a name that is not declared is refused, naming it, from a file and from an override (PAR11)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_misspelt_name_suggests_the_closest(self) -> None:
        """Check that the message for a misspelt name suggests the closest declared name (PAR11).

        "hydro.cfll" and "hdyro.cfl" are both answered with "hydro.cfl".
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_no_suggestion_when_nothing_is_close(self) -> None:
        """Check that a name close to no declared name is refused without a suggestion (PAR11)."""
        pytest.fail("Not written yet.")

    ## ---- Types (PAR12) ----

    @NOT_WRITTEN
    def test_values_of_the_declared_type_are_accepted(self) -> None:
        """Check that a value of the declared type is accepted as it is, for each type of PAR03 (PAR12)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_integer_for_float_is_converted(self) -> None:
        """Check that an integer given for a float parameter is accepted and converted to a float (PAR12)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_boolean_for_number_is_refused(self) -> None:
        """Check that a boolean given for an int or float parameter is refused, though Python treats it as one.

        The rule is explicit because bool is a subclass of int in Python (PAR12).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_float_for_int_is_refused(self) -> None:
        """Check that a float given for an int parameter is refused, even when its value is whole, as 4000.0 (PAR12)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_string_is_not_converted(self) -> None:
        """Check that a string given for a parameter of another type is refused, not converted (PAR12).

        "0.4" for a float and "true" for a bool alike; only a value with a unit is a string accepted for a number.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_list_elements_are_checked(self) -> None:
        """Check that every element of a list is checked by the same rules, and that a non-list is refused (PAR12)."""
        pytest.fail("Not written yet.")

    ## ---- Conditions (PAR13) ----

    @NOT_WRITTEN
    def test_value_failing_its_check_is_refused(self) -> None:
        """Check that a value that does not satisfy its check is refused, stating the condition in its words (PAR13).

        For example "'hydro.cfl' must be in (0, 1], got 1.5".
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_check_applies_in_code_units(self) -> None:
        """Check that the check applies to the value in code units, after a value with a unit is converted (PAR13).

        A default given with a unit included, which can only be checked once converted (PAR03).
        """
        pytest.fail("Not written yet.")

    ## ---- All mistakes at once (PAR14) ----

    @NOT_WRITTEN
    def test_all_mistakes_are_reported_at_once(self) -> None:
        """Check that several mistakes, in a file and in overrides, are reported together, as one error (PAR14)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_each_mistake_is_described_in_full(self) -> None:
        """Check that each mistake is reported with the name, the origin of its value, the value and what was expected.

        The origin is that of PAR10: the default, the file by name, or an override (PAR14).
        """
        pytest.fail("Not written yet.")
