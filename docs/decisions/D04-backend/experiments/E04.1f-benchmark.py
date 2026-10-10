# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "numpy",
#     "cython",
#     "numba; sys_platform == 'linux'",
#     "jax; sys_platform == 'linux'",
# ]
# ///
"""Experiment E04.1 (benchmark): the representative hydro kernel in five technologies, on one platform.

Builds and runs the same 2D hydrodynamics time step (``E04.1a-hydro2d-numpy.py`` to ``E04.1e-hydro2d-jax.py``)
with NumPy, Numba, Cython, C and JAX, and measures for each:

- correctness: the largest difference from the NumPy result after five steps, and whether it is bit-for-bit identical;
- throughput on one thread for grids of 64^2 to 2048^2 cells, in cell updates (full SSP-RK2 steps) per second;
- thread scaling at 1024^2 cells for the technologies with built-in threading (Numba, Cython and C with OpenMP);
- start-up cost: the build time of the ahead-of-time compiled kernels and the time of the first, compiling call of the
  just-in-time ones.

C is built twice: for a generic x86-64 CPU, as a distributed wheel would be, and for the exact CPU (``-march=native``),
as Numba compiles. Technologies that cannot be installed on a platform (Numba and JAX on macOS on Intel) are skipped.

Not meant to be run by hand: ``E04.1h-run.py`` runs it in a Linux container and natively, as
``uv run --locked --script E04.1f-benchmark.py <label> <output.json>``.
"""

import importlib.util
import json
import os
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
SIZES = [64, 256, 1024, 2048]
SCALING_SIZE = 1024
THREADS = [1, 2, 4, 6, 8]
MIN_TIME = 0.5  ## seconds of measurement per repetition
REPEATS = 3
CHECK_STEPS = 5


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ref = load("hydro2d_numpy", HERE / "E04.1a-hydro2d-numpy.py")
G = ref.N_GHOST


def compiler_supports_openmp(cc: str, workdir: Path) -> bool:
    test = workdir / "omp_test.c"
    test.write_text("#include <omp.h>\nint main(void){return omp_get_max_threads() > 0 ? 0 : 1;}\n")
    result = subprocess.run([cc, "-fopenmp", str(test), "-o", str(workdir / "omp_test")], capture_output=True)
    return result.returncode == 0


def build(workdir: Path) -> dict:
    """Compile the C and Cython kernels; return the loaded modules, build times and compiler information."""
    cc = os.environ.get("CC", "cc")
    openmp = ["-fopenmp"] if compiler_supports_openmp(cc, workdir) else []
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    info = {
        "compiler": subprocess.run([cc, "--version"], capture_output=True, text=True).stdout.splitlines()[0],
        "openmp": bool(openmp),
    }
    built = {}
    import ctypes

    for variant, extra in (("C (generic CPU)", []), ("C (-march=native)", ["-march=native"])):
        lib = workdir / f"hydro2d_{len(built)}.so"
        start = time.perf_counter()
        subprocess.run([cc, "-O3", *extra, *openmp, *shared, str(HERE / "E04.1c-hydro2d-c.c"), "-o", str(lib)],
                       check=True)
        info[f"build seconds, {variant}"] = time.perf_counter() - start
        built[variant] = ctypes.CDLL(str(lib))

    pyx = workdir / "hydro2d_cython.pyx"
    shutil.copy(HERE / "E04.1d-hydro2d-cython.pyx", pyx)
    start = time.perf_counter()
    subprocess.run([sys.executable, "-m", "cython", "-3", str(pyx), "-o", str(workdir / "hydro2d_cython.c")],
                   check=True)
    ext = workdir / f"hydro2d_cython{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run([cc, "-O3", *openmp, *shared, f"-I{sysconfig.get_paths()['include']}",
                    str(workdir / "hydro2d_cython.c"), "-o", str(ext)], check=True)
    info["build seconds, Cython"] = time.perf_counter() - start
    built["Cython"] = load("hydro2d_cython", ext)
    return {"modules": built, "info": info}


class CKernel:
    def __init__(self, lib, m: int) -> None:
        import ctypes

        n = m - 2 * G
        self.lib, self.m = lib, m
        self.w, self.fx, self.fy = np.empty((4, m, m)), np.empty((4, n + 1, n)), np.empty((4, n, n + 1))
        self.du = np.empty((4, n, n))
        ptr = ctypes.POINTER(ctypes.c_double)
        lib.rhs.argtypes = [ptr] * 5 + [ctypes.c_int, ctypes.c_int, ctypes.c_double]
        self._ptr = lambda a: a.ctypes.data_as(ptr)

    def __call__(self, u, dx):
        self.lib.rhs(self._ptr(u), self._ptr(self.w), self._ptr(self.fx), self._ptr(self.fy), self._ptr(self.du),
                     self.m, G, dx)
        return self.du


class CythonKernel:
    def __init__(self, module, m: int) -> None:
        n = m - 2 * G
        self.module = module
        self.w, self.fx, self.fy = np.empty((4, m, m)), np.empty((4, n + 1, n)), np.empty((4, n, n + 1))
        self.du = np.empty((4, n, n))

    def __call__(self, u, dx):
        self.module.rhs(u, self.w, self.fx, self.fy, self.du, G, dx)
        return self.du


