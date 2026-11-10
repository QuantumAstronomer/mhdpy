# pyright: strict
"""B3E2: option A, the one array, every call of a kernel sharing its rows among the threads of a pool."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from common import Array, Setup, Whole, fill_ghosts


def call(task: Callable[[], None]) -> None:
    """Run one task."""
    task()


class Loops:
    """The state as one array, each kernel called on the rows of every part at once and awaited before the next."""

    def __init__(self, u: Array, setup: Setup, threads: int) -> None:
        self.whole = Whole(u, threads)
        self.setup = setup
        self.pool = ThreadPoolExecutor(threads)

    def share(self, tasks: list[Callable[[], None]]) -> None:
        """Run the tasks on the threads of the pool and wait for all of them."""
        list(self.pool.map(call, tasks))

    def stage(self, a: Array, update: Callable[[int, int], None]) -> None:
        """Advance one stage that reads the array a, its kernels in turn."""
        s, k, x = self.setup, self.setup.kernels, self.whole
        fill_ghosts(a)
        self.share([partial(k.convert, a, x.w, j0, j1, s.gamma) for j0, j1 in x.converted])
        self.share([partial(k.fluxes, x.w, x.fx, x.fy, j0, j1, f1, s.gamma) for j0, j1, f1 in x.faced])
        self.share([partial(update, j0, j1) for j0, j1 in x.parts])

    def step(self) -> None:
        """Advance the state by one step of Heun's method, and by the source where the problem has one."""
        s, k, x = self.setup, self.setup.kernels, self.whole
        self.stage(x.u, lambda j0, j1: k.first(x.u, x.fx, x.fy, x.u1, j0, j1, s.dtdx, s.dtdy))
        self.stage(x.u1, lambda j0, j1: k.second(x.u, x.u1, x.fx, x.fy, j0, j1, s.dtdx, s.dtdy))
        if s.substeps:
            self.share([partial(k.source, x.u, j0, j1, s.substeps, s.rate) for j0, j1 in x.parts])

    def interior(self) -> Array:
        return self.whole.interior()

    def close(self) -> None:
        self.pool.shutdown()
