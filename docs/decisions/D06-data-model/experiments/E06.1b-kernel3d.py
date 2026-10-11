"""Three-dimensional kernel of experiment E06.1: one kernel for 1D, 2D and 3D, on ``u[var, k, j, i]``.

The same arithmetic as ``E06.1a-kernel2d.py``, written once for three dimensions in the layout of Athena++: struct of
arrays, x contiguous (index i), then y (j), then z (k). Lower-dimensional problems use the same kernel with extent 1 and
no ghost cells in the unused directions; a direction is active when its extent is larger than 1, and fluxes are only
computed in active directions. Tangential velocity components are taken cyclically (x: y, z; y: z, x; z: x, y).

Every loop runs with i innermost.
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


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.initializedcheck(False)
def face_fluxes(
    w: cython.double[:, :, :, ::1], f: cython.double[:, :, :, ::1],
    k0: cython.Py_ssize_t, k1: cython.Py_ssize_t, j0: cython.Py_ssize_t, j1: cython.Py_ssize_t,
    i0: cython.Py_ssize_t, i1: cython.Py_ssize_t, dk: cython.Py_ssize_t, dj: cython.Py_ssize_t, di: cython.Py_ssize_t,
    n: cython.Py_ssize_t, a: cython.Py_ssize_t, b: cython.Py_ssize_t,
) -> cython.void:
    """Fluxes through the faces k0 <= k < k1, ... between cell (k - dk, j - dj, i - di) and cell (k, j, i)."""
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    v: cython.Py_ssize_t
    lv: cython.double[5]
    rv: cython.double[5]
    for k in range(k0, k1):
        for j in range(j0, j1):
            for i in range(i0, i1):
                for v in range(5):
                    lv[v] = w[v, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                        w[v, k - dk, j - dj, i - di] - w[v, k - 2 * dk, j - 2 * dj, i - 2 * di],
                        w[v, k, j, i] - w[v, k - dk, j - dj, i - di])
                    rv[v] = w[v, k, j, i] - 0.5 * mc_slope(
                        w[v, k, j, i] - w[v, k - dk, j - dj, i - di], w[v, k + dk, j + dj, i + di] - w[v, k, j, i])
                hll(lv[0], lv[n], lv[a], lv[b], lv[4], rv[0], rv[n], rv[a], rv[b], rv[4], f,
                    k - k0, j - j0, i - i0, n, a, b)


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
            face_fluxes(w, fx, gz, gz + nz, gy, gy + ny, gx, gx + nx + 1, 0, 0, 1, 1, 2, 3)
            for v in range(5):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = -(fx[v, k, j, i + 1] - fx[v, k, j, i]) / dx
        if ny > 1:
            face_fluxes(w, fy, gz, gz + nz, gy, gy + ny + 1, gx, gx + nx, 0, 1, 0, 2, 3, 1)
            for v in range(5):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (fy[v, k, j + 1, i] - fy[v, k, j, i]) / dx
        if nz > 1:
            face_fluxes(w, fz, gz, gz + nz + 1, gy, gy + ny, gx, gx + nx, 1, 0, 0, 3, 1, 2)
            for v in range(5):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (fz[v, k + 1, j, i] - fz[v, k, j, i]) / dx
