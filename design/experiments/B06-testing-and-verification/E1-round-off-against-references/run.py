# pyright: strict
# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy>=2.1", "cython>=3.1", "setuptools"]
# ///
"""B6E1: round-off between the stage of B2E2, compiled with and without fused multiply-adds, and two versions in NumPy.

Run without arguments, it builds each variant, runs each version in a process of its own and gathers the differences
after one stage and over 64 steps in results/.
"""

import csv
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import sysconfig
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from numpy.typing import NDArray

import reordered
import vectorised

type Array = NDArray[np.float64]
type Stage = Callable[[Array, Array], None]

HERE = Path(__file__).parent
RESULTS = HERE / "results"
RAW = RESULTS / "raw"
## each build of loops.py and the flags that it gives to clang through CFLAGS
BUILDS: dict[str, list[str]] = {"plain": [], "within": ["-mfma"], "across": ["-mfma", "-ffp-contract=fast"]}
REFERENCES = ("vectorised", "reordered")
DIRECTIVES = ["boundscheck=False", "wraparound=False", "cdivision=True", "cpow=True", "annotation_typing=False",
              "freethreading_compatible=True", "infer_types=True"]
SIZES = [128, 512]
STEPS = [1, 2, 4, 8, 16, 32, 64]
GAMMA = 5.0 / 3.0
COURANT = 0.4
EPSILON = 2.0 ** -52
VARIABLES = ("rho", "mx", "my", "energy")
## the pairs compared: each build and the reordered version with plain NumPy, then each build with the reordered one
PAIRS = [(b, "vectorised") for b in BUILDS] + [("reordered", "vectorised")] + [(b, "reordered") for b in BUILDS]
## the instructions of fusion on x86-64: vfmadd, vfmsub, vfnmadd and vfnmsub, in all their forms
FUSED = re.compile(r"\bvfn?m(?:add|sub)")
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


def make_stage(version: str, n: int, dt: float) -> Stage:
    """Return the stage of one version on n by n cells: a build of loops.py or a version in NumPy."""
    dtdx = dtdy = dt * n
    if version == "vectorised":
        return lambda u, du: vectorised.stage(u, du, GAMMA, dtdx, dtdy)
    if version == "reordered":
        return lambda u, du: reordered.stage(u, du, GAMMA, dtdx, dtdy)
    spec = importlib.util.spec_from_file_location("loops", next((RAW / "build" / version).glob("loops.*.so")))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kernel: Callable[..., None] = module.stage
    w = np.empty((4, n + 4, n + 4))
    fx, fy = np.empty((4, n, n + 1)), np.empty((4, n + 1, n))
    return lambda u, du: kernel(u, w, fx, fy, du, GAMMA, dtdx, dtdy)


## ---- one version on one grid, in a process of its own ----

def worker(version: str, n: int) -> None:
    """Save the change of one stage from the initial state, then the states after each number of STEPS."""
    u = initial_state(n)
    stage = make_stage(version, n, time_step(u))
    u1, du = np.empty_like(u), np.zeros_like(u)
    fill_ghosts(u)
    stage(u, du)
    saved = [du.copy()]
    for count in range(1, STEPS[-1] + 1):
        step(u, u1, du, stage)
        if count in STEPS:
            saved.append(u.copy())
    np.save(RAW / f"{version}-{n}.npy", np.stack(saved))


## ---- the experiment ----

def build(name: str) -> dict[str, str]:
    """Compile loops.py with the flags of one build, and count the fused instructions in the assembly of its C."""
    folder = RAW / "build" / name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    shutil.copy(HERE / "loops.py", folder)
    shutil.copy(HERE / "loops.pxd", folder)
    flags = BUILDS[name]
    directives = [arg for directive in DIRECTIVES for arg in ("-X", directive)]
    base = shlex.split(str(sysconfig.get_config_var("CFLAGS")))
    env = {key: value for key, value in os.environ.items() if key != "CFLAGS"}
    if flags:
        ## setuptools compiles with CFLAGS instead of the flags of Python when it is set, so these come first
        env["CFLAGS"] = shlex.join([*base, *flags])
    start = time.perf_counter()
    done = subprocess.run([sys.executable, "-m", "Cython.Build.Cythonize", "-i", "-3", *directives, "loops.py"],
                          cwd=folder, env=env, capture_output=True, text=True)
    seconds = time.perf_counter() - start
    (RAW / f"build-{name}.txt").write_text(done.stdout + done.stderr)
    done.check_returncode()
    compiler = shlex.split(str(sysconfig.get_config_var("CC")))
    include = sysconfig.get_paths()["include"]
    subprocess.run([*compiler, *base, *flags, "-I", include, "-S", "loops.c", "-o", "loops.s"], cwd=folder,
                   check=True, capture_output=True)
    module = next(folder.glob("loops.*.so"))
    code = subprocess.run(["otool", "-tv", str(module)], check=True, capture_output=True, text=True).stdout
    return {"build": name, "cflags": " ".join(flags) or "none", "seconds": f"{seconds:.1f}",
            "fused_in_assembly": str(len(FUSED.findall((folder / "loops.s").read_text()))),
            "fused_in_module": str(len(FUSED.findall(code)))}


def differences(a: Array, b: Array) -> list[float]:
    """Return the largest difference of each variable relative to its largest magnitude in b, in units of EPSILON."""
    return [float(np.max(np.abs(a[k] - b[k])) / np.max(np.abs(b[k])) / EPSILON) for k in range(len(VARIABLES))]


def environment() -> dict[str, str]:
    """Return what produced the results: date, Python and its build, packages, machine, compiler and commit."""
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
        "cflags_of_python": str(sysconfig.get_config_var("CFLAGS")),
        "commit": output(["git", "rev-parse", "--short", "HEAD"]) + (" (modified)" if dirty else ""),
    }


def write_csv(name: str, rows: list[dict[str, str]]) -> None:
    """Write rows of equal keys to a file of results."""
    with open(RESULTS / name, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        worker(sys.argv[2], int(sys.argv[3]))
        return
    RAW.mkdir(parents=True, exist_ok=True)
    builds = [build(name) for name in BUILDS]
    for row in builds:
        print(row, flush=True)
    for version in [*BUILDS, *REFERENCES]:
        for n in SIZES:
            done = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", version, str(n)],
                                  cwd=HERE, env=os.environ | THREADS, capture_output=True, text=True)
            (RAW / f"worker-{version}-{n}.txt").write_text(done.stdout + done.stderr)
            done.check_returncode()
            print(version, n, "done", flush=True)
    rows: list[dict[str, str]] = []
    for n in SIZES:
        saved: dict[str, Array] = {v: np.load(RAW / f"{v}-{n}.npy") for v in [*BUILDS, *REFERENCES]}
        for a, b in PAIRS:
            for index, measure in enumerate(["stage", *(f"step{s}" for s in STEPS)]):
                first, second = saved[a][index], saved[b][index]
                d = differences(first, second)
                nan = bool(np.isnan(first).any() or np.isnan(second).any())
                rows.append({"cells": f"{n}x{n}", "compared": a, "against": b, "measure": measure,
                             **{v: f"{x:.3g}" for v, x in zip(VARIABLES, d)}, "largest": f"{max(d):.3g}",
                             "nan": str(nan)})
    write_csv("differences.csv", rows)
    write_csv("builds.csv", builds)
    (RESULTS / "environment.json").write_text(json.dumps(environment(), indent=2) + "\n")
    print((RESULTS / "differences.csv").read_text())


if __name__ == "__main__":
    main()
