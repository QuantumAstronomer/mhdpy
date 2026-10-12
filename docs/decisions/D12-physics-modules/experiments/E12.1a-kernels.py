# cython: freethreading_compatible=True
"""Kernels of experiment E12.1: passive scalars fused into the hydrodynamic kernel, or as a module's separate passes.

The state holds the five hydrodynamic variables followed by ns passive scalars (conserved: density times concentration),
in one array (D06.4). Passive scalars are advected with the mass flux (D03.6): the flux of a scalar through a face is
the mass flux times the upwind face value of its concentration, reconstructed with PLM like the other primitives. The
hydrodynamic part is the face routine of D10 (``E10.2a-face-routine.py``: one routine with the direction as constant
arguments, HLL, PLM with MC), here for 2D blocks (x and y). Two ways of adding the scalars, with the same arithmetic:

- ``rhs_fused``: one kernel; the primitive conversion, the face loop and the divergence handle all variables, and each
  face computes the scalar fluxes right after its hydrodynamic flux;
- ``rhs_separate``: the hydrodynamic kernel's passes (primitives, faces, divergence) for the five variables, writing the
  mass flux into the shared flux array, then the scalar module's own passes (concentrations, scalar fluxes from the
  stored mass flux, divergence), as a module that knows nothing of the hydrodynamic kernel would add them.
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
def face_hydro(
    w: cython.double[:, :, :, ::1], f: cython.double[:, :, :, ::1],
    k0: cython.Py_ssize_t, k1: cython.Py_ssize_t, j0: cython.Py_ssize_t, j1: cython.Py_ssize_t,
    i0: cython.Py_ssize_t, i1: cython.Py_ssize_t, dk: cython.Py_ssize_t, dj: cython.Py_ssize_t, di: cython.Py_ssize_t,
    n: cython.Py_ssize_t, a: cython.Py_ssize_t, b: cython.Py_ssize_t,
) -> cython.void:
    """Hydrodynamic fluxes through the faces (E10.2a), written to components 0-4 of f."""
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    l0: cython.double
    ln: cython.double
    la: cython.double
    lb: cython.double
    l4: cython.double
    r0: cython.double
    rn: cython.double
    ra: cython.double
    rb: cython.double
    r4: cython.double
    for k in range(k0, k1):
        for j in range(j0, j1):
            for i in range(i0, i1):
                l0 = w[0, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[0, k - dk, j - dj, i - di] - w[0, k - 2 * dk, j - 2 * dj, i - 2 * di], w[0, k, j, i] - w[0, k - dk, j - dj, i - di])
                ln = w[n, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[n, k - dk, j - dj, i - di] - w[n, k - 2 * dk, j - 2 * dj, i - 2 * di], w[n, k, j, i] - w[n, k - dk, j - dj, i - di])
                la = w[a, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[a, k - dk, j - dj, i - di] - w[a, k - 2 * dk, j - 2 * dj, i - 2 * di], w[a, k, j, i] - w[a, k - dk, j - dj, i - di])
                lb = w[b, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[b, k - dk, j - dj, i - di] - w[b, k - 2 * dk, j - 2 * dj, i - 2 * di], w[b, k, j, i] - w[b, k - dk, j - dj, i - di])
                l4 = w[4, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[4, k - dk, j - dj, i - di] - w[4, k - 2 * dk, j - 2 * dj, i - 2 * di], w[4, k, j, i] - w[4, k - dk, j - dj, i - di])
                r0 = w[0, k, j, i] - 0.5 * mc_slope(
                    w[0, k, j, i] - w[0, k - dk, j - dj, i - di], w[0, k + dk, j + dj, i + di] - w[0, k, j, i])
                rn = w[n, k, j, i] - 0.5 * mc_slope(
                    w[n, k, j, i] - w[n, k - dk, j - dj, i - di], w[n, k + dk, j + dj, i + di] - w[n, k, j, i])
                ra = w[a, k, j, i] - 0.5 * mc_slope(
                    w[a, k, j, i] - w[a, k - dk, j - dj, i - di], w[a, k + dk, j + dj, i + di] - w[a, k, j, i])
                rb = w[b, k, j, i] - 0.5 * mc_slope(
                    w[b, k, j, i] - w[b, k - dk, j - dj, i - di], w[b, k + dk, j + dj, i + di] - w[b, k, j, i])
                r4 = w[4, k, j, i] - 0.5 * mc_slope(
                    w[4, k, j, i] - w[4, k - dk, j - dj, i - di], w[4, k + dk, j + dj, i + di] - w[4, k, j, i])
                hll(l0, ln, la, lb, l4, r0, rn, ra, rb, r4, f, k - k0, j - j0, i - i0, n, a, b)


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.initializedcheck(False)
def face_fused(
    w: cython.double[:, :, :, ::1], f: cython.double[:, :, :, ::1],
    k0: cython.Py_ssize_t, k1: cython.Py_ssize_t, j0: cython.Py_ssize_t, j1: cython.Py_ssize_t,
    i0: cython.Py_ssize_t, i1: cython.Py_ssize_t, dk: cython.Py_ssize_t, dj: cython.Py_ssize_t, di: cython.Py_ssize_t,
    n: cython.Py_ssize_t, a: cython.Py_ssize_t, b: cython.Py_ssize_t, ns: cython.Py_ssize_t,
) -> cython.void:
    """Hydrodynamic fluxes, then at the same face the fluxes of ns passive scalars from the mass flux just computed."""
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    l0: cython.double
    ln: cython.double
    la: cython.double
    lb: cython.double
    l4: cython.double
    r0: cython.double
    rn: cython.double
    ra: cython.double
    rb: cython.double
    r4: cython.double
    m: cython.Py_ssize_t
    v: cython.Py_ssize_t
    sl: cython.double
    sr: cython.double
    for k in range(k0, k1):
        for j in range(j0, j1):
            for i in range(i0, i1):
                l0 = w[0, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[0, k - dk, j - dj, i - di] - w[0, k - 2 * dk, j - 2 * dj, i - 2 * di], w[0, k, j, i] - w[0, k - dk, j - dj, i - di])
                ln = w[n, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[n, k - dk, j - dj, i - di] - w[n, k - 2 * dk, j - 2 * dj, i - 2 * di], w[n, k, j, i] - w[n, k - dk, j - dj, i - di])
                la = w[a, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[a, k - dk, j - dj, i - di] - w[a, k - 2 * dk, j - 2 * dj, i - 2 * di], w[a, k, j, i] - w[a, k - dk, j - dj, i - di])
                lb = w[b, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[b, k - dk, j - dj, i - di] - w[b, k - 2 * dk, j - 2 * dj, i - 2 * di], w[b, k, j, i] - w[b, k - dk, j - dj, i - di])
                l4 = w[4, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                    w[4, k - dk, j - dj, i - di] - w[4, k - 2 * dk, j - 2 * dj, i - 2 * di], w[4, k, j, i] - w[4, k - dk, j - dj, i - di])
                r0 = w[0, k, j, i] - 0.5 * mc_slope(
                    w[0, k, j, i] - w[0, k - dk, j - dj, i - di], w[0, k + dk, j + dj, i + di] - w[0, k, j, i])
                rn = w[n, k, j, i] - 0.5 * mc_slope(
                    w[n, k, j, i] - w[n, k - dk, j - dj, i - di], w[n, k + dk, j + dj, i + di] - w[n, k, j, i])
                ra = w[a, k, j, i] - 0.5 * mc_slope(
                    w[a, k, j, i] - w[a, k - dk, j - dj, i - di], w[a, k + dk, j + dj, i + di] - w[a, k, j, i])
                rb = w[b, k, j, i] - 0.5 * mc_slope(
                    w[b, k, j, i] - w[b, k - dk, j - dj, i - di], w[b, k + dk, j + dj, i + di] - w[b, k, j, i])
                r4 = w[4, k, j, i] - 0.5 * mc_slope(
                    w[4, k, j, i] - w[4, k - dk, j - dj, i - di], w[4, k + dk, j + dj, i + di] - w[4, k, j, i])
                hll(l0, ln, la, lb, l4, r0, rn, ra, rb, r4, f, k - k0, j - j0, i - i0, n, a, b)
                for m in range(ns):
                    v = 5 + m
                    sl = w[v, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                        w[v, k - dk, j - dj, i - di] - w[v, k - 2 * dk, j - 2 * dj, i - 2 * di], w[v, k, j, i] - w[v, k - dk, j - dj, i - di])
                    sr = w[v, k, j, i] - 0.5 * mc_slope(
                        w[v, k, j, i] - w[v, k - dk, j - dj, i - di], w[v, k + dk, j + dj, i + di] - w[v, k, j, i])
                    f[v, k - k0, j - j0, i - i0] = f[0, k - k0, j - j0, i - i0] * (
                        sl if f[0, k - k0, j - j0, i - i0] >= 0.0 else sr)

@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.initializedcheck(False)
def face_scalars(
    w: cython.double[:, :, :, ::1], f: cython.double[:, :, :, ::1],
    k0: cython.Py_ssize_t, k1: cython.Py_ssize_t, j0: cython.Py_ssize_t, j1: cython.Py_ssize_t,
    i0: cython.Py_ssize_t, i1: cython.Py_ssize_t, dk: cython.Py_ssize_t, dj: cython.Py_ssize_t, di: cython.Py_ssize_t,
    ns: cython.Py_ssize_t,
) -> cython.void:
    """The scalar module's own pass: fluxes of ns scalars from the stored mass flux f[0], with the same arithmetic."""
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    m: cython.Py_ssize_t
    v: cython.Py_ssize_t
    sl: cython.double
    sr: cython.double
    for k in range(k0, k1):
        for j in range(j0, j1):
            for i in range(i0, i1):
                for m in range(ns):
                    v = 5 + m
                    sl = w[v, k - dk, j - dj, i - di] + 0.5 * mc_slope(
                        w[v, k - dk, j - dj, i - di] - w[v, k - 2 * dk, j - 2 * dj, i - 2 * di], w[v, k, j, i] - w[v, k - dk, j - dj, i - di])
                    sr = w[v, k, j, i] - 0.5 * mc_slope(
                        w[v, k, j, i] - w[v, k - dk, j - dj, i - di], w[v, k + dk, j + dj, i + di] - w[v, k, j, i])
                    f[v, k - k0, j - j0, i - i0] = f[0, k - k0, j - j0, i - i0] * (
                        sl if f[0, k - k0, j - j0, i - i0] >= 0.0 else sr)


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
@cython.initializedcheck(False)
def primitives(u: cython.double[:, :, :, ::1], w: cython.double[:, :, :, ::1], v0: cython.Py_ssize_t,
               v1: cython.Py_ssize_t) -> cython.void:
    """Primitive variables v0 .. v1 - 1 of all cells: the hydrodynamic ones (0-4) and scalar concentrations (5 on)."""
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    v: cython.Py_ssize_t
    rho: cython.double
    vx: cython.double
    vy: cython.double
    vz: cython.double
    for k in range(u.shape[1]):
        for j in range(u.shape[2]):
            for i in range(u.shape[3]):
                rho = u[0, k, j, i]
                if v0 == 0:
                    vx = u[1, k, j, i] / rho
                    vy = u[2, k, j, i] / rho
                    vz = u[3, k, j, i] / rho
                    w[0, k, j, i] = rho
                    w[1, k, j, i] = vx
                    w[2, k, j, i] = vy
                    w[3, k, j, i] = vz
                    w[4, k, j, i] = (GAMMA - 1.0) * (u[4, k, j, i] - 0.5 * rho * (vx * vx + vy * vy + vz * vz))
                for v in range(max(v0, 5), v1):
                    w[v, k, j, i] = u[v, k, j, i] / rho


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def divergence(fx: cython.double[:, :, :, ::1], fy: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1],
               v0: cython.Py_ssize_t, v1: cython.Py_ssize_t, dx: cython.double) -> cython.void:
    """du = -div F for variables v0 .. v1 - 1 (2D, x and y)."""
    v: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    for v in range(v0, v1):
        for j in range(du.shape[2]):
            for i in range(du.shape[3]):
                du[v, 0, j, i] = -(fx[v, 0, j, i + 1] - fx[v, 0, j, i]) / dx
        for j in range(du.shape[2]):
            for i in range(du.shape[3]):
                du[v, 0, j, i] = du[v, 0, j, i] - (fy[v, 0, j + 1, i] - fy[v, 0, j, i]) / dx


