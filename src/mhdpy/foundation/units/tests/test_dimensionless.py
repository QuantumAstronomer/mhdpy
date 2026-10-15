"""Tests of simulations without a unit system (UNI15-UNI17), which need the driver and are skipped until it exists."""

import pytest

## Tests that can only be written once later layers exist: physics modules declaring what they need (D12.1) and a
## simulation that can be set up and run (D13).
NEEDS_DRIVER = pytest.mark.skip(reason="needs physics modules and the driver of a simulation (layers L6 and above)")


class TestDimensionlessSimulations:
    """UNI15-UNI17: simulations without a unit system, and the independence of results from the unit system."""

    @NEEDS_DRIVER
    def test_simulation_without_unit_system_runs(self) -> None:
        """Check that a simulation without a unit system runs, with every quantity in code units (UNI15)."""
        pytest.fail("Not written yet.")

    @NEEDS_DRIVER
    def test_module_needing_units_is_refused(self) -> None:
        """Check that a module needing physical constants is refused in a dimensionless simulation (UNI16).

        The refusal comes at set-up, before the run starts, and names the module.
        """
        pytest.fail("Not written yet.")

    @NEEDS_DRIVER
    def test_results_independent_of_unit_system(self) -> None:
        """Check that a problem posed in code units gives the same state with any unit system or none (UNI17).

        The state in code units must be identical bit for bit.
        """
        pytest.fail("Not written yet.")
