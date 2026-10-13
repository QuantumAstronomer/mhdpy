# cython: freethreading_compatible=True
"""Facts about mhdpy's compute backend that the rest of the package needs to know at run time."""

import cython


def compiled() -> bool:
    """Return whether this module, and with it every kernel of mhdpy, runs compiled.

    Kernels are written in Cython's pure Python mode (D04.1). The same source runs compiled, as built by meson, or as
    plain Python, for coverage measurements (D04.3).
    """
    return bool(cython.compiled)
