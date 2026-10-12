# cython: freethreading_compatible=True
"""Kernels of experiments E10.1 and E10.2: the D09 kernels (``E09.1a-kernels.py``, unchanged), plus stand-ins for
alternative components.

``mc_alt`` and ``hll_alt`` are exact copies of ``mc_slope`` and ``hll`` under other names. They stand in for a second
limiter and a second Riemann solver, so that run-time selection between two components can be timed while every
variant computes bit-for-bit the same result. ``E10.1c-dispatch.py`` derives the selecting variants of ``rhs_block``
from this file; ``E10.1b-kernels.pxd`` declares the function-pointer types they use (Cython's pure Python mode takes
such C-level declarations from a ``.pxd`` file next to the module).
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
@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def rhs_block(
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
) -> cython.void:
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
@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def first_stage_block(
    u: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1], dt: cython.double,
    out: cython.double[:, :, :, ::1], gz: cython.Py_ssize_t, gy: cython.Py_ssize_t, gx: cython.Py_ssize_t,
) -> cython.void:
    """out = u + dt du on the interior cells."""
    v: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    for v in range(du.shape[0]):
        for k in range(du.shape[1]):
            for j in range(du.shape[2]):
                for i in range(du.shape[3]):
                    out[v, k + gz, j + gy, i + gx] = u[v, k + gz, j + gy, i + gx] + dt * du[v, k, j, i]


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def second_stage_block(
    u: cython.double[:, :, :, ::1], stage: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1],
    dt: cython.double, out: cython.double[:, :, :, ::1], gz: cython.Py_ssize_t, gy: cython.Py_ssize_t,
    gx: cython.Py_ssize_t,
) -> cython.void:
    """out = u / 2 + (stage + dt du) / 2 on the interior cells."""
    v: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    for v in range(du.shape[0]):
        for k in range(du.shape[1]):
            for j in range(du.shape[2]):
                for i in range(du.shape[3]):
                    out[v, k + gz, j + gy, i + gx] = (0.5 * u[v, k + gz, j + gy, i + gx]
                                                      + 0.5 * (stage[v, k + gz, j + gy, i + gx] + dt * du[v, k, j, i]))


@cython.boundscheck(False)
@cython.wraparound(False)
def copy_regions(pack: cython.double[:, :, :, :, ::1], plan: cython.Py_ssize_t[:, ::1], row0: cython.Py_ssize_t,
                 row1: cython.Py_ssize_t) -> None:
    """Copy the regions of plan rows row0 .. row1 - 1; a row is (dst, src, dk, dj, di, sk, sj, si, nk, nj, ni)."""
    r: cython.Py_ssize_t
    v: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    dst: cython.Py_ssize_t
    src: cython.Py_ssize_t
    with cython.nogil:
        for r in range(row0, row1):
            dst = plan[r, 0]
            src = plan[r, 1]
            for v in range(pack.shape[1]):
                for k in range(plan[r, 8]):
                    for j in range(plan[r, 9]):
                        for i in range(plan[r, 10]):
                            pack[dst, v, plan[r, 2] + k, plan[r, 3] + j, plan[r, 4] + i] = pack[
                                src, v, plan[r, 5] + k, plan[r, 6] + j, plan[r, 7] + i]


@cython.boundscheck(False)
@cython.wraparound(False)
def rhs(
    u: cython.double[:, :, :, ::1], w: cython.double[:, :, :, ::1], fx: cython.double[:, :, :, ::1],
    fy: cython.double[:, :, :, ::1], fz: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1],
    nx: cython.Py_ssize_t, ny: cython.Py_ssize_t, nz: cython.Py_ssize_t, g: cython.Py_ssize_t, dx: cython.double,
) -> None:
    with cython.nogil:
        rhs_block(u, w, fx, fy, fz, du, nx, ny, nz, g, dx)


@cython.boundscheck(False)
@cython.wraparound(False)
def first_stage(
    u: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1], dt: cython.double,
    out: cython.double[:, :, :, ::1], gz: cython.Py_ssize_t, gy: cython.Py_ssize_t, gx: cython.Py_ssize_t,
) -> None:
    with cython.nogil:
        first_stage_block(u, du, dt, out, gz, gy, gx)


@cython.boundscheck(False)
@cython.wraparound(False)
def second_stage(
    u: cython.double[:, :, :, ::1], stage: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1],
    dt: cython.double, out: cython.double[:, :, :, ::1], gz: cython.Py_ssize_t, gy: cython.Py_ssize_t,
    gx: cython.Py_ssize_t,
) -> None:
    with cython.nogil:
        second_stage_block(u, stage, du, dt, out, gz, gy, gx)


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
@cython.boundscheck(False)
@cython.wraparound(False)
def busy_block(u: cython.double[:, :, :, ::1], scratch: cython.double[:, :, ::1], repeats: cython.Py_ssize_t) -> cython.void:
    """Extra work on a block's energy without changing the state: ``repeats`` dependent square roots per cell."""
    r: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    acc: cython.double
    for k in range(scratch.shape[0]):
        for j in range(scratch.shape[1]):
            for i in range(scratch.shape[2]):
                acc = u[4, k, j, i]
                for r in range(repeats):
                    acc = sqrt(acc + 1.0)
                scratch[k, j, i] = acc


