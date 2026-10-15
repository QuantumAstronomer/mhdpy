"""Layer L0 of mhdpy, the foundation: the services every other layer builds on.

The foundation is the bottom layer of mhdpy's layered architecture (``docs/architecture.md`` §3). It holds what every
higher layer needs and what depends on nothing above it: the unit system with its notation and the physical constants,
the parameters, and, as they are built, the compute kernels in compiled and uncompiled form, the worker threads and
reductions, and logging. Nothing in this layer knows about meshes, physics modules or simulations.

Each component of the layer is a package of its own, such as ``units`` and ``parameters``, with its tests in a package
``tests/`` next to its modules (D01.4). Every package and module describes its purpose in its docstring. The layer's
``README.md`` collects these docstrings in one place, a section per component; it is generated from them with ``uv run
nox -s readmes``, and ``uv run nox`` checks that the two agree.
"""
