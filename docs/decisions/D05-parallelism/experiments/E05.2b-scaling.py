# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E05.2 (benchmark): how do the shared-memory strategies scale, and do they change the result?

One SSP-RK2 step of the D04 hydro kernel (``E05.2a-kernels.py``) on a periodic 2048 x 512 grid, a thesis-like 4:1
domain of 10^6 cells, is parallelised in three ways:

- **loop-level, OpenMP:** the whole grid is one block, and the loops inside each kernel call are shared among OpenMP
  threads (as E04.1 measured). Only where the compiler supports OpenMP.
- **block-level, Python threads:** the grid is split into square blocks of 32^2, 64^2 or 128^2 cells, each with its own
  ghost cells, and a team of Python threads updates whole blocks. The kernels release the GIL; filling ghost cells
  (NumPy copies from the neighbouring blocks) and the loop over blocks are Python and hold it, unless the interpreter
  is free-threaded.
- **block-level, processes:** the same, with a team of processes (``multiprocessing``, spawned) and the blocks in
  shared memory.

The two block-level teams do exactly the same work. Each worker owns a fixed, contiguous range of blocks and keeps its
own scratch arrays; per step it fills the ghost cells of its blocks, runs the first stage, waits at a barrier, fills
again, runs the second stage and waits again. Two barriers per step suffice, because a stage only reads the
neighbours' interior cells, which nobody writes until after the next barrier.

Every configuration is first checked bit for bit against a single-block serial reference after four steps, then timed
for 1 to 12 workers. Not meant to be run by hand: ``E05.2d-run.py`` runs it natively and in a Linux container, with the
standard and the free-threaded interpreter, as ``uv run --locked --python <python> --script E05.2b-scaling.py <label>
<output.json>``.
"""

import importlib.util
import json
import math
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
from dataclasses import dataclass, field
from multiprocessing import shared_memory
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
NX, NY = 2048, 512  ## cells along x (slow index) and y (fast index); domain [0, 4] x [0, 1]
G = 2
GAMMA = 1.4
DX = 1.0 / NY
DT = 0.2 * DX
BLOCKS = [32, 64, 128]
THREADS = [1, 2, 3, 4, 6, 8, 12]
CHECK_STEPS = 4
MIN_TIME = 0.5  ## seconds per timed repetition
REPEATS = 3


LOADED: dict[Path, object] = {}


def load(name: str, path: Path):
    """Import a module from a file path; a compiled extension is loaded only once per process."""
    if path in LOADED:
        return LOADED[path]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    LOADED[path] = module
    return module


def compiler_supports_openmp(workdir: Path) -> bool:
    test = workdir / "omp_test.c"
    test.write_text("#include <omp.h>\nint main(void){return omp_get_max_threads() > 0 ? 0 : 1;}\n")
    return subprocess.run(["cc", "-fopenmp", str(test), "-o", str(workdir / "omp_test")],
                          capture_output=True).returncode == 0


def build(workdir: Path, name: str, openmp: bool) -> Path:
    """Compile the kernels with Cython and the C compiler (-O3, generic CPU); return the extension's path."""
    (workdir / f"{name}.py").write_text((HERE / "E05.2a-kernels.py").read_text())
    subprocess.run([sys.executable, "-m", "cython", "-3", f"{name}.py", "-o", f"{name}.c"], cwd=workdir, check=True,
                   capture_output=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"{name}{sysconfig.get_config_var('EXT_SUFFIX')}"
    flags = ["-fopenmp"] if openmp else []
    subprocess.run(["cc", "-O3", *flags, *shared, f"-I{sysconfig.get_paths()['include']}", f"{name}.c", "-o",
                    str(ext)], cwd=workdir, check=True)
    return ext


def initial_state() -> np.ndarray:
    """The smooth periodic state of E04.1 on the 4 x 1 domain (interior cells only)."""
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    xx, yy = np.meshgrid(x, y, indexing="ij")
    rho = 1.0 + 0.2 * np.sin(2 * np.pi * xx) * np.sin(2 * np.pi * yy)
    vx = 0.5 + 0.1 * np.sin(2 * np.pi * yy)
    vy = 0.3 * np.cos(2 * np.pi * xx)
    pres = 1.0 + 0.1 * np.cos(2 * np.pi * (xx + yy))
    return np.array([rho, rho * vx, rho * vy, pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy)])


