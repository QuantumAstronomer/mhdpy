"""Layer L0 of mhdpy, the foundation: the services every other layer builds on.

The foundation is the bottom layer of mhdpy's layered architecture (``docs/architecture.md`` §3). It holds what every
higher layer needs and what depends on nothing above it: the unit system and the physical constants, and, as they are
built, the compute kernels in compiled and uncompiled form, the worker threads and reductions, the declared parameters
and logging. Nothing in this layer knows about meshes, physics modules or simulations.

Each module of the layer describes its purpose in its docstring. The layer's ``README.md`` collects these docstrings in
one place; it is generated from them with ``uv run nox -s readmes``, and ``uv run nox`` checks that the two agree.
"""
