# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E06.1: how do memory layout, index order and dimensionality affect the kernel?

The time derivative of the five-variable hydro kernel (D04 arithmetic, three velocity components) is evaluated on one
block, natively on one thread, in several data layouts:

- the two-dimensional kernel ``E06.1a-kernel2d.py`` in struct-of-arrays layout ``u[var, j, i]``, and the same kernel
  in array-of-structs layout ``u[j, i, var]``, derived from it by permuting the indices of every array access;
- the three-dimensional kernel ``E06.1b-kernel3d.py`` in the layout of Athena++, ``u[var, k, j, i]`` with x contiguous,
  run on 2D data (extent 1 in z) and on 1D data (extent 1 in y and z). It is written generically: one stencil routine
  for all three directions, with the direction as run-time offsets;
- the direction-specific three-dimensional kernel ``E06.1d-kernel3d-specialised.py``: the same layout and arithmetic,
  in the code style of the two-dimensional kernel (every direction written out, every variable unrolled);
- the same three-dimensional kernel with x as the *slowest* index (``u[var, x, y, z]``, as Ulula and the D04
  experiments order their 2D arrays), where lower-dimensional data has extent 1 in the contiguous direction. This is
  obtained by handing the kernel arrays whose axes are relabelled (its "k" is the physical x), with the momentum
  components permuted accordingly;
- the three-dimensional kernel on 3D blocks, for reference.

Results are compared with the three-dimensional kernel in the x-contiguous layout: bit for bit, and as the largest
relative difference.

Run from this directory with:

    uv run --locked --script E06.1c-layouts.py

