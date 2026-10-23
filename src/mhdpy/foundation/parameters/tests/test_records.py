"""Tests of reading the resolved parameters and of their record (PAR18-PAR19)."""

from collections.abc import Sequence
from typing import Any, cast

import pytest

from mhdpy.foundation.parameters.declarations import Alternatives, Declarations, Parameter
from mhdpy.foundation.parameters.resolution import resolve
from mhdpy.foundation.parameters.tests import NOT_WRITTEN
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


def identical(first: object, second: object) -> bool:
    """Return whether two values are identical: of the same type, and equal bit for bit, a list or tuple element-wise.

    == alone cannot tell them apart: in Python, 1 == 1.0 == True and 0.0 == -0.0. float.hex() writes the exact bits of a
    double, sign, exponent and digits, so that two floats with the same hex are the same double.
    """
    if type(first) is not type(second):
        return False
    if isinstance(first, list | tuple):
        ## The type checker learns that second is a list or tuple as well only from the comparison of types above, which
        ## it does not follow; cast tells it so, and that the elements may be of any type.
        firsts = cast(Sequence[object], first)
        seconds = cast(Sequence[object], second)
        return len(firsts) == len(seconds) and all(identical(a, b) for a, b in zip(firsts, seconds, strict=True))
    if isinstance(first, float):
        return first.hex() == cast(float, second).hex()
    return first == second


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

    @NOT_WRITTEN
    def test_record_is_plain_values_in_code_units(self) -> None:
        """Check that the record holds one plain value per name, in code units, for every declared parameter (PAR19)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_record_includes_the_selected_groups(self) -> None:
        """Check that the record holds the group selected for each set of alternatives (PAR19, PAR22)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_record_survives_json_exactly(self) -> None:
        """Check that the record written as JSON and read back is identical, every float bit for bit (PAR19)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_resolving_from_the_record_gives_the_same_values(self) -> None:
        """Check that resolving with the record as the restart layer gives the same values, bit for bit (PAR19, PAR15).

        Values given with a unit included, which the record holds in code units and are not converted again; the
        selected groups of alternatives are the same as well.
        """
        pytest.fail("Not written yet.")
