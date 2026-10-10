"""Shared problem setup and NumPy kernel of experiment E04.1: one time step of 2D hydrodynamics.

The kernel is the representative one of brief D03: second-order finite-volume method of lines for the 2D Euler equations
with piecewise-linear reconstruction of the primitive variables (MC limiter), the HLL Riemann solver and an SSP-RK2 step.
Every backend of E04.1 implements exactly the same arithmetic, in the same order where the language allows it, so that
results can be compared and timings mean the same work.

Layout: the conserved state is a C-contiguous float64 array ``U[var, i, j]`` with variables (rho, m_x, m_y, E) and
``N_GHOST`` ghost cells on each side of both directions; j is the fastest-varying index. The ghost cells are filled
periodically by the shared driver, outside the kernel, identically for every backend.

The module is loaded by file path, because its name is not a valid Python module name.
"""

import numpy as np
from numpy.typing import NDArray

type Array = NDArray[np.float64]

N_GHOST = 2
GAMMA = 1.4


def initial_state(n: int) -> Array:
    """Return a smooth periodic 2D state on n x n cells of the unit square, padded with ghost cells.

    Density, velocity and pressure vary in both directions, so that every branch of the limiter and of the Riemann
    solver is exercised (left- and right-moving faces, extrema), and the flow stays smooth for the few steps timed.
    """
    x = (np.arange(n) + 0.5) / n
    xx, yy = np.meshgrid(x, x, indexing="ij")
    rho = 1.0 + 0.2 * np.sin(2 * np.pi * xx) * np.sin(2 * np.pi * yy)
    vx = 0.5 + 0.1 * np.sin(2 * np.pi * yy)
    vy = 0.3 * np.cos(2 * np.pi * xx)
    pres = 1.0 + 0.1 * np.cos(2 * np.pi * (xx + yy))
    u = np.zeros((4, n + 2 * N_GHOST, n + 2 * N_GHOST))
    inner = (slice(None), slice(N_GHOST, -N_GHOST), slice(N_GHOST, -N_GHOST))
    u[inner] = np.array([rho, rho * vx, rho * vy, pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy)])
    fill_ghosts(u)
    return u


def fill_ghosts(u: Array) -> None:
    """Fill the ghost cells periodically, in place."""
    g = N_GHOST
    u[:, :g, :] = u[:, -2 * g : -g, :]
    u[:, -g:, :] = u[:, g : 2 * g, :]
    u[:, :, :g] = u[:, :, -2 * g : -g]
    u[:, :, -g:] = u[:, :, g : 2 * g]


def ssp_rk2_step(u: Array, dt: float, dx: float, rhs) -> Array:
    """Return the state after one SSP-RK2 step; ``rhs(u, dx)`` returns the time derivative of the interior cells."""
    g = N_GHOST
    inner = (slice(None), slice(g, -g), slice(g, -g))
    stage = u.copy()
    stage[inner] += dt * rhs(u, dx)
    fill_ghosts(stage)
    new = u.copy()
    new[inner] = 0.5 * u[inner] + 0.5 * (stage[inner] + dt * rhs(stage, dx))
    fill_ghosts(new)
    return new


def cons_to_prim(u: Array) -> Array:
    rho = u[0]
    vx = u[1] / rho
    vy = u[2] / rho
    pres = (GAMMA - 1.0) * (u[3] - 0.5 * rho * (vx * vx + vy * vy))
    return np.array([rho, vx, vy, pres])


def mc_slope(left: Array, right: Array) -> Array:
    limited = np.minimum(np.minimum(2.0 * np.abs(left), 2.0 * np.abs(right)), 0.5 * np.abs(left + right))
    return np.where(left * right > 0.0, np.where(left > 0.0, limited, -limited), 0.0)


def hll(wl: Array, wr: Array) -> Array:
    """HLL flux in the normal direction for primitive states (rho, u_normal, u_tangential, p)."""
    rl, ul, vl, pl = wl
    rr, ur, vr, pr = wr
    cl = np.sqrt(GAMMA * pl / rl)
    cr = np.sqrt(GAMMA * pr / rr)
    sl = np.minimum(ul - cl, ur - cr)
    sr = np.maximum(ul + cl, ur + cr)
    el = pl / (GAMMA - 1.0) + 0.5 * rl * (ul * ul + vl * vl)
    er = pr / (GAMMA - 1.0) + 0.5 * rr * (ur * ur + vr * vr)
    fl = np.array([rl * ul, rl * ul * ul + pl, rl * ul * vl, (el + pl) * ul])
    fr = np.array([rr * ur, rr * ur * ur + pr, rr * ur * vr, (er + pr) * ur])
    ql = np.array([rl, rl * ul, rl * vl, el])
    qr = np.array([rr, rr * ur, rr * vr, er])
    star = (sr * fl - sl * fr + sl * sr * (qr - ql)) / (sr - sl)
    return np.where(sl >= 0.0, fl, np.where(sr <= 0.0, fr, star))


def rhs(u: Array, dx: float) -> Array:
    """Return -div F of the interior cells (dx = dy)."""
    g = N_GHOST
    n = u.shape[1] - 2 * g
    w = cons_to_prim(u)
    ## x-direction: slopes of cells 1 .. M-2, faces i - 1/2 for i = g .. g + n.
    sx = mc_slope(w[:, 1:-1, g:-g] - w[:, :-2, g:-g], w[:, 2:, g:-g] - w[:, 1:-1, g:-g])
    wl = w[:, g - 1 : g + n, g:-g] + 0.5 * sx[:, g - 2 : g + n - 1]
    wr = w[:, g : g + n + 1, g:-g] - 0.5 * sx[:, g - 1 : g + n]
    fx = hll(wl, wr)
    ## y-direction: swap the velocity components so that the normal one comes first, and back for the flux.
    sy = mc_slope(w[:, g:-g, 1:-1] - w[:, g:-g, :-2], w[:, g:-g, 2:] - w[:, g:-g, 1:-1])
    wl = w[:, g:-g, g - 1 : g + n] + 0.5 * sy[:, :, g - 2 : g + n - 1]
    wr = w[:, g:-g, g : g + n + 1] - 0.5 * sy[:, :, g - 1 : g + n]
    fy = hll(wl[[0, 2, 1, 3]], wr[[0, 2, 1, 3]])[[0, 2, 1, 3]]
    return -(fx[:, 1:, :] - fx[:, :-1, :]) / dx - (fy[:, :, 1:] - fy[:, :, :-1]) / dx
