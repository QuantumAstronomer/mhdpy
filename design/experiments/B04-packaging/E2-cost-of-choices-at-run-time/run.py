# pyright: strict
# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy>=2.1", "cython>=3.1", "setuptools"]
# ///
"""B4E2: the rate of the stage of B2E2 with passive scalars when its choices are fixed as it is compiled, given as
a run starts, or, for the solver, made at each face through a pointer.

Run without arguments, it builds each variant, checks and times each in a process of its own, and gathers the
results in results/.
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
## each build: the module, and the number of scalars that its config.h fixes, or None where it takes it as an argument
BUILDS: dict[str, tuple[str, int | None]] = {"fixed-0": ("fixed", 0), "fixed-1": ("fixed", 1),
                                              "given": ("given", None), "pointer": ("pointer", None)}
## each worker: the variant, its build, and the number of scalars that it carries
WORKERS = [(variant, build, n) for n in (0, 1)
           for variant, build in (("fixed", f"fixed-{n}"), ("given", "given"), ("pointer", "pointer"))]
DIRECTIVES = ["boundscheck=False", "wraparound=False", "cdivision=True", "cpow=True", "annotation_typing=False",
              "infer_types=True", "freethreading_compatible=True"]
SIZES = [256, 2048]
CHECK = 128
REPEATS = 7
GAMMA = 5.0 / 3.0
COURANT = 0.4
UPDATES = 9e10  ## the cell updates of the production run, topic 42, §4
THREADS = {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                  "VECLIB_MAXIMUM_THREADS")}


## ---- the problem and the step of B2E2, with passive scalars ----

def initial_state(n: int, scalars: int) -> Array:
    """Return the conserved variables of the Kelvin-Helmholtz layer of B2E2 on n by n cells with two ghost cells a
    side, followed by the given number of scalars, each the concentration of the dense layer."""
    x = (np.arange(-2, n + 2) + 0.5) / n
    xx, yy = np.meshgrid(x, x)
    band = 0.5 * (np.tanh((yy - 0.25) / 0.05) - np.tanh((yy - 0.75) / 0.05))
    rho = 1.0 + band
    vx = -0.5 + band
    vy = 0.01 * np.sin(4.0 * np.pi * xx) * (np.exp(-((yy - 0.25) / 0.1) ** 2) + np.exp(-((yy - 0.75) / 0.1) ** 2))
    u = np.empty((4 + scalars, n + 4, n + 4))
    u[0] = rho
    u[1] = rho * vx
    u[2] = rho * vy
    u[3] = 2.5 / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy)
    for s in range(scalars):
        u[4 + s] = rho * (rho - 1.0)
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


def make_stage(variant: str, module: ModuleType | None, n: int, scalars: int, dt: float) -> Stage:
    """Return the stage of a variant, or of plain NumPy without a module, on n by n cells with the given scalars."""
    dtdx = dtdy = dt * n
    if module is None:
        return lambda u, du: vectorised.stage(u, du, GAMMA, dtdx, dtdy)
    kernel: Callable[..., None] = module.stage
    w = np.empty((4 + scalars, n + 4, n + 4))
    fx, fy = np.empty((4 + scalars, n, n + 1)), np.empty((4 + scalars, n + 1, n))
    if variant == "fixed":
        return lambda u, du: kernel(u, w, fx, fy, du, dtdx, dtdy)
    if variant == "pointer":
        choose: Callable[[str], None] = module.choose
        choose("hlle")
    return lambda u, du: kernel(u, w, fx, fy, du, GAMMA, scalars, dtdx, dtdy)


def advanced(variant: str, module: ModuleType | None, n: int, scalars: int) -> Array:
    """Return the state after one step from the initial state on n by n cells."""
    u = initial_state(n, scalars)
    stage = make_stage(variant, module, n, scalars, time_step(u))
    u1, du = np.empty_like(u), np.zeros_like(u)
    step(u, u1, du, stage)
    return u


def timings(variant: str, module: ModuleType, n: int, scalars: int) -> list[float]:
    """Return the times of REPEATS steps on n by n cells, each timed alone, after one step to warm up."""
    u = initial_state(n, scalars)
    stage = make_stage(variant, module, n, scalars, time_step(u))
    u1, du = np.empty_like(u), np.zeros_like(u)
    step(u, u1, du, stage)
    times: list[float] = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        step(u, u1, du, stage)
        times.append(time.perf_counter() - start)
    return times


def difference(a: Array, b: Array) -> float:
    """Return the largest difference of two states, relative to the largest value of each variable of b."""
    return max(float(np.max(np.abs(a[k] - b[k])) / np.max(np.abs(b[k]))) for k in range(b.shape[0]))


## ---- one build, and one variant with its scalars in a process of its own ----

def build(name: str) -> float:
    """Compile one build of a variant in its folder, with the config.h of its number of scalars, and return its seconds."""
    module, scalars = BUILDS[name]
    folder = RAW / "build" / name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for suffix in (".py", ".pxd"):
        shutil.copy(HERE / f"{module}{suffix}", folder)
    if scalars is not None:
        (folder / "config.h").write_text(f"#define GAMMA (5.0 / 3.0)\n#define NSCALARS {scalars}\n")
    flags = [arg for directive in DIRECTIVES for arg in ("-X", directive)]
    start = time.perf_counter()
    done = subprocess.run([sys.executable, "-m", "Cython.Build.Cythonize", "-i", "-3", *flags, f"{module}.py"],
                          cwd=folder, capture_output=True, text=True)
    seconds = time.perf_counter() - start
    (RAW / f"build-{name}.txt").write_text(done.stdout + done.stderr)
    done.check_returncode()
    return seconds


def load(name: str) -> ModuleType:
    """Import the compiled module of a build from its folder."""
    module = BUILDS[name][0]
    spec = importlib.util.spec_from_file_location(module, next((RAW / "build" / name).glob(f"{module}.*.so")))
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def worker(variant: str, name: str, scalars: int) -> dict[str, Any]:
    """Check one variant against the variant given, and against plain NumPy without scalars, then time it."""
    module = load(name)
    if variant == "fixed":
        fixed: Callable[[], int] = module.nscalars
        assert fixed() == scalars, "config.h fixed another number of scalars"
    result = advanced(variant, module, CHECK, scalars)
    given = result if variant == "given" else advanced("given", load("given"), CHECK, scalars)
    plain = difference(result, advanced(variant, None, CHECK, 0)) if scalars == 0 else None
    rows = [{"n": n, "times": timings(variant, module, n, scalars)} for n in SIZES]
    return {"variant": variant, "scalars": scalars, "given": difference(result, given), "numpy": plain, "rows": rows}


## ---- the experiment ----

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
        "setuptools": importlib.metadata.version("setuptools"),
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
    if len(sys.argv) == 5 and sys.argv[1] == "--worker":
        print(json.dumps(worker(sys.argv[2], sys.argv[3], int(sys.argv[4]))))
        return
    RAW.mkdir(parents=True, exist_ok=True)
    builds = [{"build": name, "module": BUILDS[name][0], "seconds": f"{build(name):.2f}"} for name in BUILDS]
    results: list[dict[str, Any]] = []
    for variant, name, scalars in WORKERS:
        done = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", variant, name, str(scalars)],
                              cwd=HERE, env=os.environ | THREADS, capture_output=True, text=True)
        (RAW / f"worker-{variant}-{scalars}.txt").write_text(done.stdout + done.stderr)
        if done.returncode == 0:
            results.append(json.loads(done.stdout.strip().splitlines()[-1]))
        print(variant, scalars, "done" if done.returncode == 0 else "failed", flush=True)
    rates: list[dict[str, Any]] = []
    for r in results:
        for row in r["rows"]:
            n, times = row["n"], row["times"]
            median = statistics.median(times)
            rates.append({"variant": r["variant"], "scalars": r["scalars"], "cells": n * n,
                          "median_s": f"{median:.6f}", "min_s": f"{min(times):.6f}", "max_s": f"{max(times):.6f}",
                          "rate_per_s": f"{n * n / median:.4g}", "hours": f"{UPDATES * median / (n * n) / 3600:.3g}"})
    write_csv("rates.csv", rates)
    write_csv("agreement.csv", [{"variant": r["variant"], "scalars": r["scalars"], "given": f"{r['given']:.3g}",
                                 "numpy": "" if r["numpy"] is None else f"{r['numpy']:.3g}"} for r in results])
    write_csv("builds.csv", builds)
    (RESULTS / "environment.json").write_text(json.dumps(environment(), indent=2) + "\n")
    print((RESULTS / "rates.csv").read_text())
    print((RESULTS / "agreement.csv").read_text())


if __name__ == "__main__":
    main()
