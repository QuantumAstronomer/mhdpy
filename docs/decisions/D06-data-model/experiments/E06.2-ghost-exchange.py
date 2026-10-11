# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E06.2: what does the grouping of variables into arrays cost when ghost cells are exchanged?

The thesis problem carries six cell-centred variables: the five of hydrodynamics and a metallicity scalar. Ghost cells
are filled per block from the neighbouring blocks (D05), and every array that holds variables needs its own copies. This
experiment fills all ghost cells of 256 blocks of 64^2 cells (a periodic 16 x 16 arrangement, two ghost cells, 2D with
x contiguous: ``[block, var, j, i]``) with the variables grouped in four ways:

- one array for all six variables (one "pack" per process, D05.6): 8 NumPy copies per block (4 edges, 4 corners);
- one array per physics module (hydro with five variables, scalars with one): 16 copies per block;
- one array per variable: 48 copies per block;
- one array for all six variables, with every ghost cell of every block filled by a single NumPy call through
  precomputed flat index arrays.

All four give identical ghost cells (checked). The time is compared with that of one evaluation of the time derivative
for the same 256 blocks, taken from E06.1 (direction-specific kernel, 64^2 cells).

Run from this directory with:

    uv run --locked --script E06.2-ghost-exchange.py

Results are written to results/.
"""

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).parent / "results"
NB = 16  ## blocks per direction
B = 64  ## cells per block and direction
G = 2
NVAR = 6
REPEATS = 7


def copies() -> list[list[tuple]]:
    """Per block: (destination slices, source block, source slices) of its 8 ghost regions, periodic."""
    dst = {-1: slice(0, G), 0: slice(G, G + B), 1: slice(G + B, 2 * G + B)}
    src = {-1: slice(B, B + G), 0: slice(G, G + B), 1: slice(G, 2 * G)}
    table = []
    for k in range(NB * NB):
        bj, bi = divmod(k, NB)
        block = []
        for oj in (-1, 0, 1):
            for oi in (-1, 0, 1):
                if oi == oj == 0:
                    continue
                source = ((bj + oj) % NB) * NB + (bi + oi) % NB
                block.append(((dst[oj], dst[oi]), source, (src[oj], src[oi])))
        table.append(block)
    return table


def fill(packs: list[np.ndarray], table) -> None:
    """Fill the ghost cells of every block of every array, one NumPy copy per region and array."""
    for pack in packs:
        views = list(pack)
        for k, block in enumerate(table):
            target = views[k]
            for d, s, ss in block:
                target[(Ellipsis, *d)] = views[s][(Ellipsis, *ss)]


def flat_indices(table, shape) -> tuple[np.ndarray, np.ndarray]:
    """Flat destination and source indices of every ghost cell of every block and variable in one pack."""
    index = np.arange(np.prod(shape)).reshape(shape)
    dst, src = [], []
    for k, block in enumerate(table):
        for d, s, ss in block:
            dst.append(index[(k, slice(None), *d)].ravel())
            src.append(index[(s, slice(None), *ss)].ravel())
    return np.concatenate(dst), np.concatenate(src)


def best(function) -> float:
    function()
    times = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        function()
        times.append(time.perf_counter() - start)
    return min(times)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    table = copies()
    m = B + 2 * G
    rng = np.random.default_rng(1)
    interior = rng.random((NB * NB, NVAR, B, B))
    one = np.zeros((NB * NB, NVAR, m, m))
    one[:, :, G:-G, G:-G] = interior
    modules = [np.ascontiguousarray(one[:, :5]), np.ascontiguousarray(one[:, 5:])]
    variables = [np.ascontiguousarray(one[:, v]) for v in range(NVAR)]
    vectorised = one.copy()
    dst, src = flat_indices(table, one.shape)
    flat = vectorised.reshape(-1)

    def fill_vectorised():
        flat[dst] = flat[src]

    variants = {
        "one array for all variables, 8 copies per block": (lambda: fill([one], table)),
        "one array per module (hydro, scalars), 16 copies per block": (lambda: fill(modules, table)),
        "one array per variable, 48 copies per block": (lambda: fill(variables, table)),
        "one array for all variables, one vectorised call": fill_vectorised,
    }
    seconds = {name: best(function) for name, function in variants.items()}
    identical = (np.array_equal(np.concatenate(modules, axis=1), one)
                 and np.array_equal(np.stack(variables, axis=1), one) and np.array_equal(vectorised, one))

    kernel = NB * NB * B * B / 1.6e7  ## one time-derivative evaluation of all blocks at E06.1's 1.6e7 cells/s
    rows = {name: {"seconds": t, "microseconds_per_block": 1e6 * t / NB**2, "fraction_of_kernel": t / kernel}
            for name, t in seconds.items()}
    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "blocks": NB * NB,
               "block_cells": [B, B], "variables": NVAR, "identical": identical, "rows": rows}
    md = [
        "# E06.2: ghost exchange and the grouping of variables",
        "",
        f"{NB * NB} blocks of {B}² cells, {NVAR} variables, {G} ghost cells, periodic; natively, one thread; Python "
        f"{platform.python_version()}, NumPy {np.__version__}, {platform.platform()}. All variants give identical "
        f"ghost cells: {identical}. The last column relates the time to one evaluation of the time derivative of all "
        f"blocks ({1e3 * kernel:.0f} ms at 1.6 × 10⁷ cells per second, E06.1).",
        "",
        "| Grouping | Time (ms) | Per block (µs) | Relative to one kernel evaluation |",
        "|---|---|---|---|",
    ]
    md += [f"| {name} | {1e3 * r['seconds']:.2f} | {r['microseconds_per_block']:.1f} | "
           f"{100 * r['fraction_of_kernel']:.1f} % |" for name, r in rows.items()]
    (RESULTS / "E06.2-ghost-exchange.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E06.2-ghost-exchange.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
