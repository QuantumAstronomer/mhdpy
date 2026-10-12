"""Minimal two-dimensional ideal-MHD solver with interchangeable divergence control: input module of experiment E03.2.

A second-order finite-volume method of lines on a periodic Cartesian grid: piecewise-linear reconstruction of the
primitive variables (MC limiter), the HLL Riemann solver for ideal MHD and SSP-RK2 time integration. The divergence of
the magnetic field is handled in one of four ways:

- ``"none"``: B is a cell-centred conserved variable updated by the flux divergence, without any control;
- ``"glm"``: as ``"none"``, plus hyperbolic-parabolic divergence cleaning (Dedner et al. 2002) with an extra scalar
  psi, in the mixed form of Mignone & Tzeferacos (2010);
- ``"ct-average"``: constrained transport. The in-plane field lives on cell faces and is updated with edge-centred
  electric fields (EMFs) obtained by arithmetically averaging the four face EMFs around each edge (Balsara & Spicer 1999);
- ``"ct-contact"``: constrained transport with the edge EMFs integrated from the faces with gradients upwinded by the
  direction of the mass flux (Gardiner & Stone 2005), as Athena++ does in ``src/field/calculate_corner_e.cpp``,
  including its upwind weighting function.

Arrays are indexed ``[i, j]`` with i along x. Face-centred ``bx[i, j]`` sits on the x-face at i - 1/2, ``by[i, j]`` on
the y-face at j - 1/2, and the edge EMF ``ez[i, j]`` at the corner (i - 1/2, j - 1/2). Units absorb the factor 4 pi.
This module is not an early version of mhdpy.

Copied unchanged from D03 (``E03.2a-mhd2d.py``) as the input module of experiment E08.2.
"""

import numpy as np
from numpy.typing import NDArray

type Array = NDArray[np.float64]

## Indices of the primitive variables (rho, v, p, B) and of the conserved ones (rho, momentum, E, B); psi is index 8.
RHO, VX, VY, VZ, PRS, BX, BY, BZ, PSI = range(9)
MX, MY, MZ, ENG = VX, VY, VZ, PRS
SCHEMES = ("none", "glm", "ct-average", "ct-contact")
GLM_ALPHA = 0.4  ## damping parameter of the mixed GLM formulation (Mignone & Tzeferacos 2010 recommend 0 < alpha < 1)


def prim_to_cons(prim: Array, gamma: float) -> Array:
    """Convert primitive to conserved variables; total energy includes the magnetic energy."""
    cons = prim.copy()
    cons[MX:MZ + 1] = prim[RHO] * prim[VX:VZ + 1]
    kinetic = 0.5 * prim[RHO] * np.sum(prim[VX:VZ + 1] ** 2, axis=0)
    magnetic = 0.5 * np.sum(prim[BX:BZ + 1] ** 2, axis=0)
    cons[ENG] = prim[PRS] / (gamma - 1.0) + kinetic + magnetic
    return cons


def cons_to_prim(cons: Array, gamma: float) -> Array:
    """Convert conserved to primitive variables."""
    prim = cons.copy()
    prim[VX:VZ + 1] = cons[MX:MZ + 1] / cons[RHO]
    kinetic = 0.5 * np.sum(cons[MX:MZ + 1] ** 2, axis=0) / cons[RHO]
    magnetic = 0.5 * np.sum(cons[BX:BZ + 1] ** 2, axis=0)
    prim[PRS] = (gamma - 1.0) * (cons[ENG] - kinetic - magnetic)
    return prim


def flux_x(prim: Array, gamma: float) -> Array:
    """Return the ideal-MHD flux in the x-direction (the psi component, if present, is left at zero)."""
    rho, vx, vy, vz, pres, bx, by, bz = prim[:8]
    b2 = bx * bx + by * by + bz * bz
    ptot = pres + 0.5 * b2
    energy = pres / (gamma - 1.0) + 0.5 * rho * (vx * vx + vy * vy + vz * vz) + 0.5 * b2
    flux = np.zeros_like(prim)
    flux[RHO] = rho * vx
    flux[MX] = rho * vx * vx + ptot - bx * bx
    flux[MY] = rho * vx * vy - bx * by
    flux[MZ] = rho * vx * vz - bx * bz
    flux[ENG] = (energy + ptot) * vx - bx * (vx * bx + vy * by + vz * bz)
    flux[BY] = by * vx - bx * vy
    flux[BZ] = bz * vx - bx * vz
    return flux


