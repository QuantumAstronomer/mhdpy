# pyright: strict
"""B2E1: one stage of the step, vectorised in NumPy, with every intermediate array allocated once and reused.

Each operation of vectorised.py is written into a buffer through the argument out, in the same order.
"""

import numpy as np
from numpy.typing import NDArray

type Array = NDArray[np.float64]


def cut(a: Array, axis: int, start: int, stop: int | None) -> Array:
    """Return the slice of an array from start to stop along one axis."""
    index = [slice(None)] * a.ndim
    index[axis] = slice(start, stop)
    return a[tuple(index)]


class Axis:
    """The buffers and fluxes of the faces normal to one axis, 2 for x or 1 for y, of a grid of n by n cells."""

    def __init__(self, n: int, axis: int) -> None:
        self.axis = axis
        cells = (4, n, n + 2) if axis == 2 else (4, n + 2, n)
        faces = (n, n + 1) if axis == 2 else (n + 1, n)
        self.dl, self.dr, self.prod, self.den, self.s = (np.empty(cells) for _ in range(5))
        self.mask = np.empty(cells, dtype=bool)
        self.left, self.right, self.flux = (np.empty((4, *faces)) for _ in range(3))
        self.cl, self.cr, self.bm, self.bp = (np.empty(faces) for _ in range(4))
        self.bpbm, self.el, self.er, self.scale = (np.empty(faces) for _ in range(4))
        self.t1, self.t2, self.t3 = (np.empty(faces) for _ in range(3))

    def fluxes(self, w: Array, gamma: float) -> Array:
        """Return the fluxes on the faces of the interior cells from the primitive variables w."""
        a = self.axis
        w = cut(w, 3 - a, 2, -2)
        n = w.shape[a]
        np.subtract(cut(w, a, 1, n - 1), cut(w, a, 0, n - 2), out=self.dl)
        np.subtract(cut(w, a, 2, n), cut(w, a, 1, n - 1), out=self.dr)
        ## the slopes of van Leer's limiter, zero where the differences differ in sign
        np.multiply(self.dl, self.dr, out=self.prod)
        np.greater(self.prod, 0.0, out=self.mask)
        self.den.fill(1.0)
        np.add(self.dl, self.dr, out=self.den, where=self.mask)
        np.multiply(self.prod, 2.0, out=self.dl)
        self.s.fill(0.0)
        np.divide(self.dl, self.den, out=self.s, where=self.mask)
        wc = cut(w, a, 1, n - 1)
        np.multiply(cut(self.s, a, 0, -1), 0.5, out=self.left)
        np.add(cut(wc, a, 0, -1), self.left, out=self.left)
        np.multiply(cut(self.s, a, 1, None), 0.5, out=self.right)
        np.subtract(cut(wc, a, 1, None), self.right, out=self.right)
        normal, along = (1, 2) if a == 2 else (2, 1)
        self.hlle(self.left[0], self.left[normal], self.left[along], self.left[3],
                  self.right[0], self.right[normal], self.right[along], self.right[3], gamma)
        return self.flux

    def hlle(self, rl: Array, ul: Array, vl: Array, pl: Array, rr: Array, ur: Array, vr: Array, pr: Array,
             gamma: float) -> None:
        """Write the HLLE fluxes into self.flux, in the order of the conserved variables."""
        cl, cr, bm, bp = self.cl, self.cr, self.bm, self.bp
        bpbm, el, er, scale = self.bpbm, self.el, self.er, self.scale
        t1, t2, t3 = self.t1, self.t2, self.t3
        normal, along = (1, 2) if self.axis == 2 else (2, 1)
        fd, fn, ft, fe = self.flux[0], self.flux[normal], self.flux[along], self.flux[3]
        np.multiply(pl, gamma, out=cl)
        np.divide(cl, rl, out=cl)
        np.sqrt(cl, out=cl)
        np.multiply(pr, gamma, out=cr)
        np.divide(cr, rr, out=cr)
        np.sqrt(cr, out=cr)
        np.subtract(ul, cl, out=t1)
        np.subtract(ur, cr, out=t2)
        np.minimum(t1, t2, out=bm)
        np.minimum(bm, 0.0, out=bm)
        np.add(ul, cl, out=t1)
        np.add(ur, cr, out=t2)
        np.maximum(t1, t2, out=bp)
        np.maximum(bp, 0.0, out=bp)
        for e, r, un, ut, p in ((el, rl, ul, vl, pl), (er, rr, ur, vr, pr)):
            np.divide(p, gamma - 1.0, out=e)
            np.multiply(un, un, out=t1)
            np.multiply(ut, ut, out=t2)
            np.add(t1, t2, out=t1)
            np.multiply(r, 0.5, out=t2)
            np.multiply(t2, t1, out=t2)
            np.add(e, t2, out=e)
        np.subtract(bp, bm, out=scale)
        np.divide(1.0, scale, out=scale)
        np.multiply(bp, bm, out=bpbm)
        ## the flux of mass
        np.multiply(rl, ul, out=t1)
        np.multiply(bp, t1, out=t1)
        np.multiply(rr, ur, out=t2)
        np.multiply(bm, t2, out=t2)
        np.subtract(t1, t2, out=t1)
        np.subtract(rr, rl, out=t2)
        np.multiply(bpbm, t2, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(t1, scale, out=fd)
        ## the flux of the normal momentum
        np.multiply(rl, ul, out=t1)
        np.multiply(t1, ul, out=t1)
        np.add(t1, pl, out=t1)
        np.multiply(bp, t1, out=t1)
        np.multiply(rr, ur, out=t2)
        np.multiply(t2, ur, out=t2)
        np.add(t2, pr, out=t2)
        np.multiply(bm, t2, out=t2)
        np.subtract(t1, t2, out=t1)
        np.multiply(rr, ur, out=t2)
        np.multiply(rl, ul, out=t3)
        np.subtract(t2, t3, out=t2)
        np.multiply(bpbm, t2, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(t1, scale, out=fn)
        ## the flux of the transverse momentum
        np.multiply(rl, ul, out=t1)
        np.multiply(t1, vl, out=t1)
        np.multiply(bp, t1, out=t1)
        np.multiply(rr, ur, out=t2)
        np.multiply(t2, vr, out=t2)
        np.multiply(bm, t2, out=t2)
        np.subtract(t1, t2, out=t1)
        np.multiply(rr, vr, out=t2)
        np.multiply(rl, vl, out=t3)
        np.subtract(t2, t3, out=t2)
        np.multiply(bpbm, t2, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(t1, scale, out=ft)
        ## the flux of energy
        np.add(el, pl, out=t1)
        np.multiply(t1, ul, out=t1)
        np.multiply(bp, t1, out=t1)
        np.add(er, pr, out=t2)
        np.multiply(t2, ur, out=t2)
        np.multiply(bm, t2, out=t2)
        np.subtract(t1, t2, out=t1)
        np.subtract(er, el, out=t2)
        np.multiply(bpbm, t2, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(t1, scale, out=fe)


class Stage:
    """One stage of the step on a grid of n by n cells, its buffers allocated when it is made."""

    def __init__(self, n: int, gamma: float, dtdx: float, dtdy: float) -> None:
        self.gamma, self.dtdx, self.dtdy = gamma, dtdx, dtdy
        self.w = np.empty((4, n + 4, n + 4))
        self.c1, self.c2 = np.empty((n + 4, n + 4)), np.empty((n + 4, n + 4))
        self.x, self.y = Axis(n, 2), Axis(n, 1)
        self.ex, self.ey = np.empty((4, n, n)), np.empty((4, n, n))

    def __call__(self, u: Array, du: Array) -> None:
        """Write into du the change of the conserved variables in the interior over one stage."""
        w, c1, c2 = self.w, self.c1, self.c2
        np.copyto(w[0], u[0])
        np.divide(u[1], u[0], out=w[1])
        np.divide(u[2], u[0], out=w[2])
        np.multiply(w[1], w[1], out=c1)
        np.multiply(w[2], w[2], out=c2)
        np.add(c1, c2, out=c1)
        np.multiply(u[0], 0.5, out=c2)
        np.multiply(c2, c1, out=c2)
        np.subtract(u[3], c2, out=w[3])
        np.multiply(w[3], self.gamma - 1.0, out=w[3])
        fx = self.x.fluxes(w, self.gamma)
        fy = self.y.fluxes(w, self.gamma)
        np.subtract(fx[:, :, 1:], fx[:, :, :-1], out=self.ex)
        np.multiply(self.ex, -self.dtdx, out=self.ex)
        np.subtract(fy[:, 1:, :], fy[:, :-1, :], out=self.ey)
        np.multiply(self.ey, self.dtdy, out=self.ey)
        np.subtract(self.ex, self.ey, out=du[:, 2:-2, 2:-2])
