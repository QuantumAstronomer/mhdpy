# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E05.3: do global reductions depend on how the grid is divided among blocks and workers?

The evolved state of E05.2 is independent of the decomposition, because every cell is computed by the same arithmetic
whichever block or worker it belongs to. Global *reductions* are different: the total mass or energy written to a
history file, or a norm in a solver, is a sum over all cells, and floating-point addition is not associative. A parallel
code sums per block (or per worker) and then combines the partial sums, so the result can depend on the block size, on
the order in which the partial sums are combined, and on the number of workers.

This experiment sums the total energy of a smooth state on a thesis-sized grid of 4096 x 1024 cells:

- with NumPy over the whole grid (pairwise summation);
- per block of 32^2, 64^2 and 128^2 cells with NumPy, the partial sums added in block order, in reverse order, and in
  a few shuffled orders (the order a dynamic scheduler or MPI reduction might produce);
- exactly rounded, with ``math.fsum`` over all cells, and per block with ``math.fsum`` followed by an exact combination
  of the per-block partials (each block hands over the exact, non-overlapping parts of its sum, as ``fsum`` keeps them
  internally), which is exact for every decomposition and order.

Each result is compared with the exactly rounded sum, in ulp. It also checks that the minimum, the reduction behind the
time step, is identical in every order, and times each method.

Run from this directory with:

    uv run --locked --script E05.3-reductions.py

Results are written to results/.
"""

import json
import math
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).parent / "results"
NX, NY = 4096, 1024
BLOCKS = [32, 64, 128]
SHUFFLES = 5
GAMMA = 1.4


def total_energy_density() -> np.ndarray:
    """The smooth state of E05.2 on a 4 x 1 domain, here its total energy density (positive, varying by ~20 %)."""
    dx = 1.0 / NY
    x = (np.arange(NX) + 0.5) * dx
    y = (np.arange(NY) + 0.5) * dx
    xx, yy = np.meshgrid(x, y, indexing="ij")
    rho = 1.0 + 0.2 * np.sin(2 * np.pi * xx) * np.sin(2 * np.pi * yy)
    vx = 0.5 + 0.1 * np.sin(2 * np.pi * yy)
    vy = 0.3 * np.cos(2 * np.pi * xx)
    pres = 1.0 + 0.1 * np.cos(2 * np.pi * (xx + yy))
    return pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy)


def blocks(field: np.ndarray, b: int) -> list[np.ndarray]:
    return [field[i : i + b, j : j + b] for i in range(0, NX, b) for j in range(0, NY, b)]


def exact_partials(values) -> list[float]:
    """Shewchuk's algorithm, as inside math.fsum: non-overlapping floats whose exact sum is the exact sum of values."""
    partials: list[float] = []
    for x in values:
        i = 0
        for y in partials:
            if abs(x) < abs(y):
                x, y = y, x
            hi = x + y
            lo = y - (hi - x)
            if lo:
                partials[i] = lo
                i += 1
            x = hi
        partials[i:] = [x]
    return partials


def sequential_sum(values: list[float]) -> float:
    """Add the values one by one, left to right, as a fixed-order combination of partial sums does."""
    total = 0.0
    for value in values:
        total += value
    return total


def ulps(value: float, exact: float) -> float:
    return (value - exact) / math.ulp(exact)


def timed(function):
    start = time.perf_counter()
    result = function()
    return result, time.perf_counter() - start


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    field = total_energy_density()
    exact, fsum_seconds = timed(lambda: math.fsum(field.ravel().tolist()))
    rows: dict[str, dict] = {}

    whole, seconds = timed(lambda: float(np.sum(field)))
    rows["NumPy, whole grid"] = {"ulp": [ulps(whole, exact)], "seconds": seconds}
    rng = random.Random(1)
    for b in BLOCKS:
        parts, seconds = timed(lambda: [float(np.sum(block)) for block in blocks(field, b)])
        orders = {"block": [parts], "reverse": [parts[::-1]], "shuffled": []}
        for _ in range(SHUFFLES):
            shuffled = parts[:]
            rng.shuffle(shuffled)
            orders["shuffled"].append(shuffled)
        for name, sequences in orders.items():
            rows[f"NumPy per block of {b}², partial sums added in {name} order"] = {
                "ulp": [ulps(sequential_sum(sequence), exact) for sequence in sequences], "seconds": seconds,
            }

    rows["exactly rounded (math.fsum), whole grid"] = {"ulp": [0.0], "seconds": fsum_seconds}
    for b in BLOCKS:

        def exact_by_blocks(order: list[int]) -> float:
            partials = [exact_partials(block.ravel().tolist()) for block in blocks(field, b)]
            return math.fsum(p for k in order for p in partials[k])

        count = (NX // b) * (NY // b)
        order = list(range(count))
        results = []
        total, seconds = timed(lambda: exact_by_blocks(order))
        results.append(total)
        for _ in range(2):
            rng.shuffle(order)
            results.append(exact_by_blocks(order))
        rows[f"exact per block of {b}² (Python), any order"] = {"ulp": [ulps(r, exact) for r in results],
                                                               "seconds": seconds}

    minima = {float(np.min(field))}
    for b in BLOCKS:
        mins = [float(np.min(block)) for block in blocks(field, b)]
        for _ in range(SHUFFLES):
            rng.shuffle(mins)
            minima.add(min(mins))

    results = {
        "python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "grid": [NX, NY],
        "exact_sum": exact, "rows": rows, "distinct_minima": len(minima),
    }
    md = [
        "# E05.3: global sums over blocks",
        "",
        f"Total energy of a smooth state on {NX} × {NY} cells; Python {platform.python_version()}, NumPy "
        f"{np.__version__}, {platform.platform()}. Differences from the exactly rounded sum in ulp (one ulp of the "
        f"sum is {math.ulp(exact):.1e}, relative {math.ulp(exact) / exact:.1e}); several values are the different "
        f"orders tried.",
        "",
        "| Method | Difference (ulp) | Distinct results | Time (ms) |",
        "|---|---|---|---|",
    ]
    for name, row in rows.items():
        values = sorted(set(row["ulp"]))
        shown = ", ".join(f"{v:+.0f}" for v in values)
        md.append(f"| {name} | {shown} | {len(values)} | {1e3 * row['seconds']:.1f} |")
    md += [
        "",
        f"The minimum over all cells, computed whole and per block in {SHUFFLES} shuffled orders for each block size, "
        f"gave {len(minima)} distinct value(s).",
        "",
    ]
    (RESULTS / "E05.3-reductions.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E05.3-reductions.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
