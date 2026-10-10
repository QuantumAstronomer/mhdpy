"""Minimal one-dimensional finite-volume Godunov solver for the Euler equations: input module of experiment E03.1.

A copy (apart from this docstring) of ``docs/decisions/D02-verification/experiments/E02.1a-hydro1d.py``, kept here so that the experiments of
brief D03 are self-contained. Second-order Godunov-type method of lines: piecewise-linear reconstruction of the primitive
variables with a choice of slope limiter, the HLL Riemann solver, SSP-RK2, and an exact Riemann solver for comparison.
It evolves total energy and is conservative by construction.

The module is loaded by file path from the experiment scripts, because its name is not a valid Python module name.
"""

import numpy as np
from numpy.typing import NDArray

type Array = NDArray[np.float64]

N_GHOST = 2
LIMITERS = ("constant", "none", "minmod", "mc")


def cons_to_prim(cons: Array, gamma: float) -> Array:
    """Convert conserved variables (density, momentum, total energy) to primitive ones (density, velocity, pressure)."""
    rho = cons[0]
    vel = cons[1] / rho
    pres = (gamma - 1.0) * (cons[2] - 0.5 * rho * vel * vel)
    return np.array([rho, vel, pres])


def prim_to_cons(prim: Array, gamma: float) -> Array:
    """Convert primitive variables (density, velocity, pressure) to conserved ones (density, momentum, energy)."""
    rho, vel, pres = prim
    return np.array([rho, rho * vel, pres / (gamma - 1.0) + 0.5 * rho * vel * vel])


def physical_flux(prim: Array, gamma: float) -> Array:
    """Return the Euler flux vector evaluated from primitive variables."""
    rho, vel, pres = prim
    energy = pres / (gamma - 1.0) + 0.5 * rho * vel * vel
    return np.array([rho * vel, rho * vel * vel + pres, (energy + pres) * vel])


def limited_slopes(prim: Array, limiter: str) -> Array:
    """Return the limited slope of every cell except the outermost one on each side.

    The slope is the undivided difference across a cell. ``constant`` gives zero slopes (first order), ``none`` the
    unlimited central difference, and ``minmod`` / ``mc`` the classic limiters, which set the slope to zero at extrema.
    """
    left = prim[:, 1:-1] - prim[:, :-2]
    right = prim[:, 2:] - prim[:, 1:-1]
    if limiter == "constant":
        return np.zeros_like(left)
    if limiter == "none":
        return 0.5 * (left + right)
    same_sign = left * right > 0.0
    if limiter == "minmod":
        slope = np.sign(left) * np.minimum(np.abs(left), np.abs(right))
    elif limiter == "mc":
        slope = np.sign(left) * np.minimum(
            np.minimum(2.0 * np.abs(left), 2.0 * np.abs(right)), 0.5 * np.abs(left + right)
        )
    else:
        raise ValueError(f"unknown limiter: {limiter}")
    return np.where(same_sign, slope, 0.0)


def hll_flux(prim_left: Array, prim_right: Array, gamma: float) -> Array:
    """Return the HLL flux for the given left and right interface states, with Davis wave-speed estimates."""
    c_left = np.sqrt(gamma * prim_left[2] / prim_left[0])
    c_right = np.sqrt(gamma * prim_right[2] / prim_right[0])
    s_left = np.minimum(prim_left[1] - c_left, prim_right[1] - c_right)
    s_right = np.maximum(prim_left[1] + c_left, prim_right[1] + c_right)
    flux_left = physical_flux(prim_left, gamma)
    flux_right = physical_flux(prim_right, gamma)
    cons_left = prim_to_cons(prim_left, gamma)
    cons_right = prim_to_cons(prim_right, gamma)
    flux_star = (s_right * flux_left - s_left * flux_right + s_left * s_right * (cons_right - cons_left)) / (
        s_right - s_left
    )
    return np.where(s_left >= 0.0, flux_left, np.where(s_right <= 0.0, flux_right, flux_star))


def with_ghosts(cons: Array, boundary: str) -> Array:
    """Return a copy of the interior state padded with ghost cells, filled periodically or by zero-gradient outflow."""
    padded = np.pad(cons, ((0, 0), (N_GHOST, N_GHOST)), mode="wrap" if boundary == "periodic" else "edge")
    return padded


def time_derivative(cons: Array, dx: float, limiter: str, boundary: str, gamma: float) -> Array:
    """Return the semi-discrete time derivative -dF/dx of the interior cells."""
    prim = cons_to_prim(with_ghosts(cons, boundary), gamma)
    slopes = limited_slopes(prim, limiter)
    ## Cells 1 .. M-2 have slopes; interface j+1/2 between cells j and j+1 takes the right edge of cell j and the left
    ## edge of cell j+1. With two ghost cells this yields exactly the n+1 faces of the n interior cells.
    prim_left = prim[:, 1:-2] + 0.5 * slopes[:, :-1]
    prim_right = prim[:, 2:-1] - 0.5 * slopes[:, 1:]
    flux = hll_flux(prim_left, prim_right, gamma)
    return -(flux[:, 1:] - flux[:, :-1]) / dx


def max_signal_speed(cons: Array, gamma: float) -> float:
    """Return the largest |u| + c over the grid."""
    rho, vel, pres = cons_to_prim(cons, gamma)
    return float(np.max(np.abs(vel) + np.sqrt(gamma * pres / rho)))


