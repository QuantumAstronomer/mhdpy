# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E08.1: should ghost cells be filled by NumPy copies or by a compiled copy kernel?

Filling ghost cells with NumPy slice copies cost about 10 % of a kernel evaluation in E06.2, and that Python holds the
GIL. D05.4 asked for the GIL-held share per block to be kept small, so that the standard interpreter scales too, and
left it to be measured here. This experiment runs full SSP-RK2 steps on the thesis grid (4000 x 1000, periodic) as in
E07.1, with the ghost cells filled in three ways:

- **NumPy:** eight slice copies per block (edges and corners), as in E05-E07;
- **compiled, per block:** an exchange plan built once from the blocks (one row per region: destination block and
  offset, source block and offset, extent) is executed by the compiled ``copy_regions`` of ``E08.1a-kernels.py`` with
  one call per block, without the GIL;
- **compiled, per worker:** the same kernel, called once per worker and stage for all regions of its blocks.

Every configuration is checked bit for bit against a single-block serial reference. Not meant to be run by hand:
``E08.1d-run.py`` runs it natively and in a Linux container, with the free-threaded and the standard interpreter, as
``uv run --locked --python <python> --script E08.1b-ghost-copies.py <label> <output.json>``.
"""

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
## (grid nx, ny) -> block shapes (bx, by), x first
GRID = (4000, 1000)
BLOCK_SHAPES = [(50, 50), (25, 25)]
MODES = ["NumPy", "compiled, per block", "compiled, per worker"]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path):
    (workdir / "kernels.py").write_text((HERE / "E08.1a-kernels.py").read_text())
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


class Blocks:
    """Blocks of bx x by cells tiling a periodic nx x ny grid, row by row, with their ghost-cell copies."""

    def __init__(self, nx: int, ny: int, bx: int, by: int) -> None:
        self.nx, self.ny, self.bx, self.by = nx, ny, bx, by
        self.nbx, self.nby = nx // bx, ny // by
        self.count = self.nbx * self.nby
        self.shape = (self.count, NVAR, 1, by + 2 * G, bx + 2 * G)
        dst_x = {-1: slice(0, G), 0: slice(G, G + bx), 1: slice(G + bx, 2 * G + bx)}
        src_x = {-1: slice(bx, bx + G), 0: slice(G, G + bx), 1: slice(G, 2 * G)}
        dst_y = {-1: slice(0, G), 0: slice(G, G + by), 1: slice(G + by, 2 * G + by)}
        src_y = {-1: slice(by, by + G), 0: slice(G, G + by), 1: slice(G, 2 * G)}
        self.copies = []
        for b in range(self.count):
            cj, ci = divmod(b, self.nbx)
            block = []
            for oj in (-1, 0, 1):
                for oi in (-1, 0, 1):
                    if oi == oj == 0:
                        continue
                    source = ((cj + oj) % self.nby) * self.nbx + (ci + oi) % self.nbx
                    block.append(((slice(None), 0, dst_y[oj], dst_x[oi]), source,
                                  (slice(None), 0, src_y[oj], src_x[oi])))
            self.copies.append(block)
        ## The same copies as an exchange plan: rows (dst, src, dk, dj, di, sk, sj, si, nk, nj, ni), ordered by block.
        rows, self.rows = [], []
        for b, block in enumerate(self.copies):
            start = len(rows)
            for (_, _, dj, di), src, (_, _, sj, si) in block:
                rows.append((b, src, 0, dj.start, di.start, 0, sj.start, si.start, 1, dj.stop - dj.start,
                             di.stop - di.start))
            self.rows.append((start, len(rows)))
        self.plan = np.array(rows, dtype=np.intp)

    def interior(self, b: int):
        cj, ci = divmod(b, self.nbx)
        return (slice(None), slice(cj * self.by, (cj + 1) * self.by), slice(ci * self.bx, (ci + 1) * self.bx))

    def scatter(self, state: np.ndarray, pack: np.ndarray) -> None:
        for b in range(self.count):
            pack[b, :, 0, G:-G, G:-G] = state[self.interior(b)]

    def gather(self, pack: np.ndarray) -> np.ndarray:
        state = np.empty((NVAR, self.ny, self.nx))
        for b in range(self.count):
            state[self.interior(b)] = pack[b, :, 0, G:-G, G:-G]
        return state


class Command:
    value = 0


class Team:
    """Worker threads, each advancing a fixed contiguous range of blocks (D05)."""

    def __init__(self, workers: int, blocks: Blocks, kernel, mode: str) -> None:
        self.blocks, self.kernel, self.mode = blocks, kernel, mode
        self.buffers = np.zeros((3, *blocks.shape))
        self.start, self.done = threading.Barrier(workers + 1), threading.Barrier(workers + 1)
        self.step_barrier, self.command = threading.Barrier(workers), Command()
        self.threads = [threading.Thread(target=self.work, args=(r, workers)) for r in range(workers)]
        for thread in self.threads:
            thread.start()

    def work(self, rank: int, workers: int) -> None:
        blocks, kernel = self.blocks, self.kernel
        mine = range(rank * blocks.count // workers, (rank + 1) * blocks.count // workers)
        views = [list(self.buffers[n]) for n in range(3)]
        bx, by = blocks.bx, blocks.by
        w = np.empty((NVAR, 1, by + 2 * G, bx + 2 * G))
        fx, fy, fz = np.empty((NVAR, 1, by, bx + 1)), np.empty((NVAR, 1, by + 1, bx)), np.empty((NVAR, 2, by, bx))
        du = np.empty((NVAR, 1, by, bx))
        dx, dt = 1.0 / blocks.ny, 0.2 / blocks.ny
        rhs, first_stage, second_stage, copy_regions = (kernel.rhs, kernel.first_stage, kernel.second_stage,
                                                        kernel.copy_regions)
        plan, rows, mode = blocks.plan, blocks.rows, self.mode
        first_row, last_row = rows[mine.start][0], rows[mine.stop - 1][1]

        def fill(views, pack):
            if mode == "NumPy":
                for b in mine:
                    for d, src, ss in blocks.copies[b]:
                        views[b][d] = views[src][ss]
            elif mode == "compiled, per block":
                for b in mine:
                    copy_regions(pack, plan, rows[b][0], rows[b][1])
            else:
                copy_regions(pack, plan, first_row, last_row)

        while True:
            self.start.wait()
            steps = self.command.value
            if steps < 0:
                return
            a, s, n = views
            pa, ps, pn = self.buffers[0], self.buffers[1], self.buffers[2]
            for _ in range(steps):
                fill(a, pa)
                for b in mine:
                    rhs(a[b], w, fx, fy, fz, du, bx, by, 1, G, dx)
                    first_stage(a[b], du, dt, s[b], 0, G, G)
                self.step_barrier.wait()
                fill(s, ps)
                for b in mine:
                    rhs(s[b], w, fx, fy, fz, du, bx, by, 1, G, dx)
                    second_stage(a[b], s[b], du, dt, n[b], 0, G, G)
                self.step_barrier.wait()
                a, n = n, a
                pa, pn = pn, pa
            self.done.wait()

    def run(self, steps: int) -> float:
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


def measure(kernel, blocks: Blocks, workers: int, expected: np.ndarray, mode: str) -> dict:
    team = Team(workers, blocks, kernel, mode)
    try:
        blocks.scatter(initial_state(blocks.nx, blocks.ny), team.buffers[0])
        team.run(CHECK_STEPS)
        identical = bool(np.array_equal(blocks.gather(team.buffers[0]), expected))
        per_step = team.run(2) / 2
        steps = 2 * max(1, math.ceil(MIN_TIME / per_step / 2))
        best = min(team.run(steps) / steps for _ in range(REPEATS))
    finally:
        team.close()
    ghost_factor = (blocks.bx + 2 * G) * (blocks.by + 2 * G) / (blocks.bx * blocks.by)
    return {"cell_updates_per_second": blocks.nx * blocks.ny / best, "bitwise_identical": identical,
            "blocks": blocks.count, "cells_with_ghosts_per_cell": ghost_factor}


def main() -> None:
    label, output = sys.argv[1], Path(sys.argv[2])
    workers_list = [int(w) for w in os.environ.get("E081_WORKERS", "1,6,12").split(",")]
    results = {"label": label, "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
               "cpu_count": os.cpu_count(), "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(),
               "rows": {}}
    nx, ny = GRID
    with tempfile.TemporaryDirectory() as tmp:
        kernel = build(Path(tmp))
        results["gil_enabled_after_import"] = getattr(sys, "_is_gil_enabled", lambda: True)()
        expected = reference(kernel, nx, ny, CHECK_STEPS)
        for bx, by in BLOCK_SHAPES:
            blocks = Blocks(nx, ny, bx, by)
            for mode in MODES:
                for workers in workers_list:
                    row = measure(kernel, blocks, workers, expected, mode)
                    results["rows"][f"{bx}x{by} | {mode} | {workers}"] = row
                    print(f"{label} | {bx}x{by} | {mode} | {workers}: {row['cell_updates_per_second']:.2e}, "
                          f"identical {row['bitwise_identical']}", flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


if __name__ == "__main__":
    main()
