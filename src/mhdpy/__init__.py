"""A Python-first package for astrophysical (magneto)hydrodynamics.

mhdpy is a framework for astrophysical (magneto)hydrodynamical simulations, meant for both educational and scientific
work: from standard verification problems up to production-scale runs. Its architecture, and the reasoning behind every
choice in it, is documented in ``docs/architecture.md`` and in the decision briefs under ``docs/decisions/``.

The package is in early development: its foundation layer (L0) is being built, starting with the unit system in
``mhdpy.foundation.units``.
"""

from importlib.metadata import version

## Imported under a name with an underscore, so that it does not appear as part of mhdpy's own interface (mhdpy.mode).
from mhdpy.foundation.kernels import mode as _kernel_mode

## Must run before any kernel is imported: selects compiled or uncompiled kernels (MHDPY_KERNELS, D04.3).
_kernel_mode.install()

__all__ = ["__version__"]

## The version is defined once, in pyproject.toml, and read back from the installed package metadata, so that the two
## can never disagree.
__version__: str = version("mhdpy")
