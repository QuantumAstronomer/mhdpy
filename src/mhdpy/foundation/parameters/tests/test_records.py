"""Tests of reading the resolved parameters and of their record (PAR18-PAR19)."""

import json
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mhdpy.foundation.parameters.declarations import Alternatives, Declarations, Parameter
from mhdpy.foundation.parameters.resolution import resolve
from mhdpy.foundation.parameters.tests import identical
from mhdpy.foundation.parameters.values import is_list
from mhdpy.foundation.units.constants import MEGAYEAR, PARSEC, SOLAR_MASS
from mhdpy.foundation.units.system import UnitSystem

## The unit system of the run: code units of 1 pc, 1 solar mass and 1 Myr.
UNITS = UnitSystem(length=PARSEC, mass=SOLAR_MASS, time=MEGAYEAR)

## The parameters of a small run: one of every type of PAR03, a length and a temperature, which stays in kelvin, lists
## of strings and of times, and the density of the ambient medium in two ways, as alternatives (PAR22). Between them
## they take every conversion a value can undergo, and every kind of value a record holds.
DECLARATIONS = Declarations(
    parameters=[
        Parameter(name="hydro.cfl", type=float, default=0.4, doc="The Courant number.", unit="dimensionless"),
        Parameter(name="hydro.solver", type=str, default="hllc", doc="The Riemann solver."),
        Parameter(name="mesh.nx1", type=int, default=64, doc="The number of cells along x1.", unit="dimensionless"),
        Parameter(name="cooling.enabled", type=bool, default=False, doc="Whether the gas cools radiatively."),
        Parameter(name="problem.radius", type=float, default=1.0, doc="The radius of the cloud.", unit="length"),
        Parameter(
            name="problem.temperature",
            type=float,
            default=1e4,
            doc="The temperature of the cloud.",
            unit={"temperature": 1},
        ),
        Parameter(name="output.variables", type=list[str], default=["rho"], doc="The variables written."),
        Parameter(name="output.times", type=list[float], default=[], doc="The times of the snapshots.", unit="time"),
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


class TestRecords:
    """PAR18-PAR19: resolved parameters are read by name, never change, and are recorded exactly."""

    ## ---- Access (PAR18) ----

    def test_values_are_read_by_name(self) -> None:
        """Check that each resolved value can be read by its name (PAR18)."""
        parameters = resolve(DECLARATIONS, overrides={"hydro.cfl": 0.3, "hydro.solver": "hlld"}, units=UNITS)

        ## A value given and a default alike, read with square brackets as from a dictionary, or with get().
        assert parameters["hydro.cfl"] == 0.3
        assert parameters["mesh.nx1"] == 64
        assert parameters.get("hydro.solver") == "hlld"

        ## Every declared name is there, in the order declared, and nothing else: a name that is not declared is not.
        assert list(parameters) == [parameter.name for parameter in DECLARATIONS.parameters]
        assert "hydro.cfll" not in parameters
        with pytest.raises(KeyError):
            parameters["hydro.cfll"]

    def test_values_have_their_type_and_code_units(self) -> None:
        """Check that each value is of its declared type and in code units, however it was given (PAR18).

        A float parameter given an integer or a value with a unit reads as a float in code units; a parameter in kelvin
        reads in kelvin.
        """
        ## An integer for a float, a value with a unit, an integer for a parameter in kelvin, and a list of times with
        ## an integer and a value with a unit.
        overrides = {
            "hydro.cfl": 1,
            "problem.radius": "1e19 cm",
            "problem.temperature": 8000,
            "output.times": [1, "1 Gyr"],
        }
        parameters = resolve(DECLARATIONS, overrides=overrides, units=UNITS)

        ## Each value as modules read it: a float, in code units, with a list as a tuple. A temperature is not
        ## converted, as code units have no temperature: 8000 K stays 8000. identical() compares the types as well,
        ## which == does not.
        expected = {
            "hydro.cfl": 1.0,
            "problem.radius": UNITS.to_code_units("1e19 cm", "length"),
            "problem.temperature": 8000.0,
            "output.times": (1.0, UNITS.to_code_units("1 Gyr", "time")),
        }
        for name, value in expected.items():
            assert identical(parameters[name], value), name

    def test_resolved_parameters_cannot_change(self) -> None:
        """Check that a resolved value cannot be changed or added, nor a list value changed in place (PAR18)."""
        ## A list given in a dictionary of overrides, which the caller still holds, and may change afterwards.
        times = [1.0, 2.0]
        parameters = resolve(DECLARATIONS, overrides={"output.times": times}, units=UNITS)

        ## The parameters as Any, so that the changes below can be written at all: the type checker knows that a Mapping
        ## has no assignment, and would report each of them as a mistake before the test could show it is refused.
        changing = cast(Any, parameters)

        ## A value can be neither replaced, nor added, nor removed: Mapping defines none of the three.
        with pytest.raises(TypeError):
            changing["hydro.cfl"] = 0.3
        with pytest.raises(TypeError):
            changing["hydro.cfll"] = 0.3
        with pytest.raises(TypeError):
            del changing["hydro.cfl"]

        ## A list value is a tuple, which has no append and refuses assignment to an element.
        assert parameters["output.times"] == (1.0, 2.0)
        with pytest.raises(AttributeError):
            changing["output.times"].append(3.0)
        with pytest.raises(TypeError):
            changing["output.times"][0] = 3.0

        ## The origins and the selected groups cannot be changed either, and the value as given in an origin is a
        ## tuple as well.
        with pytest.raises(TypeError):
            changing.origins["hydro.cfl"] = changing.origins["mesh.nx1"]
        with pytest.raises(TypeError):
            changing.selected["ambient.density"] = "number_density"
        assert parameters.origins["output.times"].value == (1.0, 2.0)

        ## Changing the list the value was given as changes neither the value nor its origin.
        times.append(3.0)
        assert parameters["output.times"] == (1.0, 2.0)
        assert parameters.origins["output.times"].value == (1.0, 2.0)

        ## Nothing above has changed any value.
        assert parameters["hydro.cfl"] == 0.4
        assert "hydro.cfll" not in parameters

    ## ---- The record (PAR19) ----

    def test_record_is_plain_values_in_code_units(self) -> None:
        """Check that the record holds one plain value per name, in code units, for every declared parameter (PAR19)."""
        ## Values given in each way that is converted: an integer for a float, a value with a unit, and a list of
        ## both.
        overrides = {"hydro.cfl": 1, "problem.radius": "1e19 cm", "output.times": [1, "1 Gyr"]}
        parameters = resolve(DECLARATIONS, overrides=overrides, units=UNITS)
        record = parameters.to_record()

        ## One value for every declared parameter, in the order declared, and nothing else.
        assert list(record["values"]) == list(parameters)

        ## Each value as the parameters give it, in code units after conversion rather than as given, with a list as a
        ## list, since JSON has no tuples.
        for name, value in record["values"].items():
            expected = list(parameters[name]) if is_list(value) else parameters[name]
            assert identical(value, expected), name
        assert identical(record["values"]["problem.radius"], UNITS.to_code_units("1e19 cm", "length"))
        assert identical(record["values"]["output.times"], [1.0, UNITS.to_code_units("1 Gyr", "time")])

        ## Plain values only: Python's own types of PAR03, with every element of a list one of them as well. type()
        ## rather than isinstance(), so that a subclass, such as NumPy's float64, would not pass.
        for value in record["values"].values():
            elements = value if is_list(value) else [value]
            assert all(type(element) in (bool, int, float, str) for element in elements)

        ## The record is a dictionary of its own: changing it, a list in it included, changes neither the parameters
        ## nor a record made afterwards.
        record["values"]["hydro.cfl"] = 0.9
        record["values"]["output.times"].append(5.0)
        record["selected"]["ambient.density"] = "number_density"
        assert parameters["hydro.cfl"] == 1.0
        assert parameters.to_record()["values"]["output.times"] == list(parameters["output.times"])
        assert parameters.to_record()["selected"] == {"ambient.density": "mass_density"}

    def test_record_includes_the_selected_groups(self) -> None:
        """Check that the record holds the group selected for each set of alternatives (PAR19, PAR22)."""
        ## The default group, with nothing given, and the other group, selected by a value given for its parameter.
        defaults = resolve(DECLARATIONS, units=UNITS).to_record()
        given = resolve(DECLARATIONS, overrides={"ambient.n": 2.0}, units=UNITS).to_record()

        ## By the name of the set, as Parameters.selected states it.
        assert defaults["selected"] == {"ambient.density": "mass_density"}
        assert given["selected"] == {"ambient.density": "number_density"}

    ## Hypothesis draws a value for a parameter of every type of PAR03: any finite float, the largest, the smallest
    ## and -0.0 included; any integer, however large; any string; and lists of floats of any length, the empty list
    ## included. Floats are finite, as every other value is refused (PAR24).
    @given(
        cfl=st.floats(allow_nan=False, allow_infinity=False),
        radius=st.floats(allow_nan=False, allow_infinity=False),
        nx1=st.integers(),
        enabled=st.booleans(),
        solver=st.text(),
        times=st.lists(st.floats(allow_nan=False, allow_infinity=False)),
    )
    def test_record_survives_json_exactly(
        self, cfl: float, radius: float, nx1: int, enabled: bool, solver: str, times: list[float]
    ) -> None:
        """Check that the record written as JSON and read back is identical, every float bit for bit (PAR19)."""
        overrides = {
            "hydro.cfl": cfl,
            "problem.radius": radius,
            "mesh.nx1": nx1,
            "cooling.enabled": enabled,
            "hydro.solver": solver,
            "output.times": times,
        }
        record = resolve(DECLARATIONS, overrides=overrides, units=UNITS).to_record()

        ## Written as text and read back, as an output would store it. JSON writes each float with the shortest digits
        ## that read back as the same double, so that text is no obstacle to exactness. allow_nan=False writes
        ## standard JSON only, which every reader of an output can read, and would raise for an infinity or NaN.
        stored = json.loads(json.dumps(record, allow_nan=False))

        ## The same names in the same order, the same groups, and every value identical, of the same type and bit for
        ## bit: == alone would take 1 for 1.0, and 0.0 for -0.0.
        assert stored["selected"] == record["selected"]
        assert list(stored["values"]) == list(record["values"])
        for name, value in record["values"].items():
            assert identical(stored["values"][name], value), name

    def test_resolving_from_the_record_gives_the_same_values(self) -> None:
        """Check that resolving with the record as the restart layer gives the same values, bit for bit (PAR19, PAR15).

        Values given with a unit included, which the record holds in code units and are not converted again; the
        selected groups of alternatives are the same as well.
        """
        ## Values given in each way that is converted, and the number density, which selects the group of the
        ## alternatives that is not the default.
        overrides = {"hydro.cfl": 1, "problem.radius": "1e19 cm", "output.times": [1, "1 Gyr"], "ambient.n": 2.0}
        original = resolve(DECLARATIONS, overrides=overrides, units=UNITS)

        ## The record as a restart file stores it, written as JSON and read back, and resolved again without a unit
        ## system: the record needs none, as it holds every value in code units already.
        stored = json.loads(json.dumps(original.to_record(), allow_nan=False))
        restarted = resolve(DECLARATIONS, record=stored)

        ## The same names in the same order, every value identical, of the same type and bit for bit, and the same
        ## group selected.
        assert list(restarted) == list(original)
        for name in original:
            assert identical(restarted[name], original[name]), name
        assert restarted.selected == original.selected == {"ambient.density": "number_density"}
