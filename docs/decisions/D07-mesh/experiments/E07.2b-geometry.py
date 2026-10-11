# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E07.2: what does general geometry cost in the kernel?

Curvilinear and nonuniform coordinates enter the finite-volume update through face areas and cell volumes. This
experiment times the three ways of supplying them in ``E07.2a-divergence.py`` against the full time-derivative kernel
of E07.1 (``E07.1a-kernels.py``), natively on one thread, for 2D and 3D blocks: uniform Cartesian (one cell width),
separable 1D factors per direction (enough for every orthogonal coordinate system), and full arrays per face and cell.
The fluxes are those computed by the kernel. With Cartesian values, all variants must reproduce the kernel's own result
bit for bit (checked). It also reports the memory each representation needs per block, relative to the conserved state.

The geometry enters the reconstruction too (slopes on nonuniform grids) and adds source terms in curvilinear
coordinates; those costs belong to the numerical building blocks (D10) and are not measured here.

Run from this directory with:

    uv run --locked --script E07.2b-geometry.py

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
NVAR = 5
MIN_TIME = 0.3
REPEATS = 5
SIZES = {"2D, 64²": (64, 64, 1), "2D, 512²": (512, 512, 1), "3D, 32³": (32, 32, 32), "3D, 64³": (64, 64, 64)}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path, name: str, source: Path):
    (workdir / f"{name}.py").write_text(source.read_text())
    subprocess.run([sys.executable, "-m", "cython", "-3", f"{name}.py", "-o", f"{name}.c"], cwd=workdir, check=True,
                   capture_output=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"{name}{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", f"{name}.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load(name, ext)


def state(nx: int, ny: int, nz: int) -> np.ndarray:
    axes = [(np.arange(n) + 0.5) / n for n in (nz, ny, nx)]
    zz, yy, xx = np.meshgrid(*axes, indexing="ij")
    s = 2 * np.pi
    rho = 1.0 + 0.2 * np.sin(s * xx) * np.cos(s * yy) * np.cos(s * zz)
    vx, vy, vz = 0.5 + 0.1 * np.sin(s * yy), 0.3 * np.cos(s * xx), 0.2 * np.sin(s * (xx + yy))
    pres = 1.0 + 0.1 * np.cos(s * (xx + yy + zz))
    u = np.array([rho, rho * vx, rho * vy, rho * vz, pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy + vz * vz)])
    pad = [(0, 0)] + [(G, G) if n > 1 else (0, 0) for n in (nz, ny, nx)]
    return np.ascontiguousarray(np.pad(u, pad, mode="wrap"))


def best_time(function) -> float:
    best = float("inf")
    for _ in range(REPEATS):
        calls, start = 0, time.perf_counter()
        while True:
            function()
            calls += 1
            elapsed = time.perf_counter() - start
            if elapsed >= MIN_TIME:
                break
        best = min(best, elapsed / calls)
    return best


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    rows = {}
    with tempfile.TemporaryDirectory() as tmp:
        kernel = build(Path(tmp), "kernels", HERE / "E07.1a-kernels.py")
        div = build(Path(tmp), "divergence", HERE / "E07.2a-divergence.py")
        for name, (nx, ny, nz) in SIZES.items():
            dx = 1.0 / nx
            u = state(nx, ny, nz)
            w = np.empty_like(u)
            fx, fy, fz = np.empty((NVAR, nz, ny, nx + 1)), np.empty((NVAR, nz, ny + 1, nx)), np.empty((NVAR, nz + 1, ny, nx))
            du = np.empty((NVAR, nz, ny, nx))
            kernel.rhs(u, w, fx, fy, fz, du, nx, ny, nz, G, dx)
            expected = du.copy()
            kernel_time = best_time(lambda: kernel.rhs(u, w, fx, fy, fz, du, nx, ny, nz, G, dx))

            ## Cartesian values: unit areas, volume factor dx along x and 1 elsewhere.
            ones = {n: np.ones(n) for n in {nx, ny, nz, nx + 1, ny + 1, nz + 1}}
            factors = (ones[nx + 1], ones[ny], ones[nz], ones[nx], ones[ny + 1], ones[nz], ones[nx], ones[ny],
                       ones[nz + 1], np.full(nx, dx), ones[ny], ones[nz])
            full = (np.ones((nz, ny, nx + 1)), np.ones((nz, ny + 1, nx)), np.ones((nz + 1, ny, nx)),
                    np.full((nz, ny, nx), dx))
            variants = {
                "uniform Cartesian (one cell width)": (lambda: div.div_cartesian(fx, fy, fz, du, nx, ny, nz, dx), 0),
                "separable 1D factors per direction": (
                    lambda: div.div_separable(fx, fy, fz, du, nx, ny, nz, *factors), sum(f.nbytes for f in factors)),
                "full arrays of areas and volumes": (
                    lambda: div.div_full(fx, fy, fz, du, nx, ny, nz, *full), sum(a.nbytes for a in full)),
            }
            case = rows[name] = {"kernel_seconds": kernel_time, "variants": {}}
            for variant, (call, nbytes) in variants.items():
                du[:] = np.nan
                call()
                identical = bool(np.array_equal(du, expected))
                seconds = best_time(call)
                case["variants"][variant] = {
                    "seconds": seconds, "fraction_of_kernel": seconds / kernel_time, "bitwise_identical": identical,
                    "geometry_bytes_per_state_bytes": nbytes / (u.nbytes),
                }
            print(name, case, flush=True)

    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "cases": rows}
    md = [
        "# E07.2: the cost of general geometry in the flux divergence",
        "",
        f"Natively, one thread; Python {platform.python_version()}, NumPy {np.__version__}, {platform.platform()}. "
        "Time of the divergence step as a share of one full time-derivative evaluation (primitives, reconstruction, "
        "HLL fluxes and Cartesian divergence); geometry memory relative to the block's conserved state.",
        "",
        "| Block | Geometry | Divergence / full kernel | Bit for bit | Geometry memory / state |",
        "|---|---|---|---|---|",
    ]
    for name, case in rows.items():
        for variant, row in case["variants"].items():
            md.append(f"| {name} | {variant} | {100 * row['fraction_of_kernel']:.1f} % | "
                      f"{'yes' if row['bitwise_identical'] else 'no'} | {100 * row['geometry_bytes_per_state_bytes']:.1f} % |")
    (RESULTS / "E07.2b-geometry.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E07.2b-geometry.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
