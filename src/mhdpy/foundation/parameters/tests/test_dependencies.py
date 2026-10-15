"""Tests of the dependencies of the parameters (PAR21)."""

import pytest

from mhdpy.foundation.parameters.tests import NOT_WRITTEN


class TestDependencies:
    """PAR21: the parameters need nothing beyond the standard library, and are given the unit system of a run."""

    @NOT_WRITTEN
    def test_standard_library_only(self) -> None:
        """Check that importing the parameters imports nothing beyond the standard library and mhdpy (PAR21).

        NumPy included: the parameters are read before anything else is loaded.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_unit_system_is_not_imported(self) -> None:
        """Check that importing the parameters does not import the unit system, which a run passes in (PAR21)."""
        pytest.fail("Not written yet.")
