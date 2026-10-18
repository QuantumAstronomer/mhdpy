"""Tests of the checks of values against their declarations: names, types, conditions, all at once (PAR11-PAR14)."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from mhdpy.foundation.parameters.declarations import Declarations, Parameter
from mhdpy.foundation.parameters.resolution import Mistake, Origin, ParameterError, resolve
from mhdpy.foundation.parameters.tests import NOT_WRITTEN, parameter_file

## The parameters of a small run, one of every type of PAR03 and lists of strings and of floats, against which the
## values of the tests are checked.
DECLARATIONS = Declarations(
    parameters=[
        Parameter(name="hydro.cfl", type=float, default=0.4, doc="The Courant number.", unit="dimensionless"),
        Parameter(name="hydro.gamma", type=float, default=5 / 3, doc="The adiabatic index.", unit="dimensionless"),
        Parameter(name="hydro.solver", type=str, default="hllc", doc="The Riemann solver."),
        Parameter(name="mesh.nx1", type=int, default=64, doc="The number of cells along x1.", unit="dimensionless"),
        Parameter(name="output.variables", type=list[str], default=["rho"], doc="The variables written."),
        Parameter(name="output.times", type=list[float], default=[], doc="The times of the snapshots.", unit="time"),
        Parameter(name="cooling.enabled", type=bool, default=False, doc="Whether the gas cools radiatively."),
    ]
)


def only_mistake(overrides: Mapping[str, Any]) -> Mistake:
    """Return the one mistake found in resolving the declarations with the given overrides.

    The test fails if no ParameterError is raised, or if it holds more than one mistake.
    """
    with pytest.raises(ParameterError) as refusal:
        resolve(DECLARATIONS, overrides=overrides)

    ## The one mistake, unpacked from the tuple of mistakes, which fails if there are more.
    (mistake,) = refusal.value.mistakes
    return mistake


class TestChecks:
    """PAR11-PAR14: every value is checked against its declaration, and all mistakes reported, before a run starts."""

    ## ---- Unknown names (PAR11) ----

    def test_unknown_name_is_refused(self, tmp_path: Path) -> None:
        """Check that a name that is not declared is refused, naming it, from a file and from an override (PAR11)."""
        ## gravity.constant, in the file, and mesh.nx3, an override, are declared by no module of this run.
        file = parameter_file(tmp_path, "[gravity]\nconstant = 1.0\n")
        with pytest.raises(ParameterError) as refusal:
            resolve(DECLARATIONS, file=file, overrides=["mesh.nx3=64"])

        ## Both are refused together, in the order they were given, each with its origin; the message names both.
        ## refusal.value is the error that was raised.
        mistakes = refusal.value.mistakes
        assert [mistake.name for mistake in mistakes] == ["gravity.constant", "mesh.nx3"]
        assert mistakes[0].origin == Origin(source="file", value=1.0, file=str(file))
        assert mistakes[1].origin == Origin(source="override", value=64)
        assert "'gravity.constant'" in str(refusal.value)
        assert "'mesh.nx3'" in str(refusal.value)

    @pytest.mark.parametrize("name", ["hydro.cfll", "hdyro.cfl"])
    def test_misspelt_name_suggests_the_closest(self, name: str) -> None:
        """Check that the message for a misspelt name suggests the closest declared name (PAR11).

        "hydro.cfll" and "hdyro.cfl" are both answered with "hydro.cfl".
        """
        with pytest.raises(ParameterError) as refusal:
            resolve(DECLARATIONS, overrides=[f"{name}=0.3"])

        ## The one mistake, unpacked from the tuple of mistakes, which fails if there are more.
        (mistake,) = refusal.value.mistakes
        assert mistake.name == name
        assert mistake.message.endswith("did you mean 'hydro.cfl'?")

    def test_no_suggestion_when_nothing_is_close(self) -> None:
        """Check that a name close to no declared name is refused without a suggestion (PAR11)."""
        with pytest.raises(ParameterError) as refusal:
            resolve(DECLARATIONS, overrides=["gravity.constant=1.0"])

        (mistake,) = refusal.value.mistakes
        assert "'gravity.constant'" in mistake.message
        assert "did you mean" not in mistake.message

    ## ---- Types (PAR12) ----

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("hydro.cfl", 0.3),
            ("hydro.solver", "hlld"),
            ("mesh.nx1", 128),
            ("cooling.enabled", True),
            ("output.variables", ["rho", "pressure"]),
            ("output.times", [1.0, 2.5]),
        ],
    )
    def test_values_of_the_declared_type_are_accepted(self, name: str, value: Any) -> None:
        """Check that a value of the declared type is accepted as it is, for each type of PAR03 (PAR12)."""
        parameters = resolve(DECLARATIONS, overrides={name: value})

        ## The type is compared as well, as == alone cannot tell them apart in Python: 1 == 1.0 == True.
        assert parameters[name] == value
        assert type(parameters[name]) is type(value)

    def test_integer_for_float_is_converted(self) -> None:
        """Check that an integer given for a float parameter is accepted and converted to a float (PAR12)."""
        ## A single float, and a list of floats with one element an integer.
        parameters = resolve(DECLARATIONS, overrides={"hydro.cfl": 1, "output.times": [1, 2.5]})

        assert parameters["hydro.cfl"] == 1.0
        assert type(parameters["hydro.cfl"]) is float
        assert parameters["output.times"] == [1.0, 2.5]
        assert all(type(time) is float for time in parameters["output.times"])

    @pytest.mark.parametrize(("name", "value"), [("hydro.cfl", True), ("mesh.nx1", False)])
    def test_boolean_for_number_is_refused(self, name: str, value: bool) -> None:
        """Check that a boolean given for an int or float parameter is refused, though Python treats it as one.

        The rule is explicit because bool is a subclass of int in Python (PAR12).
        """
        mistake = only_mistake({name: value})
        assert mistake.name == name
        assert "must be of type" in mistake.message

    def test_float_for_int_is_refused(self) -> None:
        """Check that a float given for an int parameter is refused, even when its value is whole, as 4000.0 (PAR12)."""
        mistake = only_mistake({"mesh.nx1": 4000.0})

        ## The message in full: the name, the type expected, and the type and value given.
        assert mistake.message == "'mesh.nx1' must be of type int, got float 4000.0."

    @pytest.mark.parametrize(("name", "value"), [("hydro.cfl", "0.4"), ("cooling.enabled", "true"), ("mesh.nx1", "64")])
    def test_string_is_not_converted(self, name: str, value: str) -> None:
        """Check that a string given for a parameter of another type is refused, not converted (PAR12).

        "0.4" for a float and "true" for a bool alike; only a value with a unit is a string accepted for a number.
        """
        mistake = only_mistake({name: value})
        assert mistake.name == name
        assert "must be of type" in mistake.message

    ## A list with an element of another type, of each list type, and a single value where a list is declared.
    @pytest.mark.parametrize(
        ("name", "value"),
        [("output.variables", ["rho", 3]), ("output.times", [1.0, True]), ("output.variables", "rho")],
    )
    def test_list_elements_are_checked(self, name: str, value: Any) -> None:
        """Check that every element of a list is checked by the same rules, and that a non-list is refused (PAR12)."""
        mistake = only_mistake({name: value})
        assert mistake.name == name
        assert "must be of type list" in mistake.message

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