def fast_speed(prim: Array, gamma: float) -> Array:
    """Return the fast magnetosonic speed in the x-direction."""
    rho = prim[RHO]
    a2 = gamma * prim[PRS] / rho
    b2 = np.sum(prim[BX:BZ + 1] ** 2, axis=0) / rho
    bn2 = prim[BX] ** 2 / rho
    return np.sqrt(0.5 * (a2 + b2 + np.sqrt(np.maximum((a2 + b2) ** 2 - 4.0 * a2 * bn2, 0.0))))


def hll_x(left: Array, right: Array, gamma: float) -> Array:
    """Return the HLL flux in the x-direction for primitive interface states, with Davis wave-speed estimates."""
    c_left, c_right = fast_speed(left, gamma), fast_speed(right, gamma)
    s_left = np.minimum(left[VX] - c_left, right[VX] - c_right)
    s_right = np.maximum(left[VX] + c_left, right[VX] + c_right)
    f_left, f_right = flux_x(left, gamma), flux_x(right, gamma)
    u_left, u_right = prim_to_cons(left, gamma), prim_to_cons(right, gamma)
    star = (s_right * f_left - s_left * f_right + s_left * s_right * (u_right - u_left)) / (s_right - s_left)
    return np.where(s_left >= 0.0, f_left, np.where(s_right <= 0.0, f_right, star))


def mc_slopes(q: Array, axis: int) -> Array:
    """Return MC-limited undivided slopes along ``axis`` (periodic)."""
    left = q - np.roll(q, 1, axis=axis)
    right = np.roll(q, -1, axis=axis) - q
    slope = np.sign(left) * np.minimum(np.minimum(2.0 * np.abs(left), 2.0 * np.abs(right)), 0.5 * np.abs(left + right))
    return np.where(left * right > 0.0, slope, 0.0)


## Permutation that turns the y-direction into the x-direction of flux_x and back: swap the x and y components.
_SWAP = list(range(9))
_SWAP[VX], _SWAP[VY], _SWAP[BX], _SWAP[BY] = VY, VX, BY, BX


def swap_xy(a: Array) -> Array:
    """Return ``a`` with the x and y components of velocity (or momentum) and field exchanged."""
    return a[_SWAP[: a.shape[0]]]


def face_fluxes(prim: Array, axis: int, face_bn: Array | None, scheme: str, ch: float, gamma: float) -> Array:
    """Return the fluxes through the lower faces of all cells along ``axis`` (0: x-faces, 1: y-faces).

    ``face_bn`` is the face-centred normal field for constrained transport, which replaces the reconstructed normal
    component in both interface states. For GLM, the normal field and psi are first taken from the exact solution of the
    decoupled (B_n, psi) subsystem, as proposed by Dedner et al.
    """
    slopes = mc_slopes(prim, axis + 1)
    left = np.roll(prim + 0.5 * slopes, 1, axis=axis + 1)
    right = prim - 0.5 * slopes
    if axis == 1:
        left, right = swap_xy(left), swap_xy(right)
    if face_bn is not None:
        left[BX] = face_bn
        right[BX] = face_bn
    if scheme == "glm":
        bn_star = 0.5 * (left[BX] + right[BX]) - 0.5 / ch * (right[PSI] - left[PSI])
        psi_star = 0.5 * (left[PSI] + right[PSI]) - 0.5 * ch * (right[BX] - left[BX])
        left[BX], right[BX] = bn_star, bn_star
    flux = hll_x(left, right, gamma)
    if scheme == "glm":
        flux[BX] = psi_star
        flux[PSI] = ch * ch * bn_star
    return swap_xy(flux) if axis == 1 else flux


