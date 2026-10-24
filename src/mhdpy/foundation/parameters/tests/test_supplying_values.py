"""Tests of how parameters are given values: layers, files, overrides, units and origins (PAR06-PAR10)."""

import re
from pathlib import Path
from typing import Any

import pytest

from mhdpy.foundation.parameters.declarations import Declarations, Parameter
from mhdpy.foundation.parameters.resolution import resolve
from mhdpy.foundation.parameters.resolved import Origin
from mhdpy.foundation.parameters.tests import parameter_file
from mhdpy.foundation.parameters.values import is_list
from mhdpy.foundation.units.constants import MEGAYEAR, PARSEC, SOLAR_MASS
from mhdpy.foundation.units.system import UnitSystem

## The parameters of a small run: a parameter of every type, in four sections, and a number a table deeper, in the table
## snapshot of the section output. Their defaults are the bottom layer of every test of PAR06-PAR08.
DECLARATIONS = Declarations(
    parameters=[
        Parameter(name="hydro.cfl", type=float, default=0.4, doc="The Courant number.", unit="dimensionless"),
        Parameter(name="hydro.gamma", type=float, default=5 / 3, doc="The adiabatic index.", unit="dimensionless"),
        Parameter(name="hydro.solver", type=str, default="hllc", doc="The Riemann solver."),
        Parameter(name="mesh.nx1", type=int, default=64, doc="The number of cells along x1.", unit="dimensionless"),
        Parameter(name="output.variables", type=list[str], default=["rho"], doc="The variables written."),
        Parameter(
            name="output.snapshot.every",
            type=int,
            default=100,
            doc="The number of steps between snapshots.",
            unit="dimensionless",
        ),
        Parameter(name="cooling.enabled", type=bool, default=False, doc="Whether the gas cools radiatively."),
    ]
)

## The same two values in each form TOML allows: tables, dotted keys, dotted keys in a table, and inline tables. Each
## gives hydro.cfl, a name of two parts, and output.snapshot.every, a name of three (PAR07).
FILE_FORMS = {
    "tables": "[hydro]\ncfl = 0.3\n\n[output.snapshot]\nevery = 10\n",
    "dotted keys": "hydro.cfl = 0.3\noutput.snapshot.every = 10\n",
    "dotted keys in a table": "[hydro]\ncfl = 0.3\n\n[output]\nsnapshot.every = 10\n",
    "inline tables": "hydro = { cfl = 0.3 }\noutput = { snapshot = { every = 10 } }\n",
}

## The same two values in each form a dictionary of overrides may take: by dotted names, nested as a TOML document is
## read, and the two mixed (PAR08).
DICTIONARY_FORMS: dict[str, dict[str, Any]] = {
    "dotted names": {"hydro.cfl": 0.3, "output.snapshot.every": 10},
    "nested": {"hydro": {"cfl": 0.3}, "output": {"snapshot": {"every": 10}}},
    "mixed": {"hydro": {"cfl": 0.3}, "output.snapshot": {"every": 10}},
}

## Override strings with a value of each type, written as in TOML, with the name and the value each gives (PAR08), a
## list as the tuple the parameters hold it as (PAR18). The last has spaces around the "=", as a string in quotes on a
## command line may.
STRING_OVERRIDES = [
    ("hydro.cfl=0.3", "hydro.cfl", 0.3),
    ("mesh.nx1=128", "mesh.nx1", 128),
    ("cooling.enabled=true", "cooling.enabled", True),
    ('hydro.solver="hlld"', "hydro.solver", "hlld"),
    ('output.variables=["rho", "pressure"]', "output.variables", ("rho", "pressure")),
    ("mesh.nx1 = 128", "mesh.nx1", 128),
]

## Override strings whose value is not valid TOML, a bare word without quotes, with the string each gives (PAR08).
BARE_WORDS = [
    ("hydro.solver=hlld", "hlld"),
    ("hydro.solver = hlld", "hlld"),
    ("hydro.solver=roe fix", "roe fix"),
]

## The default of each parameter, by its name: what every parameter resolves to without a file or overrides, with a
## list as a tuple, as the parameters hold it (PAR18).
DEFAULTS: dict[str, Any] = {
    parameter.name: tuple(parameter.default) if is_list(parameter.default) else parameter.default
    for parameter in DECLARATIONS.parameters
}

