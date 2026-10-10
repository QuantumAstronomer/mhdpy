# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True, initializedcheck=False
"""Cython kernel of experiment E04.1: the same arithmetic as E04.1a-hydro2d-numpy.py, as explicit typed loops.

Compiled ahead of time to C by the experiment (with OpenMP where the compiler supports it); prange releases the GIL and
runs the outer loops in parallel. Bounds checking and negative indexing are switched off, as in production Cython.
"""

from cython.parallel cimport prange
from libc.math cimport sqrt, fabs, fmin, fmax

cdef double GAMMA = 1.4
cdef int NUM_THREADS = 1


def set_threads(int n):
    """Set the number of threads of the parallel loops (ignored when compiled without OpenMP)."""
    global NUM_THREADS
    NUM_THREADS = n


cdef inline double mc_slope(double left, double right) noexcept nogil:
    cdef double limited
    if left * right > 0.0:
        limited = fmin(fmin(2.0 * fabs(left), 2.0 * fabs(right)), 0.5 * fabs(left + right))
        return limited if left > 0.0 else -limited
    return 0.0


cdef inline void hll(double rl, double ul, double vl, double pl, double rr, double ur, double vr, double pr,
                     double[:, :, ::1] out, Py_ssize_t a, Py_ssize_t b, bint swap) noexcept nogil:
    cdef double cl = sqrt(GAMMA * pl / rl)
    cdef double cr = sqrt(GAMMA * pr / rr)
    cdef double sl = fmin(ul - cl, ur - cr)
    cdef double sr = fmax(ul + cl, ur + cr)
    cdef double el = pl / (GAMMA - 1.0) + 0.5 * rl * (ul * ul + vl * vl)
    cdef double er = pr / (GAMMA - 1.0) + 0.5 * rr * (ur * ur + vr * vr)
    cdef double fl0 = rl * ul, fl1 = rl * ul * ul + pl, fl2 = rl * ul * vl, fl3 = (el + pl) * ul
    cdef double fr0 = rr * ur, fr1 = rr * ur * ur + pr, fr2 = rr * ur * vr, fr3 = (er + pr) * ur
    cdef double f0, f1, f2, f3
    if sl >= 0.0:
        f0 = fl0; f1 = fl1; f2 = fl2; f3 = fl3
    elif sr <= 0.0:
        f0 = fr0; f1 = fr1; f2 = fr2; f3 = fr3
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


def rhs(const double[:, :, ::1] u, double[:, :, ::1] w, double[:, :, ::1] fx, double[:, :, ::1] fy,
        double[:, :, ::1] du, int g, double dx):
    cdef Py_ssize_t m = u.shape[1]
    cdef Py_ssize_t n = m - 2 * g
    cdef Py_ssize_t i, j, f, ii, jj, k
    cdef double rho, vx, vy
    cdef double rl, ul, vl, pl, rr, ur, vr, pr
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
