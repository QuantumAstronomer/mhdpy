"""Tests of alternatives and of conditions across parameters (PAR22-PAR23)."""

import dataclasses
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from mhdpy.foundation.parameters.declarations import Alternatives, Check, Declarations, JointCheck, Parameter
from mhdpy.foundation.parameters.resolution import Mistake, ParameterError, resolve
from mhdpy.foundation.parameters.tests import parameter_file
from mhdpy.foundation.units.constants import MEGAYEAR, PARSEC, SOLAR_MASS
from mhdpy.foundation.units.system import UnitSystem

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


## The radii of a domain, of which the inner must be smaller than the outer: a relation between two values that each
## satisfy their own checks (PAR23). The outer radius must also be positive by itself.
RADII = [
    Parameter(name="domain.r_inner", type=float, default=1.0, doc="The inner radius.", unit="length"),
    Parameter(
        name="domain.r_outer",
        type=float,
        default=10.0,
        doc="The outer radius.",
        unit="length",
        check=Check(lambda radius: radius > 0, "positive"),
    ),
]


## The joint check that the inner radius is smaller than the outer one. The tests that break its rules change it with
## dataclasses.replace, which makes a new joint check with the given items changed, checked as any other.
INNER_BELOW_OUTER = JointCheck(
    names=["domain.r_inner", "domain.r_outer"],
    condition=lambda values: values["domain.r_inner"] < values["domain.r_outer"],
    description="'domain.r_inner' must be smaller than 'domain.r_outer'",
)

## The parameters of the domain with the joint check of its radii, as a run declares them.
DOMAIN = Declarations(parameters=RADII, joint_checks=[INNER_BELOW_OUTER])

## The unit system of the joint checks in code units: code units of 1 pc, 1 solar mass and 1 Myr (PAR23).
UNITS = UnitSystem(length=PARSEC, mass=SOLAR_MASS, time=MEGAYEAR)


