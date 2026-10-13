"""Fixtures shared by the tests of the unit system.

A fixture is a function that provides a value to tests: a test that names the fixture as an argument receives its value
from pytest. Pytest finds the fixtures of this file for every test module in this folder.
"""

import pytest

from mhdpy.foundation import units
from mhdpy.foundation.tests.units.reference import LENGTH, MASS, TIME


## scope="session" creates each unit system once for the whole test run and hands the same object to every test that
## asks for it. Sharing it is safe because a unit system cannot be changed (UNI12). The session scope is also what the
## tests with Hypothesis need: Hypothesis refuses a fixture that is created anew for each test, because one value would
## then be used for all the examples it draws, which a fixture of that kind does not promise.
@pytest.fixture(scope="session")
def system() -> units.UnitSystem:
    """Return the unit system of 1 kpc, 1e5 solar masses and 1 Myr, without a default mean molecular weight."""
    return units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)


@pytest.fixture(scope="session")
def system_with_default() -> units.UnitSystem:
    """Return the same unit system, with a default mean molecular weight of 0.6 (UNI09)."""
    return units.UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)
