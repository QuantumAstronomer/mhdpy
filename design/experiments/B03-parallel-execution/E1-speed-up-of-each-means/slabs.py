# pyright: strict
"""B3E1: the domain cut into slabs of whole rows, each with ghost cells of its own, and Heun's method on one slab."""

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

type Array = NDArray[np.float64]
type Stage = Callable[[Array, Array, Array, Array, Array, float, float, float], None]


def rows(n: int, p: int) -> list[tuple[int, int]]:
    """Return the first row and the row after the last of each of p slabs of n rows, as equal as the rows allow."""
    edges = [n * k // p for k in range(p + 1)]
    return list(zip(edges[:-1], edges[1:]))


class Slab:
    """One slab: its state and the scratch arrays of its stage, advanced through the two stages of Heun's method."""

    def __init__(self, u: Array, stage: Stage, gamma: float, dtdx: float, dtdy: float) -> None:
        ny, nx = u.shape[1] - 4, u.shape[2] - 4
        self.u = u
        self.u1 = np.empty_like(u)
        self.du = np.zeros_like(u)
        self.w = np.empty_like(u)
        self.fx = np.empty((4, ny, nx + 1))
        self.fy = np.empty((4, ny + 1, nx))
        self.stage = stage
        self.gamma, self.dtdx, self.dtdy = gamma, dtdx, dtdy

    def change(self, u: Array) -> None:
        """Fill the ghost columns of u from its own interior, periodically, and write its change over a stage to du."""
        u[:, :, :2] = u[:, :, -4:-2]
        u[:, :, -2:] = u[:, :, 2:4]
        self.stage(u, self.w, self.fx, self.fy, self.du, self.gamma, self.dtdx, self.dtdy)

    def first(self) -> None:
        """Advance u by the first stage into u1, once the ghost rows of u are filled."""
        self.change(self.u)
        np.add(self.u, self.du, out=self.u1)

    def second(self) -> None:
        """Average u with u1 advanced once more, once the ghost rows of u1 are filled."""
        self.change(self.u1)
        np.add(self.u1, self.du, out=self.u1)
        np.add(self.u, self.u1, out=self.u)
        np.multiply(self.u, 0.5, out=self.u)
