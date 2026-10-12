# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E12.1: what does it cost when a physics module runs its own passes instead of being fused into a kernel?

A module that plugs into the framework without touching other modules runs its own passes over the arrays: its own
conversion to primitive variables, its own loop over faces, its own divergence. A kernel that knows all variables does
the same work in one pass. This experiment measures the difference for passive scalars, the simplest module that
couples to the hydrodynamics (its fluxes follow the mass flux, D03.6), with the kernels of ``E12.1a-kernels.py``:

- **fused:** one kernel for the hydrodynamics and the scalars;
- **separate passes:** the hydrodynamic kernel, then the scalar module's own passes, reading the stored mass flux.

Both compute the same arithmetic, so the results must be bit-for-bit identical (checked). It times one evaluation of
the time derivative natively, on one thread, for 2D blocks of 64^2 and 512^2 cells with 0, 1 and 4 scalars, with the
repetitions interleaved (every repetition times every form once; the best is kept), as learned in E10.

Run from this directory with:

    uv run --locked --script E12.1b-modularity.py

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
G = 2
GAMMA = 1.4
MIN_TIME = 0.2
REPEATS = 9
SIZES = [64, 512]
SCALARS = [0, 1, 4]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path):
    (workdir / "kernels.py").write_text((HERE / "E12.1a-kernels.py").read_text())
    subprocess.run([sys.executable, "-m", "cython", "-3", "kernels.py", "-o", "kernels.c"], cwd=workdir, check=True,
                   capture_output=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"kernels{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", "kernels.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load("kernels", ext)


def state(n: int, ns: int) -> np.ndarray:
    """A smooth periodic 2D state [var, k=1, j, i] with ns scalars, padded with ghost cells."""
    x = (np.arange(n) + 0.5) / n
    yy, xx = np.meshgrid(x, x, indexing="ij")
    s = 2 * np.pi
    rho = 1.0 + 0.2 * np.sin(s * xx) * np.cos(s * yy)
    vx, vy, vz = 0.5 + 0.1 * np.sin(s * yy), 0.3 * np.cos(s * xx), 0.1 * np.sin(s * (xx - yy))
    pres = 1.0 + 0.1 * np.cos(s * (xx + yy))
    variables = [rho, rho * vx, rho * vy, rho * vz, pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy + vz * vz)]
    variables += [rho * (0.5 + 0.4 * np.sin(s * (m + 1) * xx) * np.cos(s * yy)) for m in range(ns)]
    u = np.array(variables)[:, None]
    return np.ascontiguousarray(np.pad(u, ((0, 0), (0, 0), (G, G), (G, G)), mode="wrap"))


def mean_time(function) -> float:
    calls, start = 0, time.perf_counter()
    while True:
        function()
        calls += 1
        elapsed = time.perf_counter() - start
        if elapsed >= MIN_TIME:
            return elapsed / calls


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "cases": {}}
    with tempfile.TemporaryDirectory() as tmp:
        k = build(Path(tmp))
        results["compiler"] = subprocess.run(["cc", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
        for n in SIZES:
            for ns in SCALARS:
                u = state(n, ns)
                nv = 5 + ns
                w = np.empty_like(u)
                fx, fy, du = np.empty((nv, 1, n, n + 1)), np.empty((nv, 1, n + 1, n)), np.empty((nv, 1, n, n))
                calls = {
                    "fused": lambda: k.rhs_fused(u, w, fx, fy, du, n, n, G, 1.0 / n, ns),
                    "separate passes": lambda: k.rhs_separate(u, w, fx, fy, du, n, n, G, 1.0 / n, ns),
                }
                outputs = {}
                for form, call in calls.items():
                    du[:] = np.nan
                    call()
                    outputs[form] = du.copy()
                identical = bool(np.array_equal(outputs["fused"], outputs["separate passes"]))
                best = dict.fromkeys(calls, float("inf"))
                for _ in range(REPEATS):
                    for form, call in calls.items():
                        best[form] = min(best[form], mean_time(call))
                results["cases"][f"{n}² | {ns}"] = {
                    "cells_per_second": {form: n * n / t for form, t in best.items()},
                    "bitwise_identical": identical,
                }
                print(n, ns, results["cases"][f"{n}² | {ns}"], flush=True)

    md = [
        "# E12.1: a module's own passes against a fused kernel",
        "",
        f"Passive scalars with the hydrodynamics; one evaluation of the time derivative, one thread, natively "
        f"({results['compiler']}); Python {platform.python_version()}, NumPy {np.__version__}. Million cells per second; "
        "cost of the scalars relative to the hydrodynamics alone (0 scalars) of the same form.",
        "",
        "| Block | Scalars | Fused | Separate passes | Separate / fused | Bit for bit |",
        "|---|---|---|---|---|---|",
    ]
    for key, row in results["cases"].items():
        n, ns = key.split(" | ")
        fused, separate = row["cells_per_second"]["fused"], row["cells_per_second"]["separate passes"]
        md.append(f"| {n} | {ns} | {fused / 1e6:.1f} | {separate / 1e6:.1f} | {fused / separate:.2f} × time | "
                  f"{'yes' if row['bitwise_identical'] else 'no'} |")
    (RESULTS / "E12.1b-modularity.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E12.1b-modularity.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
