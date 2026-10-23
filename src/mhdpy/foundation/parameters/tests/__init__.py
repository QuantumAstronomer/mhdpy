"""Tests of the parameters: requirements PAR01-PAR24 (docs/requirements/L0-foundation/parameters.md).

One test module per group of requirements in that document, each with a class of the same scope; each test names the
requirements it checks in its docstring. What several test modules need is defined here once.
"""

from pathlib import Path

import pytest

## A test that is planned but not written yet. Its body is pytest.fail("Not written yet."), which this marker declares
## an expected failure ("xfail"), so the suite stays green while the test is visibly unfinished: pytest reports it as
## "x" rather than as passed or failed. raises= accepts only that deliberate failure, so a stub that crashed for any
## other reason would still fail. strict=True turns a stub that unexpectedly passes into a failure, so the marker cannot
## be forgotten once the test is written. When a test is written, its marker is removed, and when no test uses the
## marker any more, so is this definition.
NOT_WRITTEN = pytest.mark.xfail(reason="not written yet", raises=pytest.fail.Exception, strict=True)


def parameter_file(folder: Path, text: str) -> Path:
    """Return the path of a parameter file with the given text, written in a folder of the test's own."""
    path = folder / "run.toml"
    path.write_text(text)
    return path