def ct_weights(mass_flux: Array, rho_left: Array, rho_right: Array, dt: float, dx: float) -> Array:
    """Upwind weight of the face EMF integration, as Athena++'s Hydro::GetWeightForCT: 1 for flow in +direction."""
    v_over_c = 1024.0 * dt * mass_flux / (dx * (rho_left + rho_right))
    return 0.5 + np.maximum(-0.5, np.minimum(0.5, v_over_c))


def corner_emf(fx: Array, fy: Array, prim: Array, scheme: str, dt: float, dx: float, dy: float) -> Array:
    """Return the edge EMF E_z at every corner (i - 1/2, j - 1/2) from the face fluxes."""
    ez_xface = -fx[BY]  ## E_z on x-face (i - 1/2, j)
    ez_yface = fy[BX]  ## E_z on y-face (i, j - 1/2)
    if scheme == "ct-average":
        return 0.25 * (ez_xface + np.roll(ez_xface, 1, axis=1) + ez_yface + np.roll(ez_yface, 1, axis=0))

    def im1(a: Array) -> Array:
        return np.roll(a, 1, axis=0)

    def jm1(a: Array) -> Array:
        return np.roll(a, 1, axis=1)

    ecc = prim[VY] * prim[BX] - prim[VX] * prim[BY]  ## cell-centred E_z
    wx = ct_weights(fx[RHO], im1(prim[RHO]), prim[RHO], dt, dx)
    wy = ct_weights(fy[RHO], jm1(prim[RHO]), prim[RHO], dt, dy)
    de_l2 = (1.0 - jm1(wx)) * (ez_yface - jm1(ecc)) + jm1(wx) * (im1(ez_yface) - im1(jm1(ecc)))
    de_r2 = (1.0 - wx) * (ez_yface - ecc) + wx * (im1(ez_yface) - im1(ecc))
    de_l1 = (1.0 - im1(wy)) * (ez_xface - im1(ecc)) + im1(wy) * (jm1(ez_xface) - im1(jm1(ecc)))
    de_r1 = (1.0 - wy) * (ez_xface - ecc) + wy * (jm1(ez_xface) - jm1(ecc))
    return 0.25 * (de_l1 + de_r1 + de_l2 + de_r2 + im1(ez_yface) + ez_yface + jm1(ez_xface) + ez_xface)


class State:
    """Conserved cell-centred variables plus, for constrained transport, the face-centred in-plane field."""

    def __init__(self, cons: Array, bx: Array | None, by: Array | None) -> None:
        self.cons, self.bx, self.by = cons, bx, by

    def sync_cell_field(self) -> None:
        """For constrained transport: set the cell-centred B_x, B_y to the average of their two faces."""
        if self.bx is not None and self.by is not None:
            self.cons[BX] = 0.5 * (self.bx + np.roll(self.bx, -1, axis=0))
            self.cons[BY] = 0.5 * (self.by + np.roll(self.by, -1, axis=1))


def rates(state: State, scheme: str, ch: float, dt: float, dx: float, dy: float, gamma: float):
    """Return the time derivatives of the conserved variables and, for constrained transport, of the face fields."""
    prim = cons_to_prim(state.cons, gamma)
    ct = scheme.startswith("ct")
    fx = face_fluxes(prim, 0, state.bx if ct else None, scheme, ch, gamma)
    fy = face_fluxes(prim, 1, state.by if ct else None, scheme, ch, gamma)
    dcons = -(np.roll(fx, -1, axis=1) - fx) / dx - (np.roll(fy, -1, axis=2) - fy) / dy
    if not ct:
        return dcons, None, None
    ez = corner_emf(fx, fy, prim, scheme, dt, dx, dy)
    dbx = -(np.roll(ez, -1, axis=1) - ez) / dy
    dby = (np.roll(ez, -1, axis=0) - ez) / dx
    return dcons, dbx, dby