@cython.boundscheck(False)
@cython.wraparound(False)
def rhs_fused(
    u: cython.double[:, :, :, ::1], w: cython.double[:, :, :, ::1], fx: cython.double[:, :, :, ::1],
    fy: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1], nx: cython.Py_ssize_t, ny: cython.Py_ssize_t,
    g: cython.Py_ssize_t, dx: cython.double, ns: cython.Py_ssize_t,
) -> None:
    """Hydrodynamics and ns passive scalars in one pass: one primitive loop, scalars fluxed at each face, one divergence."""
    with cython.nogil:
        primitives(u, w, 0, 5 + ns)
        face_fused(w, fx, 0, 1, g, g + ny, g, g + nx + 1, 0, 0, 1, 1, 2, 3, ns)
        face_fused(w, fy, 0, 1, g, g + ny + 1, g, g + nx, 0, 1, 0, 2, 3, 1, ns)
        divergence(fx, fy, du, 0, 5 + ns, dx)


@cython.boundscheck(False)
@cython.wraparound(False)
def rhs_separate(
    u: cython.double[:, :, :, ::1], w: cython.double[:, :, :, ::1], fx: cython.double[:, :, :, ::1],
    fy: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1], nx: cython.Py_ssize_t, ny: cython.Py_ssize_t,
    g: cython.Py_ssize_t, dx: cython.double, ns: cython.Py_ssize_t,
) -> None:
    """The hydrodynamics module's passes, then the scalar module's own passes over the same arrays."""
    with cython.nogil:
        primitives(u, w, 0, 5)
        face_hydro(w, fx, 0, 1, g, g + ny, g, g + nx + 1, 0, 0, 1, 1, 2, 3)
        face_hydro(w, fy, 0, 1, g, g + ny + 1, g, g + nx, 0, 1, 0, 2, 3, 1)
        divergence(fx, fy, du, 0, 5, dx)
        if ns > 0:
            primitives(u, w, 5, 5 + ns)
            face_scalars(w, fx, 0, 1, g, g + ny, g, g + nx + 1, 0, 0, 1, ns)
            face_scalars(w, fy, 0, 1, g, g + ny + 1, g, g + nx, 0, 1, 0, ns)
            divergence(fx, fy, du, 5, 5 + ns, dx)
