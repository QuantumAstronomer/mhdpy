# pyright: strict
# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy>=2.1", "cython>=3.1", "setuptools"]
# ///
"""B2E2: the rate of the loop module of B2E1 compiled by Cython with full declarations or with its signatures alone.

Run without arguments, it builds and times each variant in a process of its own and gathers the results in results/.
"""

import csv
import importlib.metadata
import importlib.util
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import sysconfig
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
from numpy.typing import NDArray

import vectorised

type Array = NDArray[np.float64]
type Stage = Callable[[Array, Array], None]

HERE = Path(__file__).parent
RESULTS = HERE / "results"
RAW = RESULTS / "raw"
## each variant: its file .pxd and the directives added to those of B2E1
VARIANTS: dict[str, tuple[str, list[str]]] = {"full": ("full.pxd", []), "signatures": ("signatures.pxd", []),
            "inferred": ("signatures.pxd", ["infer_types=True"])}
DIRECTIVES = ["boundscheck=False", "wraparound=False", "cdivision=True", "cpow=True", "annotation_typing=False",
              "freethreading_compatible=True"]
SIZES = [64, 128, 256, 512, 1024, 2048]
CHECK = 128
REPEATS = 7
GAMMA = 5.0 / 3.0
COURANT = 0.4
UPDATES = 9e10  ## the cell updates of the production run, topic 42, §4
THREADS = {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                  "VECLIB_MAXIMUM_THREADS")}


## ---- the problem and the step of B2E1 ----

def initial_state(n: int) -> Array:
    """Return the conserved variables of a Kelvin-Helmholtz layer on n by n cells with two ghost cells a side."""
    x = (np.arange(-2, n + 2) + 0.5) / n
    xx, yy = np.meshgrid(x, x)
    band = 0.5 * (np.tanh((yy - 0.25) / 0.05) - np.tanh((yy - 0.75) / 0.05))
    rho = 1.0 + band
    vx = -0.5 + band
    vy = 0.01 * np.sin(4.0 * np.pi * xx) * (np.exp(-((yy - 0.25) / 0.1) ** 2) + np.exp(-((yy - 0.75) / 0.1) ** 2))
    u = np.empty((4, n + 4, n + 4))
    u[0] = rho
    u[1] = rho * vx
    u[2] = rho * vy
    u[3] = 2.5 / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy)
    return u


def fill_ghosts(u: Array) -> None:
    """Fill the two ghost cells on each side from the periodic interior, rows first and columns after."""
    u[:, :2, :] = u[:, -4:-2, :]
    u[:, -2:, :] = u[:, 2:4, :]
    u[:, :, :2] = u[:, :, -4:-2]
    u[:, :, -2:] = u[:, :, 2:4]


def time_step(u: Array) -> float:
    """Return the step that the Courant number allows on the initial state, with dx = dy = 1/n."""
    n = u.shape[1] - 4
    rho = u[0]
    vx, vy = u[1] / rho, u[2] / rho
    c = np.sqrt(GAMMA * (GAMMA - 1.0) * (u[3] - 0.5 * rho * (vx * vx + vy * vy)) / rho)
    fastest = max(float(np.max(np.abs(vx) + c)), float(np.max(np.abs(vy) + c)))
    return COURANT / (n * fastest)


def step(u: Array, u1: Array, du: Array, stage: Stage) -> None:
    """Advance u by one step of Heun's method, u1 and du as scratch."""
    fill_ghosts(u)
    stage(u, du)
    np.add(u, du, out=u1)
    fill_ghosts(u1)
    stage(u1, du)
    np.add(u1, du, out=u1)
    np.add(u, u1, out=u)
    np.multiply(u, 0.5, out=u)


def make_stage(module: ModuleType | None, n: int, dt: float) -> Stage:
    """Return the stage of the compiled module, or of plain NumPy without one, on n by n cells."""
    dtdx = dtdy = dt * n
    if module is None:
        return lambda u, du: vectorised.stage(u, du, GAMMA, dtdx, dtdy)
    kernel: Callable[..., None] = module.stage
    w = np.empty((4, n + 4, n + 4))
    fx, fy = np.empty((4, n, n + 1)), np.empty((4, n + 1, n))
    return lambda u, du: kernel(u, w, fx, fy, du, GAMMA, dtdx, dtdy)


def advanced(module: ModuleType | None, n: int) -> Array:
    """Return the state after one step from the initial state on n by n cells."""
    u = initial_state(n)
    stage = make_stage(module, n, time_step(u))
    u1, du = np.empty_like(u), np.zeros_like(u)
    step(u, u1, du, stage)
    return u