def only_mistake(overrides: Mapping[str, Any]) -> Mistake:
    """Return the one mistake found in resolving the domain with the given overrides.

    The test fails if no ParameterError is raised, or if it holds more than one mistake.
    """
    with pytest.raises(ParameterError) as refusal:
        resolve(DOMAIN, overrides=overrides)

    ## The one mistake, unpacked from the tuple of mistakes, which fails if there are more.
    (mistake,) = refusal.value.mistakes
    return mistake


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

    def test_recorded_group_stays_selected_on_restart(self) -> None:
        """Check that on restart the group selected by the original run stays selected when nothing is given (PAR22).

        Also when it was not the default group, which the defaults alone would not select.
        """
        ## The original run selects the number density, which is not the default group.
        record = resolve(AMBIENT, overrides=["ambient.n=100.0"]).to_record()

        ## On restart nothing is given: the recorded group stays selected, with the recorded values (PAR15).
        parameters = resolve(AMBIENT, record=record)
        assert parameters.selected == {"ambient.density": "number_density"}
        assert parameters["ambient.n"] == 100.0

        ## Without the record, nothing given selects the default group.
        assert resolve(AMBIENT).selected == {"ambient.density": "mass_density"}

    ## The parameters of the ambient medium changeable on restart: every one of them, which lets a restart select
    ## another group; or the mass density alone, which does not, as the parameters of the number density are fixed.
    @pytest.mark.parametrize(
        ("changeable", "accepted"),
        [(set(GROUPS["mass_density"] + GROUPS["number_density"]), True), (set(GROUPS["mass_density"]), False)],
        ids=["every parameter changeable", "one group fixed"],
    )
    def test_selecting_another_group_on_restart(self, changeable: set[str], accepted: bool) -> None:
        """Check that selecting another group on restart is accepted only if every parameter of both is changeable.

        Otherwise it is refused, as a change to a fixed parameter is (PAR22, PAR16).
        """
        ## The ambient medium with the given parameters changeable. dataclasses.replace makes a new declaration with
        ## the given items changed, checked as any other.
        parameters = [
            dataclasses.replace(parameter, changeable=parameter.name in changeable) for parameter in PARAMETERS
        ]
        declarations = Declarations(parameters=parameters, alternatives=[alternatives()])

        ## The original run selects the number density; the restart gives the mass density, at its recorded value, so
        ## that only the selection changes.
        record = resolve(declarations, overrides=["ambient.n=100.0"]).to_record()
        if accepted:
            restarted = resolve(declarations, record=record, overrides=["ambient.rho=1.0"])
            assert restarted.selected == {"ambient.density": "mass_density"}
            return
        with pytest.raises(ParameterError) as refusal:
            resolve(declarations, record=record, overrides=["ambient.rho=1.0"])

        ## One mistake, of the selection alone, with no single origin.
        (mistake,) = refusal.value.mistakes
        assert mistake.name == "ambient.density"
        assert mistake.origin is None
        assert mistake.message == (
            "'ambient.density' is fixed by the restart file at the group 'number_density', got the group "
            "'mass_density' by 'ambient.rho' (override). Another group may be selected on restart only if every "
            "parameter of both groups is changeable."
        )

    ## ---- Conditions across parameters (PAR23) ----

    def test_condition_across_parameters_is_checked(self) -> None:
        """Check that values failing a condition on several parameters are refused, with its description (PAR23).

        For example "'domain.r_inner' must be smaller than 'domain.r_outer'", stating both values.
        """
        ## The defaults satisfy the condition: 1 is smaller than 10.
        assert resolve(DOMAIN)["domain.r_inner"] == 1.0

        ## An inner radius of 20, each value valid by itself: a mistake of several values, with no single name or
        ## origin, stating the description and both values with their origins.
        mistake = only_mistake({"domain.r_inner": 20.0})
        assert mistake.name is None
        assert mistake.origin is None
        assert mistake.message == (
            "'domain.r_inner' must be smaller than 'domain.r_outer', got 'domain.r_inner' = 20.0 (override) and "
            "'domain.r_outer' = 10.0 (default)."
        )

    def test_condition_applies_in_code_units(self) -> None:
        """Check that a condition applies to the resolved values in code units, values with a unit converted (PAR23)."""
        ## 0.5 kpc is 500 in code units, larger than the outer radius of 10, although the number 0.5 is not: refused,
        ## with the value as given shown as well.
        with pytest.raises(ParameterError) as refusal:
            resolve(DOMAIN, overrides=["domain.r_inner=0.5 kpc"], units=UNITS)
        (mistake,) = refusal.value.mistakes
        assert "(given as '0.5 kpc', override)" in mistake.message

        ## 1e19 cm is about 3.2 in code units, smaller than 10, although the number 1e19 is not: accepted.
        parameters = resolve(DOMAIN, overrides=["domain.r_inner=1e19 cm"], units=UNITS)
        assert parameters["domain.r_inner"] == UNITS.to_code_units("1e19 cm", "length")

    ## An outer radius that fails its own check, and an inner radius of the wrong type; either would make the condition
    ## fail, or fail to be evaluated, if it were evaluated.
    @pytest.mark.parametrize(
        ("name", "value"), [("domain.r_outer", -1.0), ("domain.r_inner", "big")], ids=["own check", "type"]
    )
    def test_condition_waits_for_the_checks_of_its_values(self, name: str, value: Any) -> None:
        """Check that a condition is not evaluated when a value it involves failed its own type or check (PAR23).

        That mistake is reported once, by itself, and not again through the condition.
        """
        mistake = only_mistake({name: value})
        assert mistake.name == name

    def test_condition_is_reported_with_the_other_mistakes(self) -> None:
        """Check that a failed condition is reported in one error with the mistakes of single values (PAR23, PAR14)."""
        ## A misspelt name, and an inner radius larger than the outer one.
        with pytest.raises(ParameterError) as refusal:
            resolve(DOMAIN, overrides={"domain.radius": 5.0, "domain.r_inner": 20.0})

        ## The misspelt name first, then the condition, which has no single name.
        assert [mistake.name for mistake in refusal.value.mistakes] == ["domain.radius", None]

    def test_condition_on_undeclared_parameter_is_refused(self) -> None:
        """Check that a condition naming a parameter that is not declared is refused when declared (PAR23)."""
        check = dataclasses.replace(INNER_BELOW_OUTER, names=["domain.r_inner", "domain.r_middle"])
        with pytest.raises(ValueError, match=re.escape("'domain.r_middle'")):
            Declarations(parameters=RADII, joint_checks=[check])

    ## A condition on one parameter, named once or twice, and a condition without a description.
    @pytest.mark.parametrize(
        "changes",
        [{"names": ["domain.r_inner"]}, {"names": ["domain.r_inner", "domain.r_inner"]}, {"description": " "}],
        ids=["one parameter", "one parameter twice", "no description"],
    )
    def test_invalid_joint_check_is_refused(self, changes: dict[str, Any]) -> None:
        """Check that a condition on fewer than two different parameters, or without a description, is refused (PAR23).

        A condition on one parameter is the check of that parameter (PAR01).
        """
        with pytest.raises(ValueError, match="joint check"):
            dataclasses.replace(INNER_BELOW_OUTER, **changes)
