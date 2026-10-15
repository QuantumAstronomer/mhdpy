"""The checks of mhdpy, run with one command: ``uv run nox`` (decision brief D16).

Each check is a session, a function marked with ``@nox.session``. ``uv run nox`` runs them all, in the order they are
defined here: formatting, linting and type checking (including whether the layer READMEs agree with the docstrings
they are made of), the tests with the kernels compiled and uncompiled, and their combined coverage. ``uv run nox -s
<name>`` runs one session, ``uv run nox --list`` lists them, and arguments after ``--`` are passed on to pytest, for
example ``uv run nox -s tests -- -k TestRecords``. The session ``readmes``, which writes the layer READMEs, runs only
when asked for.

CI runs the same sessions (D16.4), so a check is defined here once and runs the same locally and in CI.
"""

import ast
import platform
import sys
from pathlib import Path

import nox

## The lowest version of nox this file is written for; older versions refuse to run it, rather than misread it.
nox.needs_version = ">=2026.8.17"

## D16.2: every session runs in the project's own environment, the one uv keeps in line with uv.lock. nox is started
## with ``uv run nox``, so uv brings that environment up to date first, and nothing is installed or rebuilt here.
nox.options.default_venv_backend = "none"

## The two ways of running the kernels (D04.3), selected by the environment variable MHDPY_KERNELS.
KERNELS = ["compiled", "uncompiled"]

## The layers of mhdpy, such as src/mhdpy/foundation: every subpackage of mhdpy except its tests. Each has a README.md
## made of the docstrings of the layer, of its components (its own subpackages) and of their public modules.
LAYERS = sorted(path.parent for path in Path("src/mhdpy").glob("*/__init__.py") if path.parent.name != "tests")


def docstring(path: Path) -> str:
    """Return the docstring of a module, read from its source without importing it."""
    ## ast.parse turns the source into a syntax tree, from which ast.get_docstring takes the module's docstring, with
    ## its indentation removed as Python's help() does. A module without a docstring gives an empty one.
    return ast.get_docstring(ast.parse(path.read_text())) or ""


def public_modules(package: Path) -> list[Path]:
    """Return the public modules of a package, in alphabetical order: those whose name does not start with "_"."""
    return [module for module in sorted(package.glob("*.py")) if not module.name.startswith("_")]


def components(package: Path) -> list[Path]:
    """Return the components of a layer, in alphabetical order: its subpackages, except tests (D01.4)."""
    return sorted(path.parent for path in package.glob("*/__init__.py") if path.parent.name != "tests")


def layer_readme(layer: Path) -> str:
    """Return the README of a layer, made of the docstrings of its packages and their public modules (D16).

    First the docstring of the layer, then a section per component: the docstring of its package, followed by that of
    each of its public modules. Modules directly in the layer, if any, get a section each, before the components. Tests
    are not part of a layer's description.
    """
    name = ".".join(layer.parts[1:])  ## src/mhdpy/foundation -> mhdpy.foundation
    sections = [
        f"# `{name}`",
        "<!-- Generated from the docstrings of this package and its modules by `uv run nox -s readmes`: edit the "
        "docstrings, not this file. `uv run nox` checks that the two agree. -->",
        docstring(layer / "__init__.py"),
    ]
    for module in public_modules(layer):
        sections += [f"## `{name}.{module.stem}`", docstring(module)]
    for component in components(layer):
        sections += [f"## `{name}.{component.name}`", docstring(component / "__init__.py")]
        for module in public_modules(component):
            sections += [f"### `{name}.{component.name}.{module.stem}`", docstring(module)]
    return "\n\n".join(sections) + "\n"


@nox.session
def lint(session: nox.Session) -> None:
    """Check formatting, lint rules and types (D01.7, D01.8), and that the layer READMEs match their docstrings (D16).

    Formatting is checked, never applied, so that running the checks cannot change what is about to be committed.
    """
    session.run("ruff", "format", "--check")
    session.run("ruff", "check")
    session.run("pyright")

    ## Each layer's README must be exactly what the docstrings it is made of give now; otherwise a docstring was changed
    ## without regenerating the README, or the README was edited by hand. A missing README counts as out of date.
    stale: list[str] = []
    for layer in LAYERS:
        readme = layer / "README.md"
        if not readme.exists() or readme.read_text() != layer_readme(layer):
            stale.append(str(readme))
    if stale:
        session.error(f"Out of date with the docstrings: {', '.join(stale)}. Regenerate with: uv run nox -s readmes")


## default=False: this session writes files, so it runs only when asked for by name, never as part of ``uv run nox``.
@nox.session(default=False)
def readmes(session: nox.Session) -> None:
    """Write the README of each layer from the docstrings of its package and modules (D16)."""
    for layer in LAYERS:
        (layer / "README.md").write_text(layer_readme(layer))
        session.log(f"Wrote {layer / 'README.md'}")


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