def reference(kernel, steps: int) -> np.ndarray:
    """Single block, one thread, periodic ghost cells filled with NumPy as in E04.1."""
    u = np.zeros((4, NX + 2 * G, NY + 2 * G))
    u[:, G:-G, G:-G] = initial_state()
    stage, new = np.zeros_like(u), np.zeros_like(u)
    w = np.empty_like(u)
    fx, fy, du = np.empty((4, NX + 1, NY)), np.empty((4, NX, NY + 1)), np.empty((4, NX, NY))

    def fill(a):
        a[:, :G, :] = a[:, -2 * G : -G, :]
        a[:, -G:, :] = a[:, G : 2 * G, :]
        a[:, :, :G] = a[:, :, -2 * G : -G]
        a[:, :, -G:] = a[:, :, G : 2 * G]

    for _ in range(steps):
        fill(u)
        kernel.rhs(u, w, fx, fy, du, G, DX)
        kernel.first_stage(u, du, DT, stage, G)
        fill(stage)
        kernel.rhs(stage, w, fx, fy, du, G, DX)
        kernel.second_stage(u, stage, du, DT, new, G)
        u, new = new, u
    return u[:, G:-G, G:-G].copy()


@dataclass
class Layout:
    """Blocks of bx x by cells tiling the periodic grid, and the ghost-cell copies of every block."""

    bx: int
    by: int
    nbx: int = field(init=False)
    nby: int = field(init=False)
    copies: list = field(init=False)  ## per block: (destination slices, source block, source slices)

    def __post_init__(self) -> None:
        self.nbx, self.nby = NX // self.bx, NY // self.by
        bx, by = self.bx, self.by
        ## Destination and source index ranges along one direction, for offsets -1, 0 and +1.
        dst_x = {-1: slice(0, G), 0: slice(G, G + bx), 1: slice(G + bx, 2 * G + bx)}
        src_x = {-1: slice(bx, bx + G), 0: slice(G, G + bx), 1: slice(G, 2 * G)}
        dst_y = {-1: slice(0, G), 0: slice(G, G + by), 1: slice(G + by, 2 * G + by)}
        src_y = {-1: slice(by, by + G), 0: slice(G, G + by), 1: slice(G, 2 * G)}
        self.copies = []
        for k in range(self.nblocks):
            bi, bj = divmod(k, self.nby)
            block = []
            for oi in (-1, 0, 1):
                for oj in (-1, 0, 1):
                    if oi == oj == 0:
                        continue
                    source = ((bi + oi) % self.nbx) * self.nby + (bj + oj) % self.nby
                    block.append(((slice(None), dst_x[oi], dst_y[oj]), source, (slice(None), src_x[oi], src_y[oj])))
            self.copies.append(block)

    @property
    def nblocks(self) -> int:
        return self.nbx * self.nby

    @property
    def shape(self) -> tuple[int, int, int, int]:
        return (self.nblocks, 4, self.bx + 2 * G, self.by + 2 * G)

    def interior(self, k: int) -> tuple[slice, slice, slice]:
        bi, bj = divmod(k, self.nby)
        return (slice(None), slice(bi * self.bx, (bi + 1) * self.bx), slice(bj * self.by, (bj + 1) * self.by))

    def scatter(self, state: np.ndarray, blocks: np.ndarray) -> None:
        for k in range(self.nblocks):
            blocks[k][:, G:-G, G:-G] = state[self.interior(k)]

    def gather(self, blocks: np.ndarray) -> np.ndarray:
        state = np.empty((4, NX, NY))
        for k in range(self.nblocks):
            state[self.interior(k)] = blocks[k][:, G:-G, G:-G]
        return state