@cython.boundscheck(False)
@cython.wraparound(False)
def busy(u: cython.double[:, :, :, ::1], scratch: cython.double[:, :, ::1], repeats: cython.Py_ssize_t) -> None:
    with cython.nogil:
        busy_block(u, scratch, repeats)


@cython.boundscheck(False)
@cython.wraparound(False)
def stage_one(
    pa: cython.double[:, :, :, :, ::1], ps: cython.double[:, :, :, :, ::1], w: cython.double[:, :, :, ::1],
    fx: cython.double[:, :, :, ::1], fy: cython.double[:, :, :, ::1], fz: cython.double[:, :, :, ::1],
    du: cython.double[:, :, :, ::1], scratch: cython.double[:, :, ::1], costs: cython.Py_ssize_t[::1],
    b0: cython.Py_ssize_t, b1: cython.Py_ssize_t, nx: cython.Py_ssize_t, ny: cython.Py_ssize_t,
    nz: cython.Py_ssize_t, g: cython.Py_ssize_t, dx: cython.double, dt: cython.double,
    gz: cython.Py_ssize_t, gy: cython.Py_ssize_t, gx: cython.Py_ssize_t,
) -> None:
    """For blocks b0 .. b1 - 1: ps[b] = pa[b] + dt * rhs(pa[b]), plus costs[b] repeats of extra work."""
    b: cython.Py_ssize_t
    with cython.nogil:
        for b in range(b0, b1):
            rhs_block(pa[b], w, fx, fy, fz, du, nx, ny, nz, g, dx)
            if costs[b] > 0:
                busy_block(pa[b], scratch, costs[b])
            first_stage_block(pa[b], du, dt, ps[b], gz, gy, gx)


@cython.boundscheck(False)
@cython.wraparound(False)
def stage_two(
    pa: cython.double[:, :, :, :, ::1], ps: cython.double[:, :, :, :, ::1], pn: cython.double[:, :, :, :, ::1],
    w: cython.double[:, :, :, ::1], fx: cython.double[:, :, :, ::1], fy: cython.double[:, :, :, ::1],
    fz: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1], scratch: cython.double[:, :, ::1],
    costs: cython.Py_ssize_t[::1], b0: cython.Py_ssize_t, b1: cython.Py_ssize_t, nx: cython.Py_ssize_t,
    ny: cython.Py_ssize_t, nz: cython.Py_ssize_t, g: cython.Py_ssize_t, dx: cython.double, dt: cython.double,
    gz: cython.Py_ssize_t, gy: cython.Py_ssize_t, gx: cython.Py_ssize_t,
) -> None:
    """For blocks b0 .. b1 - 1: pn[b] = pa[b] / 2 + (ps[b] + dt * rhs(ps[b])) / 2, plus costs[b] repeats of extra work."""
    b: cython.Py_ssize_t
    with cython.nogil:
        for b in range(b0, b1):
            rhs_block(ps[b], w, fx, fy, fz, du, nx, ny, nz, g, dx)
            if costs[b] > 0:
                busy_block(ps[b], scratch, costs[b])
            second_stage_block(pa[b], ps[b], du, dt, pn[b], gz, gy, gx)


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
def mc_alt(left: cython.double, right: cython.double) -> cython.double:
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
def hll_alt(
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
