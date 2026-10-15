"""Tests of the declarations of parameters: their items, names, types and units, and the set they form (PAR01-PAR05)."""

import pytest

from mhdpy.foundation.parameters.tests import NOT_WRITTEN


class TestDeclarations:
    """PAR01-PAR05: a parameter exists because a module declares it, with everything mhdpy needs to know about it."""

    ## ---- The items of a declaration (PAR01) ----

    @NOT_WRITTEN
    def test_declaration_keeps_its_items(self) -> None:
        """Check that a declaration keeps its name, type, default, documentation, unit, check and restart behaviour.

        Each item is read back exactly as declared (PAR01).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_fixed_unless_declared_changeable(self) -> None:
        """Check that a parameter declared without restart behaviour is fixed on restart (PAR01)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_declaration_without_default_is_refused(self) -> None:
        """Check that a declaration without a default is refused, naming the parameter (PAR01).

        There are no required parameters: with the defaults alone, every run can start.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_check_without_description_is_refused(self) -> None:
        """Check that a check declared without a description in words is refused (PAR01).

        The description is what an error message states as the expected condition (PAR13).
        """
        pytest.fail("Not written yet.")

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
