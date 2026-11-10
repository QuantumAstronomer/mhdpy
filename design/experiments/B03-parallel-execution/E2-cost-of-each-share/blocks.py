# pyright: strict
"""B3E2: option C, blocks with ghost cells of their own, which a pool hands to its threads one at a time."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial

import numpy as np

from common import Array, Setup, rows


class Block:
    """One block: its state with two ghost cells a side, the scratch of its stages, and its four neighbours."""

    def __init__(self, u: Array) -> None:
        ny, nx = u.shape[1] - 4, u.shape[2] - 4
        self.u, self.u1, self.w = u, u.copy(), np.empty_like(u)
        self.fx, self.fy = np.empty((4, ny, nx + 1)), np.empty((4, ny + 1, nx))
        self.below = self.above = self.left = self.right = self


class Blocks:
    """The state as ny by nx blocks, each advanced through a stage by whichever thread of the pool is free."""

    def __init__(self, u: Array, setup: Setup, threads: int, ny: int, nx: int) -> None:
        bounds_y, bounds_x = rows(u.shape[1] - 4, ny), rows(u.shape[2] - 4, nx)
        self.grid = [[Block(u[:, y0:y1 + 4, x0:x1 + 4].copy()) for x0, x1 in bounds_x] for y0, y1 in bounds_y]
        for b, row in enumerate(self.grid):
            for a, block in enumerate(row):
                block.below, block.above = self.grid[b - 1][a], self.grid[(b + 1) % ny][a]
                block.left, block.right = row[a - 1], row[(a + 1) % nx]
        self.blocks = [block for row in self.grid for block in row]
        self.setup = setup
        self.pool = ThreadPoolExecutor(threads)

    def advance(self, block: Block, number: int) -> None:
        """Fill from the neighbours the ghost cells of the array that the stage reads, then run the stage."""
        s, k = self.setup, self.setup.kernels
        ## a stage reads u or u1 and writes the other, so that no neighbour writes what is copied here
        a, below, above, left, right = ((block.u, block.below.u, block.above.u, block.left.u, block.right.u)
                                        if number == 1 else
                                        (block.u1, block.below.u1, block.above.u1, block.left.u1, block.right.u1))
        a[:, :2, 2:-2] = below[:, -4:-2, 2:-2]
        a[:, -2:, 2:-2] = above[:, 2:4, 2:-2]
        a[:, 2:-2, :2] = left[:, 2:-2, -4:-2]
        a[:, 2:-2, -2:] = right[:, 2:-2, 2:4]
        ny4 = a.shape[1]
        k.convert(a, block.w, 0, ny4, s.gamma)
        k.fluxes(block.w, block.fx, block.fy, 2, ny4 - 2, ny4 - 1, s.gamma)
        if number == 1:
            k.first(block.u, block.fx, block.fy, block.u1, 2, ny4 - 2, s.dtdx, s.dtdy)
        else:
            k.second(block.u, block.u1, block.fx, block.fy, 2, ny4 - 2, s.dtdx, s.dtdy)
            if s.substeps:
                k.source(block.u, 2, ny4 - 2, s.substeps, s.rate)

    def step(self) -> None:
        """Advance every block by one step of Heun's method, and by the source where the problem has one."""
        list(self.pool.map(partial(self.advance, number=1), self.blocks))
        list(self.pool.map(partial(self.advance, number=2), self.blocks))

    def interior(self) -> Array:
        return np.concatenate([np.concatenate([b.u[:, 2:-2, 2:-2] for b in row], axis=2) for row in self.grid], axis=1)

    def close(self) -> None:
        self.pool.shutdown()