def time_step(cons: Array, dx: float, dy: float, gamma: float, cfl: float) -> float:
    """Return the CFL time step from the fast magnetosonic speed in each direction."""
    prim = cons_to_prim(cons, gamma)
    speed_x = np.abs(prim[VX]) + fast_speed(prim, gamma)
    speed_y = np.abs(prim[VY]) + fast_speed(swap_xy(prim), gamma)
    return float(cfl * min(dx / np.max(speed_x), dy / np.max(speed_y)))


def advance(state: State, scheme: str, dt: float, dx: float, dy: float, gamma: float, cfl: float) -> State:
    """Advance by one SSP-RK2 step."""
    ch = cfl * min(dx, dy) / dt  ## GLM cleaning speed: the largest speed the time step allows
    d1, bx1, by1 = rates(state, scheme, ch, dt, dx, dy, gamma)
    stage = State(state.cons + dt * d1, None, None)
    if bx1 is not None and by1 is not None and state.bx is not None and state.by is not None:
        stage.bx, stage.by = state.bx + dt * bx1, state.by + dt * by1
    stage.sync_cell_field()
    d2, bx2, by2 = rates(stage, scheme, ch, dt, dx, dy, gamma)
    new = State(0.5 * state.cons + 0.5 * (stage.cons + dt * d2), None, None)
    if bx2 is not None and by2 is not None and state.bx is not None and stage.bx is not None:
        assert state.by is not None and stage.by is not None
        new.bx = 0.5 * state.bx + 0.5 * (stage.bx + dt * bx2)
        new.by = 0.5 * state.by + 0.5 * (stage.by + dt * by2)
    new.sync_cell_field()
    if scheme == "glm":
        new.cons[PSI] *= np.exp(-GLM_ALPHA * ch * dt / min(dx, dy))
    return new


def divergence(state: State, dx: float, dy: float) -> Array:
    """Return each scheme's natural discrete divergence of B.

    For constrained transport: the face-centred divergence of every cell. For the cell-centred schemes: the central
    difference of the cell-centred field.
    """
    if state.bx is not None and state.by is not None:
        return (np.roll(state.bx, -1, axis=0) - state.bx) / dx + (np.roll(state.by, -1, axis=1) - state.by) / dy
    bx, by = state.cons[BX], state.cons[BY]
    return (np.roll(bx, -1, axis=0) - np.roll(bx, 1, axis=0)) / (2 * dx) + (
        np.roll(by, -1, axis=1) - np.roll(by, 1, axis=1)
    ) / (2 * dy)


def field_loop(nx: int, ny: int, scheme: str, gamma: float = 5.0 / 3.0) -> tuple[State, float, float]:
    """Return the field-loop advection test of Gardiner & Stone (2005) as set up by Athena++'s ``field_loop`` problem.

    Domain [-1, 1] x [-0.5, 0.5], rho = 1, p = 1, v = (2, 1, 0), and a weak loop of field (A_0 = 1e-3, radius 0.3, plasma
    beta ~ 10^6) from the vector potential A_z = A_0 (R - r). The face fields are differences of A_z between corners, so
    they are divergence-free to round-off; the cell-centred schemes start from the same field averaged to cell centres.
    """
    dx, dy = 2.0 / nx, 1.0 / ny
    xc = -1.0 + np.arange(nx) * dx  ## corner coordinates (i - 1/2)
    yc = -0.5 + np.arange(ny) * dy
    radius = np.sqrt(xc[:, None] ** 2 + yc[None, :] ** 2)
    az = np.where(radius < 0.3, 1.0e-3 * (0.3 - radius), 0.0)
    bx = (np.roll(az, -1, axis=1) - az) / dy
    by = -(np.roll(az, -1, axis=0) - az) / dx
    prim = np.zeros((9 if scheme == "glm" else 8, nx, ny))
    prim[RHO], prim[PRS], prim[VX], prim[VY] = 1.0, 1.0, 2.0, 1.0
    prim[BX] = 0.5 * (bx + np.roll(bx, -1, axis=0))
    prim[BY] = 0.5 * (by + np.roll(by, -1, axis=1))
    if scheme.startswith("ct"):
        return State(prim_to_cons(prim, gamma), bx, by), dx, dy
    return State(prim_to_cons(prim, gamma), None, None), dx, dy
