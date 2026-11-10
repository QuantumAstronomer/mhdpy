# pyright: strict
# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy>=2.1", "cython>=3.1", "mpi4py>=4.1"]
# ///
"""B3E1: the speed-up of the step of B2E1 on slabs shared by threads or by processes with MPI, and its installation.

Run without arguments, it makes an environment for each version of Python, compiles the variants of the stage in
it, and launches the workers of each means, gathering their results in results/.
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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import threads
import vectorised
from slabs import Array, Slab, Stage, rows

HERE = Path(__file__).parent
RESULTS = HERE / "results"
RAW = RESULTS / "raw"
PYTHONS = ["3.13", "3.14", "3.14t"]
PACKAGES = ["numpy", "cython", "setuptools", "mpi4py", "mpich"]
KERNELS = {"3.13": ["released"], "3.14": ["released", "held"], "3.14t": ["released", "held"]}
SIZES = [256, 512, 1024, 2048]
WORKERS = [1, 2, 3, 4, 6, 12]
CHECK = 256  ## the grid on which every means is compared with plain NumPy
REPEATS = 7
GAMMA = 5.0 / 3.0
COURANT = 0.4
UPDATES = 9e10  ## the cell updates of the production run, topic 42, §4
THREADS = {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                  "VECLIB_MAXIMUM_THREADS")}
DIRECTIVES = ["boundscheck=False", "wraparound=False", "cdivision=True", "cpow=True", "annotation_typing=False",
              "freethreading_compatible=True"]


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


def reference(n: int) -> Array:
    """Return the interior after one step of the plain NumPy version of B2E1 on one array of n by n cells."""
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
    return u[:, 2:-2, 2:-2]


def differences(result: Array, n: int) -> list[float]:
    """Return the largest difference of each variable from the reference, relative to its largest value."""
    expected = reference(n)
    return [float(np.max(np.abs(result[k] - expected[k])) / np.max(np.abs(expected[k]))) for k in range(4)]


## ---- the workers: one means on one version of Python ----

def load(label: str, kernel: str) -> Stage:
    """Return the stage of a variant, loaded from the folder in which it was compiled."""
    library = next((RAW / "build" / label).glob(f"{kernel}.*.so"))
    spec = importlib.util.spec_from_file_location(kernel, library)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stage: Stage = module.stage
    return stage


def slabs_of(stage: Stage, n: int, p: int, ks: range) -> list[Slab]:
    """Return the slabs ks of the p slabs of the initial state on n by n cells, each with its own arrays."""
    u = initial_state(n)
    dtdx = time_step(u) * n
    bounds = rows(n, p)
    return [Slab(u[:, bounds[k][0]:bounds[k][1] + 4, :].copy(), stage, GAMMA, dtdx, dtdx) for k in ks]


def gil() -> bool:
    """Tell whether the GIL is enabled in this interpreter."""
    probe: Callable[[], bool] | None = getattr(sys, "_is_gil_enabled", None)
    return True if probe is None else probe()


def thread_worker(label: str, kernel: str, launched: float) -> dict[str, Any]:
    """Check and time the threads on every number of workers and grid, and return the results."""
    stage = load(label, kernel)
    start = time.time() - launched
    agreement: list[dict[str, Any]] = []
    timed: list[dict[str, Any]] = []
    for p in WORKERS:
        with ThreadPoolExecutor(max_workers=p) as pool:
            slabs = slabs_of(stage, CHECK, p, range(p))
            threads.step(slabs, pool)
            result = np.concatenate([slab.u[:, 2:-2, 2:-2] for slab in slabs], axis=1)
            agreement.append({"workers": p, "differences": differences(result, CHECK)})
            for n in SIZES:
                slabs = slabs_of(stage, n, p, range(p))
                threads.step(slabs, pool)
                times: list[float] = []
                for _ in range(REPEATS):
                    begin = time.perf_counter()
                    threads.step(slabs, pool)
                    times.append(time.perf_counter() - begin)
                timed.append({"workers": p, "n": n, "times": times})
    return {"means": "threads", "kernel": kernel, "python": label, "workers": WORKERS[0], "start": start,
            "gil": gil(), "agreement": agreement, "rows": timed}


def mpi_worker(label: str, launched: float) -> None:
    """Check and time the processes of one launch, and print their results from the first of them."""
    from mpi4py import MPI

    import processes
    comm = MPI.COMM_WORLD
    rank, p = comm.Get_rank(), comm.Get_size()
    stage = load(label, "released")
    comm.Barrier()
    start = time.time() - launched
    slab = slabs_of(stage, CHECK, p, range(rank, rank + 1))[0]
    processes.step(slab, comm)
    parts: list[Array] | None = comm.gather(slab.u[:, 2:-2, 2:-2].copy(), root=0)
    timed: list[dict[str, Any]] = []
    for n in SIZES:
        slab = slabs_of(stage, n, p, range(rank, rank + 1))[0]
        processes.step(slab, comm)
        times: list[float] = []
        for _ in range(REPEATS):
            comm.Barrier()
            begin = time.perf_counter()
            processes.step(slab, comm)
            comm.Barrier()
            times.append(time.perf_counter() - begin)
        timed.append({"workers": p, "n": n, "times": times})
    if parts is not None:
        agreement = [{"workers": p, "differences": differences(np.concatenate(parts, axis=1), CHECK)}]
        print(json.dumps({"means": "mpi", "kernel": "released", "python": label, "workers": p, "start": start,
                          "gil": gil(), "agreement": agreement, "rows": timed}))


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


def build(python: Path, label: str, kernel: str) -> float:
    """Compile a variant of the stage by Cython in the folder of its version of Python, and return the time taken."""
    folder = RAW / "build" / label
    folder.mkdir(parents=True, exist_ok=True)
    for suffix in (".py", ".pxd"):
        shutil.copy(HERE / f"{kernel}{suffix}", folder)
    flags = [arg for directive in DIRECTIVES for arg in ("-X", directive)]
    start = time.perf_counter()
    done = subprocess.run([str(python), "-m", "Cython.Build.Cythonize", "-i", "-3", *flags, f"{kernel}.py"],
                          cwd=folder, capture_output=True, text=True)
    seconds = time.perf_counter() - start
    (RAW / "logs" / f"build-{kernel}-{label}.txt").write_text(done.stdout + done.stderr)
    done.check_returncode()
    return seconds


def launch(command: list[str], name: str, env: dict[str, str]) -> dict[str, Any] | None:
    """Run a worker with the time of its launch as its last argument, and return its results, or None if it fails."""
    done = subprocess.run([*command, str(time.time())], cwd=HERE, env=env, capture_output=True, text=True)
    (RAW / "logs" / f"worker-{name}.txt").write_text(done.stdout + done.stderr)
    print(name, "done" if done.returncode == 0 else "failed", flush=True)
    return json.loads(done.stdout.strip().splitlines()[-1]) if done.returncode == 0 else None


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
    if len(sys.argv) == 5 and sys.argv[1] == "--threads":
        print(json.dumps(thread_worker(sys.argv[2], sys.argv[3], float(sys.argv[4]))))
        return
    if len(sys.argv) == 4 and sys.argv[1] == "--mpi":
        mpi_worker(sys.argv[2], float(sys.argv[3]))
        return
    (RAW / "logs").mkdir(parents=True, exist_ok=True)
    env = os.environ | THREADS
    installs: list[dict[str, str]] = []
    builds: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []
    absent: list[dict[str, str]] = []
    for label in PYTHONS:
        python, installed = prepare(label)
        installs += installed
        for kernel in KERNELS[label]:
            builds.append({"python": label, "kernel": kernel, "seconds": f"{build(python, label, kernel):.2f}"})
        commands = {f"threads-{kernel}-{label}": [str(python), str(HERE / "run.py"), "--threads", label, kernel]
                    for kernel in KERNELS[label]}
        commands |= {f"mpi-{p}-{label}": [str(python.parent / "mpiexec"), "-n", str(p), str(python),
                                          str(HERE / "run.py"), "--mpi", label] for p in WORKERS}
        for name, command in commands.items():
            result = launch(command, name, env)
            if result is None:
                absent.append({"worker": name})
            else:
                results.append(result)
    one = {(r["means"], r["kernel"], r["python"], row["n"]): statistics.median(row["times"])
           for r in results for row in r["rows"] if row["workers"] == 1}
    rates: list[dict[str, Any]] = []
    for r in results:
        for row in r["rows"]:
            n, median = row["n"], statistics.median(row["times"])
            serial = one.get((r["means"], r["kernel"], r["python"], n))
            rates.append({"means": r["means"], "kernel": r["kernel"], "python": r["python"], "workers": row["workers"],
                          "cells": n * n, "median_s": f"{median:.6f}", "min_s": f"{min(row['times']):.6f}",
                          "max_s": f"{max(row['times']):.6f}", "rate_per_s": f"{n * n / median:.4g}",
                          "speed_up": "" if serial is None else f"{serial / median:.3g}",
                          "hours": f"{UPDATES * median / (n * n) / 3600:.3g}"})
    rates.sort(key=lambda row: (row["means"], row["kernel"], row["python"], row["cells"], row["workers"]))
    write_csv("rates.csv", rates)
    write_csv("agreement.csv", [{"means": r["means"], "kernel": r["kernel"], "python": r["python"],
                                 "workers": a["workers"],
                                 **{v: f"{d:.3g}" for v, d in zip(("rho", "mx", "my", "energy"), a["differences"])}}
                                for r in results for a in r["agreement"]])
    write_csv("starts.csv", [{"means": r["means"], "kernel": r["kernel"], "python": r["python"],
                              "workers": r["workers"], "seconds": f"{r['start']:.2f}", "gil": str(r["gil"])}
                             for r in results])
    write_csv("builds.csv", builds)
    write_csv("installs.csv", installs)
    if absent:
        write_csv("absent.csv", absent)
    counts = {name: lines(HERE / name) for name in ("threads.py", "processes.py", "slabs.py")}
    (RESULTS / "lines.json").write_text(json.dumps(counts, indent=2) + "\n")
    (RESULTS / "environment.json").write_text(json.dumps(environment(), indent=2) + "\n")
    print((RESULTS / "rates.csv").read_text())


if __name__ == "__main__":
    main()