Results are written to results/.
"""

import importlib.util
import json
import platform
import re
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
MIN_TIME = 0.3
REPEATS = 5
## Physical momentum order (rho, m_x, m_y, m_z, E) -> kernel order when the kernel's z axis is the physical x axis.
RELABEL = [0, 3, 2, 1, 4]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path, name: str, source: str):
    (workdir / f"{name}.py").write_text(source)
    subprocess.run([sys.executable, "-m", "cython", "-3", f"{name}.py", "-o", f"{name}.c"], cwd=workdir, check=True,
                   capture_output=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"{name}{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", f"{name}.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load(name, ext)


def to_array_of_structs(source: str) -> str:
    """Move the variable index of every 3-index array access to the end: a[v, j, i] -> a[j, i, v]."""
    pattern = r"\b(u|w|fx|fy|du|out)\[([^\[\],]+), ([^\[\],]+), ([^\[\],]+)\]"
    return re.sub(pattern, r"\1[\3, \4, \2]", source)


def physical_state(nx: int, ny: int, nz: int) -> np.ndarray:
    """Smooth periodic conserved state [var, z, y, x] with ghost cells in the active directions."""
    axes = [(np.arange(n) + 0.5) / n for n in (nz, ny, nx)]
    zz, yy, xx = np.meshgrid(*axes, indexing="ij")
    s = 2 * np.pi
    rho = 1.0 + 0.2 * np.sin(s * xx) * np.cos(s * yy) * np.cos(s * zz)
    vx = 0.5 + 0.1 * np.sin(s * yy) + 0.1 * np.cos(s * zz)
    vy = 0.3 * np.cos(s * xx) + 0.1 * np.sin(s * zz)
    vz = 0.2 * np.sin(s * (xx + yy))
    pres = 1.0 + 0.1 * np.cos(s * (xx + yy + zz))
    u = np.array([rho, rho * vx, rho * vy, rho * vz,
                  pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy + vz * vz)])
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


def run3d(kernel, u: np.ndarray, nx: int, ny: int, nz: int):
    """Return (time derivative [var, k, j, i], function that evaluates it) for the 3D kernel."""
    w = np.empty_like(u)
    fx, fy, fz = np.empty((5, nz, ny, nx + 1)), np.empty((5, nz, ny + 1, nx)), np.empty((5, nz + 1, ny, nx))
    du = np.empty((5, nz, ny, nx))

    def call():
        kernel.rhs(u, w, fx, fy, fz, du, nx, ny, nz, G, 1.0 / max(nx, ny, nz))

    call()
    return du.copy(), call


def compare(result: np.ndarray, reference: np.ndarray) -> dict:
    scale = np.max(np.abs(reference))
    return {"bitwise_identical": bool(np.array_equal(result, reference)),
            "max_relative_difference": float(np.max(np.abs(result - reference)) / scale)}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    rows, cells = {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        source2d = (HERE / "E06.1a-kernel2d.py").read_text()
        soa2d = build(workdir, "kernel2d_soa", source2d)
        aos2d = build(workdir, "kernel2d_aos", to_array_of_structs(source2d))
        k3d = build(workdir, "kernel3d", (HERE / "E06.1b-kernel3d.py").read_text())
        k3s = build(workdir, "kernel3d_specialised", (HERE / "E06.1d-kernel3d-specialised.py").read_text())

        def specialised(case, u, nx, ny, nz, reference):
            result, call = run3d(k3s, u, nx, ny, nz)
            case["3D kernel, direction-specific, x contiguous"] = {"seconds": best_time(call),
                                                                   **compare(result, reference)}

        for n in (64, 512):
            case = rows[f"2D, {n}² cells"] = {}
            cells[f"2D, {n}² cells"] = n * n
            u = physical_state(n, n, 1)
            reference, call = run3d(k3d, u, n, n, 1)
            case["3D kernel, x contiguous [var, k, j, i]"] = {"seconds": best_time(call), **compare(reference, reference)}
            specialised(case, u, n, n, 1, reference)

            u2 = np.ascontiguousarray(u[:, 0])
            w, fx, fy, du = np.empty_like(u2), np.empty((5, n, n + 1)), np.empty((5, n + 1, n)), np.empty((5, n, n))
            soa2d.rhs(u2, w, fx, fy, du, n, n, G, 1.0 / n)
            case["2D kernel, struct of arrays [var, j, i]"] = {
                "seconds": best_time(lambda: soa2d.rhs(u2, w, fx, fy, du, n, n, G, 1.0 / n)),
                **compare(du[:, None], reference)}

            ua = np.ascontiguousarray(np.moveaxis(u2, 0, -1))
            wa, fxa, fya, dua = (np.empty_like(ua), np.empty((n, n + 1, 5)), np.empty((n + 1, n, 5)),
                                 np.empty((n, n, 5)))
            aos2d.rhs(ua, wa, fxa, fya, dua, n, n, G, 1.0 / n)
            case["2D kernel, array of structs [j, i, var]"] = {
                "seconds": best_time(lambda: aos2d.rhs(ua, wa, fxa, fya, dua, n, n, G, 1.0 / n)),
                **compare(np.moveaxis(dua, -1, 0)[:, None], reference)}

            us = np.ascontiguousarray(u[RELABEL].transpose(0, 3, 2, 1))  ## [var, x, y, z=1]
            slow, call = run3d(k3d, us, 1, n, n)
            case["3D kernel, x slowest [var, i, j, k]"] = {
                "seconds": best_time(call), **compare(slow[RELABEL].transpose(0, 3, 2, 1), reference)}

        n = 4096
        case = rows[f"1D, {n} cells"] = {}
        cells[f"1D, {n} cells"] = n
        u = physical_state(n, 1, 1)
        reference, call = run3d(k3d, u, n, 1, 1)
        case["3D kernel, x contiguous [var, k, j, i]"] = {"seconds": best_time(call), **compare(reference, reference)}
        specialised(case, u, n, 1, 1, reference)
        us = np.ascontiguousarray(u[RELABEL].transpose(0, 3, 2, 1))
        slow, call = run3d(k3d, us, 1, 1, n)
        case["3D kernel, x slowest [var, i, j, k]"] = {
            "seconds": best_time(call), **compare(slow[RELABEL].transpose(0, 3, 2, 1), reference)}

        for n in (32, 64):
            u = physical_state(n, n, n)
            reference, call = run3d(k3d, u, n, n, n)
            cells[f"3D, {n}³ cells"] = n**3
            rows[f"3D, {n}³ cells"] = {"3D kernel, x contiguous [var, k, j, i]": {"seconds": best_time(call),
                                                                                 **compare(reference, reference)}}
            specialised(rows[f"3D, {n}³ cells"], u, n, n, n, reference)

    for name, case in rows.items():
        for row in case.values():
            row["cells_per_second"] = cells[name] / row["seconds"]
    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "cases": rows}
    md = [
        "# E06.1: memory layout, index order and dimensionality",
        "",
        f"Natively, one thread; Python {platform.python_version()}, NumPy {np.__version__}, {platform.platform()}. "
        "Cells per second for one evaluation of the time derivative (primitives, reconstruction, HLL fluxes, "
        "divergence); compared with the 3D kernel in the x-contiguous layout.",
        "",
        "| Case | Layout | Cells per second | Relative to 3D kernel, x contiguous | Bit for bit | Max. rel. difference |",
        "|---|---|---|---|---|---|",
    ]
    for name, case in rows.items():
        base = case["3D kernel, x contiguous [var, k, j, i]"]["cells_per_second"]
        for layout, row in case.items():
            md.append(f"| {name} | {layout} | {row['cells_per_second']:.2e} | {row['cells_per_second'] / base:.2f} | "
                      f"{'yes' if row['bitwise_identical'] else 'no'} | {row['max_relative_difference']:.1e} |")
    (RESULTS / "E06.1c-layouts.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E06.1c-layouts.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
