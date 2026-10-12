# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E09.2: how should blocks be assigned to workers when their cost differs?

On the thesis problem, the cost per block will not be uniform: radiative cooling with substeps, for example, costs most
where the gas cools fastest, in and around the cloud. This experiment emulates that on the thesis grid (4000 x 1000,
blocks of 50^2 in Morton order, D07.4): blocks whose centre lies within 0.25 (in units of the domain height) of a point
at x = 1, y = 0.5 get extra work in every stage (``busy_block`` of ``E09.1a-kernels.py``), calibrated to cost four times
the hydrodynamic update of a block. That is about 5 % of the blocks, adding about 20 % to the total work, concentrated in
one compact region, and therefore in a few contiguous Morton ranges.

The blocks are assigned to the workers of a persistent team (ranged calls, E09.1) in three ways:

- **static, equal counts:** contiguous Morton ranges with the same number of blocks per worker (E05-E09.1);
- **static, cost-weighted:** contiguous Morton ranges with the same total cost per worker, from the known cost of every
  block (Athena++ balances its processes this way, with measured costs);
- **dynamic:** workers claim chunks of 4 consecutive blocks from a shared counter, stage by stage, until none are left.

Each is compared with the same assignment on the same grid without extra work (static equal counts for the two
static assignments, dynamic for the dynamic one), scaled by the total work: that ratio is the efficiency of the
balance. The uniform runs also show what dynamic assignment gains when all blocks cost the same. Every run is checked bit for bit against a single-block serial reference (the extra work does not change the
state). Run from this directory with (the machine otherwise idle):

    uv run --no-project --python 3.14 E09.2-load-balance.py

