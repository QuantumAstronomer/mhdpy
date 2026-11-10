# pyright: strict
# /// script
# requires-python = ">=3.14"
# dependencies = ["numpy>=2.1", "cython>=3.1"]
# ///
"""B3E2: the rate of the step of B2E1 for each share of B3D2, on one thread and on six, on two problems.

Run without arguments, it makes an environment for each version of Python, compiles the kernels in it, and launches
a worker that runs every case, gathering the results in results/.
"""

import ast
import csv
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
from typing import Any, cast

import numpy as np

import vectorised
from blocks import Blocks
from common import Array, Kernels, Setup, Share, fill_ghosts
from loops import Loops
from parts import Parts

HERE = Path(__file__).parent
RESULTS = HERE / "results"
RAW = RESULTS / "raw"
PYTHONS = ["3.14", "3.14t"]
PACKAGES = ["numpy", "cython", "setuptools"]
GRIDS = {2048: [64, 128, 256, 512, 1024, 0], 512: [64, 128, 256, 0]}  ## the sizes of the blocks of C, 0 for slabs
SLABS = 6
THREADS = [1, 6]
REPEATS = 7
GAMMA = 5.0 / 3.0
COURANT = 0.4
SUBSTEPS = 50  ## the substeps of the source of the uneven problem
RATE = 1e-6  ## the constant c of that source, de/dt = -c e^(1/2)
LIMITS = {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                 "VECLIB_MAXIMUM_THREADS")}
DIRECTIVES = ["boundscheck=False", "wraparound=False", "cdivision=True", "cpow=True", "annotation_typing=False",
              "freethreading_compatible=True"]

type Case = tuple[str, int, str, int, int]


def cases() -> list[Case]:
    """Return every case as its problem, its cells along a side, its share, its size of block and its threads."""
    found: list[Case] = []
    for n, sizes in GRIDS.items():
        for t in THREADS:
            found += [("uniform", n, "A", 0, t), ("uniform", n, "B", 0, t)]
            found += [("uniform", n, "C", b, t) for b in sizes]
    found.append(("uneven", 2048, "A", 0, 1))
    found += [("uneven", 2048, "A", 0, 6), ("uneven", 2048, "B", 0, 6)]
    found += [("uneven", 2048, "C", b, 6) for b in GRIDS[2048]]
    return found


## ---- the problem and the reference step, those of B2E1 ----

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


def time_step(u: Array) -> float:
    """Return the step that the Courant number allows on the initial state, with dx = dy = 1/n."""
    n = u.shape[1] - 4
    rho = u[0]
    vx, vy = u[1] / rho, u[2] / rho
    c = np.sqrt(GAMMA * (GAMMA - 1.0) * (u[3] - 0.5 * rho * (vx * vx + vy * vy)) / rho)
    fastest = max(float(np.max(np.abs(vx) + c)), float(np.max(np.abs(vy) + c)))
    return COURANT / (n * fastest)


def reference(problem: str, n: int) -> Array:
    """Return the interior after one step of the plain NumPy version of B2E1, followed by the source in NumPy."""
    u = initial_state(n)
    dtdx = time_step(u) * n
    u1, du = np.empty_like(u), np.zeros_like(u)
    fill_ghosts(u)
    vectorised.stage(u, du, GAMMA, dtdx, dtdx)
    np.add(u, du, out=u1)
    fill_ghosts(u1)
    vectorised.stage(u1, du, GAMMA, dtdx, dtdx)
    np.add(u1, du, out=u1)
    np.add(u, u1, out=u)
    np.multiply(u, 0.5, out=u)
    inner = u[:, 2:-2, 2:-2].copy()
    if problem == "uneven":
        dense = inner[0] > 1.5
        e = inner[3][dense]
        for _ in range(SUBSTEPS):
            e = e - RATE * e ** 0.5
        inner[3][dense] = e
    return inner


## ---- the worker: every case on one version of Python ----

def load(label: str) -> Kernels:
    """Return the kernels, loaded from the folder in which they were compiled."""
    library = next((RAW / "build" / label).glob("kernels.*.so"))
    spec = importlib.util.spec_from_file_location("kernels", library)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(Kernels, module)


