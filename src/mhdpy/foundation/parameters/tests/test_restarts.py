"""Tests of the parameters of a restarted run: the record as the lowest layer, and what may change (PAR15-PAR17)."""

import dataclasses
from pathlib import Path
from typing import Any, cast

import pytest

from mhdpy.foundation.parameters.declarations import Alternatives, Check, Declarations, Parameter
from mhdpy.foundation.parameters.resolution import resolve
from mhdpy.foundation.parameters.resolved import Change, Changes, Origin, ParameterError, Record
from mhdpy.foundation.parameters.tests import identical, parameter_file
from mhdpy.foundation.parameters.values import is_list
from mhdpy.foundation.units.constants import MEGAYEAR, PARSEC, SOLAR_MASS
from mhdpy.foundation.units.system import UnitSystem

## The unit system of the original run and of its restart, which the restart file keeps (D13.5): code units of 1 pc,
## 1 solar mass and 1 Myr.
UNITS = UnitSystem(length=PARSEC, mass=SOLAR_MASS, time=MEGAYEAR)

## The parameters of a small run: the mesh and the variables written, which a restart may not change, the Courant
## number and the end time, which it may (PAR01), and the density of the ambient medium in two ways, as alternatives
## (PAR22).
DECLARATIONS = Declarations(
    parameters=[
        Parameter(name="mesh.nx1", type=int, default=64, doc="The number of cells along x1.", unit="dimensionless"),
        Parameter(name="output.variables", type=list[str], default=["rho"], doc="The variables written."),
        Parameter(
            name="hydro.cfl",
            type=float,
            default=0.4,
            doc="The Courant number.",
            unit="dimensionless",
            check=Check(lambda value: 0 < value <= 1, "in (0, 1]"),
            changeable=True,
        ),
        Parameter(
            name="time.end",
            type=float,
            default=1.0,
            doc="The time the run ends at.",
            unit="time",
            changeable=True,
        ),
        Parameter(name="ambient.rho", type=float, default=1.0, doc="The mass density.", unit="density"),
        Parameter(name="ambient.n", type=float, default=1.0, doc="The number density.", unit={"length": -3}),
    ],
    alternatives=[
        Alternatives(
            name="ambient.density",
            doc="The density of the ambient medium, as a mass density or as a number density.",
            groups={"mass_density": ["ambient.rho"], "number_density": ["ambient.n"]},
            default="mass_density",
        ),
    ],
)

## The values of the original run, none of them the default: an integer, a list, a float, a value with a unit, and the
## number density, which selects the group of the alternatives that is not the default.
ORIGINAL = {
    "mesh.nx1": 128,
    "output.variables": ["rho", "pressure"],
    "hydro.cfl": 0.3,
    "time.end": "10 Myr",
    "ambient.n": 2.0,
}


## The same parameters with those of the ambient medium changeable, so that a restart may select the other group of
## its density (PAR22). dataclasses.replace makes a new declaration with the given items changed, checked as any other.
CHANGEABLE_AMBIENT = Declarations(
    parameters=[
        dataclasses.replace(parameter, changeable=parameter.name.startswith("ambient."))
        for parameter in DECLARATIONS.parameters
    ],
    alternatives=DECLARATIONS.alternatives,
)


def original_record() -> Record:
    """Return the record of the original run, as its restart file holds it (PAR19)."""
    return resolve(DECLARATIONS, overrides=ORIGINAL, units=UNITS).to_record()


