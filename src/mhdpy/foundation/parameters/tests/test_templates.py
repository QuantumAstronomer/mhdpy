"""Tests of the template parameter file written for a set of declarations (PAR20)."""

import pytest

from mhdpy.foundation.parameters.tests import NOT_WRITTEN


class TestTemplates:
    """PAR20: a template gives every parameter at its default, documented, and resolves to exactly the defaults."""

    @NOT_WRITTEN
    def test_template_has_a_table_per_section(self) -> None:
        """Check that the template is a TOML document with one table per section of the names (PAR20)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_template_gives_every_default(self) -> None:
        """Check that the template gives every parameter at its default as declared, with its unit where it has one.

        A default of "100 pc" is written as that string, not in code units (PAR20).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_template_documents_every_parameter(self) -> None:
        """Check that the comments of each parameter give its documentation, unit, condition and restart behaviour.

        The template is the user's reference while editing (PAR20).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_other_alternatives_are_comments(self) -> None:
        """Check that parameters of groups of alternatives other than the default are written as comments (PAR20).

        With their defaults, so that the template selects the default group of each set of alternatives (PAR22).
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_template_resolves_to_the_defaults(self) -> None:
        """Check that the template, read back unchanged as a parameter file, resolves to exactly the defaults (PAR20).

        Every value identical, and for every type of PAR03.
        """
        pytest.fail("Not written yet.")
