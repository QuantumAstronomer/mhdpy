"""Tests of the declarations of parameters: their items, names, types and units, and the set they form (PAR01-PAR05)."""

from typing import Any

import pytest

from mhdpy.foundation.parameters.declarations import Check, Parameter
from mhdpy.foundation.parameters.tests import NOT_WRITTEN

## Declarations with every item of PAR01 given, each item by its name: a dimensionless float that may change on restart,
## a length whose default is given with a unit, and a list of strings, which has no unit. Any, because the items are of
## different types; the test passes them to Parameter by name, as a module would.
DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "hydro.cfl",
        "type": float,
        "default": 0.4,
        "doc": "The Courant number.",
        "unit": "dimensionless",
        "check": Check(lambda value: 0 < value <= 1, "in (0, 1]"),
        "changeable": True,
    },
    {
        "name": "cloud.radius",
        "type": float,
        "default": "100 pc",
        "doc": "The radius of the cloud.",
        "unit": {"length": 1},
        "check": Check(lambda value: value > 0, "positive"),
        "changeable": False,
    },
    {
        "name": "output.variables",
        "type": list[str],
        "default": ["rho", "p"],
        "doc": "The variables written to every snapshot.",
        "unit": None,
        "check": None,
        "changeable": True,
    },
]


class TestDeclarations:
    """PAR01-PAR05: a parameter exists because a module declares it, with everything mhdpy needs to know about it."""

    ## ---- The items of a declaration (PAR01) ----

    ## Run this test once for each declaration above, named by the parameter's name.
    @pytest.mark.parametrize("items", DECLARATIONS, ids=[items["name"] for items in DECLARATIONS])
    def test_declaration_keeps_its_items(self, items: dict[str, Any]) -> None:
        """Check that a declaration keeps its name, type, default, documentation, unit, check and restart behaviour.

        Each item is read back exactly as declared (PAR01).
        """
        ## **items passes each entry of the dictionary as an argument of that name: Parameter(name="hydro.cfl", ...).
        parameter = Parameter(**items)

        ## Every item reads back as it was given: the default of "100 pc" as that string, not converted, since a
        ## declaration knows no unit system; the check as the same object.
        for item, value in items.items():
            assert getattr(parameter, item) == value, item

    def test_fixed_unless_declared_changeable(self) -> None:
        """Check that a parameter declared without restart behaviour is fixed on restart (PAR01)."""
        parameter = Parameter(name="mesh.nx1", type=int, default=64, doc="The number of cells.", unit="dimensionless")
        assert parameter.changeable is False

    def test_declaration_without_default_is_refused(self) -> None:
        """Check that a declaration without a default is refused (PAR01).

        There are no required parameters: with the defaults alone, every run can start.
        """
        ## The default is a required item, so Python itself refuses the declaration, with a TypeError that names the
        ## missing item. The type checker marks the call as an error as well, which is the point; the comment at the
        ## end of the line tells it that this one is deliberate.
        with pytest.raises(TypeError, match="default"):
            Parameter(name="hydro.cfl", type=float, doc="The Courant number.", unit="dimensionless")  # pyright: ignore[reportCallIssue]

    ## Run this test for empty documentation and for documentation of spaces only, neither of which documents anything.
    @pytest.mark.parametrize("doc", ["", "   "])
    def test_declaration_without_documentation_is_refused(self, doc: str) -> None:
        """Check that a declaration with empty documentation is refused, naming the parameter (PAR01).

        The documentation is what templates and the reference documentation show of a parameter (PAR20).
        """
        with pytest.raises(ValueError, match="'hydro.cfl'"):
            Parameter(name="hydro.cfl", type=float, default=0.4, doc=doc, unit="dimensionless")

    ## Run this test for an empty description and for one of spaces only, neither of which says anything.
    @pytest.mark.parametrize("description", ["", "   "])
    def test_check_without_description_is_refused(self, description: str) -> None:
        """Check that a check declared without a description in words is refused, naming the parameter (PAR01).

        The description is what an error message states as the expected condition (PAR13).
        """
        with pytest.raises(ValueError, match="'hydro.cfl'"):
            Parameter(
                name="hydro.cfl",
                type=float,
                default=0.4,
                doc="The Courant number.",
                unit="dimensionless",
                check=Check(lambda value: 0 < value <= 1, description),
            )

    ## ---- Names (PAR02) ----

    @NOT_WRITTEN
    def test_valid_names_are_accepted(self) -> None:
        """Check that names of two or more dotted parts, each a lowercase identifier, are accepted (PAR02).

        For example "hydro.cfl", "output.snapshot.dt" and "cooling.t_floor".
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_malformed_names_are_refused(self) -> None:
        """Check that a name of any other form is refused, naming it (PAR02).

        Among them: a single part ("cfl"), an uppercase letter ("Hydro.cfl"), an empty part ("hydro..cfl"), a part that
        starts with a digit ("hydro.1cfl"), a hyphen ("hydro-x.cfl") and a trailing dot ("hydro.cfl.").
        """
        pytest.fail("Not written yet.")

    ## ---- Types (PAR03) ----

    @NOT_WRITTEN
    def test_supported_types_are_accepted(self) -> None:
        """Check that bool, int, float, str and lists of each are accepted as types (PAR03)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_unsupported_type_is_refused(self) -> None:
        """Check that any other type, such as dict, tuple or complex, or a list of mixed types, is refused (PAR03)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_default_of_wrong_type_is_refused(self) -> None:
        """Check that a default that is not of the declared type is refused, naming the parameter (PAR03).

        By the rules of PAR12: a float default for an int parameter is refused, an int default for a float parameter
        is not.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_default_failing_its_check_is_refused(self) -> None:
        """Check that a default that does not satisfy the declared check is refused, naming the parameter (PAR03).

        A plain default is checked when declared; a default with a unit is checked when resolved, in code units (PAR13).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_default_with_wrong_dimensions_is_refused(self) -> None:
        """Check that a default with a unit of other dimensions than the parameter's is refused when declared (PAR03).

        For example "100 pc", a length, as the default of a time; no unit system is needed to find it (PAR21).
        """
        pytest.fail("Not written yet.")

    ## ---- Units (PAR04) ----

    @NOT_WRITTEN
    def test_three_forms_of_unit_are_accepted(self) -> None:
        """Check that a numeric parameter accepts each form of unit (PAR04).

        Dimensionless; dimensions as exponents of length, mass, time and temperature; or a named unit of the unit
        system, such as "density" or "magnetic_field".
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_numeric_parameter_without_unit_is_refused(self) -> None:
        """Check that an int or float parameter, or a list of either, declared without a unit is refused (PAR04)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_integer_parameter_is_dimensionless(self) -> None:
        """Check that an int parameter, or a list of integers, declared with dimensions or a named unit is refused.

        Integers count things, such as cells or steps, and have no dimensions (PAR04).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_unit_of_bool_or_str_is_refused(self) -> None:
        """Check that a bool or str parameter, or a list of either, declared with a unit is refused (PAR04)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_invalid_unit_is_refused(self) -> None:
        """Check that a unit that is none of the three forms is refused (PAR04).

        For example an unknown named unit ("densty"), or dimensions with an unknown name ("lenght").
        """
        pytest.fail("Not written yet.")

    ## ---- The set of a run's parameters (PAR05) ----

    @NOT_WRITTEN
    def test_name_declared_twice_is_refused(self) -> None:
        """Check that a set declaring the same name twice is refused, naming both declarations (PAR05)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_name_that_starts_another_is_refused(self) -> None:
        """Check that a set with a name that is the start of another is refused, naming both (PAR05).

        For example "output.snapshot" and "output.snapshot.dt", which TOML cannot write in one file.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_names_sharing_their_first_letters_are_accepted(self) -> None:
        """Check that names that only share their first letters, not a whole part, are accepted (PAR05).

        For example "hydro.cfl" and "hydro.cfl_max", or "output.snap" and "output.snapshot.dt".
        """
        pytest.fail("Not written yet.")
