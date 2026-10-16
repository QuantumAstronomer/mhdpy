# cython: freethreading_compatible=True
"""The first kernel of mhdpy: facts about the compute backend that the rest of the package needs at run time.

This module is compiled by meson like every kernel (D04.1), and it is the simplest one possible: a function that reports
whether it runs compiled. Since all kernels run in the same mode (``mode.py``), that tells the rest of mhdpy, and the
tests, how every kernel runs. It is also the proof that the build compiles kernels at all: a wheel whose kernels failed
to compile would report False here, and its tests would fail.

The type checker reads the stub ``backend.pyi`` next to this file, because it cannot interpret Cython's types in a
kernel's source.
"""

import cython


def compiled() -> bool:
    """Return whether this module, and with it every kernel of mhdpy, runs compiled.

    Kernels are written in Cython's pure Python mode (D04.1). The same source runs compiled, as built by meson, or as
    plain Python, for coverage measurements (D04.3).
    """
    return bool(cython.compiled)
