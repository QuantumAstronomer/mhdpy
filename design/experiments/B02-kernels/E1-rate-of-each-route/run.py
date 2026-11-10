# pyright: strict
# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy>=2.1"]
# ///
"""B2E1: the rate of cell updates of one step of hydrodynamics in two dimensions in each route, and its installation.

Run without arguments, it starts one worker for each route and version of Python, each in an environment that uv
builds with the packages of its route, and gathers their results in results/.
"""

import ast
import csv
import importlib
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

import inplace
import vectorised

type Array = NDArray[np.float64]
type Stage = Callable[[Array, Array], None]

HERE = Path(__file__).parent
RESULTS = HERE / "results"
RAW = RESULTS / "raw"
PYTHONS = ["3.13", "3.14", "3.14t"]
ROUTES = ["numpy", "inplace", "loop", "numba", "cython", "pythran"]
EXTRAS = {"numpy": [], "inplace": [], "loop": [], "numba": ["numba"], "cython": ["cython", "setuptools"],
          "pythran": ["pythran", "setuptools"]}
SIZES = [64, 128, 256, 512, 1024, 2048]
LOOP_SIZES = [64, 128]  ## the uncompiled loop on the two smallest grids alone
CHECK = 128  ## the grid on which every version is compared with plain NumPy
REPEATS = 7
GAMMA = 5.0 / 3.0
COURANT = 0.4
UPDATES = 9e10  ## the cell updates of the production run, topic 42, §4
THREADS = {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                  "VECLIB_MAXIMUM_THREADS", "NUMBA_NUM_THREADS")}
DIRECTIVES = ["boundscheck=False", "wraparound=False", "cdivision=True", "cpow=True", "annotation_typing=False",
              "freethreading_compatible=True"]


## ---- the problem and the step, the same for every version ----

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
    ## the second stage averages u with u1 advanced once more
    np.add(u1, du, out=u1)
    np.add(u, u1, out=u)
    np.multiply(u, 0.5, out=u)


def make_stage(route: str, module: ModuleType | None, n: int, dt: float) -> Stage:
    """Return the stage of one version on n by n cells, its scratch arrays allocated once."""
    dtdx = dtdy = dt * n
    if route == "numpy":
        return lambda u, du: vectorised.stage(u, du, GAMMA, dtdx, dtdy)
    if route == "inplace":
        return inplace.Stage(n, GAMMA, dtdx, dtdy)
    assert module is not None
    kernel: Callable[..., None] = module.stage
    w = np.empty((4, n + 4, n + 4))
    fx, fy = np.empty((4, n, n + 1)), np.empty((4, n + 1, n))
    return lambda u, du: kernel(u, w, fx, fy, du, GAMMA, dtdx, dtdy)


def advanced(route: str, module: ModuleType | None, n: int) -> Array:
    """Return the state after one step from the initial state on n by n cells."""
    u = initial_state(n)
    dt = time_step(u)
    stage = make_stage(route, module, n, dt)
    u1, du = np.empty_like(u), np.zeros_like(u)
    step(u, u1, du, stage)
    return u


def timings(route: str, module: ModuleType | None, n: int) -> list[float]:
    """Return the times of REPEATS steps on n by n cells, each timed alone, after one step to warm up."""
    u = initial_state(n)
    dt = time_step(u)
    stage = make_stage(route, module, n, dt)
    u1, du = np.empty_like(u), np.zeros_like(u)
    step(u, u1, du, stage)
    times: list[float] = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        step(u, u1, du, stage)
        times.append(time.perf_counter() - start)
    return times


## ---- the worker: one route on one version of Python ----

def build(route: str, label: str) -> tuple[ModuleType, float]:
    """Compile loops.py by Cython or Pythran in a folder of its own, and return the module and the build time."""
    folder = RAW / "build" / f"{route}-{label}"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    shutil.copy(HERE / "loops.py", folder)
    if route == "cython":
        shutil.copy(HERE / "loops.pxd", folder)
        flags = [arg for directive in DIRECTIVES for arg in ("-X", directive)]
        command = [sys.executable, "-m", "Cython.Build.Cythonize", "-i", "-3", *flags, "loops.py"]
    else:
        command = [str(Path(sys.executable).parent / "pythran"), "loops.py"]
    start = time.perf_counter()
    done = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    seconds = time.perf_counter() - start
    (RAW / "logs" / f"build-{route}-{label}.txt").write_text(done.stdout + done.stderr)
    done.check_returncode()
    library = next(folder.glob("loops.*.so"))
    spec = importlib.util.spec_from_file_location("loops", library)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, seconds


def gil() -> bool:
    """Tell whether the GIL is enabled in this interpreter."""
    probe: Callable[[], bool] | None = getattr(sys, "_is_gil_enabled", None)
    return True if probe is None else probe()


