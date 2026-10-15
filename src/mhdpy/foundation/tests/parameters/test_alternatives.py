"""Tests of alternatives and of conditions across parameters (PAR22-PAR23)."""

import pytest

from mhdpy.foundation.tests.parameters import NOT_WRITTEN


class TestAlternatives:
    """PAR22-PAR23: a quantity may be given in one of several ways, and conditions may involve several parameters."""

    ## ---- Alternatives (PAR22) ----

    @NOT_WRITTEN
    def test_alternatives_are_declared(self) -> None:
        """Check that alternatives are declared as two or more groups of parameters, one of them the default (PAR22).

        For example "ambient.rho", or "ambient.n", "ambient.temperature" and "ambient.metallicity".
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_invalid_alternatives_are_refused(self) -> None:
        """Check that a declaration of alternatives that breaks the rules is refused (PAR22).

        Fewer than two groups, a parameter that is not declared or appears in more than one group, or a default that is
        not one of the groups.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_default_group_is_selected_when_nothing_is_given(self) -> None:
        """Check that with no parameter of any group given, the default group is selected (PAR22)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_giving_a_parameter_selects_its_group(self) -> None:
        """Check that a value for any parameter of a group, in the file or an override, selects that group (PAR22).

        The parameters of the group that are not given keep their default: "ambient.n" and "ambient.temperature"
        given, "ambient.metallicity" left at its default.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_values_for_two_groups_are_refused(self) -> None:
        """Check that values given for parameters of two groups are refused, naming those given in each (PAR22).

        "ambient.rho" and "ambient.n" together, whether from one layer or from the file and an override; the refusal is
        reported among the other mistakes (PAR14).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_recorded_group_stays_selected_on_restart(self) -> None:
        """Check that on restart the group selected by the original run stays selected when nothing is given (PAR22).

        Also when it was not the default group, which the defaults alone would not select.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_selecting_another_group_on_restart(self) -> None:
        """Check that selecting another group on restart is accepted only if every parameter of both is changeable.

        Otherwise it is refused, as a change to a fixed parameter is (PAR22, PAR16).
        """
        pytest.fail("Not written yet.")

    ## ---- Conditions across parameters (PAR23) ----

    @NOT_WRITTEN
    def test_condition_across_parameters_is_checked(self) -> None:
        """Check that values failing a condition on several parameters are refused, with its description (PAR23).

        For example "'domain.r_inner' must be smaller than 'domain.r_outer'", stating both values.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_condition_applies_in_code_units(self) -> None:
        """Check that a condition applies to the resolved values in code units, values with a unit converted (PAR23)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_condition_waits_for_the_checks_of_its_values(self) -> None:
        """Check that a condition is not evaluated when a value it involves failed its own type or check (PAR23).

        That mistake is reported once, by itself, and not again through the condition.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_condition_is_reported_with_the_other_mistakes(self) -> None:
        """Check that a failed condition is reported in one error with the mistakes of single values (PAR23, PAR14)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_condition_on_undeclared_parameter_is_refused(self) -> None:
        """Check that a condition naming a parameter that is not declared is refused when declared (PAR23)."""
        pytest.fail("Not written yet.")
