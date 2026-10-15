"""Tests of the dependencies of the unit system and its notation (UNI18)."""

import subprocess
import sys

import pytest


class TestDependencies:
    """UNI18: the unit system needs nothing beyond the standard library and NumPy, its notation not even NumPy."""

    ## A small program that imports one module and prints the name of every module that importing it loaded, one per
    ## line. sys.modules holds every module loaded so far; whatever is in it after the import but not before was
    ## loaded by the import. The module to import is passed as the program's first argument, sys.argv[1].
    PROGRAM = """
import importlib
import sys

before = set(sys.modules)
importlib.import_module(sys.argv[1])
for name in sorted(set(sys.modules) - before):
    print(name)
"""

    ## Run this test for each module of the unit system, with the third-party packages it may use: NumPy for the unit
    ## system and the constants it uses, none at all for the notation, which the parameters read without NumPy (PAR21).
    ## The package itself, whose __init__.py runs before any of its modules is imported, must import nothing either:
    ## otherwise importing the notation would import NumPy all the same.
    @pytest.mark.parametrize(
        ("module", "allowed"),
        [
            ("mhdpy.foundation.units.system", {"numpy"}),
            ("mhdpy.foundation.units.constants", {"numpy"}),
            ("mhdpy.foundation.units.notation", set[str]()),
            ("mhdpy.foundation.units", set[str]()),
        ],
    )
    def test_no_further_dependencies(self, module: str, allowed: set[str]) -> None:
        """Check that importing the unit system imports no third-party package other than NumPy (UNI18).

        Importing the notation imports no third-party package at all, NumPy included.
        """
        ## The program runs in a fresh Python interpreter, the one running the tests (sys.executable), because this
        ## one has long since imported pytest, Hypothesis and the unit system itself.
        result = subprocess.run(
            [sys.executable, "-c", self.PROGRAM, module], capture_output=True, text=True, check=True
        )

        ## A module's package is the part of its name before the first dot: numpy._core.multiarray is part of numpy.
        packages = {name.split(".")[0] for name in result.stdout.split()}

        ## sys.stdlib_module_names lists every module of Python's standard library. What is neither in it, nor mhdpy
        ## itself, nor an allowed package, is a further dependency. The set must be empty; if not, the assert shows it.
        further = packages - sys.stdlib_module_names - {"mhdpy"} - allowed
        assert further == set()
