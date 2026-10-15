"""Tests of reading the resolved parameters and of their record (PAR18-PAR19)."""

import pytest

from mhdpy.foundation.parameters.tests import NOT_WRITTEN


class TestRecords:
    """PAR18-PAR19: resolved parameters are read by name, never change, and are recorded exactly."""

    ## ---- Access (PAR18) ----

    @NOT_WRITTEN
    def test_values_are_read_by_name(self) -> None:
        """Check that each resolved value can be read by its name (PAR18)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_values_have_their_type_and_code_units(self) -> None:
        """Check that each value is of its declared type and in code units, however it was given (PAR18).

        A float parameter given an integer or a value with a unit reads as a float in code units; a parameter in kelvin
        reads in kelvin.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_resolved_parameters_cannot_change(self) -> None:
        """Check that a resolved value cannot be changed or added, nor a list value changed in place (PAR18)."""
        pytest.fail("Not written yet.")

    ## ---- The record (PAR19) ----

    @NOT_WRITTEN
    def test_record_is_plain_values_in_code_units(self) -> None:
        """Check that the record holds one plain value per name, in code units, for every declared parameter (PAR19)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_record_includes_the_selected_groups(self) -> None:
        """Check that the record holds the group selected for each set of alternatives (PAR19, PAR22)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_record_survives_json_exactly(self) -> None:
        """Check that the record written as JSON and read back is identical, every float bit for bit (PAR19)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_resolving_from_the_record_gives_the_same_values(self) -> None:
        """Check that resolving with the record as the restart layer gives the same values, bit for bit (PAR19, PAR15).

        Values given with a unit included, which the record holds in code units and are not converted again; the
        selected groups of alternatives are the same as well.
        """
        pytest.fail("Not written yet.")
