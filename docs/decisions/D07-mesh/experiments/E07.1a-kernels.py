# cython: freethreading_compatible=True
"""Kernels of experiments E07.1 and E07.2: the direction-specific hydro kernel of D06, plus the stage combinations.

The time derivative ``rhs`` is ``E06.1d-kernel3d-specialised.py`` unchanged: five variables in the layout decided in
D06 (``u[var, k, j, i]``, x contiguous, always three-dimensional, directions with extent 1 have no ghost cells), every
direction written out. ``first_stage`` and ``second_stage`` are the SSP-RK2 stage combinations of E04.5 for this layout.
Every kernel releases the GIL, and the first line declares the module safe for free-threaded Python (D05).
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
    out: cython.double[:, :, :, ::1], k: cython.Py_ssize_t, j: cython.Py_ssize_t, i: cython.Py_ssize_t,
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
    out[0, k, j, i] = f0
    out[n, k, j, i] = f1
    out[a, k, j, i] = f2
    out[b, k, j, i] = f3
    out[4, k, j, i] = f4


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
@cython.initializedcheck(False)
def rhs(
    u: cython.double[:, :, :, ::1],
    w: cython.double[:, :, :, ::1],
    fx: cython.double[:, :, :, ::1],
    fy: cython.double[:, :, :, ::1],
    fz: cython.double[:, :, :, ::1],
    du: cython.double[:, :, :, ::1],
    nx: cython.Py_ssize_t,
    ny: cython.Py_ssize_t,
    nz: cython.Py_ssize_t,
    g: cython.Py_ssize_t,
    dx: cython.double,
) -> None:
    """Write -div F of the interior cells into ``du``; directions with extent 1 have no ghost cells and no fluxes."""
    gx: cython.Py_ssize_t = g if nx > 1 else 0
    gy: cython.Py_ssize_t = g if ny > 1 else 0
    gz: cython.Py_ssize_t = g if nz > 1 else 0
    i: cython.Py_ssize_t
    j: cython.Py_ssize_t
    k: cython.Py_ssize_t
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
        for k in range(nz + 2 * gz):
            for j in range(ny + 2 * gy):
                for i in range(nx + 2 * gx):
                    rho = u[0, k, j, i]
                    vx = u[1, k, j, i] / rho
                    vy = u[2, k, j, i] / rho
                    vz = u[3, k, j, i] / rho
                    w[0, k, j, i] = rho
                    w[1, k, j, i] = vx
                    w[2, k, j, i] = vy
                    w[3, k, j, i] = vz
                    w[4, k, j, i] = (GAMMA - 1.0) * (u[4, k, j, i] - 0.5 * rho * (vx * vx + vy * vy + vz * vz))
        for v in range(5):
            for k in range(nz):
                for j in range(ny):
                    for i in range(nx):
                        du[v, k, j, i] = 0.0
        if nx > 1:
            for k in range(gz, gz + nz):
                for j in range(gy, gy + ny):
                    for i in range(gx, gx + nx + 1):
                        l0 = w[0, k, j, i - 1] + 0.5 * mc_slope(w[0, k, j, i - 1] - w[0, k, j, i - 2], w[0, k, j, i] - w[0, k, j, i - 1])
                        l1 = w[1, k, j, i - 1] + 0.5 * mc_slope(w[1, k, j, i - 1] - w[1, k, j, i - 2], w[1, k, j, i] - w[1, k, j, i - 1])
                        l2 = w[2, k, j, i - 1] + 0.5 * mc_slope(w[2, k, j, i - 1] - w[2, k, j, i - 2], w[2, k, j, i] - w[2, k, j, i - 1])
                        l3 = w[3, k, j, i - 1] + 0.5 * mc_slope(w[3, k, j, i - 1] - w[3, k, j, i - 2], w[3, k, j, i] - w[3, k, j, i - 1])
                        l4 = w[4, k, j, i - 1] + 0.5 * mc_slope(w[4, k, j, i - 1] - w[4, k, j, i - 2], w[4, k, j, i] - w[4, k, j, i - 1])
                        r0 = w[0, k, j, i] - 0.5 * mc_slope(w[0, k, j, i] - w[0, k, j, i - 1], w[0, k, j, i + 1] - w[0, k, j, i])
                        r1 = w[1, k, j, i] - 0.5 * mc_slope(w[1, k, j, i] - w[1, k, j, i - 1], w[1, k, j, i + 1] - w[1, k, j, i])
                        r2 = w[2, k, j, i] - 0.5 * mc_slope(w[2, k, j, i] - w[2, k, j, i - 1], w[2, k, j, i + 1] - w[2, k, j, i])
                        r3 = w[3, k, j, i] - 0.5 * mc_slope(w[3, k, j, i] - w[3, k, j, i - 1], w[3, k, j, i + 1] - w[3, k, j, i])
                        r4 = w[4, k, j, i] - 0.5 * mc_slope(w[4, k, j, i] - w[4, k, j, i - 1], w[4, k, j, i + 1] - w[4, k, j, i])
                        hll(l0, l1, l2, l3, l4, r0, r1, r2, r3, r4, fx, k - gz, j - gy, i - gx, 1, 2, 3)
            for v in range(5):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = -(fx[v, k, j, i + 1] - fx[v, k, j, i]) / dx
        if ny > 1:
            for k in range(gz, gz + nz):
                for j in range(gy, gy + ny + 1):
                    for i in range(gx, gx + nx):
                        l0 = w[0, k, j - 1, i] + 0.5 * mc_slope(w[0, k, j - 1, i] - w[0, k, j - 2, i], w[0, k, j, i] - w[0, k, j - 1, i])
                        l1 = w[1, k, j - 1, i] + 0.5 * mc_slope(w[1, k, j - 1, i] - w[1, k, j - 2, i], w[1, k, j, i] - w[1, k, j - 1, i])
                        l2 = w[2, k, j - 1, i] + 0.5 * mc_slope(w[2, k, j - 1, i] - w[2, k, j - 2, i], w[2, k, j, i] - w[2, k, j - 1, i])
                        l3 = w[3, k, j - 1, i] + 0.5 * mc_slope(w[3, k, j - 1, i] - w[3, k, j - 2, i], w[3, k, j, i] - w[3, k, j - 1, i])
                        l4 = w[4, k, j - 1, i] + 0.5 * mc_slope(w[4, k, j - 1, i] - w[4, k, j - 2, i], w[4, k, j, i] - w[4, k, j - 1, i])
                        r0 = w[0, k, j, i] - 0.5 * mc_slope(w[0, k, j, i] - w[0, k, j - 1, i], w[0, k, j + 1, i] - w[0, k, j, i])
                        r1 = w[1, k, j, i] - 0.5 * mc_slope(w[1, k, j, i] - w[1, k, j - 1, i], w[1, k, j + 1, i] - w[1, k, j, i])
                        r2 = w[2, k, j, i] - 0.5 * mc_slope(w[2, k, j, i] - w[2, k, j - 1, i], w[2, k, j + 1, i] - w[2, k, j, i])
                        r3 = w[3, k, j, i] - 0.5 * mc_slope(w[3, k, j, i] - w[3, k, j - 1, i], w[3, k, j + 1, i] - w[3, k, j, i])
                        r4 = w[4, k, j, i] - 0.5 * mc_slope(w[4, k, j, i] - w[4, k, j - 1, i], w[4, k, j + 1, i] - w[4, k, j, i])
                        hll(l0, l2, l3, l1, l4, r0, r2, r3, r1, r4, fy, k - gz, j - gy, i - gx, 2, 3, 1)
            for v in range(5):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (fy[v, k, j + 1, i] - fy[v, k, j, i]) / dx
        if nz > 1:
            for k in range(gz, gz + nz + 1):
                for j in range(gy, gy + ny):
                    for i in range(gx, gx + nx):
                        l0 = w[0, k - 1, j, i] + 0.5 * mc_slope(w[0, k - 1, j, i] - w[0, k - 2, j, i], w[0, k, j, i] - w[0, k - 1, j, i])
                        l1 = w[1, k - 1, j, i] + 0.5 * mc_slope(w[1, k - 1, j, i] - w[1, k - 2, j, i], w[1, k, j, i] - w[1, k - 1, j, i])
                        l2 = w[2, k - 1, j, i] + 0.5 * mc_slope(w[2, k - 1, j, i] - w[2, k - 2, j, i], w[2, k, j, i] - w[2, k - 1, j, i])
                        l3 = w[3, k - 1, j, i] + 0.5 * mc_slope(w[3, k - 1, j, i] - w[3, k - 2, j, i], w[3, k, j, i] - w[3, k - 1, j, i])
                        l4 = w[4, k - 1, j, i] + 0.5 * mc_slope(w[4, k - 1, j, i] - w[4, k - 2, j, i], w[4, k, j, i] - w[4, k - 1, j, i])
                        r0 = w[0, k, j, i] - 0.5 * mc_slope(w[0, k, j, i] - w[0, k - 1, j, i], w[0, k + 1, j, i] - w[0, k, j, i])
                        r1 = w[1, k, j, i] - 0.5 * mc_slope(w[1, k, j, i] - w[1, k - 1, j, i], w[1, k + 1, j, i] - w[1, k, j, i])
                        r2 = w[2, k, j, i] - 0.5 * mc_slope(w[2, k, j, i] - w[2, k - 1, j, i], w[2, k + 1, j, i] - w[2, k, j, i])
                        r3 = w[3, k, j, i] - 0.5 * mc_slope(w[3, k, j, i] - w[3, k - 1, j, i], w[3, k + 1, j, i] - w[3, k, j, i])
                        r4 = w[4, k, j, i] - 0.5 * mc_slope(w[4, k, j, i] - w[4, k - 1, j, i], w[4, k + 1, j, i] - w[4, k, j, i])
                        hll(l0, l3, l1, l2, l4, r0, r3, r1, r2, r4, fz, k - gz, j - gy, i - gx, 3, 1, 2)
            for v in range(5):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (fz[v, k + 1, j, i] - fz[v, k, j, i]) / dx


@cython.boundscheck(False)
@cython.wraparound(False)
def first_stage(
    u: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1], dt: cython.double,
    out: cython.double[:, :, :, ::1], gz: cython.Py_ssize_t, gy: cython.Py_ssize_t, gx: cython.Py_ssize_t,
) -> None:
    """out = u + dt du on the interior cells."""
    v: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    with cython.nogil:
        for v in range(du.shape[0]):
            for k in range(du.shape[1]):
                for j in range(du.shape[2]):
                    for i in range(du.shape[3]):
                        out[v, k + gz, j + gy, i + gx] = u[v, k + gz, j + gy, i + gx] + dt * du[v, k, j, i]


@cython.boundscheck(False)
@cython.wraparound(False)
def second_stage(
    u: cython.double[:, :, :, ::1], stage: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1],
    dt: cython.double, out: cython.double[:, :, :, ::1], gz: cython.Py_ssize_t, gy: cython.Py_ssize_t,
    gx: cython.Py_ssize_t,
) -> None:
    """out = u / 2 + (stage + dt du) / 2 on the interior cells."""
    v: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    with cython.nogil:
        for v in range(du.shape[0]):
            for k in range(du.shape[1]):
                for j in range(du.shape[2]):
                    for i in range(du.shape[3]):
                        out[v, k + gz, j + gy, i + gx] = (0.5 * u[v, k + gz, j + gy, i + gx]
                                                          + 0.5 * (stage[v, k + gz, j + gy, i + gx] + dt * du[v, k, j, i]))
