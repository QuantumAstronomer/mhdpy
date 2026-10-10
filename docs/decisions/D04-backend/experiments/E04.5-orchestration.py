# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E04.5: how much time does the Python orchestration around a compiled kernel cost?

In the kernel structure of D04.2, compiled kernels compute the time derivative of a block, and Python orchestrates
everything else: it fills the ghost cells, combines the Runge-Kutta stages and allocates the new state, here with NumPy
array operations. This experiment splits the time of one SSP-RK2 step of the E04.1 problem into the two compiled kernel
calls and the rest, for blocks of 16^2 to 1024^2 cells, using the compiled pure-Python-mode kernel of E04.3 on one thread.
It also times a bare call into the compiled module, the fixed cost of crossing from Python into compiled code.

The orchestration is timed in three variants, which compute bit-for-bit the same result (checked):

- "NumPy": the straightforward NumPy expressions of E04.1, which allocate temporary arrays;
- "NumPy in place": the same operations with preallocated arrays and ``out=`` arguments, without temporaries;
- "compiled stages": the two Runge-Kutta stage combinations as small compiled kernels; only the ghost filling stays NumPy.

Run from this directory with:

    uv run --locked --script E04.5-orchestration.py

Results are written to results/.
"""

import importlib.util
import json
import platform
import subprocess
import sys
import sysconfig
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RESULTS = HERE / "results"
SIZES = [16, 32, 64, 128, 256, 512, 1024]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ref = load("hydro2d_numpy", HERE / "E04.1a-hydro2d-numpy.py")
G = ref.N_GHOST


## The two SSP-RK2 stage combinations as compiled kernels, with the same arithmetic as ssp_rk2_step.
STAGES = """
import cython


@cython.boundscheck(False)
@cython.wraparound(False)
def first_stage(u: cython.double[:, :, ::1], k: cython.double[:, :, ::1], dt: cython.double,
                out: cython.double[:, :, ::1], g: cython.int) -> None:
    v: cython.Py_ssize_t
    i: cython.Py_ssize_t
    j: cython.Py_ssize_t
    for v in range(k.shape[0]):
        for i in range(k.shape[1]):
            for j in range(k.shape[2]):
                out[v, i + g, j + g] = u[v, i + g, j + g] + dt * k[v, i, j]


@cython.boundscheck(False)
@cython.wraparound(False)
def second_stage(u: cython.double[:, :, ::1], stage: cython.double[:, :, ::1], k: cython.double[:, :, ::1],
                 dt: cython.double, out: cython.double[:, :, ::1], g: cython.int) -> None:
    v: cython.Py_ssize_t
    i: cython.Py_ssize_t
    j: cython.Py_ssize_t
    for v in range(k.shape[0]):
        for i in range(k.shape[1]):
            for j in range(k.shape[2]):
                out[v, i + g, j + g] = 0.5 * u[v, i + g, j + g] + 0.5 * (stage[v, i + g, j + g] + dt * k[v, i, j])
