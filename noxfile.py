"""The checks of mhdpy, run with one command: ``uv run nox`` (decision brief D16).

Each check is a session, a function marked with ``@nox.session``. ``uv run nox`` runs them all, in the order they are
defined here: formatting, linting and type checking, the tests with the kernels compiled and uncompiled, and their
combined coverage. ``uv run nox -s <name>`` runs one session, ``uv run nox --list`` lists them, and arguments after
``--`` are passed on to pytest, for example ``uv run nox -s tests -- -k TestRecords``.

CI runs the same sessions (D16.4), so a check is defined here once and runs the same locally and in CI.
"""

import platform
import sys

import nox

## The lowest version of nox this file is written for; older versions refuse to run it, rather than misread it.
nox.needs_version = ">=2026.8.17"

## D16.2: every session runs in the project's own environment, the one uv keeps in line with uv.lock. nox is started
## with ``uv run nox``, so uv brings that environment up to date first, and nothing is installed or rebuilt here.
nox.options.default_venv_backend = "none"

## The two ways of running the kernels (D04.3), selected by the environment variable MHDPY_KERNELS.
KERNELS = ["compiled", "uncompiled"]


@nox.session
def lint(session: nox.Session) -> None:
    """Check formatting, lint rules and types, as in CI (D01.7, D01.8).

    Formatting is checked, never applied, so that running the checks cannot change what is about to be committed.
    """
    session.run("ruff", "format", "--check")
    session.run("ruff", "check")
    session.run("pyright")


## The tests session is parametrised: nox runs it once for each kernel mode, as two sessions named tests(compiled) and
## tests(uncompiled). ids= gives them those short names; -s tests runs both, -s "tests(uncompiled)" one of them.
@nox.session
@nox.parametrize("kernels", KERNELS, ids=KERNELS)
def tests(session: nox.Session, kernels: str) -> None:
    """Run the tests with the kernels compiled or uncompiled, measuring coverage (D02.8, D04.3).

    The coverage of a single run is not checked here: it reaches 100 % only when both kernel modes are combined, which
    the coverage session does.
    """
    ## Each run writes its coverage to a file of its own, named after the platform, the Python version and the kernel
    ## mode, for example .coverage.darwin-3.14-compiled. The names differ between all jobs of the CI matrix as well,
    ## so the coverage session can combine the files of a local run and those collected from CI alike.
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    coverage_file = f".coverage.{platform.system().lower()}-{python}-{kernels}"

    ## --cov measures coverage, --cov-report= (empty) prints no report, and --cov-fail-under=0 overrides the 100 %
    ## required in pyproject.toml for this single run. session.posargs holds the arguments given after --.
    session.run(
        "pytest",
        "--cov",
        "--cov-report=",
        "--cov-fail-under=0",
        *session.posargs,
        env={"MHDPY_KERNELS": kernels, "COVERAGE_FILE": coverage_file},
    )


@nox.session
def coverage(session: nox.Session) -> None:
    """Combine the coverage of all test runs and require 100 % line and branch coverage (D02.8).

    Meaningful after full runs of both test sessions: a run with a selection of tests leaves lines uncovered.
    """
    ## coverage combine merges every .coverage.* file present into one file, .coverage, and removes them; coverage
    ## report then prints the result and fails below the 100 % required in pyproject.toml. The files of the test runs
    ## are used up by combining them, so a second coverage session needs the tests to be run again first.
    session.run("coverage", "combine")
    session.run("coverage", "report")