## The parameters of a problem posed in physical units: a length, a time whose default is given with a unit, a velocity,
## a list of densities, a temperature in kelvin and a dimensionless number (PAR09).
PHYSICAL = Declarations(
    parameters=[
        Parameter(name="problem.radius", type=float, default=1.0, doc="The radius of the cloud.", unit="length"),
        Parameter(name="problem.time", type=float, default="10 Myr", doc="The time the run ends at.", unit="time"),
        Parameter(name="problem.velocity", type=float, default=0.0, doc="The velocity of the cloud.", unit="velocity"),
        Parameter(
            name="problem.densities",
            type=list[float],
            default=[1.0],
            doc="The densities of the layers of the cloud.",
            unit="density",
        ),
        Parameter(
            name="problem.temperature",
            type=float,
            default=1e4,
            doc="The temperature of the cloud.",
            unit={"temperature": 1},
        ),
        Parameter(
            name="problem.mach",
            type=float,
            default=2.0,
            doc="The Mach number of the shock.",
            unit="dimensionless",
        ),
    ]
)

## The unit system of the runs in physical units: code units of 1 pc, 1 solar mass and 1 Myr. The conversion itself is
## tested with the unit system (UNI20); here it is the same conversion, applied to the values of the parameters.
UNITS = UnitSystem(length=PARSEC, mass=SOLAR_MASS, time=MEGAYEAR)


