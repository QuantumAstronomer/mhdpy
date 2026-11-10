# pyright: strict
"""B3E2: option B, the one array, each thread holding fixed rows through every kernel and waiting between them."""

import threading

from common import Array, Setup, Whole, fill_ghosts


class Parts:
    """The state as one array, each thread advancing its part through the kernels of a stage, waiting at barriers."""

    def __init__(self, u: Array, setup: Setup, threads: int) -> None:
        self.whole = Whole(u, threads)
        self.setup = setup
        ## a timeout turns a thread that fails into an error of the others rather than a run that hangs
        self.outer = threading.Barrier(threads + 1, timeout=120)
        self.inner = threading.Barrier(threads, timeout=120)
        self.number = 0  ## the stage that the threads run next, 1 or 2, or 0 to stop
        self.threads = [threading.Thread(target=self.work, args=(p,)) for p in range(threads)]
        for thread in self.threads:
            thread.start()

    def work(self, p: int) -> None:
        """Run the stages of part p as the main thread starts them, waiting for the other parts between kernels."""
        s, k, x = self.setup, self.setup.kernels, self.whole
        (c0, c1), (j0, j1, f1), (r0, r1) = x.converted[p], x.faced[p], x.parts[p]
        while True:
            self.outer.wait()
            if self.number == 0:
                return
            k.convert(x.u if self.number == 1 else x.u1, x.w, c0, c1, s.gamma)
            self.inner.wait()
            k.fluxes(x.w, x.fx, x.fy, j0, j1, f1, s.gamma)
            self.inner.wait()
            if self.number == 1:
                k.first(x.u, x.fx, x.fy, x.u1, r0, r1, s.dtdx, s.dtdy)
            else:
                k.second(x.u, x.u1, x.fx, x.fy, r0, r1, s.dtdx, s.dtdy)
                if s.substeps:
                    k.source(x.u, r0, r1, s.substeps, s.rate)
            self.outer.wait()

    def stage(self, number: int) -> None:
        """Fill the ghost cells of the array that the stage reads, then start the stage and wait for its end."""
        fill_ghosts(self.whole.u if number == 1 else self.whole.u1)
        self.number = number
        self.outer.wait()
        self.outer.wait()

    def step(self) -> None:
        """Advance the state by one step of Heun's method, and by the source where the problem has one."""
        self.stage(1)
        self.stage(2)

    def interior(self) -> Array:
        return self.whole.interior()

    def close(self) -> None:
        self.number = 0
        self.outer.wait()
        for thread in self.threads:
            thread.join()
