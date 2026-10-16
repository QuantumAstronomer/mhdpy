"""Tests of the declarations of parameters: their items, names, types and units, and the set they form (PAR01-PAR05)."""

import re
from typing import Any

import pytest

from mhdpy.foundation.parameters.declarations import Check, Parameter
from mhdpy.foundation.parameters.tests import NOT_WRITTEN


def label(value: object) -> str:
    """Return the name of a value in pytest's report of a test case: a type by its name, as int, others by str().

    Without it, pytest would name a type as <class 'int'>. A generic type such as list[int] is not a class, and str()
    writes it as it is written in Python already.
    """
    return value.__name__ if isinstance(value, type) else str(value)


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


## Names of the form of PAR02: two or more parts separated by dots, each a lowercase identifier, with digits and
## underscores after the first character. A quantity named by a Greek letter is written by the letter's name, as
## "hydro.rho"; the letter itself is refused (MALFORMED_NAMES).
VALID_NAMES = ["hydro.cfl", "output.snapshot.dt", "cooling.t_floor", "mesh.nx1", "problem.r_0", "hydro.rho"]

## Names of other forms, each refused for the reason in its comment.
# fmt: off
MALFORMED_NAMES = [
    "cfl",                               ## a single part, not namespaced by a module
    "Hydro.cfl",                         ## an uppercase letter
    "hydro..cfl",                        ## an empty part
    ".hydro.cfl",                        ## an empty first part
    "hydro.cfl.",                        ## an empty last part
    "hydro.1cfl",                        ## a part that starts with a digit
    "hydro-x.cfl",                       ## a hyphen
    "hydro. cfl",                        ## a space
    "hydro.\N{GREEK SMALL LETTER RHO}",  ## a Greek letter, outside ASCII, which TOML does not allow in a bare key
    "",                                  ## no name at all
]
# fmt: on

## Types of PAR03, each with a default the declaration accepts and the unit it needs. Besides a default of the type
## itself, a float takes an integer, which PAR12 accepts and converts, and a value with a unit (PAR09), alone or in a
## list. Any, for the same reason as in DECLARATIONS.
# fmt: off
ACCEPTED: list[tuple[Any, Any, Any]] = [
    (bool,        True,                None           ),
    (int,         64,                  "dimensionless"),
    (float,       0.4,                 "dimensionless"),
    (float,       1,                   "dimensionless"),
    (float,       "100 pc",            {"length": 1}  ),
    (str,         "hllc",              None           ),
    (list[bool],  [True, False],       None           ),
    (list[int],   [1, 2],              "dimensionless"),
    (list[float], [0.1, 2],            "dimensionless"),
    (list[float], ["1 pc", 2.5],       {"length": 1}  ),
    (list[str],   ["rho", "pressure"], None           ),
]

## Types outside PAR03, each refused for the reason in its comment.
UNSUPPORTED: list[Any] = [
    dict,               ## a mapping
    tuple,              ## a tuple, not a list
    complex,            ## a number TOML cannot write
    type(None),         ## no value at all
    list,               ## a list without the type of its elements
    list[int | str],    ## a list of mixed types
    list[list[int]],    ## a list of lists
    dict[str, float],   ## a mapping with typed keys and values
]

## Defaults that are not of their declared type, by the rules of PAR12, each with the unit its type needs.
WRONG_DEFAULTS: list[tuple[Any, Any, Any]] = [
    (int,         64.0,             "dimensionless"),  ## a float for an int, although whole
    (int,         True,             "dimensionless"),  ## a boolean for an int, though Python counts it one
    (int,         "64",             "dimensionless"),  ## a string for an int
    (float,       False,            "dimensionless"),  ## a boolean for a float
    (float,       "0.4",            "dimensionless"),  ## a string for a float that is not a value with a unit
    (bool,        1,                None           ),  ## an integer for a bool
    (bool,        "true",           None           ),  ## a string for a bool
    (str,         1.0,              None           ),  ## a number for a str
    (list[float], 0.4,              "dimensionless"),  ## a single value for a list
    (list[str],   ("rho",),         None           ),  ## a tuple for a list
    (list[int],   [1, 2.0],         "dimensionless"),  ## an element of the wrong type
    (list[float], [0.1, "x"],       "dimensionless"),  ## an element that is not a value with a unit
]

## Defaults given with a unit whose dimensions differ from those of the parameter's unit, each for the reason in its
## comment. The notation finds the dimensions of both without a unit system (PAR03, PAR21).
WRONG_DIMENSIONS: list[tuple[Any, Any, Any]] = [
    (float,       "100 pc",           {"time": 1}    ),  ## a length for a time
    (float,       "100 pc",           "density"      ),  ## a length for a named unit of other dimensions
    (float,       "100 pc",           "dimensionless"),  ## a length for a pure number
    (float,       "1e4 K",            {"length": 1}  ),  ## a temperature for a length
    (list[float], ["1 pc", "1 Myr"],  {"length": 1}  ),  ## one element of a list a time instead of a length
]

