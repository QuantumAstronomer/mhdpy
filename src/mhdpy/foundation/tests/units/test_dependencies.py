"""Tests of the dependencies of the unit system (UNI18)."""

import subprocess
import sys

import pytest


class TestDependencies:
    """UNI18: the unit system needs nothing beyond the standard library and NumPy."""

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

    ## Run this test for both modules of the unit system: the units and the constants they use.
    @pytest.mark.parametrize("module", ["mhdpy.foundation.units", "mhdpy.foundation.constants"])
    def test_no_further_dependencies(self, module: str) -> None:
        """Check that importing the unit system imports no third-party package other than NumPy (UNI18)."""
        ## The program runs in a fresh Python interpreter, the one running the tests (sys.executable), because this
        ## one has long since imported pytest, Hypothesis and the unit system itself.
        result = subprocess.run(
            [sys.executable, "-c", self.PROGRAM, module], capture_output=True, text=True, check=True
        )

        ## A module's package is the part of its name before the first dot: numpy._core.multiarray is part of numpy.
        packages = {name.split(".")[0] for name in result.stdout.split()}

        ## sys.stdlib_module_names lists every module of Python's standard library. What is neither in it, nor mhdpy
        ## itself, nor NumPy, is a further dependency. The set must be empty; if not, the assert shows it.
        further = packages - sys.stdlib_module_names - {"mhdpy", "numpy"}
        assert further == set()
