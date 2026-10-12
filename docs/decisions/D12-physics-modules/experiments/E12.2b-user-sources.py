# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E12.2: can a user write a source term in NumPy, or must it be compiled?

Users and module authors without a C compiler would write source terms in NumPy. Under the execution model of D09
(a thread pool, workers claiming ranges of blocks), how does such a source term perform compared with a compiled one?
NumPy releases the GIL inside its array operations, so a NumPy source over a whole range of blocks might scale with
threads even under the standard interpreter, while a Python loop over blocks would not.

The source is a constant gravitational acceleration (E += dt g m_y, then m_y += dt g rho) applied to the state of the
thesis grid (4000 x 1000 cells in 1600 blocks of 50^2, two ghost cells). Three forms:

- **compiled:** ``gravity`` of ``E12.2a-source-kernel.py``, one call per range of blocks;
- **NumPy, per range:** the same arithmetic as two NumPy statements over the whole range of blocks;
- **NumPy, per block:** the same statements in a Python loop over the blocks of the range.

Each is run by a thread pool with 1 and 6 workers, each worker taking one sixth of the blocks, with the free-threaded and
the standard interpreter; all forms must give the same result bit for bit (checked). For scale, one evaluation of the
hydrodynamic time derivative runs at about 6-7 million cells per second per core (E07.1, E09.1).

Run from this directory with (the machine otherwise idle):

    uv run --no-project --python 3.14 E12.2b-user-sources.py

which runs ``E12.2b-user-sources.py run`` with both interpreters and summarises. Results are written to results/.
"""

import concurrent.futures
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
BLOCKS, B, G = 1600, 50, 2
DTG = 1.0e-3
WORKERS = [1, 6]
REPEATS = 7
MIN_TIME = 0.3
RUNS = {"macos-native-3.14t": "3.14t", "macos-native-3.14": "3.14+gil"}
FORMS = ["compiled", "NumPy, per range", "NumPy, per block"]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path):
    (workdir / "source.py").write_text((HERE / "E12.2a-source-kernel.py").read_text())
    subprocess.run([sys.executable, "-m", "cython", "-3", "source.py", "-o", "source.c"], cwd=workdir, check=True,
                   capture_output=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"source{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", "source.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    return load("source", ext)


def run(label: str, output: Path) -> None:
    import numpy as np

    rng = np.random.default_rng(1)
    initial = 1.0 + rng.random((BLOCKS, 5, 1, B + 2 * G, B + 2 * G))
    inner = (slice(None), 0, slice(G, -G), slice(G, -G))
    results = {"label": label, "python": sys.version, "platform": platform.platform(), "rows": {}}
    with tempfile.TemporaryDirectory() as tmp:
        kernel = build(Path(tmp))
        results["gil_enabled_after_import"] = getattr(sys, "_is_gil_enabled", lambda: True)()

        def numpy_range(pack, b0, b1):
            part = pack[b0:b1]
            part[(slice(None), 4, *inner[1:])] += DTG * part[(slice(None), 2, *inner[1:])]
            part[(slice(None), 2, *inner[1:])] += DTG * part[(slice(None), 0, *inner[1:])]

        def numpy_block(pack, b0, b1):
            for b in range(b0, b1):
                block = pack[b]
                block[(4, *inner[1:])] += DTG * block[(2, *inner[1:])]
                block[(2, *inner[1:])] += DTG * block[(0, *inner[1:])]

        functions = {"compiled": lambda pack, b0, b1: kernel.gravity(pack, b0, b1, G, DTG),
                     "NumPy, per range": numpy_range, "NumPy, per block": numpy_block}
        reference = initial.copy()
        functions["compiled"](reference, 0, BLOCKS)
        for workers in WORKERS:
            ranges = [(r * BLOCKS // workers, (r + 1) * BLOCKS // workers) for r in range(workers)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                def apply(function, pack):
                    for future in [pool.submit(function, pack, b0, b1) for b0, b1 in ranges]:
                        future.result()

                identical = {}
                for form, function in functions.items():
                    pack = initial.copy()
                    apply(function, pack)
                    identical[form] = bool(np.array_equal(pack, reference))
                pack = initial.copy()
                best = dict.fromkeys(functions, float("inf"))
                for _ in range(REPEATS):
                    for form, function in functions.items():
                        calls, start = 0, time.perf_counter()
                        while True:
                            apply(function, pack)
                            calls += 1
                            elapsed = time.perf_counter() - start
                            if elapsed >= MIN_TIME:
                                break
                        best[form] = min(best[form], elapsed / calls)
                for form in functions:
                    results["rows"][f"{form} | {workers}"] = {
                        "cells_per_second": BLOCKS * B * B / best[form], "bitwise_identical": identical[form]}
                print(label, workers, {f: f"{BLOCKS * B * B / best[f]:.2e}" for f in functions}, identical, flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2], Path(sys.argv[3]))
        return
    RESULTS.mkdir(exist_ok=True)
    for label, python in RUNS.items():
        subprocess.run(["uv", "run", "--locked", "--python", python, "--script", str(HERE / "E12.2b-user-sources.py"),
                        "run", label, str(RESULTS / f"E12.2b-{label}.json")], check=True)
    md = ["# E12.2: user source terms in NumPy or compiled", "",
          f"Constant gravity on {BLOCKS} blocks of {B}² (the thesis grid), thread pool, natively. Million cells per "
          "second for the source term alone; ✓ = bit-for-bit identical to the compiled form on one worker.", "",
          "| Interpreter | Workers | " + " | ".join(FORMS) + " |", "|" + "---|" * (len(FORMS) + 2)]
    for label in RUNS:
        r = json.loads((RESULTS / f"E12.2b-{label}.json").read_text())
        name = "with GIL" if r["gil_enabled_after_import"] else "free-threaded"
        for workers in WORKERS:
            cells = [f"{r['rows'][f'{f} | {workers}']['cells_per_second'] / 1e6:.0f} "
                     f"{'✓' if r['rows'][f'{f} | {workers}']['bitwise_identical'] else '✗'}" for f in FORMS]
            md.append(f"| {name} | {workers} | " + " | ".join(cells) + " |")
    (RESULTS / "E12.2b-user-sources.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