def evolve(
    cons: Array, dx: float, t_end: float, *, limiter: str, boundary: str, gamma: float = 1.4, cfl: float = 0.4
) -> tuple[Array, int]:
    """Advance the state to ``t_end`` with SSP-RK2 and return the final state and the number of steps taken."""
    time, steps = 0.0, 0
    while time < t_end:
        dt = min(cfl * dx / max_signal_speed(cons, gamma), t_end - time)
        stage = cons + dt * time_derivative(cons, dx, limiter, boundary, gamma)
        cons = 0.5 * cons + 0.5 * (stage + dt * time_derivative(stage, dx, limiter, boundary, gamma))
        time += dt
        steps += 1
    return cons, steps


def cell_centres(n: int) -> Array:
    """Return the cell centres of a uniform grid of ``n`` cells on [0, 1]."""
    return (np.arange(n) + 0.5) / n


def sound_wave(n: int, amplitude: float = 1.0e-6, gamma: float = 1.4) -> Array:
    """Return a right-moving linear sound wave of one wavelength on [0, 1], with sound speed 1.

    After a time of 1 the exact solution equals the initial state, so any difference is numerical error.
    """
    x = cell_centres(n)
    shape = amplitude * np.sin(2.0 * np.pi * x)
    rho0, pres0 = 1.0, 1.0 / gamma
    prim = np.array([rho0 + shape, shape, pres0 + shape])
    return prim_to_cons(prim, gamma)


SOD_LEFT = (1.0, 0.0, 1.0)
SOD_RIGHT = (0.125, 0.0, 0.1)


def shock_tube(n: int, left: tuple[float, float, float], right: tuple[float, float, float], gamma: float = 1.4) -> Array:
    """Return a Riemann problem on [0, 1] with the discontinuity at x = 0.5."""
    x = cell_centres(n)
    prim = np.array([np.where(x < 0.5, left[k], right[k]) for k in range(3)])
    return prim_to_cons(prim, gamma)


def exact_riemann(
    left: tuple[float, float, float], right: tuple[float, float, float], xi: Array, gamma: float = 1.4
) -> Array:
    """Return the exact solution of the Riemann problem at similarity coordinates ``xi = (x - x0) / t``.

    Follows the exact solver of Toro (2009, chapter 4): the star-region pressure is found by Newton iteration on the
    pressure function, after which every point is sampled according to the wave pattern.
    """
    rho_l, u_l, p_l = left
    rho_r, u_r, p_r = right
    c_l, c_r = np.sqrt(gamma * p_l / rho_l), np.sqrt(gamma * p_r / rho_r)
    g1, g2 = (gamma - 1.0) / (2.0 * gamma), (gamma + 1.0) / (2.0 * gamma)

    def pressure_function(p: float, rho_k: float, p_k: float, c_k: float) -> tuple[float, float]:
        if p > p_k:
            a_k, b_k = 2.0 / ((gamma + 1.0) * rho_k), (gamma - 1.0) / (gamma + 1.0) * p_k
            root = np.sqrt(a_k / (p + b_k))
            return (p - p_k) * root, root * (1.0 - 0.5 * (p - p_k) / (b_k + p))
        ratio = p / p_k
        return 2.0 * c_k / (gamma - 1.0) * (ratio**g1 - 1.0), ratio ** (-g2) / (rho_k * c_k)

    p_star = max(1.0e-8, 0.5 * (p_l + p_r))
    for _ in range(100):
        f_l, df_l = pressure_function(p_star, rho_l, p_l, c_l)
        f_r, df_r = pressure_function(p_star, rho_r, p_r, c_r)
        p_new = max(1.0e-8, p_star - (f_l + f_r + u_r - u_l) / (df_l + df_r))
        if abs(p_new - p_star) < 1.0e-14 * (p_new + p_star):
            p_star = p_new
            break
        p_star = p_new
    f_l, _ = pressure_function(p_star, rho_l, p_l, c_l)
    f_r, _ = pressure_function(p_star, rho_r, p_r, c_r)
    u_star = 0.5 * (u_l + u_r) + 0.5 * (f_r - f_l)

    out = np.empty((3, xi.size))
    for i, s in enumerate(xi):
        if s <= u_star:  ## left of the contact
            rho_k, u_k, p_k, c_k, sign = rho_l, u_l, p_l, c_l, 1.0
        else:  ## right of the contact: mirror the left-side formulas
            rho_k, u_k, p_k, c_k, sign = rho_r, u_r, p_r, c_r, -1.0
        ratio = p_star / p_k
        if p_star > p_k:  ## shock
            shock_speed = u_k - sign * c_k * np.sqrt(g2 * ratio + g1)
            if sign * (s - shock_speed) <= 0.0:
                out[:, i] = rho_k, u_k, p_k
            else:
                gr = (gamma - 1.0) / (gamma + 1.0)
                out[:, i] = rho_k * (ratio + gr) / (gr * ratio + 1.0), u_star, p_star
        else:  ## rarefaction
            c_star = c_k * ratio**g1
            head, tail = u_k - sign * c_k, u_star - sign * c_star
            if sign * (s - head) <= 0.0:
                out[:, i] = rho_k, u_k, p_k
            elif sign * (s - tail) >= 0.0:
                out[:, i] = rho_k * ratio ** (1.0 / gamma), u_star, p_star
            else:
                factor = 2.0 / (gamma + 1.0) + sign * (gamma - 1.0) / ((gamma + 1.0) * c_k) * (u_k - s)
                rho = rho_k * factor ** (2.0 / (gamma - 1.0))
                vel = 2.0 / (gamma + 1.0) * (sign * c_k + (gamma - 1.0) / 2.0 * u_k + s)
                out[:, i] = rho, vel, p_k * factor ** (2.0 * gamma / (gamma - 1.0))
    return out
