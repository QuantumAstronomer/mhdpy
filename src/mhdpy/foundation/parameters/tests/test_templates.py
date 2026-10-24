"""Tests of the template parameter file written for a set of declarations (PAR20)."""

import tomllib
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mhdpy.foundation.parameters.declarations import Alternatives, Check, Declarations, Parameter
from mhdpy.foundation.parameters.resolution import resolve
from mhdpy.foundation.parameters.templates import template
from mhdpy.foundation.parameters.tests import identical, parameter_file
from mhdpy.foundation.parameters.values import is_list
from mhdpy.foundation.units.constants import MEGAYEAR, PARSEC, SOLAR_MASS
from mhdpy.foundation.units.system import UnitSystem

## The unit system of the run, which the defaults given with a unit need: code units of 1 pc, 1 solar mass and 1 Myr.
UNITS = UnitSystem(length=PARSEC, mass=SOLAR_MASS, time=MEGAYEAR)

## The parameters of a small run: one of every type of PAR03, in five sections and a section a table deeper, with
## every form of unit (PAR04), defaults given with a unit (PAR09), a check, a changeable parameter, documentation longer
## than a line, and the density of the ambient medium in two ways, as alternatives (PAR22).
DECLARATIONS = Declarations(
    parameters=[
        Parameter(
            name="hydro.cfl",
            type=float,
            default=0.4,
            doc="The Courant number: the time step as a fraction of the time a signal takes to cross a cell.",
            unit="dimensionless",
            check=Check(lambda value: 0 < value <= 1, "in (0, 1]"),
            changeable=True,
        ),
        Parameter(name="hydro.solver", type=str, default="hllc", doc="The Riemann solver."),
        Parameter(name="mesh.nx1", type=int, default=64, doc="The number of cells along x1.", unit="dimensionless"),
        Parameter(name="cooling.enabled", type=bool, default=False, doc="Whether the gas cools radiatively."),
        Parameter(name="output.variables", type=list[str], default=["rho", "pressure"], doc="The variables written."),
        Parameter(
            name="output.snapshot.dt",
            type=float,
            default="1 Myr",
            doc="The time between snapshots.",
            unit="time",
            changeable=True,
        ),
        Parameter(name="problem.radius", type=float, default="100 pc", doc="The radius of the cloud.", unit="length"),
        Parameter(
            name="problem.temperature",
            type=float,
            default=1e4,
            doc="The temperature of the cloud.",
            unit={"temperature": 1},
        ),
        Parameter(
            name="problem.diffusivity",
            type=float,
            default=0.0,
            doc=(
                "The thermal diffusivity of the gas inside the cloud, which smooths the temperature across its edge "
                "over a few cells, and which is zero for a cloud whose edge is meant to stay sharp."
            ),
            unit={"length": 2, "time": -1},
        ),
        Parameter(name="ambient.rho", type=float, default=1.0, doc="The mass density.", unit="density"),
        Parameter(name="ambient.n", type=float, default=1.0, doc="The number density.", unit={"length": -3}),
    ],
    alternatives=[
        Alternatives(
            name="ambient.density",
            doc="The density of the ambient medium.",
            groups={"mass_density": ["ambient.rho"], "number_density": ["ambient.n"]},
            default="mass_density",
        ),
    ],
)


