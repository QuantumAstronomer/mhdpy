"""Tests of the dependencies of the parameters (PAR21)."""

import subprocess
import sys

import pytest

## The parameters as a run imports them: the package, whose __init__.py runs before any of its modules is imported, and
## each of its modules. A module added to the component is added here as well.
MODULES = [
    "mhdpy.foundation.parameters",
    "mhdpy.foundation.parameters.declarations",
    "mhdpy.foundation.parameters.resolution",
    "mhdpy.foundation.parameters.resolved",
    "mhdpy.foundation.parameters.templates",
    "mhdpy.foundation.parameters.values",
]

## A small program that imports one module and prints the name of every module that importing it loaded, one per line.
## sys.modules holds every module loaded so far; whatever is in it after the import but not before was loaded by the
## import. The module to import is passed as the program's first argument, sys.argv[1].
PROGRAM = """
import importlib
import sys

before = set(sys.modules)
importlib.import_module(sys.argv[1])
for name in sorted(set(sys.modules) - before):
    print(name)
"""


def loaded_by(module: str) -> set[str]:
    """Return the names of the modules that importing a module loads, in a fresh Python interpreter.

    A fresh interpreter, the one running the tests (sys.executable), because this one has long since imported pytest,
    NumPy and the unit system itself, which importing a module again would not load anew.
    """
    result = subprocess.run([sys.executable, "-c", PROGRAM, module], capture_output=True, text=True, check=True)
    return set(result.stdout.split())


class TestDependencies:
    """PAR21: the parameters need nothing beyond the standard library, and are given the unit system of a run."""

    @pytest.mark.parametrize("module", MODULES)
    def test_standard_library_only(self, module: str) -> None:
        """Check that importing the parameters imports nothing beyond the standard library and mhdpy (PAR21).

        NumPy included: the parameters are read before anything else is loaded.
        """
        ## A module's package is the part of its name before the first dot: numpy._core.multiarray is part of numpy.
        packages = {name.split(".")[0] for name in loaded_by(module)}

        ## sys.stdlib_module_names lists every module of Python's standard library. What is neither in it nor mhdpy
        ## itself is a further dependency. The set must be empty; if not, the assert shows it.
        further = packages - sys.stdlib_module_names - {"mhdpy"}
        assert further == set()

    @pytest.mark.parametrize("module", MODULES)
    def test_unit_system_is_not_imported(self, module: str) -> None:
        """Check that importing the parameters does not import the unit system, which a run passes in (PAR21)."""
        loaded = loaded_by(module)

        ## The unit system and the constants it uses, both of which need NumPy; the notation, which needs nothing
        ## beyond the standard library, is what the parameters check units with, and may be loaded.
        assert "mhdpy.foundation.units.system" not in loaded
        assert "mhdpy.foundation.units.constants" not in loaded