def worker(route: str, label: str) -> dict[str, Any]:
    """Load, check and time one route, and return its results."""
    gil_before = gil()
    seconds = None
    module: ModuleType | None = None
    if route in ("loop", "numba"):
        module = importlib.import_module("loops")
    if route == "numba":
        numba = importlib.import_module("numba")
        for name in ("limit", "face", "hlle", "stage"):
            setattr(module, name, numba.njit(getattr(module, name)))
        start = time.perf_counter()
        advanced(route, module, 16)
        seconds = time.perf_counter() - start
    if route in ("cython", "pythran"):
        module, seconds = build(route, label)
    reference = advanced("numpy", None, CHECK)
    result = advanced(route, module, CHECK)
    agreement = [float(np.max(np.abs(result[k] - reference[k])) / np.max(np.abs(reference[k]))) for k in range(4)]
    rows = [{"n": n, "times": timings(route, module, n)} for n in (LOOP_SIZES if route == "loop" else SIZES)]
    versions = {name: importlib.metadata.version(name) for name in ["numpy", *EXTRAS[route]]}
    return {"route": route, "python": label, "version": sys.version.split()[0], "packages": versions,
            "seconds": seconds, "gil_before": gil_before, "gil_after": gil(), "agreement": agreement, "rows": rows}


## ---- the experiment ----

def installs() -> list[dict[str, str]]:
    """Record for each version of Python whether each package installs from wheels alone, and its version."""
    rows: list[dict[str, str]] = []
    for label in PYTHONS:
        for package in ("numpy", "cython", "pythran", "numba"):
            probe = f"import importlib.metadata as m; print(m.version('{package}'))"
            done = subprocess.run(["uv", "run", "--no-project", "--no-build", "--python", label, "--with", package,
                                   "python", "-c", probe], capture_output=True, text=True)
            version = done.stdout.strip().splitlines()[-1] if done.returncode == 0 else ""
            rows.append({"python": label, "package": package, "from_wheels": str(done.returncode == 0),
                         "version": version})
    return rows


def lines(path: Path) -> int:
    """Count the lines of a module without blank lines, comments and docstrings."""
    text = path.read_text()
    skipped: set[int] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                skipped.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return sum(1 for number, line in enumerate(text.splitlines(), 1)
               if line.strip() and not line.strip().startswith("#") and number not in skipped)


def environment() -> dict[str, str]:
    """Return what produced the results: date, Python and its build, uv, machine, compiler and commit."""
    def output(command: list[str]) -> str:
        return subprocess.run(command, capture_output=True, text=True).stdout.strip()
    dirty = output(["git", "status", "--porcelain", "--untracked-files=no"])
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "free_threaded": str(bool(sysconfig.get_config_var("Py_GIL_DISABLED"))),
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
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        print(json.dumps(worker(sys.argv[2], sys.argv[3])))
        return
    (RAW / "logs").mkdir(parents=True, exist_ok=True)
    env = os.environ | THREADS
    results: list[dict[str, Any]] = []
    absent: list[dict[str, str]] = []
    for label in PYTHONS:
        for route in ROUTES:
            extras = [arg for package in EXTRAS[route] for arg in ("--with", package)]
            command = ["uv", "run", "--no-build", "--python", label, *extras, str(Path(__file__).resolve()),
                       "--worker", route, label]
            done = subprocess.run(command, cwd=HERE, env=env, capture_output=True, text=True)
            (RAW / "logs" / f"worker-{route}-{label}.txt").write_text(done.stdout + done.stderr)
            if done.returncode == 0:
                results.append(json.loads(done.stdout.strip().splitlines()[-1]))
            else:
                reason = (done.stderr.strip().splitlines() or [""])[-1]
                absent.append({"route": route, "python": label, "reason": reason})
            print(route, label, "done" if done.returncode == 0 else "failed", flush=True)
    rates: list[dict[str, Any]] = []
    for r in results:
        for row in r["rows"]:
            n, times = row["n"], row["times"]
            median = statistics.median(times)
            rates.append({"route": r["route"], "python": r["python"], "cells": n * n, "median_s": f"{median:.6f}",
                          "min_s": f"{min(times):.6f}", "max_s": f"{max(times):.6f}",
                          "rate_per_s": f"{n * n / median:.4g}", "hours": f"{UPDATES * median / (n * n) / 3600:.3g}"})
    write_csv("rates.csv", rates)
    write_csv("agreement.csv", [{"route": r["route"], "python": r["python"],
                                 **{v: f"{d:.3g}" for v, d in zip(("rho", "mx", "my", "energy"), r["agreement"])}}
                                for r in results])
    write_csv("builds.csv", [{"route": r["route"], "python": r["python"], "version": r["version"],
                              "packages": " ".join(f"{k} {v}" for k, v in r["packages"].items()),
                              "seconds": "" if r["seconds"] is None else f"{r['seconds']:.2f}",
                              "gil_before": str(r["gil_before"]), "gil_after": str(r["gil_after"])}
                             for r in results])
    if absent:
        write_csv("absent.csv", absent)
    write_csv("installs.csv", installs())
    pxd = [line for line in (HERE / "loops.pxd").read_text().splitlines() if line.strip() and not line.startswith("#")]
    exports = [line for line in (HERE / "loops.py").read_text().splitlines() if line.startswith("#pythran export")]
    counts = {name: lines(HERE / name) for name in ("vectorised.py", "inplace.py", "loops.py")}
    (RESULTS / "lines.json").write_text(json.dumps(counts | {"loops.pxd": len(pxd), "pythran export": len(exports)},
                                                   indent=2) + "\n")
    (RESULTS / "environment.json").write_text(json.dumps(environment(), indent=2) + "\n")
    print((RESULTS / "rates.csv").read_text())


if __name__ == "__main__":
    main()
