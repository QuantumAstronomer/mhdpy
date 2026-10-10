# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython", "coverage", "ruff", "pyright"]
# ///
"""Experiment E04.3 (container part): one source file, compiled for speed and run uncompiled for coverage and checks.

Tests the kernel written in Cython's pure Python mode (``E04.3a-hydro2d-purepython.py``) against the questions E04.1 and
E04.2 left open:

1. compiled with Cython: is it bit-for-bit identical to NumPy, and as fast as the .pyx kernel of E04.1?
2. run uncompiled: does coverage.py measure its lines and branches, as it does for Numba with the JIT disabled?
3. static checks: what do ruff and pyright (the tools of D01.7 and D01.8) report on the file?

Not meant to be run by hand: ``E04.3c-run.py`` runs it in the E04.1 Linux container as
``uv run --locked --script E04.3b-purepython.py <output.json>``.
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

import numpy as np

HERE = Path(__file__).parent
KERNEL = HERE / "E04.3a-hydro2d-purepython.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ref = load("hydro2d_numpy", HERE / "E04.1a-hydro2d-numpy.py")


def compile_module(source: Path, name: str, workdir: Path) -> Path:
    target = workdir / (name + source.suffix)
    shutil.copy(source, target)
    subprocess.run([sys.executable, "-m", "cython", "-3", str(target), "-o", str(workdir / f"{name}.c")], check=True)
    ext = workdir / f"{name}{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", "-fopenmp", "-shared", "-fPIC", f"-I{sysconfig.get_paths()['include']}",
                    str(workdir / f"{name}.c"), "-o", str(ext)], check=True)
    return ext


def make_step(module, n: int):
    m = n + 2 * ref.N_GHOST
    w, fx, fy, du = np.empty((4, m, m)), np.empty((4, n + 1, n)), np.empty((4, n, n + 1)), np.empty((4, n, n))

    def kernel(u, dx):
        module.rhs(u, w, fx, fy, du, ref.N_GHOST, dx)
        return du

    return lambda u, dt, dx: ref.ssp_rk2_step(u, dt, dx, kernel)


def rate(step, n: int, steps: int = 10) -> float:
    u = ref.initial_state(n)
    step(u, 1e-4, 1.0 / n)
    start = time.perf_counter()
    for _ in range(steps):
        step(u, 1e-4, 1.0 / n)
    return steps * n * n / (time.perf_counter() - start)


def main() -> None:
    output = Path(sys.argv[1])
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pure = load("kernel_pure", compile_module(KERNEL, "kernel_pure", tmp))
        pyx = load("kernel_pyx", compile_module(HERE / "E04.1d-hydro2d-cython.pyx", "kernel_pyx", tmp))

        ## 1. Correctness and speed of the compiled pure-mode kernel.
        n = 256
        u, reference = ref.initial_state(n), ref.initial_state(n)
        step = make_step(pure, n)
        for _ in range(5):
            u = step(u, 0.1 / n, 1.0 / n)
            reference = ref.ssp_rk2_step(reference, 0.1 / n, 1.0 / n, ref.rhs)
        results["compiled"] = {"bitwise_identical_to_numpy": bool(np.array_equal(u, reference))}
        for name, module in (("pure Python mode", pure), (".pyx", pyx)):
            module.set_threads(1)
            results["compiled"][f"throughput 1024^2, 1 thread, {name}"] = rate(make_step(module, 1024), 1024)
        for threads in (4, 8):
            pure.set_threads(threads)
            results["compiled"][f"throughput 1024^2, {threads} threads, pure Python mode"] = rate(
                make_step(pure, 1024), 1024)

        ## 2. Coverage of the uncompiled file.
        driver = tmp / "driver.py"
        driver.write_text(
            "import importlib.util, sys\n"
            f"sys.path.insert(0, {str(HERE)!r})\n"
            f"spec = importlib.util.spec_from_file_location('ref', {str(HERE / 'E04.1a-hydro2d-numpy.py')!r})\n"
            "ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)\n"
            f"spec = importlib.util.spec_from_file_location('kernel', {str(KERNEL)!r})\n"
            "kernel = importlib.util.module_from_spec(spec); spec.loader.exec_module(kernel)\n"
            "import numpy as np\n"
            "n = 16; m = n + 4; u = ref.initial_state(n)\n"
            "w, fx, fy, du = np.empty((4, m, m)), np.empty((4, n + 1, n)), np.empty((4, n, n + 1)), np.empty((4, n, n))\n"
            "kernel.rhs(u, w, fx, fy, du, 2, 1.0 / n)\n"
        )
        start = time.perf_counter()
        subprocess.run([sys.executable, "-m", "coverage", "run", "--branch", str(driver)], cwd=tmp, check=True)
        seconds = time.perf_counter() - start
        subprocess.run([sys.executable, "-m", "coverage", "json", "-o", "cov.json"], cwd=tmp, check=True)
        files = json.loads((tmp / "cov.json").read_text())["files"]
        summary = next(f["summary"] for name, f in files.items() if Path(name).name == KERNEL.name)
        results["uncompiled_coverage"] = {
            "line_coverage_percent": round(100 * summary["covered_lines"] / summary["num_statements"], 1),
            "branches_covered": f"{summary['covered_branches']} of {summary['num_branches']}",
            "seconds_for_one_rhs_at_16x16": round(seconds, 2),
        }

        ## 3. Static checks with the tools of D01.
        env = dict(os.environ)
        ruff = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--isolated", "--line-length", "120",
             "--select", "E,W,F,I,B,UP,NPY", "--output-format", "concise", str(KERNEL)],
            capture_output=True, text=True, env=env,
        )
        pyright = subprocess.run(
            [sys.executable, "-m", "pyright", "--outputjson", str(KERNEL)], capture_output=True, text=True, env=env
        )
        diagnostics = json.loads(pyright.stdout)["generalDiagnostics"] if pyright.stdout.strip() else []
        results["static_checks"] = {
            "ruff_findings": [line for line in ruff.stdout.splitlines() if ":" in line and "Found" not in line],
            "pyright_errors": len([d for d in diagnostics if d["severity"] == "error"]),
            "pyright_first_messages": sorted({d["message"].splitlines()[0] for d in diagnostics})[:6],
        }
    output.write_text(json.dumps(results, indent=1) + "\n")
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
