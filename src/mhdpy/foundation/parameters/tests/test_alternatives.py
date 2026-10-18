"""Tests of alternatives and of conditions across parameters (PAR22-PAR23)."""

import re
from pathlib import Path
from typing import Any

import pytest

from mhdpy.foundation.parameters.declarations import Alternatives, Declarations, Parameter
from mhdpy.foundation.parameters.resolution import ParameterError, resolve
from mhdpy.foundation.parameters.tests import NOT_WRITTEN, parameter_file

## The parameters of the ambient medium, whose density can be given in two ways: as a mass density, or from a number
## density, a temperature and a metallicity (PAR22).
PARAMETERS = [
    Parameter(name="ambient.rho", type=float, default=1.0, doc="The mass density.", unit="density"),
    Parameter(name="ambient.n", type=float, default=1.0, doc="The number density.", unit={"length": -3}),
    Parameter(name="ambient.temperature", type=float, default=1e4, doc="The temperature.", unit={"temperature": 1}),
    Parameter(name="ambient.metallicity", type=float, default=0.02, doc="The metallicity.", unit="dimensionless"),
]

## The two groups of the ambient density, by their names.
GROUPS = {
    "mass_density": ["ambient.rho"],
    "number_density": ["ambient.n", "ambient.temperature", "ambient.metallicity"],
}


def alternatives(**changes: Any) -> Alternatives:
    """Return the alternatives of the ambient density, with the given items changed."""
    items: dict[str, Any] = {
        "name": "ambient.density",
        "doc": "The density of the ambient medium.",
        "groups": GROUPS,
        "default": "mass_density",
    }
    return Alternatives(**(items | changes))


## The parameters of the ambient medium with the alternatives of its density, as a run declares them.
AMBIENT = Declarations(parameters=PARAMETERS, alternatives=[alternatives()])

## The number density and the temperature of the ambient medium, given in a parameter file or as overrides; the
## metallicity is not given (PAR22).
NUMBER_DENSITY: dict[str, tuple[str | None, list[str]]] = {
    "parameter file": ("[ambient]\nn = 100.0\ntemperature = 8000.0\n", []),
    "overrides": (None, ["ambient.n=100.0", "ambient.temperature=8000.0"]),
}

## Values for both groups of the ambient density, from one layer or from two, each with a misspelt name as well: a
## mistake of another kind, reported in the same error (PAR14).
BOTH_GROUPS: dict[str, tuple[str | None, list[str]]] = {
    "one layer": (None, ["ambient.rho=2.0", "ambient.n=100.0", "ambient.pressure=1.0"]),
    "file and override": ("[ambient]\nrho = 2.0\n", ["ambient.n=100.0", "ambient.pressure=1.0"]),
}


## Alternatives that break a rule of PAR22, each by the changes to the alternatives of the ambient density in every set
## of alternatives declared, and what the refusal names. Some are refused as they are made, the others when they are
## gathered with the parameters, which alone tell which parameters are declared.
# fmt: off
INVALID: dict[str, tuple[list[dict[str, Any]], str]] = {
    "name of one part":         ([{"name": "density"}],                                         "'density'"),
    "no documentation":         ([{"doc": "  "}],                                               "'ambient.density'"),
    "one group":                ([{"groups": {"mass_density": ["ambient.rho"]}}],               "'ambient.density'"),
    "empty group":              ([{"groups": GROUPS | {"pressure": []}}],                       "'pressure'"),
    "default not a group":      ([{"default": "pressure"}],                                     "'pressure'"),
    "undeclared parameter":     ([{"groups": GROUPS | {"pressure": ["ambient.pressure"]}}],     "'ambient.pressure'"),
    "parameter in two groups":  ([{"groups": GROUPS | {"pressure": ["ambient.rho"]}}],          "'ambient.rho'"),
    "parameter in two sets":    ([{}, {"name": "ambient.mass"}],                                "'ambient.rho'"),
    "set declared twice":       ([{}, {}],                                                      "'ambient.density'"),
}
# fmt: on


class TestAlternatives:
    """PAR22-PAR23: a quantity may be given in one of several ways, and conditions may involve several parameters."""

    ## ---- Alternatives (PAR22) ----

    def test_alternatives_are_declared(self) -> None:
        """Check that alternatives are declared as two or more groups of parameters, one of them the default (PAR22).

        For example "ambient.rho", or "ambient.n", "ambient.temperature" and "ambient.metallicity".
        """
        density = alternatives()
        declarations = Declarations(parameters=PARAMETERS, alternatives=[density])

        ## The alternatives keep what they were declared with, the groups as tuples, and the set keeps them.
        assert density.name == "ambient.density"
        assert density.doc == "The density of the ambient medium."
        assert density.groups == {group: tuple(names) for group, names in GROUPS.items()}
        assert density.default == "mass_density"
        assert declarations.alternatives == (density,)

        ## A set declared without alternatives has none.
        assert Declarations(parameters=PARAMETERS).alternatives == ()

    @pytest.mark.parametrize(("changes", "named"), list(INVALID.values()), ids=list(INVALID))
    def test_invalid_alternatives_are_refused(self, changes: list[dict[str, Any]], named: str) -> None:
        """Check that a declaration of alternatives that breaks the rules is refused (PAR22).

        Fewer than two groups, a parameter that is not declared or appears in more than one group, or a default that is
        not one of the groups.
        """
        with pytest.raises(ValueError, match=re.escape(named)):
            Declarations(parameters=PARAMETERS, alternatives=[alternatives(**change) for change in changes])

    def test_default_group_is_selected_when_nothing_is_given(self) -> None:
        """Check that with no parameter of any group given, the default group is selected (PAR22)."""
        parameters = resolve(AMBIENT)
        assert parameters.selected == {"ambient.density": "mass_density"}

    ## text is that of the parameter file, or None for a run without one.
    @pytest.mark.parametrize(("text", "overrides"), list(NUMBER_DENSITY.values()), ids=list(NUMBER_DENSITY))
    def test_giving_a_parameter_selects_its_group(self, tmp_path: Path, text: str | None, overrides: list[str]) -> None:
        """Check that a value for any parameter of a group, in the file or an override, selects that group (PAR22).

        The parameters of the group that are not given keep their default: "ambient.n" and "ambient.temperature"
        given, "ambient.metallicity" left at its default.
        """
        file = parameter_file(tmp_path, text) if text is not None else None
        parameters = resolve(AMBIENT, file=file, overrides=overrides)

        assert parameters.selected == {"ambient.density": "number_density"}
        assert parameters["ambient.n"] == 100.0
        assert parameters["ambient.metallicity"] == 0.02

    @pytest.mark.parametrize(("text", "overrides"), list(BOTH_GROUPS.values()), ids=list(BOTH_GROUPS))
    def test_values_for_two_groups_are_refused(self, tmp_path: Path, text: str | None, overrides: list[str]) -> None:
        """Check that values given for parameters of two groups are refused, naming those given in each (PAR22).

        "ambient.rho" and "ambient.n" together, whether from one layer or from the file and an override; the refusal is
        reported among the other mistakes (PAR14).
        """
        file = parameter_file(tmp_path, text) if text is not None else None
        with pytest.raises(ParameterError) as refusal:
            resolve(AMBIENT, file=file, overrides=overrides)

        ## The misspelt name, then the alternatives: a mistake of several values, with no single origin, that names
        ## the parameters given for each group.
        misspelt, density = refusal.value.mistakes
        assert misspelt.name == "ambient.pressure"
        assert density.name == "ambient.density"
        assert density.origin is None
        assert "'ambient.rho'" in density.message
        assert "'ambient.n'" in density.message

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
