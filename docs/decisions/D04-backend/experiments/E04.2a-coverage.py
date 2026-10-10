# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "numba", "cython", "coverage"]
# ///
"""Experiment E04.2 (container part): can the kernels of each technology be measured by coverage.py?

Brief D02 requires 100 % line and branch coverage, measured with coverage.py. This script checks, for the E04.1 kernels:

- Numba: with ``NUMBA_DISABLE_JIT=1`` the kernel runs as plain Python, so coverage.py sees every line and branch;
- Cython: a build with line tracing (directive ``linetrace``, macro ``CYTHON_TRACE_NOGIL``) and Cython's coverage plugin
  let coverage.py measure the .pyx source; the price is a slower build, measured here with tracing switched off. On
  Python 3.12 and later two settings are needed, both found while setting up this experiment: coverage.py's default
  engine (sys.monitoring) does not support Cython's plugin, so the classic tracing engine is selected with
  ``COVERAGE_CORE=ctrace``; and Cython (3.1 and later) reports line events through sys.monitoring, which that engine
  does not receive, so the extension is built with ``CYTHON_USE_SYS_MONITORING=0``;
- C: coverage.py has no access to compiled C, so no measurement is attempted.

Not meant to be run by hand: ``E04.2b-run.py`` runs it in the E04.1 Linux container as
``uv run --locked --script E04.2a-coverage.py <output.json>``.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
SMALL, TIMING = 16, 256

## A driver that runs one SSP-RK2 step of the kernel given on the command line; executed under coverage.py.
DRIVER = '''
import importlib.util, sys
import numpy as np

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

ref = load("hydro2d_numpy", "{work}/E04.1a-hydro2d-numpy.py")
n = {n}
u = ref.initial_state(n)
m = u.shape[1]
if sys.argv[1] == "numba":
    nb = load("hydro2d_numba", "{work}/E04.1b-hydro2d-numba.py")
    kernel = nb.Kernel(m, 2)
else:
    cy = load("hydro2d_cython", sys.argv[2])
    w, fx, fy, du = np.empty((4, m, m)), np.empty((4, n + 1, n)), np.empty((4, n, n + 1)), np.empty((4, n, n))
    def kernel(u, dx):
        cy.rhs(u, w, fx, fy, du, 2, dx)
        return du
ref.ssp_rk2_step(u, 1e-3, 1.0 / n, kernel)
'''


def coverage_of(run_dir: Path, args: list[str], env: dict, source: Path, rcfile: Path | None = None) -> dict:
    command = [sys.executable, "-m", "coverage", "run", "--branch"]
    if rcfile:
        command.append(f"--rcfile={rcfile}")
    subprocess.run([*command, "driver.py", *args], cwd=run_dir, env=env, check=True)
    report = subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", "cov.json", *([f"--rcfile={rcfile}"] if rcfile else [])],
        cwd=run_dir, env=env, capture_output=True, text=True, check=True,
    )
    _ = report
    data = json.loads((run_dir / "cov.json").read_text())
    for name, file in data["files"].items():
        if Path(name).name == source.name:
            s = file["summary"]
            return {
                "measured": True,
                "line_coverage_percent": round(100 * s["covered_lines"] / max(s["num_statements"], 1), 1),
                "branches_covered": f"{s['covered_branches']} of {s['num_branches']}",
            }
    return {"measured": False}


def build_cython(workdir: Path, trace: bool) -> Path:
    name = "hydro2d_cython"
    src = workdir / f"{name}.pyx"
    shutil.copy(HERE / "E04.1d-hydro2d-cython.pyx", src)
    directives = ["-X", "linetrace=True"] if trace else []
    subprocess.run([sys.executable, "-m", "cython", "-3", *directives, str(src), "-o", str(workdir / f"{name}.c")],
                   check=True)
    macros = ["-DCYTHON_TRACE=1", "-DCYTHON_TRACE_NOGIL=1", "-DCYTHON_USE_SYS_MONITORING=0"] if trace else []
    ext = workdir / f"{name}{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", "-fopenmp", "-shared", "-fPIC", *macros, f"-I{sysconfig.get_paths()['include']}",
                    str(workdir / f"{name}.c"), "-o", str(ext)], check=True)
    return ext


def cython_rate(ext: Path) -> float:
    """Single-thread throughput of a Cython build at TIMING^2 cells, without coverage running."""
    import numpy as np

    spec = importlib.util.spec_from_file_location("ref", HERE / "E04.1a-hydro2d-numpy.py")
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    name = f"hydro2d_cython_{ext.parent.name}"
    spec = importlib.util.spec_from_file_location("hydro2d_cython", ext)
    cy = importlib.util.module_from_spec(spec)
    sys.modules[name] = cy
    spec.loader.exec_module(cy)
    cy.set_threads(1)
    n = TIMING
    u = ref.initial_state(n)
    m = u.shape[1]
    w, fx, fy, du = np.empty((4, m, m)), np.empty((4, n + 1, n)), np.empty((4, n, n + 1)), np.empty((4, n, n))

    def kernel(u, dx):
        cy.rhs(u, w, fx, fy, du, 2, dx)
        return du

    ref.ssp_rk2_step(u, 1e-4, 1.0 / n, kernel)
    start = time.perf_counter()
    for _ in range(10):
        ref.ssp_rk2_step(u, 1e-4, 1.0 / n, kernel)
    return 10 * n * n / (time.perf_counter() - start)


def main() -> None:
    output = Path(sys.argv[1])
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "driver.py").write_text(DRIVER.format(work=HERE, n=SMALL))

        env = dict(os.environ, NUMBA_DISABLE_JIT="1")
        start = time.perf_counter()
        results["Numba (NUMBA_DISABLE_JIT=1)"] = coverage_of(tmp, ["numba"], env, HERE / "E04.1b-hydro2d-numba.py")
        results["Numba (NUMBA_DISABLE_JIT=1)"]["seconds_for_one_step_at_16x16"] = round(time.perf_counter() - start, 2)

        traced_dir, plain_dir = tmp / "traced", tmp / "plain"
        traced_dir.mkdir()
        plain_dir.mkdir()
        traced = build_cython(traced_dir, trace=True)
        plain = build_cython(plain_dir, trace=False)
        (traced_dir / "driver.py").write_text(DRIVER.format(work=HERE, n=SMALL))
        rc = traced_dir / ".coveragerc"
        rc.write_text("[run]\nplugins = Cython.Coverage\n")
        results["Cython (line-tracing build)"] = coverage_of(
            traced_dir, ["cython", str(traced)], dict(os.environ, COVERAGE_CORE="ctrace"),
            traced_dir / "hydro2d_cython.pyx", rc,
        )
        plain_rate, traced_rate = cython_rate(plain), cython_rate(traced)
        results["Cython (line-tracing build)"]["throughput_normal_build"] = plain_rate
        results["Cython (line-tracing build)"]["throughput_tracing_build"] = traced_rate
        results["Cython (line-tracing build)"]["slowdown"] = round(plain_rate / traced_rate, 2)
        results["C"] = {"measured": False, "note": "coverage.py cannot see compiled C"}
    output.write_text(json.dumps(results, indent=1) + "\n")
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
