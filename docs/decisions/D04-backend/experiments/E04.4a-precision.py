# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E04.4 (measurement): what single precision would change, for future reference.

Decision D04.4 chose double precision on correctness grounds. This experiment records what single precision would have
given, on the development machine (natively, one thread):

1. speed: one SSP-RK2 step of the E04.1 kernel at 1024^2 cells, in float64 and float32, for NumPy and for the compiled
   pure-Python-mode Cython kernel of E04.3. The float32 Cython kernel is generated from the same source by declaring
   ``cython.float`` instead of ``cython.double``; its arrays are single precision, but C evaluates the expressions with
   double-precision literals (0.5, gamma) partly in double precision, so it is "single-precision storage" rather than a
   pure single-precision kernel;
2. accuracy: the L1 error of a linear sound wave after one period (the E02.1 test, here on the 2D kernel with the wave
   along x) for N = 32 ... 256 and amplitudes 10^-6 and 10^-3, computed with NumPy, which keeps float32 arrays in float32
   throughout; plus the change of total mass over the run, which is exactly conserved apart from round-off.

Run from this directory with:

    uv run --locked --script E04.4a-precision.py

Results are written to results/; the figure is drawn from them by E04.4b-figure.py.
"""

import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RESULTS = HERE / "results"
RESOLUTIONS = [32, 64, 128, 256]
AMPLITUDES = [1.0e-6, 1.0e-3]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ref = load("hydro2d_numpy", HERE / "E04.1a-hydro2d-numpy.py")
G = ref.N_GHOST


def build_kernel(workdir: Path, precision: str):
    """Compile the E04.3 pure-Python-mode kernel, optionally with every double declared as float."""
    name = f"kernel_{precision}"
    source = (HERE / "E04.3a-hydro2d-purepython.py").read_text()
    if precision == "float32":
        source = source.replace("cython.double", "cython.float")
    (workdir / f"{name}.py").write_text(source)
    subprocess.run([sys.executable, "-m", "cython", "-3", f"{name}.py", "-o", f"{name}.c"], cwd=workdir, check=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"{name}{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", f"{name}.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load(name, ext)


def compiled_step(module, n: int, dtype):
    m = n + 2 * G
    w = np.empty((4, m, m), dtype)
    fx, fy, du = np.empty((4, n + 1, n), dtype), np.empty((4, n, n + 1), dtype), np.empty((4, n, n), dtype)

    def kernel(u, dx):
        module.rhs(u, w, fx, fy, du, G, dx)
        return du

    return lambda u, dt, dx: ref.ssp_rk2_step(u, dt, dx, kernel)


def numpy_step(u, dt, dx):
    return ref.ssp_rk2_step(u, dt, dx, ref.rhs)


def seconds_per_step(step, u, dx, repeats: int = 5) -> float:
    step(u, 1e-4, dx)
    start = time.perf_counter()
    for _ in range(repeats):
        step(u, 1e-4, dx)
    return (time.perf_counter() - start) / repeats


def sound_wave(n: int, amplitude: float, dtype) -> np.ndarray:
    """A right-moving linear sound wave along x (uniform in y), sound speed 1, padded with ghost cells."""
    x = (np.arange(n) + 0.5) / n
    shape = amplitude * np.sin(2 * np.pi * x)[:, None] * np.ones((1, n))
    gamma = ref.GAMMA
    rho, vel, pres = 1.0 + shape, shape, 1.0 / gamma + shape
    u = np.zeros((4, n + 2 * G, n + 2 * G))
    u[:, G:-G, G:-G] = [rho, rho * vel, 0.0 * rho, pres / (gamma - 1.0) + 0.5 * rho * vel * vel]
    ref.fill_ghosts(u)
    return u.astype(dtype)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {"speed": {}, "accuracy": {}, "python": sys.version, "numpy": np.__version__,
               "platform": platform.platform()}
    with tempfile.TemporaryDirectory() as tmp:
        kernels = {p: build_kernel(Path(tmp), p) for p in ("float64", "float32")}
        n = 1024
        for precision, dtype in (("float64", np.float64), ("float32", np.float32)):
            u = ref.initial_state(n).astype(dtype)
            results["speed"][f"NumPy, {precision}"] = n * n / seconds_per_step(numpy_step, u, 1.0 / n, repeats=2)
            results["speed"][f"compiled, {precision}"] = n * n / seconds_per_step(
                compiled_step(kernels[precision], n, dtype), u, 1.0 / n)
            print(precision, "speed done", flush=True)
        shutil.rmtree(tmp, ignore_errors=True)

    for precision, dtype in (("float64", np.float64), ("float32", np.float32)):
        for amplitude in AMPLITUDES:
            key = f"{precision}, amplitude {amplitude:g}"
            results["accuracy"][key] = {}
            for n in RESOLUTIONS:
                dx = 1.0 / n
                u0 = sound_wave(n, amplitude, dtype)
                u, t, steps = u0, 0.0, 0
                dt_max = 0.4 * dx / (1.0 + 2.0 * amplitude)
                while t < 1.0:
                    dt = min(dt_max, 1.0 - t)
                    u = numpy_step(u, dt, dx)
                    t += dt
                    steps += 1
                interior = (slice(G, -G), slice(G, -G))
                error = float(np.mean(np.abs(u[0][interior].astype(np.float64) - u0[0][interior].astype(np.float64))))
                mass0 = float(np.sum(u0[0][interior], dtype=np.float64))
                mass = float(np.sum(u[0][interior], dtype=np.float64))
                results["accuracy"][key][n] = {"l1_error": error, "mass_change": mass / mass0 - 1.0, "steps": steps}
                print(key, n, error, flush=True)

    s = results["speed"]
    md = [
        "# E04.4: single against double precision",
        "",
        f"Python {platform.python_version()}, NumPy {np.__version__}, {platform.platform()}; natively, one thread.",
        "",
        "## Speed (cell updates per second, 1024² cells)",
        "",
        "| Implementation | float64 | float32 | Speed-up |",
        "|---|---|---|---|",
        f"| NumPy | {s['NumPy, float64']:.2e} | {s['NumPy, float32']:.2e} | "
        f"{s['NumPy, float32'] / s['NumPy, float64']:.2f}× |",
        f"| Compiled (Cython, pure Python mode) | {s['compiled, float64']:.2e} | {s['compiled, float32']:.2e} | "
        f"{s['compiled, float32'] / s['compiled, float64']:.2f}× |",
        "",
        "## Accuracy: linear sound wave after one period (NumPy)",
        "",
        "| Precision, amplitude | " + " | ".join(f"L1 error N={n}" for n in RESOLUTIONS) + " | Mass change (N=256) |",
        "|" + "---|" * (len(RESOLUTIONS) + 2),
    ]
    for key, rows in results["accuracy"].items():
        md.append(f"| {key} | " + " | ".join(f"{rows[n]['l1_error']:.2e}" for n in RESOLUTIONS)
                  + f" | {rows[RESOLUTIONS[-1]]['mass_change']:+.1e} |")
    md += ["", "![E04.4](E04.4b-precision.png)", ""]
    (RESULTS / "E04.4a-precision.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E04.4a-precision.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
