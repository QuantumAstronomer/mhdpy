"""mhdpy, a finite-volume code for magnetohydrodynamics in five strata.

mhdpy simulates astrophysical gases, in hydrodynamics and MHD, and serves educational and scientific work, from
standard verification problems to production-scale runs of the size used in published studies. Its code is cut into
five strata by the kind of code that each holds, each a subpackage that imports only the strata below it, so that each
can be read and tested with those below it alone.

The top package imports no stratum, as Python runs it before any of them, and gives the version of mhdpy, which
setuptools-scm derives from git when mhdpy is built.

Contents
========================================================================================================================
__version__
    The version in the metadata of the installation.
infrastructure
    The infrastructure, stratum 1.
mesh
    The mesh and its data, stratum 2.
core
    The numerical core, stratum 3.
physics
    The physics, stratum 4.
driver
    The driver and the problems, stratum 5.

Its requirements are in design/requirements/infrastructure/package.md, and docs/package.md explains it.
"""

import importlib.metadata


## the version in the metadata of the installation (PACK12)
__version__ = importlib.metadata.version("mhdpy")