class TestTemplates:
    """PAR20: a template gives every parameter at its default, documented, and resolves to exactly the defaults."""

    def test_template_has_a_table_per_section(self) -> None:
        """Check that the template is a TOML document with one table per section of the names (PAR20)."""
        text = template(DECLARATIONS)

        ## A TOML document, whose tables are the sections, in the order their first parameter was declared: the section
        ## output.snapshot is a table inside the table output.
        document = tomllib.loads(text)
        assert list(document) == ["hydro", "mesh", "cooling", "output", "problem", "ambient"]
        assert list(document["output"]) == ["variables", "snapshot"]

        ## Each table is written once, by its name in square brackets, after a header in comments.
        tables = [line for line in text.splitlines() if line.startswith("[")]
        assert tables == ["[hydro]", "[mesh]", "[cooling]", "[output]", "[output.snapshot]", "[problem]", "[ambient]"]
        assert text.startswith("# The parameters of the run, each at its default.")

    def test_template_gives_every_default(self) -> None:
        """Check that the template gives every parameter at its default as declared, with its unit where it has one.

        A default of "100 pc" is written as that string, not in code units (PAR20).
        """
        document = tomllib.loads(template(DECLARATIONS))

        ## Every parameter but the number density, which is written as a comment (PAR22), at its default as declared.
        assert document["hydro"] == {"cfl": 0.4, "solver": "hllc"}
        assert document["mesh"] == {"nx1": 64}
        assert document["cooling"] == {"enabled": False}
        assert document["output"] == {"variables": ["rho", "pressure"], "snapshot": {"dt": "1 Myr"}}
        assert document["problem"] == {"radius": "100 pc", "temperature": 1e4, "diffusivity": 0.0}
        assert document["ambient"] == {"rho": 1.0}

    ## The comment of facts of a parameter of each kind, in front of its key: dimensionless with a check and changeable;
    ## a str, without a unit; a named unit, with its label in cgs; a temperature, in kelvin; dimensions; and a list of
    ## strings, without a unit.
    @pytest.mark.parametrize(
        ("key", "facts"),
        [
            ("cfl", "Dimensionless. Must be in (0, 1]. Changeable on restart."),
            ("solver", "Fixed on restart."),
            ("radius", "Unit: length (cm). Fixed on restart."),
            ("temperature", "Unit: kelvin. Fixed on restart."),
            ("diffusivity", "Dimensions: length^2 time^-1. Fixed on restart."),
            ("variables", "Fixed on restart."),
        ],
    )
    def test_template_documents_every_parameter(self, key: str, facts: str) -> None:
        """Check that the comments of each parameter give its documentation, unit, condition and restart behaviour.

        The template is the user's reference while editing (PAR20).
        """
        text = template(DECLARATIONS)
        lines = text.splitlines()

        ## The line of facts comes right before the parameter's key, and its documentation right before that.
        index = next(number for number, line in enumerate(lines) if line.startswith(f"{key} = "))
        assert lines[index - 1] == f"# {facts}"
        assert lines[index - 2].startswith("# ")

    def test_long_documentation_is_wrapped(self) -> None:
        """Check that documentation longer than a line is wrapped at 120 characters, keeping every word (PAR20).

        As mhdpy's own code is, so that the template reads well in an editor.
        """
        lines = template(DECLARATIONS).splitlines()
        assert all(len(line) <= 120 for line in lines)

        ## The comments between the blank line before the thermal diffusivity and its line of facts are its
        ## documentation: more than one line, which together give the documentation as declared.
        index = lines.index("diffusivity = 0.0")
        start = max(number for number in range(index) if lines[number] == "") + 1
        documentation = [line.removeprefix("# ") for line in lines[start : index - 1]]
        declared = next(
            parameter.doc for parameter in DECLARATIONS.parameters if parameter.name == "problem.diffusivity"
        )
        assert len(documentation) > 1
        assert " ".join(documentation) == declared

    def test_other_alternatives_are_comments(self) -> None:
        """Check that parameters of groups of alternatives other than the default are written as comments (PAR20).

        With their defaults, so that the template selects the default group of each set of alternatives (PAR22).
        """
        lines = template(DECLARATIONS).splitlines()

        ## The number density, of the group that is not the default, as a comment with its default, after its
        ## documentation; the mass density, of the default group, as a value.
        assert lines.index("# n = 1.0") == lines.index("# The number density.") + 2
        assert "rho = 1.0" in lines

        ## The set of alternatives is described before its first parameter, the first of its table, with its groups and
        ## the default named: the comments between the table's name and the documentation of the mass density.
        start = lines.index("[ambient]") + 1
        end = lines.index("# The mass density.")
        assert " ".join(line.removeprefix("# ") for line in lines[start:end]) == (
            "ambient.density: The density of the ambient medium. Given in one of these ways: mass_density "
            "(ambient.rho), the default; number_density (ambient.n)."
        )

    def test_template_resolves_to_the_defaults(self, tmp_path: Path) -> None:
        """Check that the template, read back unchanged as a parameter file, resolves to exactly the defaults (PAR20).

        Every value identical, and for every type of PAR03.
        """
        file = parameter_file(tmp_path, template(DECLARATIONS))
        parameters = resolve(DECLARATIONS, file=file, units=UNITS)
        defaults = resolve(DECLARATIONS, units=UNITS)

        ## The same names, every value identical, of the same type and bit for bit, the defaults given with a unit
        ## converted alike, and the default group of the alternatives selected.
        assert list(parameters) == list(defaults)
        for name in defaults:
            assert identical(parameters[name], defaults[name]), name
        assert parameters.selected == {"ambient.density": "mass_density"}

        ## Every value but the one written as a comment comes from the file.
        assert [name for name, origin in parameters.origins.items() if origin.source != "file"] == ["ambient.n"]

    ## Hypothesis draws a default of every type of PAR03: any finite float, the largest, the smallest and -0.0 included;
    ## any integer of 64 bits, which TOML guarantees to read; any string, quotes, backslashes, control characters and
    ## letters outside ASCII included; and lists of floats and of strings.
    @given(
        number=st.floats(allow_nan=False, allow_infinity=False),
        count=st.integers(min_value=-(2**63), max_value=2**63 - 1),
        flag=st.booleans(),
        text=st.text(),
        numbers=st.lists(st.floats(allow_nan=False, allow_infinity=False)),
        texts=st.lists(st.text()),
    )
    def test_every_default_survives_the_template(
        self, number: float, count: int, flag: bool, text: str, numbers: list[float], texts: list[str]
    ) -> None:
        """Check that a default of every type of PAR03 reads back from the template identical, bit for bit (PAR20)."""
        ## A parameter of each type, with the drawn default.
        defaults: dict[str, tuple[Any, Any]] = {
            "drawn.number": (float, number),
            "drawn.count": (int, count),
            "drawn.flag": (bool, flag),
            "drawn.text": (str, text),
            "drawn.numbers": (list[float], numbers),
            "drawn.texts": (list[str], texts),
        }
        declarations = Declarations(
            parameters=[
                Parameter(
                    name=name,
                    type=type_,
                    default=default,
                    doc="A drawn default.",
                    unit="dimensionless" if type_ in (float, int, list[float]) else None,
                )
                for name, (type_, default) in defaults.items()
            ]
        )

        ## The template read as TOML gives every default identical; a dictionary of overrides, nested as the document
        ## is, reads it as a parameter file would, without a file for each example.
        document = tomllib.loads(template(declarations))
        parameters = resolve(declarations, overrides=document)
        for name, (_, default) in defaults.items():
            expected = tuple(default) if is_list(default) else default
            assert identical(parameters[name], expected), name
