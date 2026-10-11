"""Two-dimensional kernel of experiment E06.1: the D04 hydro kernel with five variables, struct-of-arrays layout.

The state is ``u[var, j, i]`` with variables (rho, m_x, m_y, m_z, E): x is the contiguous index i, as in Athena++, and
the z-momentum is carried along, as every 2D run of a 3D-capable code must (it is needed for 2.5D MHD). The arithmetic
is that of ``E04.3a-hydro2d-purepython.py``: primitive variables, MC-limited piecewise-linear reconstruction and HLL
fluxes, here with three velocity components. Array sizes are passed explicitly, so that ``E06.1c-layouts.py`` can derive
the array-of-structs variant ``u[j, i, var]`` from this file by permuting the indices of every array access.

Every loop runs with the contiguous index innermost.
"""

import cython
from cython.cimports.libc.math import sqrt

GAMMA = cython.declare(cython.double, 1.4)


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
    rl: cython.double, nl: cython.double, al: cython.double, bl: cython.double, pl: cython.double,
    rr: cython.double, nr: cython.double, ar: cython.double, br: cython.double, pr: cython.double,
    out: cython.double[:, :, ::1], j: cython.Py_ssize_t, i: cython.Py_ssize_t,
    n: cython.Py_ssize_t, a: cython.Py_ssize_t, b: cython.Py_ssize_t,
) -> cython.void:
    """HLL flux for normal velocity n and tangential velocities a, b; writes momentum fluxes to components n, a, b."""
    cl: cython.double = sqrt(GAMMA * pl / rl)
    cr: cython.double = sqrt(GAMMA * pr / rr)
    sl: cython.double = min(nl - cl, nr - cr)
    sr: cython.double = max(nl + cl, nr + cr)
    el: cython.double = pl / (GAMMA - 1.0) + 0.5 * rl * (nl * nl + al * al + bl * bl)
    er: cython.double = pr / (GAMMA - 1.0) + 0.5 * rr * (nr * nr + ar * ar + br * br)
    fl0: cython.double = rl * nl
    fl1: cython.double = rl * nl * nl + pl
    fl2: cython.double = rl * nl * al
    fl3: cython.double = rl * nl * bl
    fl4: cython.double = (el + pl) * nl
    fr0: cython.double = rr * nr
    fr1: cython.double = rr * nr * nr + pr
    fr2: cython.double = rr * nr * ar
    fr3: cython.double = rr * nr * br
    fr4: cython.double = (er + pr) * nr
    f0: cython.double
    f1: cython.double
    f2: cython.double
    f3: cython.double
    f4: cython.double
    if sl >= 0.0:
        f0, f1, f2, f3, f4 = fl0, fl1, fl2, fl3, fl4
    elif sr <= 0.0:
        f0, f1, f2, f3, f4 = fr0, fr1, fr2, fr3, fr4
    else:
        f0 = (sr * fl0 - sl * fr0 + sl * sr * (rr - rl)) / (sr - sl)
        f1 = (sr * fl1 - sl * fr1 + sl * sr * (rr * nr - rl * nl)) / (sr - sl)
        f2 = (sr * fl2 - sl * fr2 + sl * sr * (rr * ar - rl * al)) / (sr - sl)
        f3 = (sr * fl3 - sl * fr3 + sl * sr * (rr * br - rl * bl)) / (sr - sl)
        f4 = (sr * fl4 - sl * fr4 + sl * sr * (er - el)) / (sr - sl)
    out[0, j, i] = f0
    out[n, j, i] = f1
    out[a, j, i] = f2
    out[b, j, i] = f3
    out[4, j, i] = f4


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
    nx: cython.Py_ssize_t,
    ny: cython.Py_ssize_t,
    g: cython.Py_ssize_t,
    dx: cython.double,
) -> None:
    """Write -div F of the ny x nx interior cells of ``u`` (with g ghost cells in x and y) into ``du``."""
    i: cython.Py_ssize_t
    j: cython.Py_ssize_t
    v: cython.Py_ssize_t
    rho: cython.double
    vx: cython.double
    vy: cython.double
    vz: cython.double
    l0: cython.double
    l1: cython.double
    l2: cython.double
    l3: cython.double
    l4: cython.double
    r0: cython.double
    r1: cython.double
    r2: cython.double
    r3: cython.double
    r4: cython.double
    with cython.nogil:
        for j in range(ny + 2 * g):
            for i in range(nx + 2 * g):
                rho = u[0, j, i]
                vx = u[1, j, i] / rho
                vy = u[2, j, i] / rho
                vz = u[3, j, i] / rho
                w[0, j, i] = rho
                w[1, j, i] = vx
                w[2, j, i] = vy
                w[3, j, i] = vz
                w[4, j, i] = (GAMMA - 1.0) * (u[4, j, i] - 0.5 * rho * (vx * vx + vy * vy + vz * vz))
        ## x-faces: face f lies between cells f - 1 and f (array indices g + f - 1 and g + f).
        for j in range(g, g + ny):
            for i in range(g, g + nx + 1):
                l0 = w[0, j, i - 1] + 0.5 * mc_slope(w[0, j, i - 1] - w[0, j, i - 2], w[0, j, i] - w[0, j, i - 1])
                l1 = w[1, j, i - 1] + 0.5 * mc_slope(w[1, j, i - 1] - w[1, j, i - 2], w[1, j, i] - w[1, j, i - 1])
                l2 = w[2, j, i - 1] + 0.5 * mc_slope(w[2, j, i - 1] - w[2, j, i - 2], w[2, j, i] - w[2, j, i - 1])
                l3 = w[3, j, i - 1] + 0.5 * mc_slope(w[3, j, i - 1] - w[3, j, i - 2], w[3, j, i] - w[3, j, i - 1])
                l4 = w[4, j, i - 1] + 0.5 * mc_slope(w[4, j, i - 1] - w[4, j, i - 2], w[4, j, i] - w[4, j, i - 1])
                r0 = w[0, j, i] - 0.5 * mc_slope(w[0, j, i] - w[0, j, i - 1], w[0, j, i + 1] - w[0, j, i])
                r1 = w[1, j, i] - 0.5 * mc_slope(w[1, j, i] - w[1, j, i - 1], w[1, j, i + 1] - w[1, j, i])
                r2 = w[2, j, i] - 0.5 * mc_slope(w[2, j, i] - w[2, j, i - 1], w[2, j, i + 1] - w[2, j, i])
                r3 = w[3, j, i] - 0.5 * mc_slope(w[3, j, i] - w[3, j, i - 1], w[3, j, i + 1] - w[3, j, i])
                r4 = w[4, j, i] - 0.5 * mc_slope(w[4, j, i] - w[4, j, i - 1], w[4, j, i + 1] - w[4, j, i])
                hll(l0, l1, l2, l3, l4, r0, r1, r2, r3, r4, fx, j - g, i - g, 1, 2, 3)
        ## y-faces.
        for j in range(g, g + ny + 1):
            for i in range(g, g + nx):
                l0 = w[0, j - 1, i] + 0.5 * mc_slope(w[0, j - 1, i] - w[0, j - 2, i], w[0, j, i] - w[0, j - 1, i])
                l1 = w[1, j - 1, i] + 0.5 * mc_slope(w[1, j - 1, i] - w[1, j - 2, i], w[1, j, i] - w[1, j - 1, i])
                l2 = w[2, j - 1, i] + 0.5 * mc_slope(w[2, j - 1, i] - w[2, j - 2, i], w[2, j, i] - w[2, j - 1, i])
                l3 = w[3, j - 1, i] + 0.5 * mc_slope(w[3, j - 1, i] - w[3, j - 2, i], w[3, j, i] - w[3, j - 1, i])
                l4 = w[4, j - 1, i] + 0.5 * mc_slope(w[4, j - 1, i] - w[4, j - 2, i], w[4, j, i] - w[4, j - 1, i])
                r0 = w[0, j, i] - 0.5 * mc_slope(w[0, j, i] - w[0, j - 1, i], w[0, j + 1, i] - w[0, j, i])
                r1 = w[1, j, i] - 0.5 * mc_slope(w[1, j, i] - w[1, j - 1, i], w[1, j + 1, i] - w[1, j, i])
                r2 = w[2, j, i] - 0.5 * mc_slope(w[2, j, i] - w[2, j - 1, i], w[2, j + 1, i] - w[2, j, i])
                r3 = w[3, j, i] - 0.5 * mc_slope(w[3, j, i] - w[3, j - 1, i], w[3, j + 1, i] - w[3, j, i])
                r4 = w[4, j, i] - 0.5 * mc_slope(w[4, j, i] - w[4, j - 1, i], w[4, j + 1, i] - w[4, j, i])
                hll(l0, l2, l3, l1, l4, r0, r2, r3, r1, r4, fy, j - g, i - g, 2, 3, 1)
        for v in range(5):
            for j in range(ny):
                for i in range(nx):
                    du[v, j, i] = -(fx[v, j, i + 1] - fx[v, j, i]) / dx
        for v in range(5):
            for j in range(ny):
                for i in range(nx):
                    du[v, j, i] = du[v, j, i] - (fy[v, j + 1, i] - fy[v, j, i]) / dx
