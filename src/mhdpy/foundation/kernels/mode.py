"""The switch between compiled and uncompiled kernels: run mhdpy's kernels compiled (the default) or as plain Python.

Kernels are written in Cython's pure Python mode, so every kernel exists twice in an installation: as a compiled
extension module and as its ``.py`` source, installed next to it under the same name (D04.1). Python always imports the
compiled module. Setting the environment variable ``MHDPY_KERNELS=uncompiled`` before mhdpy is imported makes every
module of mhdpy load from its source instead (D04.3).

The uncompiled kernels are there for checking, not for running simulations. Coverage is measured with them, because
coverage cannot look inside compiled code, and a debugger can step through them; the tests of each kernel check that
both ways give bit-for-bit identical results, comparing the selected kernels with an uncompiled copy loaded next to
them. ``uv run nox`` runs every test both ways and combines the coverage of the two runs (D16).

The switch acts when mhdpy is imported: ``mhdpy/__init__.py`` calls ``install`` before any kernel is imported, and an
unknown value of ``MHDPY_KERNELS`` is refused there and then. The tests are in ``tests/test_backend.py``.
"""

import importlib.resources
import importlib.util
import os
import sys
from importlib.machinery import ModuleSpec
from types import ModuleType

VARIABLE = "MHDPY_KERNELS"
MODES = ("compiled", "uncompiled")


def selected() -> str:
    """Return the kernel mode requested through ``MHDPY_KERNELS``, which defaults to compiled.

    An unknown value is an error rather than a silent fallback, so that a typing error cannot make an uncompiled
    coverage run quietly test the compiled kernels instead.
    """
    mode = os.environ.get(VARIABLE, "compiled")
    if mode not in MODES:
        raise ValueError(f"{VARIABLE} must be one of {', '.join(MODES)}, got: {mode!r}.")
    return mode


def source_spec(name: str) -> ModuleSpec | None:
    """Return a spec that loads module ``name`` of mhdpy from its ``.py`` source, or None if it has none."""
    package, _, leaf = name.rpartition(".")
    source = importlib.resources.files(package).joinpath(f"{leaf}.py")
    if not source.is_file():
        return None
    return importlib.util.spec_from_file_location(name, str(source))


class SourceFinder:
    """Find mhdpy's modules as ``.py`` sources, ahead of their compiled versions."""

    @staticmethod
    def find_spec(name: str, path: object = None, target: object = None) -> ModuleSpec | None:
        """Return the source spec of a module of mhdpy; leave every other module to the usual finders."""
        if not name.startswith("mhdpy."):
            return None
        return source_spec(name)


def install() -> None:
    """Put the source finder in front of all others if uncompiled kernels are requested."""
    if selected() == "uncompiled":
        sys.meta_path.insert(0, SourceFinder())


def load_uncompiled(name: str) -> ModuleType:
    """Load a fresh, uncompiled copy of module ``name``, whatever the kernel mode; for equivalence tests.

    The copy is not registered in ``sys.modules``, so it exists next to the compiled module rather than replacing it.
    """
    spec = source_spec(name)
    if spec is None or spec.loader is None:
        raise ImportError(f"{name} has no source file")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