which runs ``E09.2-load-balance.py run`` with the free-threaded (3.14t) and the standard (3.14+gil) interpreter, on 6
and 12 workers, and summarises. Results are written to results/.
"""

import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results"
WORKERS = [6, 12]
BLOCK = 50
CLOUD = (1.0, 0.5, 0.25)  ## centre x, centre y, radius, in units of the domain height
COST_FACTOR = 4.0  ## extra work of a cloud block, relative to its hydrodynamic update
CHUNK = 4
RUNS = {"macos-native-3.14t": "3.14t", "macos-native-3.14": "3.14+gil"}
TITLES = {"macos-native-3.14t": "free-threaded", "macos-native-3.14": "with GIL"}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def weighted_ranges(weights, workers: int) -> list[tuple[int, int]]:
    """Contiguous ranges whose total weights are as equal as possible (split at the prefix-sum quantiles)."""
    total = sum(weights)
    bounds, acc, b = [0], 0.0, 0
    for r in range(1, workers):
        target = total * r / workers
        while b < len(weights) and acc + weights[b] / 2 < target:
            acc += weights[b]
            b += 1
        bounds.append(b)
    bounds.append(len(weights))
    return [(bounds[r], bounds[r + 1]) for r in range(workers)]


def run(label: str, output: Path) -> None:
    import numpy as np

    o = load("orchestration", HERE / "E09.1b-orchestration.py")
    nx, ny = o.GRID
    results = {"label": label, "python": sys.version, "platform": platform.platform(), "rows": {}}
    with tempfile.TemporaryDirectory() as tmp:
        kernel = o.build(Path(tmp))
        results["gil_enabled_after_import"] = getattr(sys, "_is_gil_enabled", lambda: True)()
        expected = o.reference(kernel, nx, ny, o.CHECK_STEPS)
        blocks = o.Blocks(nx, ny, BLOCK, BLOCK)

        ## Calibrate the extra work: repeats of busy_block that cost COST_FACTOR times one block's stage.
        worker = o.Worker(blocks, kernel, np.zeros((3, *blocks.shape)), np.zeros(blocks.count, dtype=np.intp))
        worker.buffers[0, :, 0] = 1.0
        worker.buffers[0, :, 4] = 2.5
        start = time.perf_counter()
        for _ in range(20):
            worker.stage(1, 0, 1, 2, 0, 16, True)
        hydro = (time.perf_counter() - start) / (20 * 16)
        start = time.perf_counter()
        for _ in range(20):
            kernel.busy(worker.buffers[0, 0], worker.scratch, 100)
        per_repeat = (time.perf_counter() - start) / (20 * 100)
        repeats = max(1, round(COST_FACTOR * hydro / per_repeat))

        cloud = []
        for ci, cj in blocks.locations:
            x, y = (ci + 0.5) * BLOCK / ny, (cj + 0.5) * BLOCK / ny
            cloud.append((x - CLOUD[0]) ** 2 + (y - CLOUD[1]) ** 2 < CLOUD[2] ** 2)
        costs = np.array([repeats if c else 0 for c in cloud], dtype=np.intp)
        weights = [1.0 + COST_FACTOR * c for c in cloud]
        work = sum(weights) / blocks.count
        results.update({"repeats": repeats, "cloud_blocks": int(sum(cloud)), "blocks": blocks.count,
                        "work_factor": work})

        for workers in WORKERS:
            equal = o.equal_ranges(blocks.count, workers)
            uniform = o.measure(o.Team(workers, blocks, kernel, "ranged calls, persistent team", equal), blocks,
                                expected)
            results["rows"][f"uniform cost, static equal counts | {workers}"] = {**uniform, "efficiency": 1.0}
            uniform_dynamic = o.measure(o.Team(workers, blocks, kernel, "ranged calls, persistent team", "dynamic",
                                               chunk=CHUNK), blocks, expected)
            results["rows"][f"uniform cost, dynamic, chunks of 4 | {workers}"] = {**uniform_dynamic, "efficiency": 1.0}
            schedules = {
                "static, equal counts": equal,
                "static, cost-weighted": weighted_ranges(weights, workers),
                "dynamic, chunks of 4": "dynamic",
            }
            for name, schedule in schedules.items():
                team = o.Team(workers, blocks, kernel, "ranged calls, persistent team", schedule, costs=costs,
                              chunk=CHUNK)
                row = o.measure(team, blocks, expected)
                base = uniform_dynamic if schedule == "dynamic" else uniform
                row["efficiency"] = base["seconds_per_step"] * work / row["seconds_per_step"]
                if schedule != "dynamic":
                    loads = [sum(weights[b0:b1]) for b0, b1 in schedule]
                    row["max_over_mean_worker_load"] = max(loads) / (sum(loads) / len(loads))
                results["rows"][f"{name} | {workers}"] = row
                print(f"{label} | {name} | {workers}: {row['seconds_per_step'] * 1e3:.1f} ms/step, efficiency "
                      f"{row['efficiency']:.2f}, identical {row['bitwise_identical']}", flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2], Path(sys.argv[3]))
        return
    RESULTS.mkdir(exist_ok=True)
    for label, python in RUNS.items():
        subprocess.run(["uv", "run", "--locked", "--python", python, "--script", str(HERE / "E09.2-load-balance.py"),
                        "run", label, str(RESULTS / f"E09.2-{label}.json")], check=True)
    md = ["# E09.2: assigning blocks of unequal cost to workers", ""]
    for label in RUNS:
        r = json.loads((RESULTS / f"E09.2-{label}.json").read_text())
        md += [
            f"## {TITLES[label]}",
            "",
            f"{r['platform']}; Python {r['python'].split()[0]}; GIL enabled after importing the kernels: "
            f"{r['gil_enabled_after_import']}. {r['cloud_blocks']} of {r['blocks']} blocks of {BLOCK}² carry extra work "
            f"of {COST_FACTOR:g}× their hydrodynamic update ({r['repeats']} repeats); total work × {r['work_factor']:.3f}. "
            "Efficiency: time of the uniform-cost run with the same kind of assignment (static or dynamic), scaled by "
            "the total work, divided by the measured time. ✓ = bit for bit identical to the reference.",
            "",
            "| Assignment | Workers | ms per step | Efficiency | Max / mean worker load | Bit for bit |",
            "|---|---|---|---|---|---|",
        ]
        for key, row in r["rows"].items():
            name, workers = key.split(" | ")
            load_ratio = row.get("max_over_mean_worker_load")
            md.append(f"| {name} | {workers} | {row['seconds_per_step'] * 1e3:.1f} | {row['efficiency']:.2f} | "
                      f"{'' if load_ratio is None else f'{load_ratio:.2f}'} | "
                      f"{'✓' if row['bitwise_identical'] else '✗'} |")
        md.append("")
    (RESULTS / "E09.2-load-balance.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