def work(rank: int, workers: int, layout: Layout, buffers: np.ndarray, kernel, start, done, step_barrier,
         command) -> None:
    """The loop of one worker (thread or process): wait for a command, advance its blocks, report back."""
    mine = range(rank * layout.nblocks // workers, (rank + 1) * layout.nblocks // workers)
    views = [[buffers[b, k] for k in range(layout.nblocks)] for b in range(3)]
    copies = [[(dst, src, srcsl) for dst, src, srcsl in layout.copies[k]] for k in range(layout.nblocks)]
    bx, by = layout.bx, layout.by
    w = np.empty((4, bx + 2 * G, by + 2 * G))
    fx, fy, du = np.empty((4, bx + 1, by)), np.empty((4, bx, by + 1)), np.empty((4, bx, by))
    rhs, first_stage, second_stage = kernel.rhs, kernel.first_stage, kernel.second_stage
    while True:
        start.wait()
        steps = command.value
        if steps < 0:
            return
        a, s, b = views
        for _ in range(steps):
            for k in mine:
                for dst, src, srcsl in copies[k]:
                    a[k][dst] = a[src][srcsl]
            for k in mine:
                rhs(a[k], w, fx, fy, du, G, DX)
                first_stage(a[k], du, DT, s[k], G)
            step_barrier.wait()
            for k in mine:
                for dst, src, srcsl in copies[k]:
                    s[k][dst] = s[src][srcsl]
            for k in mine:
                rhs(s[k], w, fx, fy, du, G, DX)
                second_stage(a[k], s[k], du, DT, b[k], G)
            step_barrier.wait()
            a, b = b, a
        done.wait()


def process_main(rank, workers, layout, shm_name, kernel_path, start, done, step_barrier, command) -> None:
    shm = shared_memory.SharedMemory(name=shm_name)
    buffers = np.ndarray((3, *layout.shape), dtype=np.float64, buffer=shm.buf)
    kernel = load(Path(kernel_path).stem.split(".")[0], Path(kernel_path))
    try:
        work(rank, workers, layout, buffers, kernel, start, done, step_barrier, command)
    finally:
        del buffers
        shm.close()


class Command:
    """Stand-in for multiprocessing.Value in the thread team."""

    value = 0


class Team:
    """A team of worker threads or processes that advances the blocks of one layout."""

    def __init__(self, kind: str, workers: int, layout: Layout, kernel_path: Path) -> None:
        self.kind, self.layout = kind, layout
        if kind == "threads":
            self.buffers = np.zeros((3, *layout.shape))
            self.start, self.done = threading.Barrier(workers + 1), threading.Barrier(workers + 1)
            self.step_barrier, self.command = threading.Barrier(workers), Command()
            kernel = load(kernel_path.stem.split(".")[0], kernel_path)
            self.members = [
                threading.Thread(target=work, args=(r, workers, layout, self.buffers, kernel, self.start, self.done,
                                                    self.step_barrier, self.command))
                for r in range(workers)
            ]
        else:
            ctx = mp.get_context("spawn")
            size = 3 * math.prod(layout.shape) * 8
            self.shm = shared_memory.SharedMemory(create=True, size=size)
            self.buffers = np.ndarray((3, *layout.shape), dtype=np.float64, buffer=self.shm.buf)
            self.buffers[:] = 0.0
            self.start, self.done = ctx.Barrier(workers + 1), ctx.Barrier(workers + 1)
            ## Kept as attributes: a synchronisation object collected in the parent unlinks its semaphore, which a
            ## spawned child that has not yet unpickled it would then fail to find.
            self.step_barrier, self.command = ctx.Barrier(workers), ctx.Value("i", 0)
            self.members = [
                ctx.Process(target=process_main, args=(r, workers, layout, self.shm.name, str(kernel_path),
                                                       self.start, self.done, self.step_barrier, self.command))
                for r in range(workers)
            ]
        for member in self.members:
            member.start()

    def run(self, steps: int) -> float:
        self.command.value = steps
        begin = time.perf_counter()
        self.start.wait()
        self.done.wait()
        return time.perf_counter() - begin

    def close(self) -> None:
        self.command.value = -1
        self.start.wait()
        for member in self.members:
            member.join()
        if self.kind == "processes":
            del self.buffers
            self.shm.close()
            self.shm.unlink()


def measure(team: Team, expected: np.ndarray) -> dict:
    team.layout.scatter(initial_state(), team.buffers[0])
    team.run(CHECK_STEPS)
    identical = bool(np.array_equal(team.layout.gather(team.buffers[0]), expected))
    per_step = team.run(2) / 2
    steps = 2 * max(1, math.ceil(MIN_TIME / per_step / 2))
    best = min(team.run(steps) / steps for _ in range(REPEATS))
    return {"cell_updates_per_second": NX * NY / best, "bitwise_identical": identical}


def main() -> None:
    label, output = sys.argv[1], Path(sys.argv[2])
    gil = getattr(sys, "_is_gil_enabled", lambda: True)()
    threads = [t for t in THREADS if t <= (os.cpu_count() or 1)]
    results = {
        "label": label, "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
        "cpu_count": os.cpu_count(), "steps_checked": CHECK_STEPS, "grid": [NX, NY], "configurations": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        serial_path = build(workdir, "kernels_serial", openmp=False)
        openmp = compiler_supports_openmp(workdir)
        omp_path = build(workdir, "kernels_openmp", openmp=True) if openmp else None
        serial = load("kernels_serial", serial_path)
        results["gil_enabled_after_import"] = getattr(sys, "_is_gil_enabled", lambda: True)()
        results["gil_enabled_at_start"], results["openmp"] = gil, openmp
        expected = reference(serial, CHECK_STEPS)

        configurations = [("single block, one thread", Layout(NX, NY), "threads", serial_path, [1])]
        if omp_path is not None:
            configurations.append(("single block, loop-level OpenMP", Layout(NX, NY), "threads", omp_path, threads))
        for b in BLOCKS:
            configurations.append((f"blocks of {b}², Python threads", Layout(b, b), "threads", serial_path, threads))
            configurations.append((f"blocks of {b}², processes", Layout(b, b), "processes", serial_path, threads))

        for name, layout, kind, path, counts in configurations:
            rows = results["configurations"][name] = {}
            for t in counts:
                workers = 1 if "OpenMP" in name else t
                if "OpenMP" in name:
                    load(path.stem.split(".")[0], path).set_threads(t)
                team = Team(kind, workers, layout, path)
                try:
                    rows[t] = measure(team, expected)
                finally:
                    team.close()
                print(f"{label} | {name} | {t}: {rows[t]['cell_updates_per_second']:.2e}, "
                      f"identical {rows[t]['bitwise_identical']}", flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


if __name__ == "__main__":
    main()
