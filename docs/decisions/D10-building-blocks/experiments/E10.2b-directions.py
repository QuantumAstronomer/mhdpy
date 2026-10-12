# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E10.2: can the flux computation be written once for all three directions without losing speed?

D06.3 decided that kernels are written direction by direction, because a generic stencil with run-time offsets was
1.4-1.9x slower (E06.1); writing every direction out by hand triples the code. This experiment times four versions of
the same time derivative, natively (Clang) and in a Linux container (GCC, ``E10.1d-Dockerfile``), on one thread, for 2D
blocks of 64^2 and 512^2 and 3D blocks of 32^3:

- **direction-specific:** every direction written out (``rhs`` of ``E10.1a-kernels.py``, the D09 kernel);
- **one routine, inline:** ``rhs_routine`` of ``E10.2a-face-routine.py``, whose three directions call one inline routine
  with the direction as constant arguments, the five variables written out;
- **one routine, no inline hint:** the same with the ``@cython.inline`` hint removed, leaving inlining to the compiler;
- **generic:** ``rhs_generic``, the D06 generic kernel, whose routine also loops over the variables.

All versions must give the same result bit for bit (checked). Run from this directory with (Docker running, the
machine otherwise idle):

    uv run --no-project --python 3.14 E10.2b-directions.py

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

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
IMAGE = "mhdpy-e10"
G = 2
GAMMA = 1.4
NVAR = 5
MIN_TIME = 0.3
REPEATS = 9  ## interleaved: every repetition times every form once, so drift affects all forms alike
SIZES = {"2D, 64²": (64, 64, 1), "2D, 512²": (512, 512, 1), "3D, 32³": (32, 32, 32)}
FORMS = ["direction-specific", "one routine, inline", "one routine, no inline hint", "generic"]