def share_of(kernels: Kernels, case: Case) -> Share:
    """Return the share of a case on its initial state."""
    problem, n, share, size, threads = case
    u = initial_state(n)
    dtdx = time_step(u) * n
    setup = Setup(kernels, GAMMA, dtdx, dtdx, SUBSTEPS if problem == "uneven" else 0, RATE)
    if share == "A":
        return Loops(u, setup, threads)
    if share == "B":
        return Parts(u, setup, threads)
    ny, nx = (SLABS, 1) if size == 0 else (n // size, n // size)
    return Blocks(u, setup, threads, ny, nx)


def gil() -> bool:
    """Tell whether the GIL is enabled in this interpreter."""
    probe: Callable[[], bool] | None = getattr(sys, "_is_gil_enabled", None)
    return True if probe is None else probe()


def worker(label: str) -> dict[str, Any]:
    """Check and time every case, and return the results."""
    kernels = load(label)
    references: dict[tuple[str, int], Array] = {}
    done: list[dict[str, Any]] = []
    for case in cases():
        problem, n, share, size, threads = case
        if (problem, n) not in references:
            references[(problem, n)] = reference(problem, n)
        expected = references[(problem, n)]
        steps = share_of(kernels, case)
        steps.step()
        result = steps.interior()
        differences = [float(np.max(np.abs(result[k] - expected[k])) / np.max(np.abs(expected[k]))) for k in range(4)]
        times: list[float] = []
        for _ in range(REPEATS):
            begin = time.perf_counter()
            steps.step()
            times.append(time.perf_counter() - begin)
        steps.close()
        done.append({"problem": problem, "n": n, "share": share, "block": size, "threads": threads,
                     "differences": differences, "times": times})
        print(label, *case, f"{statistics.median(times):.4f} s", file=sys.stderr, flush=True)
    return {"python": label, "version": sys.version.split()[0], "gil": gil(), "cases": done}


## ---- the experiment ----

def prepare(label: str) -> tuple[Path, list[dict[str, str]]]:
    """Make an environment for one version of Python, install each package into it from wheels alone, and record it."""
    env = RAW / f"env-{label}"
    shutil.rmtree(env, ignore_errors=True)
    subprocess.run(["uv", "venv", "--quiet", "--python", label, str(env)], check=True)
    python = env / "bin" / "python"
    installed: list[dict[str, str]] = []
    for package in PACKAGES:
        done = subprocess.run(["uv", "pip", "install", "--quiet", "--no-build", "--python", str(python), package],
                              capture_output=True, text=True)
        probe = f"import importlib.metadata as m; print(m.version('{package}'))"
        version = subprocess.run([str(python), "-c", probe], capture_output=True, text=True).stdout.strip()
        installed.append({"python": label, "package": package, "from_wheels": str(done.returncode == 0),
                          "version": version})
    return python, installed


def build(python: Path, label: str) -> float:
    """Compile the kernels by Cython in the folder of their version of Python, and return the time taken."""
    folder = RAW / "build" / label
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for suffix in (".py", ".pxd"):
        shutil.copy(HERE / f"kernels{suffix}", folder)
    flags = [arg for directive in DIRECTIVES for arg in ("-X", directive)]
    start = time.perf_counter()
    done = subprocess.run([str(python), "-m", "Cython.Build.Cythonize", "-i", "-3", *flags, "kernels.py"],
                          cwd=folder, capture_output=True, text=True)
    seconds = time.perf_counter() - start
    (RAW / "logs" / f"build-{label}.txt").write_text(done.stdout + done.stderr)
    done.check_returncode()
    return seconds


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
        "cores": f"{output(['sysctl', '-n', 'hw.physicalcpu'])} cores, {output(['sysctl', '-n', 'hw.logicalcpu'])} "
                 f"threads, {int(output(['sysctl', '-n', 'hw.memsize'])) // 2**30} GB",
        "compiler": output(["clang", "--version"]).splitlines()[0],
        "commit": output(["git", "rev-parse", "--short", "HEAD"]) + (" (modified)" if dirty else ""),
    }


def write_csv(name: str, table: list[dict[str, Any]]) -> None:
    """Write rows of equal keys to a file of results."""
    with open(RESULTS / name, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        print(json.dumps(worker(sys.argv[2])))
        return
    (RAW / "logs").mkdir(parents=True, exist_ok=True)
    env = os.environ | LIMITS
    installs: list[dict[str, str]] = []
    builds: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []
    for label in PYTHONS:
        python, installed = prepare(label)
        installs += installed
        seconds = build(python, label)
        with open(RAW / "logs" / f"worker-{label}.txt", "w") as log:
            done = subprocess.run([str(python), str(HERE / "run.py"), "--worker", label], cwd=HERE, env=env,
                                  stdout=subprocess.PIPE, stderr=log, text=True)
        done.check_returncode()
        result = json.loads(done.stdout.strip().splitlines()[-1])
        results.append(result)
        builds.append({"python": label, "version": result["version"], "seconds": f"{seconds:.2f}",
                       "gil": str(result["gil"])})
        print(label, "done", flush=True)
    serial = {(r["python"], c["problem"], c["n"]): statistics.median(c["times"])
              for r in results for c in r["cases"] if c["share"] == "A" and c["threads"] == 1}
    rates: list[dict[str, Any]] = []
    agreement: list[dict[str, Any]] = []
    for r in results:
        for c in r["cases"]:
            n, median = c["n"], statistics.median(c["times"])
            block = "" if c["share"] != "C" else ("slabs" if c["block"] == 0 else str(c["block"]))
            key = {"problem": c["problem"], "cells": n * n, "share": c["share"], "block": block,
                   "python": r["python"], "threads": c["threads"]}
            rates.append(key | {"median_s": f"{median:.6f}", "min_s": f"{min(c['times']):.6f}",
                                "max_s": f"{max(c['times']):.6f}", "rate_per_s": f"{n * n / median:.4g}",
                                "speed_up": f"{serial[(r['python'], c['problem'], n)] / median:.3g}"})
            agreement.append(key | {v: f"{d:.3g}" for v, d in zip(("rho", "mx", "my", "energy"), c["differences"])})
    write_csv("rates.csv", rates)
    write_csv("agreement.csv", agreement)
    write_csv("builds.csv", builds)
    write_csv("installs.csv", installs)
    counts = {name: lines(HERE / name) for name in ("loops.py", "parts.py", "blocks.py", "common.py")}
    (RESULTS / "lines.json").write_text(json.dumps(counts, indent=2) + "\n")
    (RESULTS / "environment.json").write_text(json.dumps(environment(), indent=2) + "\n")
    print((RESULTS / "rates.csv").read_text())


if __name__ == "__main__":
    main()
