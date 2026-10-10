"""Minimal one-dimensional ZEUS-type solver for the Euler equations: input module of experiment E03.1.

Follows the hydrodynamic algorithm of ZEUS-2D (Stone & Norman 1992, paper I; see the ZEUS synthesis in ``References/``)
in one Cartesian dimension, as the representative of the staggered finite-difference family:

- staggered mesh: density and internal energy density at zone centres, velocity at zone faces;
- the internal energy equation, not total energy;
- operator splitting into a source step (pressure gradient, von Neumann-Richtmyer artificial viscosity, compressional
  heating with the implicit time-centred update for a gamma-law gas) and a transport step;
- transport in control-volume form with upwinded, time-centred van Leer interpolation, and "consistent transport":
  internal energy and momentum are advected as specific quantities carried by the mass fluxes;
- time step from the root sum of squares of the sound, flow and viscous rates (Courant number 0.5).

It is a faithful sketch for comparison, not a complete reimplementation of ZEUS. Velocity index ``i`` belongs to the
face on the lower side of zone ``i``, as in ZEUS. Arrays carry ``N_GHOST`` ghost zones on each side.
"""

import numpy as np
from numpy.typing import NDArray

type Array = NDArray[np.float64]

N_GHOST = 2


def fill_ghosts(rho: Array, eint: Array, vel: Array, boundary: str) -> None:
    """Fill the ghost zones in place, periodically or by copying the outermost active values (outflow)."""
    g = N_GHOST
    n = rho.size - 2 * g
    if boundary == "periodic":
        for arr in (rho, eint, vel):
            arr[:g] = arr[n : n + g]
            arr[n + g :] = arr[g : 2 * g]
    else:
        for arr in (rho, eint):
            arr[:g] = arr[g]
            arr[n + g :] = arr[n + g - 1]
        vel[: g + 1] = vel[g + 1]
        vel[n + g :] = vel[n + g - 1]


def van_leer_slopes(q: Array) -> Array:
    """Return van Leer's monotonised harmonic-mean slope of every zone (zero at the outermost zones and at extrema)."""
    slope = np.zeros_like(q)
    left = q[1:-1] - q[:-2]
    right = q[2:] - q[1:-1]
    product = left * right
    with np.errstate(divide="ignore", invalid="ignore"):
        slope[1:-1] = np.where(product > 0.0, 2.0 * product / (left + right), 0.0)
    return slope


def upwind_interface(q: Array, speed: Array, dt: float, dx: float) -> Array:
    """Return time-centred upwind values of the zone quantity ``q`` at the face below every zone.

    ``speed[i]`` is the advection velocity at that face. The value is taken from the upwind zone and moved to the
    position the fluid crossing the face comes from, half a step back in time, as in ZEUS's van Leer interpolation.
    """
    slope = van_leer_slopes(q)
    from_left = np.roll(q, 1) + 0.5 * (1.0 - speed * dt / dx) * np.roll(slope, 1)
    from_right = q - 0.5 * (1.0 + speed * dt / dx) * slope
    return np.where(speed >= 0.0, from_left, from_right)


def time_step(rho: Array, eint: Array, vel: Array, dx: float, gamma: float, c_visc: float, courant: float) -> float:
    """Return the ZEUS time step: Courant number over the root sum of squares of the limiting rates."""
    g = N_GHOST
    sl = slice(g, rho.size - g)
    sound = np.sqrt(gamma * (gamma - 1.0) * eint[sl] / rho[sl]) / dx
    flow = np.abs(0.5 * (vel[sl] + vel[g + 1 : rho.size - g + 1])) / dx
    dv = vel[g + 1 : rho.size - g + 1] - vel[sl]
    visc = 4.0 * c_visc * np.where(dv < 0.0, -dv, 0.0) / dx
    return float(courant / np.max(np.sqrt(sound**2 + flow**2 + visc**2)))


