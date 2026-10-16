"""The kernels of mhdpy, compiled or uncompiled: the switch between the two, and the first kernel (decision D04).

A kernel is a function that does the numerical work on the arrays of a block: a reconstruction, a Riemann solver, an
update. Kernels are written once, as ``.py`` files in Cython's pure Python mode, and run in two ways (D04.1, D04.3).
Compiled, by meson into extension modules, they run at the speed a production run needs; uncompiled, as plain Python,
they can be measured for coverage and stepped through in a debugger. The tests check that both ways give bit-for-bit
identical results. The kernels themselves belong to the layers that use them; this package holds what every kernel
relies on:

- ``mode.py``, the switch: the environment variable ``MHDPY_KERNELS`` selects compiled kernels (the default) or
  uncompiled ones, for the whole package, when mhdpy is imported.
- ``backend.py``, the first and simplest kernel: it reports whether the kernels run compiled, and in doing so shows
  that the build compiles kernels at all.

Like every component, this package imports none of its modules itself; ``mhdpy/__init__.py`` imports the switch, before
any kernel is imported. The tests are in the test package ``tests/`` next to the modules.
"""
