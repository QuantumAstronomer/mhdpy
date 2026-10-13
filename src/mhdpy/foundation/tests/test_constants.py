"""Tests of the physical constants and astronomical units: requirements UNI10-UNI11.

The requirements are part of those of the unit system (docs/requirements/L0-foundation/units.md), which converts the
constants to code units; the other requirements of that document are tested in test_units.py. Each test names the
requirements it checks in its docstring.
"""

import pytest

## A test that is planned but not written yet, declared an expected failure; see the marker of the same name in
## test_units.py for how it works. When a test is written, its marker is removed.
NOT_WRITTEN = pytest.mark.xfail(reason="not written yet", raises=pytest.fail.Exception, strict=True)


class TestPhysicalConstants:
    """UNI10-UNI11: physical constants and astronomical units from cited sources."""

    @NOT_WRITTEN
    def test_measured_constants_in_cgs(self) -> None:
        """Check the measured constants in cgs against the values of CODATA 2022 (UNI10)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_exact_constants_in_cgs(self) -> None:
        """Check that the exact constants are the doubles nearest to their exact values in cgs (UNI10).

        The constants exact by the definition of the SI are c, h and k_B.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_hydrogen_mass(self) -> None:
        """Check the mass of the hydrogen atom against the Atomic Mass Evaluation 2020 (UNI10).

        The reference is the atomic mass of 1H in units of the atomic mass unit.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_constants_in_code_units(self) -> None:
        """Check that every constant converts to code units by its dimensions (UNI10).

        A constant containing the kelvin, such as k_B, keeps it: code units have no temperature dimension.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_astronomical_units(self) -> None:
        """Check the astronomical units in cgs against the IAU resolutions (UNI11)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_unit_system_from_astronomical_units(self) -> None:
        """Check that a unit system can be defined in astronomical units (UNI11).

        The example of the requirement: 1 kpc, 1e5 solar masses and 1 Myr.
        """
        pytest.fail("Not written yet.")
