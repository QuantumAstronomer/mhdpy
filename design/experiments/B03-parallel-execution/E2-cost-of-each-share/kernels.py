# pyright: strict
"""B3E2: the stage of B2E1 split into kernels over a range of rows, each run without the GIL once compiled.

The rows are counted in the array, ghost rows included, so that a state of ny by nx cells has ny + 4 rows of nx + 4
cells. The arrays are annotated by strings, as in B2E1, and Cython takes the types from kernels.pxd beside this file.
"""

import cython  # pyright: ignore[reportMissingTypeStubs]
import numpy as np


def limit(dl: float, dr: float) -> float:
    """Return the slope of van Leer's limiter from the differences to the left and right."""
    prod = dl * dr
    if prod > 0.0:
        return 2.0 * prod / (dl + dr)
    return 0.0


def face(wm2: float, wm1: float, w0: float, wp1: float) -> tuple[float, float]:
    """Return the states left and right of the face between the cells of wm1 and w0."""
    left = wm1 + 0.5 * limit(wm1 - wm2, w0 - wm1)
    right = w0 - 0.5 * limit(w0 - wm1, wp1 - w0)
    return left, right


def hlle(rl: float, ul: float, vl: float, pl: float, rr: float, ur: float, vr: float, pr: float,
         gamma: float) -> tuple[float, float, float, float]:
    """Return the HLLE fluxes of mass, normal and transverse momentum and energy, ul and ur normal."""
    cl = (gamma * pl / rl) ** 0.5
    cr = (gamma * pr / rr) ** 0.5
    bm = min(min(ul - cl, ur - cr), 0.0)
    bp = max(max(ul + cl, ur + cr), 0.0)
    el = pl / (gamma - 1.0) + 0.5 * rl * (ul * ul + vl * vl)
    er = pr / (gamma - 1.0) + 0.5 * rr * (ur * ur + vr * vr)
    scale = 1.0 / (bp - bm)
    fd = (bp * (rl * ul) - bm * (rr * ur) + bp * bm * (rr - rl)) * scale
    fn = (bp * (rl * ul * ul + pl) - bm * (rr * ur * ur + pr) + bp * bm * (rr * ur - rl * ul)) * scale
    ft = (bp * (rl * ul * vl) - bm * (rr * ur * vr) + bp * bm * (rr * vr - rl * vl)) * scale
    fe = (bp * ((el + pl) * ul) - bm * ((er + pr) * ur) + bp * bm * (er - el)) * scale
    return fd, fn, ft, fe


def convert(u: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
            w: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
            j0: int, j1: int, gamma: float) -> None:
    """Write into w the primitive variables of the rows j0 to j1 - 1 of u."""
    nx4 = u.shape[2]
    with cython.nogil:
        for j in range(j0, j1):
            for i in range(nx4):
                rho = u[0, j, i]
                vx = u[1, j, i] / rho
                vy = u[2, j, i] / rho
                w[0, j, i] = rho
                w[1, j, i] = vx
                w[2, j, i] = vy
                w[3, j, i] = (gamma - 1.0) * (u[3, j, i] - 0.5 * rho * (vx * vx + vy * vy))


def fluxes(w: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
           fx: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
           fy: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
           j0: int, j1: int, f1: int, gamma: float) -> None:
    """Write the fluxes along x of the rows j0 to j1 - 1, and along y on the faces below the rows j0 to f1 - 1."""
    nx4 = w.shape[2]
    with cython.nogil:
        ## the faces normal to x, between the cells i - 1 and i of each row
        for j in range(j0, j1):
            for i in range(2, nx4 - 1):
                rl, rr = face(w[0, j, i - 2], w[0, j, i - 1], w[0, j, i], w[0, j, i + 1])
                ul, ur = face(w[1, j, i - 2], w[1, j, i - 1], w[1, j, i], w[1, j, i + 1])
                vl, vr = face(w[2, j, i - 2], w[2, j, i - 1], w[2, j, i], w[2, j, i + 1])
                pl, pr = face(w[3, j, i - 2], w[3, j, i - 1], w[3, j, i], w[3, j, i + 1])
                fd, fn, ft, fe = hlle(rl, ul, vl, pl, rr, ur, vr, pr, gamma)
                fx[0, j - 2, i - 2] = fd
                fx[1, j - 2, i - 2] = fn
                fx[2, j - 2, i - 2] = ft
                fx[3, j - 2, i - 2] = fe
        ## the faces normal to y, between the rows j - 1 and j of the interior columns
        for j in range(j0, f1):
            for i in range(2, nx4 - 2):
                rl, rr = face(w[0, j - 2, i], w[0, j - 1, i], w[0, j, i], w[0, j + 1, i])
                ul, ur = face(w[1, j - 2, i], w[1, j - 1, i], w[1, j, i], w[1, j + 1, i])
                vl, vr = face(w[2, j - 2, i], w[2, j - 1, i], w[2, j, i], w[2, j + 1, i])
                pl, pr = face(w[3, j - 2, i], w[3, j - 1, i], w[3, j, i], w[3, j + 1, i])
                fd, fn, ft, fe = hlle(rl, vl, ul, pl, rr, vr, ur, pr, gamma)
                fy[0, j - 2, i - 2] = fd
                fy[1, j - 2, i - 2] = ft
                fy[2, j - 2, i - 2] = fn
                fy[3, j - 2, i - 2] = fe


def first(u: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
          fx: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
          fy: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
          u1: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
          j0: int, j1: int, dtdx: float, dtdy: float) -> None:
    """Write into u1 the rows j0 to j1 - 1 of u advanced by the first stage of Heun's method."""
    nx4 = u.shape[2]
    with cython.nogil:
        for k in range(4):
            for j in range(j0, j1):
                for i in range(2, nx4 - 2):
                    u1[k, j, i] = u[k, j, i] + (-dtdx * (fx[k, j - 2, i - 1] - fx[k, j - 2, i - 2])
                                                - dtdy * (fy[k, j - 1, i - 2] - fy[k, j - 2, i - 2]))


def second(u: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
           u1: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
           fx: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
           fy: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
           j0: int, j1: int, dtdx: float, dtdy: float) -> None:
    """Average the rows j0 to j1 - 1 of u with those of u1 advanced once more, as B2E1 orders the operations."""
    nx4 = u.shape[2]
    with cython.nogil:
        for k in range(4):
            for j in range(j0, j1):
                for i in range(2, nx4 - 2):
                    t = u1[k, j, i] + (-dtdx * (fx[k, j - 2, i - 1] - fx[k, j - 2, i - 2])
                                       - dtdy * (fy[k, j - 1, i - 2] - fy[k, j - 2, i - 2]))
                    u[k, j, i] = (u[k, j, i] + t) * 0.5


def source(u: "np.ndarray[tuple[int, int, int], np.dtype[np.float64]]",
           j0: int, j1: int, n: int, c: float) -> None:
    """Take n substeps of de/dt = -c e^(1/2) in every interior cell of the rows j0 to j1 - 1 denser than 1.5."""
    nx4 = u.shape[2]
    with cython.nogil:
        for j in range(j0, j1):
            for i in range(2, nx4 - 2):
                if u[0, j, i] > 1.5:
                    e = u[3, j, i]
                    for _ in range(n):
                        e = e - c * e ** 0.5
                    u[3, j, i] = e