def step(
    rho: Array, eint: Array, vel: Array, dt: float, dx: float, *, gamma: float, c_visc: float, boundary: str
) -> tuple[Array, Array, Array]:
    """Advance one ZEUS cycle: the source step followed by the transport step. Returns new arrays."""
    rho, eint, vel = rho.copy(), eint.copy(), vel.copy()
    inner = slice(1, -1)

    ## Source substep 1: pressure gradient accelerates the face velocities.
    pres = (gamma - 1.0) * eint
    rho_face = 0.5 * (rho + np.roll(rho, 1))
    vel[inner] -= (dt / dx * (pres - np.roll(pres, 1)) / rho_face)[inner]
    fill_ghosts(rho, eint, vel, boundary)

    ## Source substep 2: artificial viscosity, a zone-centred viscous pressure acting only in compression.
    dv = np.roll(vel, -1) - vel
    q = np.where(dv < 0.0, c_visc * rho * dv * dv, 0.0)
    vel[inner] -= (dt / dx * (q - np.roll(q, 1)) / rho_face)[inner]
    eint[inner] -= (dt / dx * q * dv)[inner]
    fill_ghosts(rho, eint, vel, boundary)

    ## Source substep 3: compressional heating, time-centred implicit update for a gamma-law gas.
    divv = (np.roll(vel, -1) - vel) / dx
    factor = 0.5 * dt * (gamma - 1.0) * divv
    eint[inner] = (eint * (1.0 - factor) / (1.0 + factor))[inner]
    fill_ghosts(rho, eint, vel, boundary)

    ## Transport step: mass first, then internal energy and momentum as specific quantities ("consistent transport").
    mass_flux = upwind_interface(rho, vel, dt, dx) * vel
    eint_flux = upwind_interface(eint / rho, vel, dt, dx) * mass_flux
    momentum = 0.5 * (rho + np.roll(rho, 1)) * vel
    ## The momentum control volumes are centred on the faces; their fluxes sit at zone centres, carried by the average
    ## mass flux there, with the velocity interpolated upwind along the faces.
    centre_speed = 0.5 * (vel + np.roll(vel, -1))
    centre_mass_flux = 0.5 * (mass_flux + np.roll(mass_flux, -1))
    vel_at_centre = np.roll(upwind_interface(vel, np.roll(centre_speed, 1), dt, dx), -1)
    momentum_flux = centre_mass_flux * vel_at_centre

    new_rho = rho.copy()
    new_rho[inner] -= (dt / dx * (np.roll(mass_flux, -1) - mass_flux))[inner]
    eint[inner] -= (dt / dx * (np.roll(eint_flux, -1) - eint_flux))[inner]
    momentum[inner] -= (dt / dx * (momentum_flux - np.roll(momentum_flux, 1)))[inner]
    vel[inner] = (momentum / (0.5 * (new_rho + np.roll(new_rho, 1))))[inner]
    fill_ghosts(new_rho, eint, vel, boundary)
    return new_rho, eint, vel


def evolve(
    rho: Array,
    eint: Array,
    vel: Array,
    dx: float,
    t_end: float,
    *,
    gamma: float = 1.4,
    c_visc: float = 2.0,
    courant: float = 0.5,
    boundary: str = "periodic",
) -> tuple[Array, Array, Array, int]:
    """Evolve padded arrays to ``t_end``; returns the final density, internal energy density, velocity and step count."""
    fill_ghosts(rho, eint, vel, boundary)
    time, steps = 0.0, 0
    while time < t_end:
        dt = min(time_step(rho, eint, vel, dx, gamma, c_visc, courant), t_end - time)
        rho, eint, vel = step(rho, eint, vel, dt, dx, gamma=gamma, c_visc=c_visc, boundary=boundary)
        time += dt
        steps += 1
    return rho, eint, vel, steps


def pad(zone_values: Array) -> Array:
    """Return an array with ghost zones around the given active-zone values (ghosts are filled later)."""
    return np.pad(zone_values, N_GHOST)
