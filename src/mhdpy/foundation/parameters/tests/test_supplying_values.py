"""Tests of how parameters are given values: layers, files, overrides, units and origins (PAR06-PAR10)."""

from pathlib import Path

import pytest

from mhdpy.foundation.parameters.declarations import Declarations, Parameter
from mhdpy.foundation.parameters.resolution import resolve
from mhdpy.foundation.parameters.tests import NOT_WRITTEN

## The parameters of a small run: three numbers in two sections, and a list. Their defaults are the bottom layer of
## every test of PAR06.
DECLARATIONS = Declarations(
    parameters=[
        Parameter(name="hydro.cfl", type=float, default=0.4, doc="The Courant number.", unit="dimensionless"),
        Parameter(name="hydro.gamma", type=float, default=5 / 3, doc="The adiabatic index.", unit="dimensionless"),
        Parameter(name="mesh.nx1", type=int, default=64, doc="The number of cells along x1.", unit="dimensionless"),
        Parameter(name="output.variables", type=list[str], default=["rho"], doc="The variables written."),
    ]
)

## The default of each parameter, by its name: what every parameter resolves to without a file or overrides.
DEFAULTS = {parameter.name: parameter.default for parameter in DECLARATIONS.parameters}


def parameter_file(folder: Path, text: str) -> Path:
    """Return the path of a parameter file with the given text, written in a folder of the test's own."""
    path = folder / "run.toml"
    path.write_text(text)
    return path


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

    @NOT_WRITTEN
    def test_tables_and_dotted_keys_give_the_same_names(self) -> None:
        """Check that a key in a table and a dotted key give the same parameter (PAR07).

        The key "cfl" in the table [hydro] and the dotted key "hydro.cfl" both give "hydro.cfl", as do nested tables
        and dotted keys of more parts.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_invalid_file_is_refused(self) -> None:
        """Check that a file that is not valid TOML is refused, with the file's name and the position of the error.

        The position is the line and column the TOML reader reports (PAR07).
        """
        pytest.fail("Not written yet.")

    ## ---- Overrides (PAR08) ----

    @NOT_WRITTEN
    def test_overrides_as_dictionary(self) -> None:
        """Check that overrides given as a dictionary, with dotted names or nested as in TOML, give the same (PAR08)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_overrides_as_strings(self) -> None:
        """Check that an override "name=value" is read with its value as TOML (PAR08).

        "hydro.cfl=0.3" gives a float, "cooling.enabled=true" a boolean, "output.variables=["rho"]" a list, and
        "problem.radius="100 pc"" a string.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_invalid_value_is_taken_as_string(self) -> None:
        """Check that a value that is not valid TOML is taken as a string (PAR08).

        "cooling.enabled=no" is then refused for its type, with a message about the parameter rather than about TOML
        syntax (PAR12).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_override_without_equals_is_refused(self) -> None:
        """Check that an override string without "=", such as "hydro.cfl 0.3", is refused, naming the string (PAR08)."""
        pytest.fail("Not written yet.")

    ## ---- Values with a unit (PAR09) ----

    @NOT_WRITTEN
    def test_value_with_unit_is_converted(self) -> None:
        """Check that a value with a unit is converted to code units by the run's unit system (PAR09, UNI20).

        In every layer: the default, the parameter file and the overrides.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_list_elements_with_units_are_converted(self) -> None:
        """Check that each element of a list may be given with a unit, and is converted on its own (PAR09)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_plain_number_is_in_code_units(self) -> None:
        """Check that a plain number is taken as a value in code units, with or without a unit system (PAR09).

        For a parameter in kelvin, a plain number is in kelvin.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_value_with_unit_without_unit_system_is_refused(self) -> None:
        """Check that a value with a unit is refused when the run has no unit system, a default included (PAR09)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_value_with_wrong_dimensions_is_refused(self) -> None:
        """Check that a value whose unit has other dimensions than the parameter's is refused (PAR09).

        For example "100 pc", a length, given for a time.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_dimensionless_parameter_takes_plain_numbers_only(self) -> None:
        """Check that a value with a unit given for a dimensionless parameter is refused (PAR09)."""
        pytest.fail("Not written yet.")

    ## ---- Origins (PAR10) ----

    @NOT_WRITTEN
    def test_origin_is_recorded(self) -> None:
        """Check that each resolved value records its origin: the default, the parameter file by name, or an override.

        The origin of a value from the restart record is tested with the restarts (PAR10, PAR15).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_value_as_given_is_recorded(self) -> None:
        """Check that each resolved value records the value as it was given: for a value with a unit, the string.

        "100 pc" is kept next to its value in code units (PAR10).
        """
        pytest.fail("Not written yet.")