class TestRestarts:
    """PAR15-PAR17: a restart continues with the values of the original run, and changes only what may change."""

    ## ---- The record as the lowest layer (PAR15) ----

    def test_record_replaces_the_defaults(self) -> None:
        """Check that on restart every parameter not given anew keeps its recorded value, not its default (PAR15).

        A restart then needs no parameter file at all, and each value records the restart record as its origin
        (PAR10).
        """
        record = original_record()

        ## Neither a parameter file nor overrides, nor a unit system: the record holds every value in code units, and
        ## none is converted again.
        parameters = resolve(DECLARATIONS, record=record)

        ## Every value is the recorded one, the list as a tuple (PAR18), and none is its default.
        assert dict(parameters) == {
            "mesh.nx1": 128,
            "output.variables": ("rho", "pressure"),
            "hydro.cfl": 0.3,
            "time.end": UNITS.to_code_units("10 Myr", "time"),
            "ambient.rho": 1.0,
            "ambient.n": 2.0,
        }

        ## Each with the restart record as its origin, and the recorded value as the value as given, a list as a tuple
        ## (PAR18). The report of a mistake names the origin as "restart record" (PAR14).
        for name, value in record["values"].items():
            given = tuple(value) if is_list(value) else value
            assert parameters.origins[name] == Origin(source="restart", value=given), name
        assert str(parameters.origins["mesh.nx1"]) == "restart record"

        ## The group the original run selected stays selected, although nothing selects it now and it is not the
        ## default (PAR22).
        assert parameters.selected == {"ambient.density": "number_density"}

    def test_file_and_overrides_replace_the_record(self) -> None:
        """Check that the parameter file and the overrides lie above the record, as above the defaults (PAR15, PAR06).

        Only the values they give replace the recorded ones; every other parameter keeps its recorded value.
        """
        parameters = resolve(DECLARATIONS, record=original_record(), overrides={"time.end": 20.0})

        assert parameters["time.end"] == 20.0
        assert parameters.origins["time.end"] == Origin(source="override", value=20.0)
        assert parameters["hydro.cfl"] == 0.3
        assert parameters.origins["hydro.cfl"].source == "restart"

    def test_parameter_missing_from_record_takes_its_default(self) -> None:
        """Check that a declared parameter missing from the record takes its default, without refusal (PAR15)."""
        ## The record of a run made before the module declared hydro.cfl.
        record = original_record()
        del record["values"]["hydro.cfl"]

        parameters = resolve(DECLARATIONS, record=record)
        assert parameters["hydro.cfl"] == 0.4
        assert parameters.origins["hydro.cfl"] == Origin(source="default", value=0.4)

        ## The other values are still the recorded ones.
        assert parameters["mesh.nx1"] == 128

    def test_recorded_name_no_longer_declared_is_ignored(self) -> None:
        """Check that a name in the record that is no longer declared is ignored, without refusal (PAR15).

        It is not refused as a name that is not declared (PAR11), as a name in a parameter file would be.
        """
        ## The record of a run made while a module still declared gravity.constant.
        record = original_record()
        record["values"]["gravity.constant"] = 1.0

        parameters = resolve(DECLARATIONS, record=record)
        assert "gravity.constant" not in parameters
        assert "gravity.constant" not in parameters.origins
        assert parameters["mesh.nx1"] == 128

    ## A set of alternatives missing from the record, and one whose recorded group no longer exists.
    @pytest.mark.parametrize("group", [None, "column_density"], ids=["set missing", "group no longer declared"])
    def test_alternatives_missing_from_record_select_as_usual(self, group: str | None) -> None:
        """Check that a set of alternatives without a valid recorded group selects its group as without a restart.

        The default group, when nothing is given, or the group of a parameter given (PAR15, PAR22).
        """
        record = original_record()
        if group is None:
            del record["selected"]["ambient.density"]
        else:
            record["selected"]["ambient.density"] = group

        ## Nothing given: the default group, although the record holds the number density of the original run.
        assert resolve(DECLARATIONS, record=record).selected == {"ambient.density": "mass_density"}

        ## The number density given anew, at its recorded value, so that nothing changes but the selection: its group.
        parameters = resolve(DECLARATIONS, record=record, overrides={"ambient.n": 2.0})
        assert parameters.selected == {"ambient.density": "number_density"}

    def test_recorded_value_refused_by_its_declaration_is_refused(self) -> None:
        """Check that a recorded value its declaration now refuses is refused, with the restart record as origin.

        A newer version of a module may have changed a parameter's type or check; both kinds are refused, together
        and among the other mistakes (PAR15, PAR14).
        """
        ## The number of cells recorded as a float, which the declaration of an int refuses (PAR12), and a Courant
        ## number outside the check (PAR13).
        record = original_record()
        record["values"]["mesh.nx1"] = 128.0
        record["values"]["hydro.cfl"] = 1.5

        with pytest.raises(ParameterError) as refusal:
            resolve(DECLARATIONS, record=record)
        mistakes = refusal.value.mistakes
        assert [mistake.name for mistake in mistakes] == ["mesh.nx1", "hydro.cfl"]
        assert mistakes[0].origin == Origin(source="restart", value=128.0)
        assert str(refusal.value).splitlines()[1:] == [
            "- restart record: 'mesh.nx1' must be of type int, got float 128.0.",
            "- restart record: 'hydro.cfl' must be in (0, 1], got 1.5.",
        ]

    ## ---- What may change (PAR16) ----

    def test_changeable_parameter_may_change(self, tmp_path: Path) -> None:
        """Check that a changeable parameter takes a new value from the parameter file or an override (PAR16)."""
        ## The Courant number from the file, and the end time as an override, with a unit.
        file = parameter_file(tmp_path, "[hydro]\ncfl = 0.5\n")
        parameters = resolve(
            DECLARATIONS, record=original_record(), file=file, overrides=["time.end=20 Myr"], units=UNITS
        )

        assert parameters["hydro.cfl"] == 0.5
        assert parameters["time.end"] == UNITS.to_code_units("20 Myr", "time")

    def test_changeable_parameter_not_given_keeps_its_record(self) -> None:
        """Check that a changeable parameter given by neither the file nor an override keeps its recorded value.

        It does not fall back to its default (PAR16).
        """
        ## The end time is changed; the Courant number, changeable as well, is not given.
        parameters = resolve(DECLARATIONS, record=original_record(), overrides={"time.end": 20.0})

        ## The recorded 0.3, not the default 0.4.
        assert parameters["hydro.cfl"] == 0.3
        assert parameters.origins["hydro.cfl"].source == "restart"

    def test_change_to_fixed_parameter_is_refused(self, tmp_path: Path) -> None:
        """Check that a new value for a fixed parameter is refused, stating that the restart file fixes it (PAR16).

        The refusal states the recorded value as well, and is reported among the other mistakes, with the origin of
        the new value (PAR14).
        """
        ## A list in the file, an integer as an override, and a changeable parameter as well, whose change is accepted.
        file = parameter_file(tmp_path, '[output]\nvariables = ["rho"]\n')
        with pytest.raises(ParameterError) as refusal:
            resolve(DECLARATIONS, record=original_record(), file=file, overrides=["mesh.nx1=256", "hydro.cfl=0.5"])

        ## Both changes to fixed parameters, in the order declared, and nothing else.
        assert str(refusal.value).splitlines()[1:] == [
            "- override: 'mesh.nx1' is fixed by the restart file at 128, got 256.",
            f"- parameter file {file}: 'output.variables' is fixed by the restart file at ['rho', 'pressure'], got "
            "['rho'].",
        ]

    def test_equal_value_is_not_a_change(self, tmp_path: Path) -> None:
        """Check that a fixed parameter given its recorded value is accepted, as no change (PAR16).

        The original parameter file can then be used unchanged for the restart, a value with a unit included.
        """
        ## The parameter file of the original run, with a fixed parameter given with a unit: a number density of
        ## 2e-3 per cubic centimetre, converted to code units when the original run was resolved.
        file = parameter_file(
            tmp_path,
            '[mesh]\nnx1 = 128\n\n[output]\nvariables = ["rho", "pressure"]\n\n[ambient]\nn = "2e-3 cm^-3"\n',
        )
        original = resolve(DECLARATIONS, file=file, units=UNITS)

        ## The restart with the same file: every value equals its recorded one in code units, so nothing is refused.
        ## A value with a unit is converted again, with the same unit system, to the same double.
        parameters = resolve(DECLARATIONS, record=original.to_record(), file=file, units=UNITS)
        assert dict(parameters) == dict(original)
        assert parameters.origins["ambient.n"].value == "2e-3 cm^-3"

    def test_equal_value_keeps_the_recorded_value(self) -> None:
        """Check that a value given anew that equals the recorded one leaves the recorded value, bit for bit (PAR16).

        0.0 and -0.0 compare equal but differ in their sign bit: the restart continues with the value of the original
        run, of a fixed parameter and of a changeable one alike, so that it continues bit for bit (PAR19).
        """
        ## A record with the number density, fixed, and the end time, changeable, both at 0.0, given anew as -0.0.
        record = original_record()
        record["values"]["ambient.n"] = 0.0
        record["values"]["time.end"] = 0.0
        parameters = resolve(DECLARATIONS, record=record, overrides={"ambient.n": -0.0, "time.end": -0.0})

        ## Both keep the recorded 0.0, the sign included, and neither is a change; the origin still states where the
        ## value was given anew, and how (PAR10).
        for name in ("ambient.n", "time.end"):
            assert identical(parameters[name], 0.0), name
            assert parameters.origins[name].source == "override"
        assert parameters.changes is not None
        assert not parameters.changes.values

    def test_equal_value_replaces_a_refused_record(self) -> None:
        """Check that a value given anew is used where it equals a recorded value its declaration now refuses (PAR16).

        The recorded value cannot be kept, as its declaration refuses it (PAR15); the equal value given anew can.
        """
        ## The number of cells recorded as a float, which the declaration of an int refuses, given anew as an integer.
        record = original_record()
        record["values"]["mesh.nx1"] = 128.0
        parameters = resolve(DECLARATIONS, record=record, overrides={"mesh.nx1": 128})
        assert identical(parameters["mesh.nx1"], 128)

    ## ---- The list of changes (PAR17) ----

    def test_changes_are_listed(self) -> None:
        """Check that every parameter whose value differs from the record is listed with both values (PAR17).

        In code units, as the parameters give them; a value given anew that equals the recorded one is no change, and
        is not listed.
        """
        ## Two changeable parameters changed, the end time with a unit, and a fixed one given its recorded value.
        overrides = ["hydro.cfl=0.5", "time.end=20 Myr", "mesh.nx1=128"]
        parameters = resolve(DECLARATIONS, record=original_record(), overrides=overrides, units=UNITS)

        ## The changes alone, each with the recorded value and the new one.
        changes = parameters.changes
        assert changes is not None
        assert dict(changes.values) == {
            "hydro.cfl": Change(recorded=0.3, new=0.5),
            "time.end": Change(
                recorded=UNITS.to_code_units("10 Myr", "time"), new=UNITS.to_code_units("20 Myr", "time")
            ),
        }

        ## Nothing else changed: no parameter is missing, no name ignored, and no group selected anew.
        assert not changes.missing
        assert not changes.ignored
        assert not changes.selected

    def test_no_changes_without_a_restart(self) -> None:
        """Check that a run that is not a restart lists no changes at all, and a restart without changes an empty list.

        So that the driver can tell a run that is no restart from a restart that changes nothing (PAR17).
        """
        assert resolve(DECLARATIONS).changes is None
        assert resolve(DECLARATIONS, record=original_record()).changes == Changes(
            values={}, missing={}, ignored={}, selected={}
        )

    def test_change_of_selected_group_is_listed(self) -> None:
        """Check that a set of alternatives whose selected group changed is listed with both groups (PAR17, PAR22).

        As is a set whose recorded group is no longer one of its groups, which selects as without a restart (PAR15).
        """
        ## The original run selects the number density; its restart gives the mass density, at its recorded value, so
        ## that only the selection changes, which the changeable parameters of the ambient medium allow (PAR16).
        record = resolve(CHANGEABLE_AMBIENT, overrides=ORIGINAL, units=UNITS).to_record()
        parameters = resolve(CHANGEABLE_AMBIENT, record=record, overrides={"ambient.rho": 1.0})
        assert parameters.changes is not None
        assert dict(parameters.changes.selected) == {
            "ambient.density": Change(recorded="number_density", new="mass_density")
        }

        ## A recorded group that is no longer declared: the default group is selected instead, and listed.
        record["selected"]["ambient.density"] = "column_density"
        parameters = resolve(CHANGEABLE_AMBIENT, record=record)
        assert parameters.changes is not None
        assert dict(parameters.changes.selected) == {
            "ambient.density": Change(recorded="column_density", new="mass_density")
        }

    def test_missing_and_ignored_names_are_listed(self) -> None:
        """Check that missing parameters are listed with their default, and ignored names with their recorded value.

        These are the cases of PAR15 that are reported rather than refused (PAR17).
        """
        ## The record of a run made before the module declared hydro.cfl, and while a module still declared
        ## gravity.constant and gravity.softening, the latter a list.
        record = original_record()
        del record["values"]["hydro.cfl"]
        record["values"]["gravity.constant"] = 1.0
        record["values"]["gravity.softening"] = [0.1, 0.2]

        parameters = resolve(DECLARATIONS, record=record)
        assert parameters.changes is not None
        assert dict(parameters.changes.missing) == {"hydro.cfl": 0.4}
        assert dict(parameters.changes.ignored) == {"gravity.constant": 1.0, "gravity.softening": (0.1, 0.2)}

        ## A missing parameter given anew took no default, and is not listed as missing.
        parameters = resolve(DECLARATIONS, record=record, overrides={"hydro.cfl": 0.5})
        assert parameters.changes is not None
        assert not parameters.changes.missing

    def test_changes_cannot_change(self) -> None:
        """Check that the list of changes cannot be changed once resolved, as the parameters cannot (PAR17, PAR18)."""
        parameters = resolve(DECLARATIONS, record=original_record(), overrides={"hydro.cfl": 0.5})
        changes = parameters.changes
        assert changes is not None

        ## Each as Any, so that the changes below can be written at all, as in the tests of the parameters themselves:
        ## a list cannot be replaced, nor a change added to one, nor a change itself changed.
        with pytest.raises(dataclasses.FrozenInstanceError):
            cast(Any, changes).values = {}
        with pytest.raises(TypeError):
            cast(Any, changes.values)["mesh.nx1"] = Change(recorded=128, new=256)
        with pytest.raises(dataclasses.FrozenInstanceError):
            cast(Any, changes.values["hydro.cfl"]).new = 0.9
        assert dict(changes.values) == {"hydro.cfl": Change(recorded=0.3, new=0.5)}
