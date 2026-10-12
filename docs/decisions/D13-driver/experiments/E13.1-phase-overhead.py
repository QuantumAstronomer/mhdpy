# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E13.1: what does a synchronised phase cost, and should block-local phases be merged?

A step is a sequence of phases (D09.1, D11, D12): exchanges, boundary conditions, conversions, fluxes with their attached
passes, updates, sources, corrections, the time step. If the main thread runs every phase as a set of tasks on the
thread pool (D09.4) and waits for all of them, each phase costs a fixed amount of synchronisation, independent of the
grid. Phases that only touch their own blocks need no synchronisation between them: they could run back to back in one
task per worker. Only phases that read neighbouring blocks (after an exchange) or reduce over all blocks need to wait.

This experiment measures the fixed cost of one synchronised phase: a thread pool runs phases whose tasks do (almost)
nothing, one task per worker, for 1, 6 and 12 workers, with the free-threaded and the standard interpreter. It also
times a realistic step structure with the work removed: 24 phases per step (an SSP-RK2 step with stiff sources and
diagnostics), of which 6 must be synchronised, run either with every phase synchronised or with block-local phases
merged into the tasks of the next synchronised phase.

Run from this directory with (the machine otherwise idle):

    uv run --no-project --python 3.14 E13.1-phase-overhead.py

which runs ``E13.1-phase-overhead.py run`` with both interpreters and summarises. Results are written to results/.
"""

import concurrent.futures
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
WORKERS = [1, 6, 12]
PHASES_PER_STEP = 24
SYNCHRONISED_PER_STEP = 6
STEPS = 400
REPEATS = 5
RUNS = {"macos-native-3.14t": "3.14t", "macos-native-3.14": "3.14+gil"}


def task(n: int) -> int:
    """A placeholder for a phase's work on a range of blocks: almost nothing."""
    return n + 1


def run(label: str, output: Path) -> None:
    results = {"label": label, "python": sys.version, "platform": platform.platform(),
               "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(), "rows": {}}
    for workers in WORKERS:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            def phase(merged: int = 1):
                futures = [pool.submit(task, merged) for _ in range(workers)]
                for future in futures:
                    future.result()

            for _ in range(200):
                phase()
            best_single, best_all, best_merged = float("inf"), float("inf"), float("inf")
            for _ in range(REPEATS):
                start = time.perf_counter()
                for _ in range(STEPS * PHASES_PER_STEP):
                    phase()
                best_single = min(best_single, (time.perf_counter() - start) / (STEPS * PHASES_PER_STEP))
                start = time.perf_counter()
                for _ in range(STEPS):
                    for _ in range(PHASES_PER_STEP):
                        phase()
                best_all = min(best_all, (time.perf_counter() - start) / STEPS)
                start = time.perf_counter()
                for _ in range(STEPS):
                    for _ in range(SYNCHRONISED_PER_STEP):
                        phase(PHASES_PER_STEP // SYNCHRONISED_PER_STEP)
                best_merged = min(best_merged, (time.perf_counter() - start) / STEPS)
        results["rows"][str(workers)] = {"seconds_per_phase": best_single, "seconds_per_step_all_synchronised": best_all,
                                         "seconds_per_step_merged": best_merged}
        print(label, workers, results["rows"][str(workers)], flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2], Path(sys.argv[3]))
        return
    RESULTS.mkdir(exist_ok=True)
    for label, python in RUNS.items():
        subprocess.run(["uv", "run", "--locked", "--python", python, "--script", str(HERE / "E13.1-phase-overhead.py"),
                        "run", label, str(RESULTS / f"E13.1-{label}.json")], check=True)
    md = ["# E13.1: the fixed cost of synchronised phases", "",
          f"Thread pool, one task per worker per phase, tasks doing nothing; natively. A step has {PHASES_PER_STEP} "
          f"phases, of which {SYNCHRONISED_PER_STEP} must be synchronised. For scale: a step of the thesis grid takes "
          "about 110-150 ms on 6-12 workers (E09.1).", "",
          "| Interpreter | Workers | One synchronised phase | Step, every phase synchronised | Step, block-local phases "
          "merged | Share of a 120 ms step (all / merged) |", "|---|---|---|---|---|---|"]
    for label in RUNS:
        r = json.loads((RESULTS / f"E13.1-{label}.json").read_text())
        name = "with GIL" if r["gil_enabled"] else "free-threaded"
        for workers in WORKERS:
            row = r["rows"][str(workers)]
            md.append(f"| {name} | {workers} | {1e6 * row['seconds_per_phase']:.0f} µs | "
                      f"{1e3 * row['seconds_per_step_all_synchronised']:.2f} ms | {1e3 * row['seconds_per_step_merged']:.2f} ms "
                      f"| {100 * row['seconds_per_step_all_synchronised'] / 0.12:.1f} % / "
                      f"{100 * row['seconds_per_step_merged'] / 0.12:.1f} % |")
    (RESULTS / "E13.1-phase-overhead.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