class TestSupplyingValues:
    """PAR06-PAR10: values come from defaults, a parameter file and overrides, each layer replacing the one below."""

    ## ---- Layers (PAR06) ----

    def test_defaults_alone_resolve(self) -> None:
        """Check that without a parameter file or overrides every parameter resolves to its default (PAR06)."""
        parameters = resolve(DECLARATIONS)

        ## Every declared parameter, and nothing else, with its default. dict() goes through the names and reads
        ## each value, as a module would; len() counts the names.
        assert dict(parameters) == DEFAULTS
        assert len(parameters) == len(DEFAULTS)

    ## tmp_path is a fixture of pytest: a new, empty folder for this test alone, removed again later.
    def test_file_replaces_default(self, tmp_path: Path) -> None:
        """Check that a value in the parameter file replaces the default, only for the parameters it gives (PAR06)."""
        file = parameter_file(tmp_path, "[hydro]\ncfl = 0.3\n")
        parameters = resolve(DECLARATIONS, file=file)

        ## The file gives hydro.cfl; every other parameter keeps its default.
        assert dict(parameters) == DEFAULTS | {"hydro.cfl": 0.3}

    def test_override_replaces_file(self, tmp_path: Path) -> None:
        """Check that an override replaces the value in the parameter file and the default (PAR06)."""
        file = parameter_file(tmp_path, "[hydro]\ncfl = 0.3\n")
        parameters = resolve(DECLARATIONS, file=file, overrides={"hydro.cfl": 0.2, "mesh.nx1": 128})

        ## hydro.cfl is given by the file and an override, which wins; mesh.nx1 by an override alone, which replaces
        ## its default. The others keep their defaults.
        assert dict(parameters) == DEFAULTS | {"hydro.cfl": 0.2, "mesh.nx1": 128}

    def test_later_override_replaces_earlier(self) -> None:
        """Check that of two overrides of the same parameter, the later one is used (PAR06)."""
        ## Overrides as a command line gives them: strings of the form name=value, read in order.
        parameters = resolve(DECLARATIONS, overrides=["hydro.cfl=0.3", "hydro.cfl=0.5"])
        assert parameters["hydro.cfl"] == 0.5

    ## ---- Parameter files (PAR07) ----

    @pytest.mark.parametrize("text", list(FILE_FORMS.values()), ids=list(FILE_FORMS))
    def test_tables_and_dotted_keys_give_the_same_names(self, tmp_path: Path, text: str) -> None:
        """Check that a key in a table and a dotted key give the same parameter (PAR07).

        The key "cfl" in the table [hydro] and the dotted key "hydro.cfl" both give "hydro.cfl", as do nested tables
        and dotted keys of more parts.
        """
        file = parameter_file(tmp_path, text)
        parameters = resolve(DECLARATIONS, file=file)

        ## Every form gives the same names, so the same values; the parameters the file does not give keep their
        ## defaults, output.variables among them, next to output.snapshot.every in the same section.
        assert dict(parameters) == DEFAULTS | {"hydro.cfl": 0.3, "output.snapshot.every": 10}

    def test_invalid_file_is_refused(self, tmp_path: Path) -> None:
        """Check that a file that is not valid TOML is refused, with the file's name and the position of the error.

        The position is the line and column the TOML reader reports (PAR07).
        """
        ## The key cfl, on line 2, has no "=" after it: the reader stops at the value, in column 5.
        file = parameter_file(tmp_path, "[hydro]\ncfl 0.3\n")

        ## re.escape, as the path has dots in it, which match any character in a regular expression.
        with pytest.raises(ValueError, match=re.escape(str(file))) as refusal:
            resolve(DECLARATIONS, file=file)
        assert "line 2, column 5" in str(refusal.value)

    ## ---- Overrides (PAR08) ----

    @pytest.mark.parametrize("overrides", list(DICTIONARY_FORMS.values()), ids=list(DICTIONARY_FORMS))
    def test_overrides_as_dictionary(self, overrides: dict[str, Any]) -> None:
        """Check that overrides given as a dictionary, with dotted names or nested as in TOML, give the same (PAR08)."""
        parameters = resolve(DECLARATIONS, overrides=overrides)
        assert dict(parameters) == DEFAULTS | {"hydro.cfl": 0.3, "output.snapshot.every": 10}

    @pytest.mark.parametrize(("override", "name", "value"), STRING_OVERRIDES, ids=[o for o, _, _ in STRING_OVERRIDES])
    def test_overrides_as_strings(self, override: str, name: str, value: Any) -> None:
        """Check that an override "name=value" is read with its value as TOML (PAR08).

        "hydro.cfl=0.3" gives a float, "mesh.nx1=128" an integer, "cooling.enabled=true" a boolean,
        'hydro.solver="hlld"' a string and 'output.variables=["rho", "pressure"]' a list, read as a tuple (PAR18).
        """
        parameters = resolve(DECLARATIONS, overrides=[override])

        ## The type is compared as well, as == alone cannot tell them apart in Python: 1 == 1.0 == True.
        assert parameters[name] == value
        assert type(parameters[name]) is type(value)

    @pytest.mark.parametrize(("override", "value"), BARE_WORDS, ids=[override for override, _ in BARE_WORDS])
    def test_invalid_value_is_taken_as_string(self, override: str, value: str) -> None:
        """Check that a value that is not valid TOML is taken as a string, without the spaces around it (PAR08).

        A bare word such as "cooling.enabled=no" is then refused for its type, with a message about the parameter
        rather than about TOML syntax; that is tested with the types (PAR12).
        """
        parameters = resolve(DECLARATIONS, overrides=[override])
        assert parameters["hydro.solver"] == value

    @pytest.mark.parametrize("override", ["hydro.cfl 0.3", "hydro.cfl"])
    def test_override_without_equals_is_refused(self, override: str) -> None:
        """Check that an override string without "=", such as "hydro.cfl 0.3", is refused, naming the string (PAR08)."""
        with pytest.raises(ValueError, match=re.escape(repr(override))):
            resolve(DECLARATIONS, overrides=[override])

    def test_single_string_is_refused(self) -> None:
        """Check that a single override string given in place of a list of them is refused, naming it (PAR08).

        A string is itself a sequence of strings, one per character, and would otherwise be read as one override per
        character. The message advises passing a list.
        """
        with pytest.raises(TypeError, match=re.escape("['hydro.cfl=0.3']")):
            resolve(DECLARATIONS, overrides="hydro.cfl=0.3")

    ## ---- Values with a unit (PAR09) ----

    def test_value_with_unit_is_converted(self, tmp_path: Path) -> None:
        """Check that a value with a unit is converted to code units by the run's unit system (PAR09, UNI20).

        In every layer: the default, the parameter file and the overrides.
        """
        ## problem.time is given with a unit by its default, problem.radius by the file, and problem.velocity by an
        ## override, written as on a command line without quotes: not valid TOML, so taken as a string (PAR08).
        file = parameter_file(tmp_path, '[problem]\nradius = "100 pc"\n')
        parameters = resolve(PHYSICAL, file=file, overrides=["problem.velocity=10 km s^-1"], units=UNITS)

        assert parameters["problem.time"] == UNITS.to_code_units("10 Myr", "time")
        assert parameters["problem.radius"] == UNITS.to_code_units("100 pc", "length")
        assert parameters["problem.velocity"] == UNITS.to_code_units("10 km s^-1", "velocity")

    def test_list_elements_with_units_are_converted(self) -> None:
        """Check that each element of a list may be given with a unit, and is converted on its own (PAR09)."""
        ## One element with a unit and one plain number, in code units already, which stays as it is.
        overrides = {"problem.densities": ["1e-24 g cm^-3", 2.0]}
        parameters = resolve(PHYSICAL, overrides=overrides, units=UNITS)
        assert parameters["problem.densities"] == (UNITS.to_code_units("1e-24 g cm^-3", "density"), 2.0)

    @pytest.mark.parametrize("units", [None, UNITS], ids=["without unit system", "with unit system"])
    def test_plain_number_is_in_code_units(self, units: UnitSystem | None) -> None:
        """Check that a plain number is taken as a value in code units, with or without a unit system (PAR09).

        For a parameter in kelvin, a plain number is in kelvin.
        """
        ## Plain numbers for every parameter with dimensions, problem.time among them: its default with a unit is then
        ## not used, and needs no unit system.
        overrides = {
            "problem.radius": 2.0,
            "problem.time": 3.0,
            "problem.velocity": 4.0,
            "problem.densities": [1.0, 0.5],
            "problem.temperature": 1e6,
        }
        parameters = resolve(PHYSICAL, overrides=overrides, units=units)

        ## Each value as given, with the list as a tuple (PAR18).
        assert {name: parameters[name] for name in overrides} == overrides | {"problem.densities": (1.0, 0.5)}

    ## The default of problem.time is "10 Myr": resolved without overrides, the default is the value with a unit.
    @pytest.mark.parametrize(
        ("overrides", "name"),
        [([], "problem.time"), (["problem.time=1.0", "problem.radius=100 pc"], "problem.radius")],
        ids=["default", "override"],
    )
    def test_value_with_unit_without_unit_system_is_refused(self, overrides: list[str], name: str) -> None:
        """Check that a value with a unit is refused when the run has no unit system, a default included (PAR09)."""
        with pytest.raises(ValueError, match=re.escape(repr(name))):
            resolve(PHYSICAL, overrides=overrides)

    @pytest.mark.parametrize(
        ("override", "name"),
        [("problem.time=100 pc", "problem.time"), ('problem.densities=["1 pc"]', "problem.densities")],
        ids=["single value", "element of a list"],
    )
    def test_value_with_wrong_dimensions_is_refused(self, override: str, name: str) -> None:
        """Check that a value whose unit has other dimensions than the parameter's is refused (PAR09).

        For example "100 pc", a length, given for a time.
        """
        with pytest.raises(ValueError, match=re.escape(repr(name))):
            resolve(PHYSICAL, overrides=[override], units=UNITS)

    ## A string of a number alone, '"2"', is no plain number either: a number written in quotes is a string in TOML.
    @pytest.mark.parametrize("override", ["problem.mach=2 cm", 'problem.mach="2"'])
    def test_dimensionless_parameter_takes_plain_numbers_only(self, override: str) -> None:
        """Check that a value with a unit given for a dimensionless parameter is refused (PAR09)."""
        with pytest.raises(ValueError, match=re.escape("'problem.mach'")):
            resolve(PHYSICAL, overrides=[override], units=UNITS)

    ## ---- Origins (PAR10) ----

    def test_origin_is_recorded(self, tmp_path: Path) -> None:
        """Check that each resolved value records its origin: the default, the parameter file by name, or an override.

        The origin of a value from the restart record is tested with the restarts (PAR10, PAR15).
        """
        ## hydro.cfl is given by the file and an override, hydro.gamma by the file alone, mesh.nx1 by an override alone,
        ## and the other parameters by no layer.
        file = parameter_file(tmp_path, "[hydro]\ncfl = 0.3\ngamma = 1.4\n")
        parameters = resolve(DECLARATIONS, file=file, overrides=["hydro.cfl=0.2", "mesh.nx1=128"])
        origins = parameters.origins

        ## One origin for every declared parameter, from the highest layer that gives it. The file is named only for a
        ## value that came from it, by the name it was passed as.
        assert set(origins) == set(DEFAULTS)
        assert origins["hydro.cfl"] == Origin(source="override", value=0.2)
        assert origins["hydro.gamma"] == Origin(source="file", value=1.4, file=str(file))
        assert origins["mesh.nx1"] == Origin(source="override", value=128)
        assert origins["hydro.solver"] == Origin(source="default", value="hllc")

    def test_value_as_given_is_recorded(self, tmp_path: Path) -> None:
        """Check that each resolved value records the value as it was given: for a value with a unit, the string.

        "100 pc" is kept next to its value in code units (PAR10).
        """
        file = parameter_file(tmp_path, '[problem]\nradius = "100 pc"\n')
        overrides = {"problem.densities": ["1e-24 g cm^-3", 2.0]}
        parameters = resolve(PHYSICAL, file=file, overrides=overrides, units=UNITS)
        origins = parameters.origins

        ## The value in code units is read by name; its origin keeps the string as given. A list is kept whole, as a
        ## tuple (PAR18), and a default with a unit, problem.time, as declared.
        assert parameters["problem.radius"] == UNITS.to_code_units("100 pc", "length")
        assert origins["problem.radius"].value == "100 pc"
        assert origins["problem.densities"].value == ("1e-24 g cm^-3", 2.0)
        assert origins["problem.time"].value == "10 Myr"
