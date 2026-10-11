# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E07.1: which block sizes suit the thesis grid of 4000 x 1000 cells?

The thesis grid cannot be divided into blocks of 64^2 cells, the size the D04 and D05 experiments favoured: the block
sizes that tile it exactly divide 1000 (25, 40, 50, 100, 125, 200, 250, ...). This experiment measures full SSP-RK2
steps of the D06 kernel (``E07.1a-kernels.py``) on the periodic thesis grid for such block sizes, square and
rectangular, and for comparison on a 4096 x 1024 grid with power-of-two blocks. It answers whether block sizes must be
powers of two, how small blocks may get before ghost cells and per-block overhead dominate, and how large before
parallel scaling suffers.

The parallel model is that of D05: a team of Python threads, each owning a contiguous range of blocks in a fixed order,
filling its blocks' ghost cells from their neighbours with NumPy copies, then running the compiled kernels, with a
barrier after each stage. The data layout is that of D06: ``[block, var, k, j, i]`` with x contiguous and extent 1 in z.

Every configuration is checked bit for bit against a single-block serial reference after two steps. Not meant to be
run by hand: ``E07.1c-run.py`` runs it with the free-threaded and the standard interpreter, as
``uv run --locked --python <python> --script E07.1b-block-size.py <label> <output.json>``.
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
CASES = {
    (4000, 1000): [(25, 25), (40, 40), (50, 50), (100, 100), (125, 125), (200, 200), (250, 250), (100, 50),
                   (200, 50)],
    (4096, 1024): [(32, 32), (64, 64), (128, 128), (256, 256)],
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path):
    (workdir / "kernels.py").write_text((HERE / "E07.1a-kernels.py").read_text())
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

    def __init__(self, workers: int, blocks: Blocks, kernel) -> None:
        self.blocks, self.kernel = blocks, kernel
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
        rhs, first_stage, second_stage = kernel.rhs, kernel.first_stage, kernel.second_stage
        while True:
            self.start.wait()
            steps = self.command.value
            if steps < 0:
                return
            a, s, n = views
            for _ in range(steps):
                for b in mine:
                    for d, src, ss in blocks.copies[b]:
                        a[b][d] = a[src][ss]
                for b in mine:
                    rhs(a[b], w, fx, fy, fz, du, bx, by, 1, G, dx)
                    first_stage(a[b], du, dt, s[b], 0, G, G)
                self.step_barrier.wait()
                for b in mine:
                    for d, src, ss in blocks.copies[b]:
                        s[b][d] = s[src][ss]
                for b in mine:
                    rhs(s[b], w, fx, fy, fz, du, bx, by, 1, G, dx)
                    second_stage(a[b], s[b], du, dt, n[b], 0, G, G)
                self.step_barrier.wait()
                a, n = n, a
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


def measure(kernel, blocks: Blocks, workers: int, expected: np.ndarray) -> dict:
    team = Team(workers, blocks, kernel)
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
    workers_list = [int(w) for w in os.environ.get("E071_WORKERS", "1,6").split(",")]
    results = {"label": label, "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
               "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(), "cases": {}}
    with tempfile.TemporaryDirectory() as tmp:
        kernel = build(Path(tmp))
        results["gil_enabled_after_import"] = getattr(sys, "_is_gil_enabled", lambda: True)()
        for (nx, ny), shapes in CASES.items():
            expected = reference(kernel, nx, ny, CHECK_STEPS)
            case = results["cases"][f"{nx}x{ny}"] = {}
            for workers in workers_list:
                for bx, by in [(nx, ny)] + shapes if workers == 1 else shapes:
                    row = measure(kernel, Blocks(nx, ny, bx, by), workers, expected)
                    case[f"{bx}x{by}, {workers} workers"] = row
                    print(f"{label} | {nx}x{ny} | {bx}x{by} | {workers}: {row['cell_updates_per_second']:.2e}, "
                          f"identical {row['bitwise_identical']}", flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


if __name__ == "__main__":
    main()
