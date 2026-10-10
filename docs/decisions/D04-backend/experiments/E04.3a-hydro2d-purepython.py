"""Cython pure-Python-mode kernel of experiment E04.3: E04.1d-hydro2d-cython.pyx rewritten as an ordinary Python file.

The types are given as annotations and decorators from the ``cython`` module, so the same file can be compiled by Cython
(fast) or imported and run by the Python interpreter (slow, but visible to coverage.py, ruff and pyright). Built-in
``min``, ``max`` and ``abs`` replace ``fmin``, ``fmax`` and ``fabs``: Cython compiles them to C comparisons for typed
doubles, while ``libc.math`` maps to Python's ``math`` module when the file runs uncompiled, which lacks ``fmin``.
"""

import cython
from cython.cimports.libc.math import sqrt
from cython.parallel import prange

GAMMA = cython.declare(cython.double, 1.4)
NUM_THREADS = cython.declare(cython.int, 1)


def set_threads(n: cython.int) -> None:
    """Set the number of threads of the parallel loops (ignored when uncompiled or compiled without OpenMP)."""
    global NUM_THREADS
    NUM_THREADS = n


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
def mc_slope(left: cython.double, right: cython.double) -> cython.double:
    limited: cython.double
    if left * right > 0.0:
        limited = min(min(2.0 * abs(left), 2.0 * abs(right)), 0.5 * abs(left + right))
        return limited if left > 0.0 else -limited
    return 0.0


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def hll(
    rl: cython.double, ul: cython.double, vl: cython.double, pl: cython.double,
    rr: cython.double, ur: cython.double, vr: cython.double, pr: cython.double,
    out: cython.double[:, :, ::1], a: cython.Py_ssize_t, b: cython.Py_ssize_t, swap: cython.bint,
) -> cython.void:
    cl: cython.double = sqrt(GAMMA * pl / rl)
    cr: cython.double = sqrt(GAMMA * pr / rr)
    sl: cython.double = min(ul - cl, ur - cr)
    sr: cython.double = max(ul + cl, ur + cr)
    el: cython.double = pl / (GAMMA - 1.0) + 0.5 * rl * (ul * ul + vl * vl)
    er: cython.double = pr / (GAMMA - 1.0) + 0.5 * rr * (ur * ur + vr * vr)
    fl0: cython.double = rl * ul
    fl1: cython.double = rl * ul * ul + pl
    fl2: cython.double = rl * ul * vl
    fl3: cython.double = (el + pl) * ul
    fr0: cython.double = rr * ur
    fr1: cython.double = rr * ur * ur + pr
    fr2: cython.double = rr * ur * vr
    fr3: cython.double = (er + pr) * ur
    f0: cython.double
    f1: cython.double
    f2: cython.double
    f3: cython.double
    if sl >= 0.0:
        f0, f1, f2, f3 = fl0, fl1, fl2, fl3
    elif sr <= 0.0:
        f0, f1, f2, f3 = fr0, fr1, fr2, fr3
    else:
        f0 = (sr * fl0 - sl * fr0 + sl * sr * (rr - rl)) / (sr - sl)
        f1 = (sr * fl1 - sl * fr1 + sl * sr * (rr * ur - rl * ul)) / (sr - sl)
        f2 = (sr * fl2 - sl * fr2 + sl * sr * (rr * vr - rl * vl)) / (sr - sl)
        f3 = (sr * fl3 - sl * fr3 + sl * sr * (er - el)) / (sr - sl)
    out[0, a, b] = f0
    if swap:
        out[1, a, b] = f2
        out[2, a, b] = f1
    else:
        out[1, a, b] = f1
        out[2, a, b] = f2
    out[3, a, b] = f3


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
@cython.initializedcheck(False)
def rhs(
    u: cython.double[:, :, ::1],
    w: cython.double[:, :, ::1],
    fx: cython.double[:, :, ::1],
    fy: cython.double[:, :, ::1],
    du: cython.double[:, :, ::1],
    g: cython.int,
    dx: cython.double,
) -> None:
    m: cython.Py_ssize_t = u.shape[1]
    n: cython.Py_ssize_t = m - 2 * g
    i: cython.Py_ssize_t
    j: cython.Py_ssize_t
    f: cython.Py_ssize_t
    ii: cython.Py_ssize_t
    jj: cython.Py_ssize_t
    k: cython.Py_ssize_t
    rho: cython.double
    vx: cython.double
    vy: cython.double
    rl: cython.double
    ul: cython.double
    vl: cython.double
    pl: cython.double
    rr: cython.double
    ur: cython.double
    vr: cython.double
    pr: cython.double
    for i in prange(m, nogil=True, schedule="static", num_threads=NUM_THREADS):
        for j in range(m):
            rho = u[0, i, j]
            vx = u[1, i, j] / rho
            vy = u[2, i, j] / rho
            w[0, i, j] = rho
            w[1, i, j] = vx
            w[2, i, j] = vy
            w[3, i, j] = (GAMMA - 1.0) * (u[3, i, j] - 0.5 * rho * (vx * vx + vy * vy))
    for f in prange(n + 1, nogil=True, schedule="static", num_threads=NUM_THREADS):
        i = g + f
        for jj in range(n):
            j = g + jj
            rl = w[0, i - 1, j] + 0.5 * mc_slope(w[0, i - 1, j] - w[0, i - 2, j], w[0, i, j] - w[0, i - 1, j])
            ul = w[1, i - 1, j] + 0.5 * mc_slope(w[1, i - 1, j] - w[1, i - 2, j], w[1, i, j] - w[1, i - 1, j])
            vl = w[2, i - 1, j] + 0.5 * mc_slope(w[2, i - 1, j] - w[2, i - 2, j], w[2, i, j] - w[2, i - 1, j])
            pl = w[3, i - 1, j] + 0.5 * mc_slope(w[3, i - 1, j] - w[3, i - 2, j], w[3, i, j] - w[3, i - 1, j])
            rr = w[0, i, j] - 0.5 * mc_slope(w[0, i, j] - w[0, i - 1, j], w[0, i + 1, j] - w[0, i, j])
            ur = w[1, i, j] - 0.5 * mc_slope(w[1, i, j] - w[1, i - 1, j], w[1, i + 1, j] - w[1, i, j])
            vr = w[2, i, j] - 0.5 * mc_slope(w[2, i, j] - w[2, i - 1, j], w[2, i + 1, j] - w[2, i, j])
            pr = w[3, i, j] - 0.5 * mc_slope(w[3, i, j] - w[3, i - 1, j], w[3, i + 1, j] - w[3, i, j])
            hll(rl, ul, vl, pl, rr, ur, vr, pr, fx, f, jj, False)
    for ii in prange(n, nogil=True, schedule="static", num_threads=NUM_THREADS):
        i = g + ii
        for f in range(n + 1):
            j = g + f
            rl = w[0, i, j - 1] + 0.5 * mc_slope(w[0, i, j - 1] - w[0, i, j - 2], w[0, i, j] - w[0, i, j - 1])
            ul = w[2, i, j - 1] + 0.5 * mc_slope(w[2, i, j - 1] - w[2, i, j - 2], w[2, i, j] - w[2, i, j - 1])
            vl = w[1, i, j - 1] + 0.5 * mc_slope(w[1, i, j - 1] - w[1, i, j - 2], w[1, i, j] - w[1, i, j - 1])
            pl = w[3, i, j - 1] + 0.5 * mc_slope(w[3, i, j - 1] - w[3, i, j - 2], w[3, i, j] - w[3, i, j - 1])
            rr = w[0, i, j] - 0.5 * mc_slope(w[0, i, j] - w[0, i, j - 1], w[0, i, j + 1] - w[0, i, j])
            ur = w[2, i, j] - 0.5 * mc_slope(w[2, i, j] - w[2, i, j - 1], w[2, i, j + 1] - w[2, i, j])
            vr = w[1, i, j] - 0.5 * mc_slope(w[1, i, j] - w[1, i, j - 1], w[1, i, j + 1] - w[1, i, j])
            pr = w[3, i, j] - 0.5 * mc_slope(w[3, i, j] - w[3, i, j - 1], w[3, i, j + 1] - w[3, i, j])
            hll(rl, ul, vl, pl, rr, ur, vr, pr, fy, ii, f, True)
    for ii in prange(n, nogil=True, schedule="static", num_threads=NUM_THREADS):
        for jj in range(n):
            for k in range(4):
                du[k, ii, jj] = -(fx[k, ii + 1, jj] - fx[k, ii, jj]) / dx - (fy[k, ii, jj + 1] - fy[k, ii, jj]) / dx
