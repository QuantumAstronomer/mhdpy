# pyright: strict
"""B6E1: the stage of vectorised.py written apart from the loop, with the limiter, the pressure and the HLLE fluxes
in other forms of the same formulas."""

import numpy as np
from numpy.typing import NDArray

type Array = NDArray[np.float64]


def cut(a: Array, axis: int, start: int, stop: int | None) -> Array:
    """Return the slice of an array from start to stop along one axis."""
    index = [slice(None)] * a.ndim
    index[axis] = slice(start, stop)
    return a[tuple(index)]


def primitive(u: Array, gamma: float) -> Array:
    """Return the density, velocities and pressure, the pressure from the momenta."""
    rho = u[0]
    p = (gamma - 1.0) * (u[3] - (u[1] * u[1] + u[2] * u[2]) / (2.0 * rho))
    return np.stack((rho, u[1] / rho, u[2] / rho, p))


def limited(dl: Array, dr: Array) -> Array:
    """Return the slopes of van Leer's limiter in the form (dl |dr| + |dl| dr) / (|dl| + |dr|)."""
    num = dl * np.abs(dr) + np.abs(dl) * dr
    den = np.abs(dl) + np.abs(dr)
    ## zero where both differences vanish, as the numerator then does
    return np.divide(num, den, out=np.zeros_like(num), where=den > 0.0)


def hlle(rl: Array, ul: Array, vl: Array, pl: Array, rr: Array, ur: Array, vr: Array, pr: Array,
         gamma: float) -> tuple[Array, Array, Array, Array]:
    """Return the HLLE fluxes of mass, normal and transverse momentum and energy, divided by the spread of speeds."""
    cl = (gamma * pl / rl) ** 0.5
    cr = (gamma * pr / rr) ** 0.5
    bm = np.minimum(np.minimum(ul - cl, ur - cr), 0.0)
    bp = np.maximum(np.maximum(ul + cl, ur + cr), 0.0)
    el = pl / (gamma - 1.0) + 0.5 * rl * (ul * ul + vl * vl)
    er = pr / (gamma - 1.0) + 0.5 * rr * (ur * ur + vr * vr)
    spread = bp - bm
    fd = (bp * (rl * ul) - bm * (rr * ur) + bp * bm * (rr - rl)) / spread
    fn = (bp * (rl * ul * ul + pl) - bm * (rr * ur * ur + pr) + bp * bm * (rr * ur - rl * ul)) / spread
    ft = (bp * (rl * ul * vl) - bm * (rr * ur * vr) + bp * bm * (rr * vr - rl * vl)) / spread
    fe = (bp * ((el + pl) * ul) - bm * ((er + pr) * ur) + bp * bm * (er - el)) / spread
    return fd, fn, ft, fe


def fluxes(w: Array, gamma: float, axis: int) -> Array:
    """Return the fluxes on the faces normal to an axis, 2 for x or 1 for y, of the interior cells."""
    w = cut(w, 3 - axis, 2, -2)
    n = w.shape[axis]
    dl = cut(w, axis, 1, n - 1) - cut(w, axis, 0, n - 2)
    dr = cut(w, axis, 2, n) - cut(w, axis, 1, n - 1)
    s = limited(dl, dr)
    ## the states on both sides of the faces between the cells 1 to n - 2
    wc = cut(w, axis, 1, n - 1)
    left = cut(wc, axis, 0, -1) + 0.5 * cut(s, axis, 0, -1)
    right = cut(wc, axis, 1, None) - 0.5 * cut(s, axis, 1, None)
    normal, along = (1, 2) if axis == 2 else (2, 1)
    fd, fn, ft, fe = hlle(left[0], left[normal], left[along], left[3],
                          right[0], right[normal], right[along], right[3], gamma)
    return np.stack((fd, fn, ft, fe) if axis == 2 else (fd, ft, fn, fe))


def stage(u: Array, du: Array, gamma: float, dtdx: float, dtdy: float) -> None:
    """Write into du the change of the conserved variables in the interior over one stage."""
    w = primitive(u, gamma)
    fx = fluxes(w, gamma, 2)
    fy = fluxes(w, gamma, 1)
    du[:, 2:-2, 2:-2] = -dtdx * (fx[:, :, 1:] - fx[:, :, :-1]) - dtdy * (fy[:, 1:, :] - fy[:, :-1, :])