## Each form of unit of PAR04, with a default given with a unit of the same dimensions, or a plain number: a pure
## number, named units (the magnetic field among them, whose code unit has the factor sqrt(4 pi)), and dimensions,
## among them a temperature, half-integer exponents and an exponent of zero, which is left out.
UNIT_FORMS: list[tuple[Any, Any]] = [
    ("dimensionless",                             0.4             ),
    ("density",                                   "1e-24 g cm^-3" ),
    ("magnetic_field",                            "1e-6 G"        ),
    ({"length": 1, "time": -1},                   "10 km s^-1"    ),
    ({"temperature": 1},                          "1e4 K"         ),
    ({"length": -0.5, "mass": 0.5, "time": -1},   1.0             ),
    ({"length": 2, "mass": 0},                    "1 cm^2"        ),
]
# fmt: on


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

    ## Run this test once for each name of VALID_NAMES.
    @pytest.mark.parametrize("name", VALID_NAMES)
    def test_valid_names_are_accepted(self, name: str) -> None:
        """Check that names of two or more dotted parts, each a lowercase identifier, are accepted (PAR02).

        For example "hydro.cfl", "output.snapshot.dt" and "cooling.t_floor".
        """
        parameter = Parameter(name=name, type=float, default=0.4, doc="A parameter.", unit="dimensionless")
        assert parameter.name == name

    ## Run this test once for each name of MALFORMED_NAMES. ids= names each case by its string in quotes, so that the
    ## empty name and the one with a space can be told apart in a report.
    @pytest.mark.parametrize("name", MALFORMED_NAMES, ids=[repr(name) for name in MALFORMED_NAMES])
    def test_malformed_names_are_refused(self, name: str) -> None:
        """Check that a name of any other form is refused, naming it (PAR02).

        Among them: a single part ("cfl"), an uppercase letter ("Hydro.cfl"), an empty part ("hydro..cfl"), a part that
        starts with a digit ("hydro.1cfl"), a hyphen ("hydro-x.cfl") and a Greek letter.
        """
        ## The message contains the name as Python writes it, in quotes; re.escape makes its dots match literally.
        with pytest.raises(ValueError, match=re.escape(repr(name))):
            Parameter(name=name, type=float, default=0.4, doc="A parameter.", unit="dimensionless")

    ## ---- Types (PAR03) ----

    ## Run this test once for each type and default of ACCEPTED, named by both.
    @pytest.mark.parametrize(("type_", "default", "unit"), ACCEPTED, ids=[f"{label(t)}-{d!r}" for t, d, _ in ACCEPTED])
    def test_supported_types_are_accepted(self, type_: Any, default: Any, unit: Any) -> None:
        """Check that bool, int, float, str and lists of each are accepted as types, with defaults of them (PAR03).

        A float also takes an integer default and a default with a unit, alone or in a list (PAR12, PAR09).
        """
        ## type_, with a trailing underscore, because the name type is Python's own.
        parameter = Parameter(name="test.value", type=type_, default=default, doc="A parameter.", unit=unit)
        assert parameter.type == type_
        assert parameter.default == default

    ## Run this test once for each type of UNSUPPORTED.
    @pytest.mark.parametrize("type_", UNSUPPORTED, ids=label)
    def test_unsupported_type_is_refused(self, type_: Any) -> None:
        """Check that any other type, such as dict, tuple or complex, or a list of mixed types, is refused (PAR03).

        The refusal is a TypeError, as Python's own for a value of the wrong type, and names the parameter.
        """
        with pytest.raises(TypeError, match="'test.value'"):
            Parameter(name="test.value", type=type_, default=None, doc="A parameter.")

    ## Run this test once for each type and default of WRONG_DEFAULTS, named by both.
    @pytest.mark.parametrize(
        ("type_", "default", "unit"), WRONG_DEFAULTS, ids=[f"{label(t)}-{d!r}" for t, d, _ in WRONG_DEFAULTS]
    )
    def test_default_of_wrong_type_is_refused(self, type_: Any, default: Any, unit: Any) -> None:
        """Check that a default that is not of the declared type is refused, naming the parameter (PAR03).

        By the rules of PAR12: a float default for an int parameter is refused, an int default for a float parameter
        is not (see the test above).
        """
        with pytest.raises(TypeError, match="'test.value'"):
            Parameter(name="test.value", type=type_, default=default, doc="A parameter.", unit=unit)

    def test_default_failing_its_check_is_refused(self) -> None:
        """Check that a default that does not satisfy the declared check is refused, naming the parameter (PAR03).

        A plain default is checked when declared; a default with a unit is checked when resolved, in code units (PAR13).
        """
        in_unit_interval = Check(lambda value: 0 < value <= 1, "in (0, 1]")

        ## The message names the parameter and states the condition in the words of the declaration.
        with pytest.raises(ValueError, match=re.escape("'hydro.cfl' must be in (0, 1]")):
            Parameter(
                name="hydro.cfl",
                type=float,
                default=1.5,
                doc="The Courant number.",
                unit="dimensionless",
                check=in_unit_interval,
            )

        ## A default with a unit cannot be checked yet: the condition applies in code units, and a declaration knows no
        ## unit system. So a negative radius is accepted here, and refused when the parameters are resolved.
        positive = Check(lambda value: value > 0, "positive")
        Parameter(
            name="cloud.radius", type=float, default="-100 pc", doc="A radius.", unit={"length": 1}, check=positive
        )

    ## Run this test once for each case of WRONG_DIMENSIONS, named by the default and the unit.
    @pytest.mark.parametrize(
        ("type_", "default", "unit"), WRONG_DIMENSIONS, ids=[f"{d!r}-{u!r}" for _, d, u in WRONG_DIMENSIONS]
    )
    def test_default_with_wrong_dimensions_is_refused(self, type_: Any, default: Any, unit: Any) -> None:
        """Check that a default with a unit of other dimensions than the parameter's is refused when declared (PAR03).

        For example "100 pc", a length, as the default of a time; no unit system is needed to find it (PAR21).
        """
        with pytest.raises(ValueError, match="'test.value'"):
            Parameter(name="test.value", type=type_, default=default, doc="A parameter.", unit=unit)

    ## ---- Units (PAR04) ----

    ## Run this test once for each unit of UNIT_FORMS, named by the unit.
    @pytest.mark.parametrize(("unit", "default"), UNIT_FORMS, ids=[repr(unit) for unit, _ in UNIT_FORMS])
    def test_three_forms_of_unit_are_accepted(self, unit: Any, default: Any) -> None:
        """Check that a numeric parameter accepts each form of unit (PAR04).

        Dimensionless; dimensions as exponents of length, mass, time and temperature; or a named unit of the unit
        system, such as "density" or "magnetic_field".
        """
        ## The unit is kept as declared, whatever its form; a default with a unit of the same dimensions is accepted.
        parameter = Parameter(name="test.value", type=float, default=default, doc="A parameter.", unit=unit)
        assert parameter.unit == unit

    ## Run this test for each numeric type, alone and in a list.
    @pytest.mark.parametrize(
        ("type_", "default"), [(int, 1), (float, 1.0), (list[int], [1]), (list[float], [1.0])], ids=label
    )
    def test_numeric_parameter_without_unit_is_refused(self, type_: Any, default: Any) -> None:
        """Check that an int or float parameter, or a list of either, declared without a unit is refused (PAR04)."""
        ## A missing unit is a mistake in the declaration, found here, rather than a value that cannot be converted
        ## in a user's run; dimensionless is stated, not implied.
        with pytest.raises(ValueError, match="'test.value'"):
            Parameter(name="test.value", type=type_, default=default, doc="A parameter.")

    ## Run this test for an integer with dimensions, one with a named unit, and a list of integers with dimensions.
    @pytest.mark.parametrize(
        ("type_", "default", "unit"),
        [(int, 1, {"length": 1}), (int, 1, "density"), (list[int], [1], {"time": 1})],
        ids=label,
    )
    def test_integer_parameter_is_dimensionless(self, type_: Any, default: Any, unit: Any) -> None:
        """Check that an int parameter, or a list of integers, declared with dimensions or a named unit is refused.

        Integers count things, such as cells or steps, and have no dimensions (PAR04).
        """
        with pytest.raises(ValueError, match="'test.value'"):
            Parameter(name="test.value", type=type_, default=default, doc="A parameter.", unit=unit)

    ## Run this test for a bool, a str and lists of both, each declared with a unit of some form.
    @pytest.mark.parametrize(
        ("type_", "default", "unit"),
        [
            (bool, True, "dimensionless"),
            (str, "hllc", {"length": 1}),
            (list[bool], [True], "dimensionless"),
            (list[str], ["rho"], "density"),
        ],
        ids=label,
    )
    def test_unit_of_bool_or_str_is_refused(self, type_: Any, default: Any, unit: Any) -> None:
        """Check that a bool or str parameter, or a list of either, declared with a unit is refused (PAR04)."""
        with pytest.raises(ValueError, match="'test.value'"):
            Parameter(name="test.value", type=type_, default=default, doc="A parameter.", unit=unit)

    ## Run this test for each unit of none of the three forms: a misspelt named unit, a misspelt dimension, an exponent
    ## that is not a multiple of a quarter, and a number instead of a unit. The notation's own messages for each are
    ## tested with the conversion (UNI20); here the refusal must name the parameter.
    @pytest.mark.parametrize("unit", ["densty", {"lenght": 1}, {"length": 0.3}, 5], ids=label)
    def test_invalid_unit_is_refused(self, unit: Any) -> None:
        """Check that a unit that is none of the three forms is refused (PAR04).

        For example an unknown named unit ("densty"), or dimensions with an unknown name ("lenght").
        """
        with pytest.raises(ValueError, match="'test.value'"):
            Parameter(name="test.value", type=float, default=1.0, doc="A parameter.", unit=unit)

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