def timings(module: ModuleType, n: int) -> list[float]:
    """Return the times of REPEATS steps on n by n cells, each timed alone, after one step to warm up."""
    u = initial_state(n)
    stage = make_stage(module, n, time_step(u))
    u1, du = np.empty_like(u), np.zeros_like(u)
    step(u, u1, du, stage)
    times: list[float] = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        step(u, u1, du, stage)
        times.append(time.perf_counter() - start)
    return times


## ---- one variant, in a process of its own ----

def worker(variant: str) -> dict[str, Any]:
    """Build one variant, compare it with plain NumPy and time it."""
    pxd, extra = VARIANTS[variant]
    folder = RAW / "build" / variant
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    shutil.copy(HERE / "loops.py", folder)
    shutil.copy(HERE / pxd, folder / "loops.pxd")
    flags = [arg for directive in DIRECTIVES + extra for arg in ("-X", directive)]
    start = time.perf_counter()
    done = subprocess.run([sys.executable, "-m", "Cython.Build.Cythonize", "-i", "-3", *flags, "loops.py"],
                          cwd=folder, capture_output=True, text=True)
    seconds = time.perf_counter() - start
    (RAW / f"build-{variant}.txt").write_text(done.stdout + done.stderr)
    done.check_returncode()
    spec = importlib.util.spec_from_file_location("loops", next(folder.glob("loops.*.so")))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reference, result = advanced(None, CHECK), advanced(module, CHECK)
    agreement = [float(np.max(np.abs(result[k] - reference[k])) / np.max(np.abs(reference[k]))) for k in range(4)]
    rows = [{"n": n, "times": timings(module, n)} for n in SIZES]
    return {"variant": variant, "seconds": seconds, "agreement": agreement, "rows": rows}


## ---- the experiment ----

def lines(path: Path) -> int:
    """Count the lines of a file .pxd without blank lines and comments."""
    return sum(1 for line in path.read_text().splitlines() if line.strip() and not line.strip().startswith("#"))


def environment() -> dict[str, str]:
    """Return what produced the results: date, Python and its build, Cython, machine, compiler and commit."""
    def output(command: list[str]) -> str:
        return subprocess.run(command, capture_output=True, text=True).stdout.strip()
    dirty = output(["git", "status", "--porcelain", "--untracked-files=no"])
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "free_threaded": str(bool(sysconfig.get_config_var("Py_GIL_DISABLED"))),
        "numpy": importlib.metadata.version("numpy"),
        "cython": importlib.metadata.version("cython"),
        "uv": output(["uv", "--version"]),
        "machine": f"{platform.system()} {platform.release()}, {platform.machine()}, "
                   f"{output(['sysctl', '-n', 'machdep.cpu.brand_string'])}",
        "compiler": output(["clang", "--version"]).splitlines()[0],
        "commit": output(["git", "rev-parse", "--short", "HEAD"]) + (" (modified)" if dirty else ""),
    }


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    """Write rows of equal keys to a file of results."""
    with open(RESULTS / name, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        print(json.dumps(worker(sys.argv[2])))
        return
    RAW.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for variant in VARIANTS:
        done = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", variant], cwd=HERE,
                              env=os.environ | THREADS, capture_output=True, text=True)
        (RAW / f"worker-{variant}.txt").write_text(done.stdout + done.stderr)
        if done.returncode == 0:
            results.append(json.loads(done.stdout.strip().splitlines()[-1]))
        print(variant, "done" if done.returncode == 0 else "failed", flush=True)
    rates: list[dict[str, Any]] = []
    for r in results:
        for row in r["rows"]:
            n, times = row["n"], row["times"]
            median = statistics.median(times)
            rates.append({"variant": r["variant"], "cells": n * n, "median_s": f"{median:.6f}",
                          "min_s": f"{min(times):.6f}", "max_s": f"{max(times):.6f}",
                          "rate_per_s": f"{n * n / median:.4g}", "hours": f"{UPDATES * median / (n * n) / 3600:.3g}"})
    write_csv("rates.csv", rates)
    write_csv("agreement.csv", [{"variant": r["variant"],
                                 **{v: f"{d:.3g}" for v, d in zip(("rho", "mx", "my", "energy"), r["agreement"])}}
                                for r in results])
    write_csv("builds.csv", [{"variant": v, "pxd": VARIANTS[v][0], "directives": " ".join(VARIANTS[v][1]) or "none",
                              "built": str(any(r["variant"] == v for r in results)),
                              "seconds": next((f"{r['seconds']:.2f}" for r in results if r["variant"] == v), "")}
                             for v in VARIANTS])
    counts = {name: lines(HERE / name) for name in ("full.pxd", "signatures.pxd")}
    (RESULTS / "lines.json").write_text(json.dumps(counts, indent=2) + "\n")
    (RESULTS / "environment.json").write_text(json.dumps(environment(), indent=2) + "\n")
    print((RESULTS / "rates.csv").read_text())


if __name__ == "__main__":
    main()
