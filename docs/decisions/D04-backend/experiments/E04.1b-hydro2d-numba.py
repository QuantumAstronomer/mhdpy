"""Numba kernel of experiment E04.1: the same arithmetic as ``E04.1a-hydro2d-numpy.py``, written as explicit loops.

Compiled just in time by Numba for the host CPU. The outer loop over i runs in parallel (``prange``); the number of
threads is set with ``numba.set_num_threads``. ``fastmath`` is off, so floating-point semantics follow IEEE 754.
"""

import numpy as np
from numba import njit, prange

GAMMA = 1.4


@njit(inline="always")
def mc_slope(left, right):
    if left * right > 0.0:
        limited = min(min(2.0 * abs(left), 2.0 * abs(right)), 0.5 * abs(left + right))
        return limited if left > 0.0 else -limited
    return 0.0


@njit(inline="always")
def hll(rl, ul, vl, pl, rr, ur, vr, pr, out, k, a, b, swap):
    """Write the HLL flux of the given normal-frame states into out[:, a, b] (tangential flux in slot 2 or 1)."""
    cl = np.sqrt(GAMMA * pl / rl)
    cr = np.sqrt(GAMMA * pr / rr)
    sl = min(ul - cl, ur - cr)
    sr = max(ul + cl, ur + cr)
    el = pl / (GAMMA - 1.0) + 0.5 * rl * (ul * ul + vl * vl)
    er = pr / (GAMMA - 1.0) + 0.5 * rr * (ur * ur + vr * vr)
    fl0, fl1, fl2, fl3 = rl * ul, rl * ul * ul + pl, rl * ul * vl, (el + pl) * ul
    fr0, fr1, fr2, fr3 = rr * ur, rr * ur * ur + pr, rr * ur * vr, (er + pr) * ur
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


@njit(parallel=True)
def rhs_kernel(u, dx, g, w, fx, fy, du):
    m = u.shape[1]
    n = m - 2 * g
    for i in prange(m):
        for j in range(m):
            rho = u[0, i, j]
            vx = u[1, i, j] / rho
            vy = u[2, i, j] / rho
            w[0, i, j] = rho
            w[1, i, j] = vx
            w[2, i, j] = vy
            w[3, i, j] = (GAMMA - 1.0) * (u[3, i, j] - 0.5 * rho * (vx * vx + vy * vy))
    for f in prange(n + 1):
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
            hll(rl, ul, vl, pl, rr, ur, vr, pr, fx, 0, f, jj, False)
    for ii in prange(n):
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
            hll(rl, ul, vl, pl, rr, ur, vr, pr, fy, 0, ii, f, True)
    for ii in prange(n):
        for jj in range(n):
            for k in range(4):
                du[k, ii, jj] = -(fx[k, ii + 1, jj] - fx[k, ii, jj]) / dx - (fy[k, ii, jj + 1] - fy[k, ii, jj]) / dx


class Kernel:
    """Holds the scratch arrays for a grid size, so that the kernel itself allocates nothing."""

    def __init__(self, m: int, g: int) -> None:
        n = m - 2 * g
        self.g = g
        self.w = np.empty((4, m, m))
        self.fx = np.empty((4, n + 1, n))
        self.fy = np.empty((4, n, n + 1))
        self.du = np.empty((4, n, n))

    def __call__(self, u, dx):
        rhs_kernel(u, dx, self.g, self.w, self.fx, self.fy, self.du)
        return self.du
