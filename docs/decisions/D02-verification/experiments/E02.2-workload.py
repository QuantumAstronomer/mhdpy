"""Workload of experiment E02.2: a fixed set of floating-point computations, run once per environment.

Run by ``E02.2-fp-reproducibility.py`` in each Python / NumPy environment; not meant to be run by hand. Computes:

- reductions: a pairwise sum and a BLAS dot product over 10^6 elements;
- elementwise functions on 100 001 points: sqrt (correctly rounded by IEEE 754) and sin, exp, log and power (not
  required to be correctly rounded, so implementations may differ);
- two runs of the E02.1 solver: the Sod shock tube (arithmetic, sqrt, min/max only) and the linear sound wave (whose
  initial condition also uses sin).

The arrays are written to the .npz file given as the first argument; a JSON description of the environment is printed.
"""

import importlib.util
import json
import platform
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("hydro1d", HERE / "E02.1-hydro1d.py")
assert _spec is not None and _spec.loader is not None
hydro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hydro)


def main() -> None:
    k = np.arange(1, 1_000_001, dtype=np.float64)
    x = np.linspace(1.0e-3, 10.0, 100_001)
    results = {
        "sum": np.array([np.sum(1.0 / k)]),
        "dot": np.array([np.dot(1.0 / k, np.sqrt(k))]),
        "sqrt": np.sqrt(x),
        "sin": np.sin(x),
        "exp": np.exp(x),
        "log": np.log(x),
        "power": np.power(x, 1.4),
    }
    n = 256
    sod, _ = hydro.evolve(
        hydro.shock_tube(n, hydro.SOD_LEFT, hydro.SOD_RIGHT), 1.0 / n, 0.2, limiter="mc", boundary="outflow"
    )
    wave, _ = hydro.evolve(hydro.sound_wave(n), 1.0 / n, 1.0, limiter="mc", boundary="periodic")
    results["Sod solver run"] = sod
    results["sound-wave solver run"] = wave
    np.savez(sys.argv[1], **results)

    from numpy._core._multiarray_umath import __cpu_features__  # noqa: PLC0415

    ## Newer NumPy versions dispatch whole feature groups (X86_V3 contains AVX2 and FMA3, X86_V4 the AVX-512 set) and
    ## then report hardware support for the individual features; older versions report the individual features as
    ## dispatched. Report whichever level NumPy actually dispatches on. On ARM, report the vector extensions.
    if platform.machine() in ("aarch64", "arm64"):
        levels = ("ASIMD", "ASIMDHP", "ASIMDDP", "SVE")
    elif "X86_V3" in __cpu_features__:
        levels = ("X86_V3", "X86_V4")
    else:
        levels = ("AVX2", "FMA3", "AVX512F")
    print(
        json.dumps(
            {
                "system": f"{platform.system()} {platform.machine()} {' '.join(platform.libc_ver())}".strip(),
                "python": platform.python_version(),
                "numpy": np.__version__,
                "simd": [f for f in levels if __cpu_features__.get(f)],
            }
        )
    )


if __name__ == "__main__":
    main()
