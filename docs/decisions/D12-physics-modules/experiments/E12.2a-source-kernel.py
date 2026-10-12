# cython: freethreading_compatible=True
"""Kernel of experiment E12.2: a constant gravitational acceleration as a compiled source term over a range of blocks.

For blocks b0 .. b1 - 1 of the state's array ``[block, var, k, j, i]`` (variables rho, m_x, m_y, m_z, E), and g ghost
cells in x and y: E += dt g m_y, then m_y += dt g rho, on the interior cells. The same arithmetic as the NumPy forms of
``E12.2b-user-sources.py``, so that all forms give bit-for-bit the same result.
"""

import cython


@cython.boundscheck(False)
@cython.wraparound(False)
def gravity(pack: cython.double[:, :, :, :, ::1], b0: cython.Py_ssize_t, b1: cython.Py_ssize_t, g: cython.Py_ssize_t,
            dtg: cython.double) -> None:
    b: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    with cython.nogil:
        for b in range(b0, b1):
            for j in range(g, pack.shape[3] - g):
                for i in range(g, pack.shape[4] - g):
                    pack[b, 4, 0, j, i] = pack[b, 4, 0, j, i] + dtg * pack[b, 2, 0, j, i]
                    pack[b, 2, 0, j, i] = pack[b, 2, 0, j, i] + dtg * pack[b, 0, 0, j, i]
