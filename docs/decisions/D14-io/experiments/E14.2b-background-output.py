# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython", "h5py", "hdf5plugin"]
# ///
"""Experiment E14.2: can snapshots be written in the background while the run continues?

Full SSP-RK2 steps on the thesis grid (4000 x 1000, periodic, blocks of 50^2 in Morton order) with the ranged kernels of
``E14.2a-kernels.py`` (a copy of E09.1a), run on a thread pool with one task per worker and stage, as in E09.1. Every
few steps a snapshot of the state (interior cells, five conserved variables, 160 MB) is written to an HDF5 file, either
uncompressed or with zstd (E14.1), in one of two ways:

- **synchronous:** the main thread copies the state and writes the file, then continues with the next step;
- **in the background:** the main thread copies the state (the copy is what keeps the snapshot consistent while the
  state changes) and hands the copy to a writer thread, then continues with the next step at once; before the next
  snapshot it waits for the previous one to be finished.

The cost of a snapshot is the extra time of the run over the same steps without output, divided by the number of
snapshots. Under the GIL, the writer thread can only overlap with the steps if h5py releases the GIL while writing;
with the free-threaded interpreter it can always. The snapshots of the two ways are checked to be bit-for-bit
identical. Repetitions are interleaved; the best of three is kept.

Run from this directory with (the machine otherwise idle):

    uv run --no-project --python 3.14 E14.2b-background-output.py

which runs ``E14.2b-background-output.py run`` with both interpreters and summarises. Results are written to results/.
"""