def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def compile_module(workdir: Path, name: str, source: str):
    (workdir / f"{name}.py").write_text(source)
    subprocess.run([sys.executable, "-m", "cython", "-3", f"{name}.py", "-o", f"{name}.c"], cwd=workdir, check=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"{name}{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", f"{name}.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load(name, ext)


def build(workdir: Path):
    specific = compile_module(workdir, "specific", (HERE / "E10.1a-kernels.py").read_text())
    source = (HERE / "E10.2a-face-routine.py").read_text()
    routine = compile_module(workdir, "routine", source)
    marker = "@cython.cfunc\n@cython.inline\n@cython.nogil\n@cython.exceptval(check=False)\n@cython.boundscheck(False)\n" \
             "@cython.wraparound(False)\n@cython.initializedcheck(False)\ndef face_fluxes_unrolled("
    assert marker in source
    plain = compile_module(workdir, "routine_plain", source.replace(marker, marker.replace("@cython.inline\n", "")))
    compiler = subprocess.run(["cc", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    return (specific, routine, plain), compiler


def state(nx: int, ny: int, nz: int):
    import numpy as np

    axes = [(np.arange(n) + 0.5) / n for n in (nz, ny, nx)]
    zz, yy, xx = np.meshgrid(*axes, indexing="ij")
    s = 2 * np.pi
    rho = 1.0 + 0.2 * np.sin(s * xx) * np.cos(s * yy) * np.cos(s * zz)
    vx, vy, vz = 0.5 + 0.1 * np.sin(s * yy), 0.3 * np.cos(s * xx), 0.2 * np.sin(s * (xx + yy))
    pres = 1.0 + 0.1 * np.cos(s * (xx + yy + zz))
    u = np.array([rho, rho * vx, rho * vy, rho * vz, pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy + vz * vz)])
    pad = [(0, 0)] + [(G, G) if n > 1 else (0, 0) for n in (nz, ny, nx)]
    return np.ascontiguousarray(np.pad(u, pad, mode="wrap"))


def mean_time(function) -> float:
    """Mean duration of ``function()`` over calls lasting at least MIN_TIME in total."""
    calls, start = 0, time.perf_counter()
    while True:
        function()
        calls += 1
        elapsed = time.perf_counter() - start
        if elapsed >= MIN_TIME:
            return elapsed / calls


def run(label: str, output: Path) -> None:
    import numpy as np

    results = {"label": label, "python": sys.version, "platform": platform.platform(), "cases": {}}
    with tempfile.TemporaryDirectory() as tmp:
        (specific, routine, plain), compiler = build(Path(tmp))
        results["compiler"] = compiler
        for name, (nx, ny, nz) in SIZES.items():
            u = state(nx, ny, nz)
            w = np.empty_like(u)
            fx, fy, fz = (np.empty((NVAR, nz, ny, nx + 1)), np.empty((NVAR, nz, ny + 1, nx)),
                          np.empty((NVAR, nz + 1, ny, nx)))
            du = np.empty((NVAR, nz, ny, nx))
            dx = 1.0 / nx
            calls = {
                "direction-specific": lambda: specific.rhs(u, w, fx, fy, fz, du, nx, ny, nz, G, dx),
                "one routine, inline": lambda: routine.rhs_routine(u, w, fx, fy, fz, du, nx, ny, nz, G, dx),
                "one routine, no inline hint": lambda: plain.rhs_routine(u, w, fx, fy, fz, du, nx, ny, nz, G, dx),
                "generic": lambda: routine.rhs_generic(u, w, fx, fy, fz, du, nx, ny, nz, G, dx),
            }
            calls["direction-specific"]()
            expected = du.copy()
            case = results["cases"][name] = {}
            for form, call in calls.items():
                du[:] = np.nan
                call()
                case[form] = {"bitwise_identical": bool(np.array_equal(du, expected))}
            best = dict.fromkeys(calls, float("inf"))
            for _ in range(REPEATS):
                for form, call in calls.items():
                    best[form] = min(best[form], mean_time(call))
            for form in calls:
                case[form]["cells_per_second"] = nx * ny * nz / best[form]
            print(label, name, case, flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2], Path(sys.argv[3]))
        return
    RESULTS.mkdir(exist_ok=True)
    script = ["uv", "run", "--locked", "--script"]
    subprocess.run([*script, str(HERE / "E10.2b-directions.py"), "run", "macos-native",
                    str(RESULTS / "E10.2b-macos-native.json")], check=True)
    subprocess.run(["docker", "build", "--quiet", "-t", IMAGE, "-f", str(HERE / "E10.1d-Dockerfile"), str(HERE)],
                   check=True)
    subprocess.run(["docker", "run", "--rm", "--platform", "linux/amd64", "-v", f"{HERE}:/work:ro",
                    "-v", f"{RESULTS}:/out", "-v", "mhdpy-e10-uv-cache:/root/.cache/uv", "-w", "/work", IMAGE,
                    *script, "E10.2b-directions.py", "run", "linux-container", "/out/E10.2b-linux-container.json"],
                   check=True)
    md = ["# E10.2: one flux routine for all directions", "",
          "One evaluation of the time derivative on one block, one thread. Million cells per second, and relative to "
          "the direction-specific kernel; ✓ = bit-for-bit identical to it.", ""]
    for label in ("macos-native", "linux-container"):
        r = json.loads((RESULTS / f"E10.2b-{label}.json").read_text())
        md += [f"## {label} ({r['compiler']})", "", "| Block | " + " | ".join(FORMS) + " |", "|" + "---|" * 5]
        for name, case in r["cases"].items():
            base = case["direction-specific"]["cells_per_second"]
            md.append(f"| {name} | " + " | ".join(
                f"{case[f]['cells_per_second'] / 1e6:.1f} ({case[f]['cells_per_second'] / base:.2f}) "
                f"{'✓' if case[f]['bitwise_identical'] else '✗'}" for f in FORMS) + " |")
        md.append("")
    (RESULTS / "E10.2b-directions.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