"""


def build(workdir: Path, name: str, source: str):
    (workdir / f"{name}.py").write_text(source)
    subprocess.run([sys.executable, "-m", "cython", "-3", f"{name}.py", "-o", f"{name}.c"], cwd=workdir, check=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"{name}{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", f"{name}.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load(name, ext)


def inplace_step(rhs, shape):
    """SSP-RK2 with preallocated arrays and out= arguments; same operations and rounding as ssp_rk2_step."""
    inner = (slice(None), slice(G, -G), slice(G, -G))
    stage, new = np.empty(shape), np.empty(shape)
    tmp = np.empty((shape[0], shape[1] - 2 * G, shape[2] - 2 * G))

    def step(u, dt, dx):
        np.multiply(rhs(u, dx), dt, out=tmp)
        np.add(u[inner], tmp, out=stage[inner])
        ref.fill_ghosts(stage)
        np.multiply(rhs(stage, dx), dt, out=tmp)
        np.add(stage[inner], tmp, out=tmp)
        np.multiply(tmp, 0.5, out=tmp)
        np.multiply(u[inner], 0.5, out=new[inner])
        np.add(new[inner], tmp, out=new[inner])
        ref.fill_ghosts(new)
        return new

    return step


def compiled_stages_step(rhs, stages, shape):
    """SSP-RK2 with the stage combinations as compiled kernels; same arithmetic as ssp_rk2_step."""
    stage, new = np.empty(shape), np.empty(shape)

    def step(u, dt, dx):
        stages.first_stage(u, rhs(u, dx), dt, stage, G)
        ref.fill_ghosts(stage)
        stages.second_stage(u, stage, rhs(stage, dx), dt, new, G)
        ref.fill_ghosts(new)
        return new

    return step


def best_time(function, min_seconds: float = 0.3, repeats: int = 5) -> float:
    """Best average duration of ``function()`` over several repetitions of at least min_seconds each."""
    best = float("inf")
    for _ in range(repeats):
        calls, start = 0, time.perf_counter()
        while True:
            function()
            calls += 1
            elapsed = time.perf_counter() - start
            if elapsed >= min_seconds:
                break
        best = min(best, elapsed / calls)
    return best


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    rows = {}
    with tempfile.TemporaryDirectory() as tmp:
        kernel = build(Path(tmp), "kernel", (HERE / "E04.3a-hydro2d-purepython.py").read_text())
        stages = build(Path(tmp), "stages", STAGES)
        call_cost = best_time(lambda: kernel.set_threads(1))
        for n in SIZES:
            m = n + 2 * G
            u, dx = ref.initial_state(n), 1.0 / n
            w, fx, fy, du = np.empty((4, m, m)), np.empty((4, n + 1, n)), np.empty((4, n, n + 1)), np.empty((4, n, n))

            def rhs(u, dx):
                kernel.rhs(u, w, fx, fy, du, G, dx)
                return du

            variants = {
                "NumPy": lambda u, dt, dx: ref.ssp_rk2_step(u, dt, dx, rhs),
                "NumPy in place": inplace_step(rhs, u.shape),
                "compiled stages": compiled_stages_step(rhs, stages, u.shape),
            }
            reference = variants["NumPy"](u, 1e-4, dx).copy()
            kernel_time = 2 * best_time(lambda: rhs(u, dx))
            rows[n] = {"kernel_seconds": kernel_time, "variants": {}}
            for name, step in variants.items():
                identical = bool(np.array_equal(step(u, 1e-4, dx), reference))
                step_time = best_time(lambda: step(u, 1e-4, dx))
                rows[n]["variants"][name] = {
                    "step_seconds": step_time,
                    "orchestration_fraction": 1.0 - kernel_time / step_time,
                    "cell_updates_per_second": n * n / step_time,
                    "bitwise_identical_to_numpy_variant": identical,
                }
            print(n, rows[n], flush=True)

    names = list(rows[SIZES[0]]["variants"])
    md = [
        "# E04.5: cost of the Python orchestration around a compiled kernel",
        "",
        f"Python {platform.python_version()}, NumPy {np.__version__}, {platform.platform()}; natively, one thread. "
        f"A bare call into the compiled module costs {call_cost * 1e6:.2f} µs. All variants give bit-for-bit "
        f"identical results: {all(v['bitwise_identical_to_numpy_variant'] for r in rows.values() for v in r['variants'].values())}.",
        "",
        "Share of each step spent outside the two compiled kernel calls, and resulting cell updates per second:",
        "",
        "| Block | Kernels per step | " + " | ".join(names) + " |",
        "|" + "---|" * (len(names) + 2),
    ]
    for n, r in rows.items():
        cells = [
            f"{100 * v['orchestration_fraction']:.0f} % ({v['cell_updates_per_second']:.2e})"
            for v in r["variants"].values()
        ]
        md.append(f"| {n}² | {r['kernel_seconds'] * 1e3:.3f} ms | " + " | ".join(cells) + " |")
    (RESULTS / "E04.5-orchestration.json").write_text(
        json.dumps({"bare_call_seconds": call_cost, "sizes": rows, "platform": platform.platform()}, indent=1) + "\n"
    )
    (RESULTS / "E04.5-orchestration.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