import concurrent.futures
import importlib.util
import json
import platform
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
RUNS = {"macos-native-3.14t": "3.14t", "macos-native-3.14": "3.14+gil"}
G = 2
GAMMA = 1.4
NVAR = 5
GRID = (4000, 1000)
BLOCK = 50
WORKERS = [6, 12]
STEPS = 40
EVERY = 5
REPEATS = 3


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path):
    (workdir / "kernels.py").write_text((HERE / "E14.2a-kernels.py").read_text())
    subprocess.run([sys.executable, "-m", "cython", "-3", "kernels.py", "-o", "kernels.c"], cwd=workdir, check=True,
                   capture_output=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"kernels{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", "kernels.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load("kernels", ext)


def morton(cx: int, cy: int) -> int:
    code = 0
    for bit in range(16):
        code |= ((cx >> bit) & 1) << (2 * bit) | ((cy >> bit) & 1) << (2 * bit + 1)
    return code


class Run:
    """The thesis grid in blocks, its exchange plan, and SSP-RK2 steps on a thread pool (ranged calls, as E09.1)."""

    def __init__(self, np, kernel, workers: int) -> None:
        nx, ny = GRID
        nbx, nby = nx // BLOCK, ny // BLOCK
        self.np, self.kernel, self.workers = np, kernel, workers
        self.locations = sorted(((ci, cj) for cj in range(nby) for ci in range(nbx)), key=lambda c: morton(*c))
        index = {loc: b for b, loc in enumerate(self.locations)}
        self.count = len(self.locations)
        dst = {-1: (0, G), 0: (G, BLOCK), 1: (G + BLOCK, G)}
        src = {-1: (BLOCK, G), 0: (G, BLOCK), 1: (G, G)}
        rows, self.rows = [], []
        for b, (ci, cj) in enumerate(self.locations):
            start = len(rows)
            for oj in (-1, 0, 1):
                for oi in (-1, 0, 1):
                    if oi == oj == 0:
                        continue
                    s = index[((ci + oi) % nbx, (cj + oj) % nby)]
                    rows.append((b, s, 0, dst[oj][0], dst[oi][0], 0, src[oj][0], src[oi][0], 1, dst[oj][1], dst[oi][1]))
            self.rows.append((start, len(rows)))
        self.plan = np.array(rows, dtype=np.intp)
        self.buffers = np.zeros((3, self.count, NVAR, 1, BLOCK + 2 * G, BLOCK + 2 * G))
        self.costs = np.zeros(self.count, dtype=np.intp)
        self.ranges = [(r * self.count // workers, (r + 1) * self.count // workers) for r in range(workers)]
        self.local = threading.local()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        self.dx, self.dt = 1.0 / ny, 0.2 / ny
        self.a, self.s, self.n = 0, 1, 2

    def reset(self) -> None:
        np = self.np
        nx, ny = GRID
        x, y = (np.arange(nx) + 0.5) / ny, (np.arange(ny) + 0.5) / ny
        yy, xx = np.meshgrid(y, x, indexing="ij")
        s = 2 * np.pi
        rho = 1.0 + 0.2 * np.sin(s * xx) * np.sin(s * yy)
        vx, vy, vz = 0.5 + 0.1 * np.sin(s * yy), 0.3 * np.cos(s * xx), 0.1 * np.sin(s * (xx - yy))
        pres = 1.0 + 0.1 * np.cos(s * (xx + yy))
        state = np.array([rho, rho * vx, rho * vy, rho * vz,
                          pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy + vz * vz)])
        self.a, self.s, self.n = 0, 1, 2
        for b, (ci, cj) in enumerate(self.locations):
            self.buffers[0, b, :, 0, G:-G, G:-G] = state[:, cj * BLOCK : (cj + 1) * BLOCK, ci * BLOCK : (ci + 1) * BLOCK]

    def task(self, which: int, b0: int, b1: int) -> None:
        np, k, p = self.np, self.kernel, self.buffers
        if not hasattr(self.local, "scratch"):
            self.local.scratch = (np.empty((NVAR, 1, BLOCK + 2 * G, BLOCK + 2 * G)), np.empty((NVAR, 1, BLOCK, BLOCK + 1)),
                                  np.empty((NVAR, 1, BLOCK + 1, BLOCK)), np.empty((NVAR, 2, BLOCK, BLOCK)),
                                  np.empty((NVAR, 1, BLOCK, BLOCK)), np.empty((1, BLOCK, BLOCK)))
        w, fx, fy, fz, du, scratch = self.local.scratch
        a, s, n = self.a, self.s, self.n
        k.copy_regions(p[a] if which == 1 else p[s], self.plan, self.rows[b0][0], self.rows[b1 - 1][1])
        if which == 1:
            k.stage_one(p[a], p[s], w, fx, fy, fz, du, scratch, self.costs, b0, b1, BLOCK, BLOCK, 1, G, self.dx,
                        self.dt, 0, G, G)
        else:
            k.stage_two(p[a], p[s], p[n], w, fx, fy, fz, du, scratch, self.costs, b0, b1, BLOCK, BLOCK, 1, G, self.dx,
                        self.dt, 0, G, G)

    def step(self) -> None:
        for which in (1, 2):
            futures = [self.pool.submit(self.task, which, b0, b1) for b0, b1 in self.ranges]
            for future in futures:
                future.result()
        self.a, self.n = self.n, self.a

    def snapshot(self):
        """A copy of the interior cells of the current state, [block, var, k, j, i]."""
        return self.np.ascontiguousarray(self.buffers[self.a, :, :, :, G:-G, G:-G])


def writer(h5py, hdf5plugin, form: str):
    options = {} if form == "uncompressed" else {
        "chunks": (16, NVAR, 1, BLOCK, BLOCK), **hdf5plugin.Blosc(cname="zstd", clevel=1, shuffle=hdf5plugin.Blosc.SHUFFLE)}

    def write(data, path: Path) -> None:
        with h5py.File(path, "w") as f:
            f.create_dataset("cons", data=data, **options)

    return write


def run(label: str, output: Path) -> None:
    import h5py
    import hdf5plugin
    import numpy as np

    results = {"label": label, "python": sys.version, "numpy": np.__version__, "h5py": h5py.__version__,
               "hdf5": h5py.version.hdf5_version, "platform": platform.platform(), "rows": {}}
    modes = ["no output"] + [f"{way}, {form}" for form in ("uncompressed", "zstd") for way in ("synchronous", "background")]
    with tempfile.TemporaryDirectory() as tmp:
        kernel = build(Path(tmp))
        results["gil_enabled"] = getattr(sys, "_is_gil_enabled", lambda: True)()
        out = Path(tmp) / "out"
        out.mkdir()
        for workers in WORKERS:
            sim = Run(np, kernel, workers)
            best = dict.fromkeys(modes, float("inf"))
            copy_time = float("inf")
            identical = True
            for repeat in range(REPEATS):
                for mode in modes:
                    sim.reset()
                    sim.step()
                    background = mode.startswith("background")
                    write = None if mode == "no output" else writer(h5py, hdf5plugin, mode.split(", ")[1])
                    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1) if background else None
                    pending = None
                    start = time.perf_counter()
                    for step in range(1, STEPS + 1):
                        sim.step()
                        if write is not None and step % EVERY == 0:
                            if pending is not None:
                                pending.result()
                            t0 = time.perf_counter()
                            data = sim.snapshot()
                            copy_time = min(copy_time, time.perf_counter() - t0)
                            path = out / f"{mode.replace(', ', '-')}-{step:03d}.h5"
                            if background:
                                pending = pool.submit(write, data, path)
                            else:
                                write(data, path)
                    if pending is not None:
                        pending.result()
                    elapsed = time.perf_counter() - start
                    if pool is not None:
                        pool.shutdown()
                    best[mode] = min(best[mode], elapsed)
                if repeat == 0:
                    for form in ("uncompressed", "zstd"):
                        for step in range(EVERY, STEPS + 1, EVERY):
                            files = [out / f"{way}-{form}-{step:03d}.h5" for way in ("synchronous", "background")]
                            with h5py.File(files[0]) as f0, h5py.File(files[1]) as f1:
                                identical &= bool(np.array_equal(f0["cons"][...], f1["cons"][...]))
                for path in out.iterdir():
                    path.unlink()
            snapshots = STEPS // EVERY
            step_time = best["no output"] / STEPS
            row = {"seconds_per_step": step_time, "copy_seconds": copy_time, "snapshots_identical": identical,
                   "seconds": best,
                   "seconds_per_snapshot": {m: (best[m] - best["no output"]) / snapshots for m in modes[1:]}}
            results["rows"][str(workers)] = row
            print(label, workers, json.dumps(row), flush=True)
            sim.pool.shutdown()
    output.write_text(json.dumps(results, indent=1) + "\n")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2], Path(sys.argv[3]))
        return
    RESULTS.mkdir(exist_ok=True)
    for label, python in RUNS.items():
        subprocess.run(["uv", "run", "--locked", "--python", python, "--script", str(HERE / "E14.2b-background-output.py"),
                        "run", label, str(RESULTS / f"E14.2-{label}.json")], check=True)
    md = ["# E14.2: writing snapshots in the background", "",
          f"Thesis grid (4000 x 1000, blocks of 50²), SSP-RK2 with ranged calls on a thread pool; a snapshot (five "
          f"conserved variables, 160 MB) every {EVERY} steps, {STEPS} steps; natively, internal SSD. Cost of a snapshot: "
          "the extra time of the run over the same steps without output, per snapshot, in seconds and in steps.", "",
          "| Interpreter | Workers | Step | Copy of the state | Uncompressed: synchronous | Uncompressed: background "
          "| zstd: synchronous | zstd: background | Snapshots identical |", "|---|---|---|---|---|---|---|---|---|"]
    for label in RUNS:
        r = json.loads((RESULTS / f"E14.2-{label}.json").read_text())
        name = "with GIL" if r["gil_enabled"] else "free-threaded"
        for workers, row in r["rows"].items():
            cost = row["seconds_per_snapshot"]
            cells = [f"{cost[m]:.2f} s ({cost[m] / row['seconds_per_step']:.1f})"
                     for m in ("synchronous, uncompressed", "background, uncompressed", "synchronous, zstd",
                               "background, zstd")]
            md.append(f"| {name} | {workers} | {1e3 * row['seconds_per_step']:.0f} ms | "
                      f"{1e3 * row['copy_seconds']:.0f} ms | {' | '.join(cells)} | "
                      f"{'yes' if row['snapshots_identical'] else 'no'} |")
    (RESULTS / "E14.2-background-output.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
