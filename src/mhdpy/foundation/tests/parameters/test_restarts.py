"""Tests of the parameters of a restarted run: the record as the lowest layer, and what may change (PAR15-PAR17)."""

import pytest

from mhdpy.foundation.tests.parameters import NOT_WRITTEN


class TestRestarts:
    """PAR15-PAR17: a restart continues with the values of the original run, and changes only what may change."""

    ## ---- The record as the lowest layer (PAR15) ----

    @NOT_WRITTEN
    def test_record_replaces_the_defaults(self) -> None:
        """Check that on restart every parameter not given anew keeps its recorded value, not its default (PAR15).

        A restart then needs no parameter file at all, and each value records the restart record as its origin
        (PAR10).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_parameter_missing_from_record_takes_its_default(self) -> None:
        """Check that a declared parameter missing from the record takes its default, without refusal (PAR15)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_recorded_name_no_longer_declared_is_ignored(self) -> None:
        """Check that a name in the record that is no longer declared is ignored, without refusal (PAR15)."""
        pytest.fail("Not written yet.")

    ## ---- What may change (PAR16) ----

    @NOT_WRITTEN
    def test_changeable_parameter_may_change(self) -> None:
        """Check that a changeable parameter takes a new value from the parameter file or an override (PAR16)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_changeable_parameter_not_given_keeps_its_record(self) -> None:
        """Check that a changeable parameter given by neither the file nor an override keeps its recorded value.

        It does not fall back to its default (PAR16).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_change_to_fixed_parameter_is_refused(self) -> None:
        """Check that a new value for a fixed parameter is refused, stating that the restart file fixes it (PAR16)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_equal_value_is_not_a_change(self) -> None:
        """Check that a fixed parameter given its recorded value is accepted, as no change (PAR16).

        The original parameter file can then be used unchanged for the restart, a value with a unit included.
        """
        pytest.fail("Not written yet.")

    ## ---- The list of changes (PAR17) ----

    @NOT_WRITTEN
    def test_changes_are_listed(self) -> None:
        """Check that every parameter whose value differs from the record is listed with both values (PAR17)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_change_of_selected_group_is_listed(self) -> None:
        """Check that a set of alternatives whose selected group changed is listed with both groups (PAR17, PAR22)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_missing_and_ignored_names_are_listed(self) -> None:
        """Check that missing parameters are listed with their default, and ignored names with their recorded value.

        These are the cases of PAR15 that are reported rather than refused (PAR17).
        """
        pytest.fail("Not written yet.")