def make_backends(built: dict) -> dict:
    """Return, per technology, (step factory, thread setter or None). A factory takes m and returns step(u, dt, dx)."""
    backends = {"NumPy": (lambda m: lambda u, dt, dx: ref.ssp_rk2_step(u, dt, dx, ref.rhs), None)}
    try:
        nb = load("hydro2d_numba", HERE / "E04.1b-hydro2d-numba.py")
        import numba

        def numba_factory(m):
            kernel = nb.Kernel(m, G)
            return lambda u, dt, dx: ref.ssp_rk2_step(u, dt, dx, kernel)

        backends["Numba"] = (numba_factory, lambda n: numba.set_num_threads(min(n, numba.config.NUMBA_NUM_THREADS)))
    except ImportError:
        pass
    backends["Cython"] = (
        lambda m: (lambda kernel: lambda u, dt, dx: ref.ssp_rk2_step(u, dt, dx, kernel))(
            CythonKernel(built["Cython"], m)),
        built["Cython"].set_threads,
    )
    for variant in ("C (generic CPU)", "C (-march=native)"):
        lib = built[variant]
        backends[variant] = (
            (lambda lib: lambda m: (lambda kernel: lambda u, dt, dx: ref.ssp_rk2_step(u, dt, dx, kernel))(
                CKernel(lib, m)))(lib),
            lib.set_threads,
        )
    try:
        jx = load("hydro2d_jax", HERE / "E04.1e-hydro2d-jax.py")
        import jax.numpy as jnp

        def jax_factory(m):
            return lambda u, dt, dx: np.asarray(jx.step(jnp.asarray(u), dt, dx).block_until_ready())

        backends["JAX"] = (jax_factory, None)
    except ImportError:
        pass
    return backends


def time_per_step(step, u, dt, dx) -> float:
    best = float("inf")
    for _ in range(REPEATS):
        steps, start = 0, time.perf_counter()
        while True:
            step(u, dt, dx)
            steps += 1
            elapsed = time.perf_counter() - start
            if elapsed >= MIN_TIME and steps >= 2:
                break
        best = min(best, elapsed / steps)
    return best


def main() -> None:
    label, output = sys.argv[1], Path(sys.argv[2])
    with tempfile.TemporaryDirectory() as tmp:
        built = build(Path(tmp))
        backends = make_backends(built["modules"])
        results = {
            "label": label,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "versions": {"numpy": np.__version__},
            "build": built["info"],
            "first_call_seconds": {},
            "correctness": {},
            "throughput": {name: {} for name in backends},
            "scaling": {},
        }
        for module in ("numba", "jax", "Cython"):
            try:
                results["versions"][module] = __import__(module).__version__
            except ImportError:
                pass

        ## Correctness and first-call (compilation) cost, on 256^2 cells.
        n = 256
        u0, dx = ref.initial_state(n), 1.0 / n
        dt = 0.1 * dx
        reference = u0
        for _ in range(CHECK_STEPS):
            reference = ref.ssp_rk2_step(reference, dt, dx, ref.rhs)
        for name, (factory, set_threads) in backends.items():
            if set_threads:
                set_threads(1)
            step = factory(u0.shape[1])
            start = time.perf_counter()
            u = step(u0, dt, dx)
            results["first_call_seconds"][name] = time.perf_counter() - start
            for _ in range(CHECK_STEPS - 1):
                u = step(u, dt, dx)
            results["correctness"][name] = {
                "bitwise_identical": bool(np.array_equal(u, reference)),
                "max_relative_difference": float(np.max(np.abs(u - reference)) / np.max(np.abs(reference))),
            }
            print(f"{label}: {name} checked: {results['correctness'][name]}", flush=True)

        ## Single-thread throughput.
        for n in SIZES:
            u0, dx = ref.initial_state(n), 1.0 / n
            for name, (factory, set_threads) in backends.items():
                if set_threads:
                    set_threads(1)
                step = factory(u0.shape[1])
                step(u0, 0.1 * dx, dx)  ## warm-up
                seconds = time_per_step(step, u0, 0.1 * dx, dx)
                results["throughput"][name][n] = n * n / seconds
                print(f"{label}: {name} N={n}: {n * n / seconds:.3e} cell updates/s", flush=True)

        ## Thread scaling.
        n = SCALING_SIZE
        u0, dx = ref.initial_state(n), 1.0 / n
        for name, (factory, set_threads) in backends.items():
            if set_threads is None or (name != "Numba" and not built["info"]["openmp"]):
                continue
            results["scaling"][name] = {}
            step = factory(u0.shape[1])
            for threads in THREADS:
                set_threads(threads)
                step(u0, 0.1 * dx, dx)
                seconds = time_per_step(step, u0, 0.1 * dx, dx)
                results["scaling"][name][threads] = n * n / seconds
                print(f"{label}: {name} threads={threads}: {n * n / seconds:.3e}", flush=True)

    output.write_text(json.dumps(results, indent=1) + "\n")


if __name__ == "__main__":
    main()
