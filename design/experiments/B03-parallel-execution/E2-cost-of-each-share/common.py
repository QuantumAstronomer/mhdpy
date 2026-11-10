# pyright: strict
"""B3E2: what the three shares have in common: the kernels, the parameters of the step, and the state as one array."""

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

type Array = NDArray[np.float64]


class Kernels(Protocol):
    """The compiled kernels of kernels.py, each over the rows j0 to j1 - 1, counted with the ghost rows."""

    def convert(self, u: Array, w: Array, j0: int, j1: int, gamma: float, /) -> None: ...

    def fluxes(self, w: Array, fx: Array, fy: Array, j0: int, j1: int, f1: int, gamma: float, /) -> None: ...

    def first(self, u: Array, fx: Array, fy: Array, u1: Array, j0: int, j1: int, dtdx: float, dtdy: float,
              /) -> None: ...

    def second(self, u: Array, u1: Array, fx: Array, fy: Array, j0: int, j1: int, dtdx: float, dtdy: float,
               /) -> None: ...

    def source(self, u: Array, j0: int, j1: int, n: int, c: float, /) -> None: ...


class Share(Protocol):
    """A share of the step among threads, which advances the state by one step and returns its interior."""

    def step(self) -> None: ...

    def interior(self) -> Array: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class Setup:
    """The kernels and the parameters of the step, with the substeps of the source, none on the uniform problem."""

    kernels: Kernels
    gamma: float
    dtdx: float
    dtdy: float
    substeps: int
    rate: float


def rows(n: int, p: int) -> list[tuple[int, int]]:
    """Return the first row and the row after the last of each of p parts of n rows, as equal as the rows allow."""
    edges = [n * k // p for k in range(p + 1)]
    return list(zip(edges[:-1], edges[1:]))


def fill_ghosts(u: Array) -> None:
    """Fill the two ghost cells on each side from the periodic interior, rows first and columns after."""
    u[:, :2, :] = u[:, -4:-2, :]
    u[:, -2:, :] = u[:, 2:4, :]
    u[:, :, :2] = u[:, :, -4:-2]
    u[:, :, -2:] = u[:, :, 2:4]


class Whole:
    """The state as one array with the scratch of its stages, and for each of p parts the rows of each kernel."""

    def __init__(self, u: Array, p: int) -> None:
        ny, nx = u.shape[1] - 4, u.shape[2] - 4
        self.u, self.u1, self.w = u, u.copy(), np.empty_like(u)
        self.fx, self.fy = np.empty((4, ny, nx + 1)), np.empty((4, ny + 1, nx))
        self.parts = [(lo + 2, hi + 2) for lo, hi in rows(ny, p)]
        ## the first part also converts the ghost rows below the domain, and the last those above it and its top faces
        self.converted = [(j0 - 2 if k == 0 else j0, j1 + 2 if k == p - 1 else j1)
                          for k, (j0, j1) in enumerate(self.parts)]
        self.faced = [(j0, j1, j1 + 1 if k == p - 1 else j1) for k, (j0, j1) in enumerate(self.parts)]

    def interior(self) -> Array:
        """Return a copy of the interior of the state."""
        return self.u[:, 2:-2, 2:-2].copy()
