# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E09.1: how should a step be orchestrated over blocks and workers?

Full SSP-RK2 steps on the thesis grid (4000 x 1000, periodic, blocks of 50^2 and 25^2 in Morton order, D07.4) with the
kernels of ``E09.1a-kernels.py``, the data layout of D06 and ghost cells filled through an exchange plan by the compiled
copy kernel, one call per worker and stage (D08). Four ways of orchestrating the same work are compared:

- **per-block calls, persistent team:** a fixed team of worker threads, each owning a contiguous range of blocks, with a
  barrier after each stage; the kernels are called once per block (as in E05-E08);
- **ranged calls, persistent team:** the same team, but each worker calls the kernels once per stage for its whole range
  of blocks, which they loop over in compiled code without the GIL;
- **ranged calls, thread pool:** the main thread runs each stage as a set of tasks on a ``ThreadPoolExecutor``, one per
  worker, and waits for all of them before the next stage; no persistent team, no barriers of its own;
- **barriers only:** the persistent team synchronising twice per step without doing any work, which measures the cost
  of the synchronisation itself.

Every configuration that computes is checked bit for bit against a single-block serial reference. The module also
provides the blocks, plans and teams that ``E09.2-load-balance.py`` uses. Not meant to be run by hand:
``E09.1d-run.py`` runs it natively and in a Linux container with both interpreters, as
``uv run --locked --python <python> --script E09.1b-orchestration.py <label> <output.json>``.
"""

import concurrent.futures
import importlib.util
import json
import math
import os
import platform
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
G = 2
GAMMA = 1.4
NVAR = 5
CHECK_STEPS = 2
MIN_TIME = 1.0
REPEATS = 3
GRID = (4000, 1000)
BLOCK_SHAPES = [(50, 50), (25, 25)]
MODES = ["per-block calls, persistent team", "ranged calls, persistent team", "ranged calls, thread pool"]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path):
    (workdir / "kernels.py").write_text((HERE / "E09.1a-kernels.py").read_text())
    subprocess.run([sys.executable, "-m", "cython", "-3", "kernels.py", "-o", "kernels.c"], cwd=workdir, check=True,
                   capture_output=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"kernels{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", "kernels.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load("kernels", ext)


def initial_state(nx: int, ny: int) -> np.ndarray:
    """Smooth periodic state [var, y, x] on a domain of nx / ny by 1 (interior cells only)."""
    dx = 1.0 / ny
    x = (np.arange(nx) + 0.5) * dx
    y = (np.arange(ny) + 0.5) * dx
    yy, xx = np.meshgrid(y, x, indexing="ij")
    s = 2 * np.pi
    rho = 1.0 + 0.2 * np.sin(s * xx) * np.sin(s * yy)
    vx = 0.5 + 0.1 * np.sin(s * yy)
    vy = 0.3 * np.cos(s * xx)
    vz = 0.1 * np.sin(s * (xx - yy))
    pres = 1.0 + 0.1 * np.cos(s * (xx + yy))
    return np.array([rho, rho * vx, rho * vy, rho * vz,
                     pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy + vz * vz)])


def reference(kernel, nx: int, ny: int, steps: int) -> np.ndarray:
    """Single block, one thread, periodic ghost cells filled with NumPy."""
    dx, dt = 1.0 / ny, 0.2 / ny
    u = np.zeros((NVAR, 1, ny + 2 * G, nx + 2 * G))
    u[:, 0, G:-G, G:-G] = initial_state(nx, ny)
    stage, new, w = np.zeros_like(u), np.zeros_like(u), np.empty_like(u)
    fx, fy, fz = np.empty((NVAR, 1, ny, nx + 1)), np.empty((NVAR, 1, ny + 1, nx)), np.empty((NVAR, 2, ny, nx))
    du = np.empty((NVAR, 1, ny, nx))

    def fill(a):
        a[:, :, :G, :] = a[:, :, -2 * G : -G, :]
        a[:, :, -G:, :] = a[:, :, G : 2 * G, :]
        a[:, :, :, :G] = a[:, :, :, -2 * G : -G]
        a[:, :, :, -G:] = a[:, :, :, G : 2 * G]

    for _ in range(steps):
        fill(u)
        kernel.rhs(u, w, fx, fy, fz, du, nx, ny, 1, G, dx)
        kernel.first_stage(u, du, dt, stage, 0, G, G)
        fill(stage)
        kernel.rhs(stage, w, fx, fy, fz, du, nx, ny, 1, G, dx)
        kernel.second_stage(u, stage, du, dt, new, 0, G, G)
        u, new = new, u
    return u[:, 0, G:-G, G:-G].copy()


def morton(cx: int, cy: int) -> int:
    """Interleave the bits of the block coordinates (x in the even bits)."""
    code = 0
    for bit in range(16):
        code |= ((cx >> bit) & 1) << (2 * bit) | ((cy >> bit) & 1) << (2 * bit + 1)
    return code


class Blocks:
    """Blocks of bx x by cells tiling a periodic nx x ny grid, stored in Morton order, with their exchange plan."""

    def __init__(self, nx: int, ny: int, bx: int, by: int) -> None:
        self.nx, self.ny, self.bx, self.by = nx, ny, bx, by
        nbx, nby = nx // bx, ny // by
        self.locations = sorted(((ci, cj) for cj in range(nby) for ci in range(nbx)), key=lambda c: morton(*c))
        index = {loc: b for b, loc in enumerate(self.locations)}
        self.count = len(self.locations)
        self.shape = (self.count, NVAR, 1, by + 2 * G, bx + 2 * G)
        dst_x = {-1: (0, G), 0: (G, bx), 1: (G + bx, G)}
        src_x = {-1: (bx, G), 0: (G, bx), 1: (G, G)}
        dst_y = {-1: (0, G), 0: (G, by), 1: (G + by, G)}
        src_y = {-1: (by, G), 0: (G, by), 1: (G, G)}
        rows, self.rows = [], []
        for b, (ci, cj) in enumerate(self.locations):
            start = len(rows)
            for oj in (-1, 0, 1):
                for oi in (-1, 0, 1):
                    if oi == oj == 0:
                        continue
                    src = index[((ci + oi) % nbx, (cj + oj) % nby)]
                    (dj, nj), (di, ni) = dst_y[oj], dst_x[oi]
                    rows.append((b, src, 0, dj, di, 0, src_y[oj][0], src_x[oi][0], 1, nj, ni))
            self.rows.append((start, len(rows)))
        self.plan = np.array(rows, dtype=np.intp)

    def interior(self, b: int):
        ci, cj = self.locations[b]
        return (slice(None), slice(cj * self.by, (cj + 1) * self.by), slice(ci * self.bx, (ci + 1) * self.bx))

    def scatter(self, state: np.ndarray, pack: np.ndarray) -> None:
        for b in range(self.count):
            pack[b, :, 0, G:-G, G:-G] = state[self.interior(b)]

    def gather(self, pack: np.ndarray) -> np.ndarray:
        state = np.empty((NVAR, self.ny, self.nx))
        for b in range(self.count):
            state[self.interior(b)] = pack[b, :, 0, G:-G, G:-G]
        return state


def equal_ranges(count: int, workers: int) -> list[tuple[int, int]]:
    return [(r * count // workers, (r + 1) * count // workers) for r in range(workers)]


class Worker:
    """What one worker needs: its scratch arrays and the kernels, for per-block or ranged calls."""

    def __init__(self, blocks: Blocks, kernel, buffers: np.ndarray, costs: np.ndarray) -> None:
        bx, by = blocks.bx, blocks.by
        self.blocks, self.kernel, self.buffers, self.costs = blocks, kernel, buffers, costs
        self.w = np.empty((NVAR, 1, by + 2 * G, bx + 2 * G))
        self.fx, self.fy = np.empty((NVAR, 1, by, bx + 1)), np.empty((NVAR, 1, by + 1, bx))
        self.fz, self.du = np.empty((NVAR, 2, by, bx)), np.empty((NVAR, 1, by, bx))
        self.scratch = np.empty((1, by, bx))
        self.dx, self.dt = 1.0 / blocks.ny, 0.2 / blocks.ny

    def stage(self, which: int, a: int, s: int, n: int, b0: int, b1: int, ranged: bool) -> None:
        """Fill the ghost cells of blocks b0 .. b1 - 1 and compute stage ``which`` (1 or 2) for them."""
        k, blocks, pack = self.kernel, self.blocks, self.buffers
        source = pack[a] if which == 1 else pack[s]
        k.copy_regions(source, blocks.plan, blocks.rows[b0][0], blocks.rows[b1 - 1][1])
        args = (self.w, self.fx, self.fy, self.fz, self.du)
        if ranged:
            if which == 1:
                k.stage_one(pack[a], pack[s], *args, self.scratch, self.costs, b0, b1, blocks.bx, blocks.by, 1, G,
                            self.dx, self.dt, 0, G, G)
            else:
                k.stage_two(pack[a], pack[s], pack[n], *args, self.scratch, self.costs, b0, b1, blocks.bx, blocks.by,
                            1, G, self.dx, self.dt, 0, G, G)
            return
        for b in range(b0, b1):
            if which == 1:
                k.rhs(pack[a, b], *args, blocks.bx, blocks.by, 1, G, self.dx)
                if self.costs[b] > 0:
                    k.busy(pack[a, b], self.scratch, self.costs[b])
                k.first_stage(pack[a, b], self.du, self.dt, pack[s, b], 0, G, G)
            else:
                k.rhs(pack[s, b], *args, blocks.bx, blocks.by, 1, G, self.dx)
                if self.costs[b] > 0:
                    k.busy(pack[s, b], self.scratch, self.costs[b])
                k.second_stage(pack[a, b], pack[s, b], self.du, self.dt, pack[n, b], 0, G, G)


class Command:
    value = 0


class Team:
    """A persistent team of worker threads with barriers between stages.

    ``schedule`` is a list of (b0, b1) per worker (static), or the string "dynamic", in which case workers claim chunks
    of ``chunk`` blocks from a shared counter, stage by stage.
    """

    def __init__(self, workers: int, blocks: Blocks, kernel, mode: str, schedule, costs=None, chunk: int = 4) -> None:
        self.blocks, self.mode, self.schedule, self.chunk = blocks, mode, schedule, chunk
        self.buffers = np.zeros((3, *blocks.shape))
        self.costs = np.zeros(blocks.count, dtype=np.intp) if costs is None else costs
        self.workers = workers
        self.start, self.done = threading.Barrier(workers + 1), threading.Barrier(workers + 1)
        self.step_barrier, self.command = threading.Barrier(workers), Command()
        self.lock, self.counters = threading.Lock(), []
        self.kernel = kernel
        self.threads = [threading.Thread(target=self.work, args=(r,)) for r in range(workers)]
        for thread in self.threads:
            thread.start()

    def claim(self, phase: int) -> int:
        with self.lock:
            start = self.counters[phase]
            self.counters[phase] += self.chunk
        return start

    def work(self, rank: int) -> None:
        worker = Worker(self.blocks, self.kernel, self.buffers, self.costs)
        ranged = self.mode.startswith("ranged")
        idle = self.mode == "barriers only"
        count = self.blocks.count
        while True:
            self.start.wait()
            steps = self.command.value
            if steps < 0:
                return
            a, s, n = 0, 1, 2
            for step in range(steps):
                for which in (1, 2):
                    if not idle:
                        if self.schedule == "dynamic":
                            phase = 2 * step + which - 1
                            while (b0 := self.claim(phase)) < count:
                                worker.stage(which, a, s, n, b0, min(b0 + self.chunk, count), ranged)
                        else:
                            b0, b1 = self.schedule[rank]
                            if b1 > b0:
                                worker.stage(which, a, s, n, b0, b1, ranged)
                    self.step_barrier.wait()
                a, n = n, a
            self.done.wait()

    def run(self, steps: int) -> float:
        self.counters = [0] * (2 * steps)
        self.command.value = steps
        begin = time.perf_counter()
        self.start.wait()
        self.done.wait()
        return time.perf_counter() - begin

    def close(self) -> None:
        self.command.value = -1
        self.start.wait()
        for thread in self.threads:
            thread.join()


class Pool:
    """The main thread runs every stage as one task per worker on a thread pool and waits for all of them."""

    def __init__(self, workers: int, blocks: Blocks, kernel, schedule) -> None:
        self.blocks, self.schedule = blocks, schedule
        self.buffers = np.zeros((3, *blocks.shape))
        costs = np.zeros(blocks.count, dtype=np.intp)
        self.local = threading.local()
        self.kernel, self.costs = kernel, costs
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)

    def task(self, which: int, a: int, s: int, n: int, b0: int, b1: int) -> None:
        if not hasattr(self.local, "worker"):
            self.local.worker = Worker(self.blocks, self.kernel, self.buffers, self.costs)
        self.local.worker.stage(which, a, s, n, b0, b1, True)

    def run(self, steps: int) -> float:
        begin = time.perf_counter()
        a, s, n = 0, 1, 2
        for _ in range(steps):
            for which in (1, 2):
                futures = [self.pool.submit(self.task, which, a, s, n, b0, b1) for b0, b1 in self.schedule if b1 > b0]
                for future in futures:
                    future.result()
            a, n = n, a
        return time.perf_counter() - begin

    def close(self) -> None:
        self.pool.shutdown()


def measure(runner, blocks: Blocks, expected: np.ndarray | None) -> dict:
    try:
        blocks.scatter(initial_state(blocks.nx, blocks.ny), runner.buffers[0])
        runner.run(CHECK_STEPS)
        identical = None if expected is None else bool(np.array_equal(blocks.gather(runner.buffers[0]), expected))
        per_step = max(runner.run(2) / 2, 1e-6)
        steps = 2 * max(1, math.ceil(MIN_TIME / per_step / 2))
        best = min(runner.run(steps) / steps for _ in range(REPEATS))
    finally:
        runner.close()
    return {"cell_updates_per_second": blocks.nx * blocks.ny / best, "seconds_per_step": best,
            "bitwise_identical": identical}


def main() -> None:
    label, output = sys.argv[1], Path(sys.argv[2])
    workers_list = [int(w) for w in os.environ.get("E091_WORKERS", "1,6,12").split(",")]
    results = {"label": label, "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
               "cpu_count": os.cpu_count(), "rows": {}}
    nx, ny = GRID
    with tempfile.TemporaryDirectory() as tmp:
        kernel = build(Path(tmp))
        results["gil_enabled_after_import"] = getattr(sys, "_is_gil_enabled", lambda: True)()
        expected = reference(kernel, nx, ny, CHECK_STEPS)
        for bx, by in BLOCK_SHAPES:
            blocks = Blocks(nx, ny, bx, by)
            for workers in workers_list:
                schedule = equal_ranges(blocks.count, workers)
                for mode in [*MODES, "barriers only"]:
                    if mode == "ranged calls, thread pool":
                        runner = Pool(workers, blocks, kernel, schedule)
                    else:
                        runner = Team(workers, blocks, kernel, mode, schedule)
                    row = measure(runner, blocks, None if mode == "barriers only" else expected)
                    results["rows"][f"{bx}x{by} | {mode} | {workers}"] = row
                    print(f"{label} | {bx}x{by} | {mode} | {workers}: {row['cell_updates_per_second']:.2e} "
                          f"({1e6 * row['seconds_per_step']:.0f} µs/step), identical {row['bitwise_identical']}",
                          flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


if __name__ == "__main__":
    main()
