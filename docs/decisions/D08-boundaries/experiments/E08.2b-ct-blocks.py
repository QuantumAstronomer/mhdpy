# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E08.2: constrained transport on blocks. Do shared faces agree, and which ghost width is needed?

With constrained transport (D03.5), the face-centred magnetic field on a face shared by two blocks is stored by both,
and each block updates its copy from edge EMFs it computes itself from its own ghost cells. Athena++ averages such
shared values, because round-off and nondeterministic message ordering can let them drift apart (S20). D05.5 requires
the arithmetic not to depend on block boundaries instead, which would make the two copies identical by construction.

This experiment runs the field-loop test of D03 (Gardiner & Stone 2005, Athena++ set-up; ``ct-contact`` scheme, the
upwinded EMFs of Athena++) with the unchanged D03 solver ``E08.2a-mhd2d.py`` on a periodic 128 x 64 grid:

- as one grid, the reference;
- divided into blocks of 32^2, 16^2 and 8^2 cells, each with g ghost cells (g = 1, 2, 3) filled from the neighbouring
  blocks' own cells and faces before every stage. Every block updates the cells it owns and *both* x-faces (and both
  y-faces) of its cells, so that a face shared by two blocks is computed twice, independently.

The D03 solver wraps its stencils around the array (``np.roll``); applied to a block with ghost cells, the wrapped
values land only in the outer ghost layers, which the stencil must not reach for the owned cells to be correct. That
is exactly the question of how many ghost cells the scheme needs.

After every stage it compares the two copies of every shared face; after 64 steps it compares the assembled state
(cells and faces) with the reference bit for bit, and reports the largest face-centred divergence of B.

Run from this directory with:

    uv run --locked --script E08.2b-ct-blocks.py

Results are written to results/.
"""

import importlib.util
import json
import platform
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RESULTS = HERE / "results"
NX, NY = 128, 64
STEPS = 64
SCHEME = "ct-contact"
GAMMA = 5.0 / 3.0
CFL = 0.4
BLOCKS = [32, 16, 8]
GHOSTS = [1, 2, 3]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mhd = load("mhd2d", HERE / "E08.2a-mhd2d.py")


class Blocks:
    """Square blocks of b cells tiling the periodic NX x NY grid, each with g ghost cells; arrays are [var, i, j]."""

    def __init__(self, b: int, g: int) -> None:
        self.b, self.g, self.m = b, g, b + 2 * g
        self.origins = [(ox, oy) for ox in range(0, NX, b) for oy in range(0, NY, b)]

    def window(self, ox: int, oy: int) -> tuple[np.ndarray, np.ndarray]:
        """Global indices of a block's local cells, ghost cells included, wrapped periodically."""
        return np.ix_((ox - self.g + np.arange(self.m)) % NX, (oy - self.g + np.arange(self.m)) % NY)

    def scatter(self, cons: np.ndarray, bx: np.ndarray, by: np.ndarray) -> list[list[np.ndarray]]:
        """Fill every block, ghost cells and faces included, from global arrays of owned values."""
        blocks = []
        for ox, oy in self.origins:
            ii, jj = self.window(ox, oy)
            blocks.append([cons[:, ii, jj].copy(), bx[ii, jj].copy(), by[ii, jj].copy()])
        return blocks

    def gather(self, blocks) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Assemble global arrays from the cells and faces each block owns (its cells, and their lower faces)."""
        g, b = self.g, self.b
        cons, bx, by = np.empty((8, NX, NY)), np.empty((NX, NY)), np.empty((NX, NY))
        for (ox, oy), (c, fx, fy) in zip(self.origins, blocks, strict=True):
            own = (slice(g, g + b), slice(g, g + b))
            cons[:, ox : ox + b, oy : oy + b] = c[(slice(None), *own)]
            bx[ox : ox + b, oy : oy + b] = fx[own]
            by[ox : ox + b, oy : oy + b] = fy[own]
        return cons, bx, by

    def neighbour(self, n: int, dx: int, dy: int) -> int:
        ox, oy = self.origins[n]
        return self.origins.index(((ox + dx * self.b) % NX, (oy + dy * self.b) % NY))


def stage_update(blocks: "Blocks", current, base, weights, dt, dx, dy, ch, mismatches):
    """One SSP-RK2 stage on every block: new = w0 * base + w1 * (current + dt * rate), on owned cells and on both faces
    of every owned cell; then compare the two copies of each shared face and set the cell-centred field from the faces."""
    g, b = blocks.g, blocks.b
    w0, w1 = weights
    result = []
    for (c, fx, fy), (c0, fx0, fy0) in zip(current, base, strict=True):
        dc, dbx, dby = mhd.rates(mhd.State(c, fx, fy), SCHEME, ch, dt, dx, dy, GAMMA)
        nc, nfx, nfy = c.copy(), fx.copy(), fy.copy()
        cells = (slice(g, g + b), slice(g, g + b))
        xfaces = (slice(g, g + b + 1), slice(g, g + b))
        yfaces = (slice(g, g + b), slice(g, g + b + 1))
        if w0 == 0.0:
            nc[(slice(None), *cells)] = c[(slice(None), *cells)] + dt * dc[(slice(None), *cells)]
            nfx[xfaces] = fx[xfaces] + dt * dbx[xfaces]
            nfy[yfaces] = fy[yfaces] + dt * dby[yfaces]
        else:
            nc[(slice(None), *cells)] = w0 * c0[(slice(None), *cells)] + w1 * (
                c[(slice(None), *cells)] + dt * dc[(slice(None), *cells)])
            nfx[xfaces] = w0 * fx0[xfaces] + w1 * (fx[xfaces] + dt * dbx[xfaces])
            nfy[yfaces] = w0 * fy0[yfaces] + w1 * (fy[yfaces] + dt * dby[yfaces])
        ## The cell-centred in-plane field is the average of the two faces of each owned cell (State.sync_cell_field).
        nc[mhd.BX][cells] = 0.5 * (nfx[g : g + b, g : g + b] + nfx[g + 1 : g + b + 1, g : g + b])
        nc[mhd.BY][cells] = 0.5 * (nfy[g : g + b, g : g + b] + nfy[g : g + b, g + 1 : g + b + 1])
        result.append([nc, nfx, nfy])
    for n, (_, fx, fy) in enumerate(result):
        right, up = result[blocks.neighbour(n, 1, 0)], result[blocks.neighbour(n, 0, 1)]
        mismatches["x-faces"] += int(np.count_nonzero(fx[g + b, g : g + b] != right[1][g, g : g + b]))
        mismatches["y-faces"] += int(np.count_nonzero(fy[g : g + b, g + b] != up[2][g : g + b, g]))
        mismatches["compared"] += 2 * b
    return result


def run_blocks(state0, b: int, g: int, dt: float, dx: float, dy: float):
    blocks = Blocks(b, g)
    ch = CFL * min(dx, dy) / dt
    mismatches = {"x-faces": 0, "y-faces": 0, "compared": 0}
    current = blocks.scatter(state0.cons, state0.bx, state0.by)
    for _ in range(STEPS):
        stage = stage_update(blocks, current, current, (0.0, 1.0), dt, dx, dy, ch, mismatches)
        stage = blocks.scatter(*blocks.gather(stage))
        new = stage_update(blocks, stage, current, (0.5, 0.5), dt, dx, dy, ch, mismatches)
        current = blocks.scatter(*blocks.gather(new))
    return blocks.gather(current), mismatches


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    state0, dx, dy = mhd.field_loop(NX, NY, SCHEME, GAMMA)
    dt = mhd.time_step(state0.cons, dx, dy, GAMMA, CFL)
    reference = state0
    for _ in range(STEPS):
        reference = mhd.advance(reference, SCHEME, dt, dx, dy, GAMMA, CFL)
    rows = {}
    for b in BLOCKS:
        for g in GHOSTS:
            (cons, bx, by), mismatches = run_blocks(state0, b, g, dt, dx, dy)
            div = mhd.divergence(mhd.State(cons, bx, by), dx, dy)
            rows[f"{b}² blocks, {g} ghost cells"] = {
                "blocks": (NX // b) * (NY // b),
                "cells_identical": bool(np.array_equal(cons, reference.cons)),
                "faces_identical": bool(np.array_equal(bx, reference.bx) and np.array_equal(by, reference.by)),
                "max_relative_difference": float(np.max(np.abs(cons - reference.cons)) / np.max(np.abs(reference.cons))),
                "shared_face_mismatches": mismatches,
                "max_div_b": float(np.max(np.abs(div))),
            }
            print(b, g, rows[f"{b}² blocks, {g} ghost cells"], flush=True)
    reference_div = float(np.max(np.abs(mhd.divergence(reference, dx, dy))))
    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "grid": [NX, NY],
               "steps": STEPS, "scheme": SCHEME, "reference_max_div_b": reference_div, "rows": rows}
    md = [
        "# E08.2: constrained transport on blocks",
        "",
        f"Field loop ({SCHEME}), {NX} × {NY} cells, {STEPS} SSP-RK2 steps; Python {platform.python_version()}, NumPy "
        f"{np.__version__}. Shared faces: copies of a face computed independently by both neighbouring blocks that "
        f"differ, out of all compared (after every stage). Reference (one grid) max |div B| = {reference_div:.1e}.",
        "",
        "| Blocks | Ghost cells | Cells bit for bit | Faces bit for bit | Max. rel. difference | Shared faces differing "
        "| Max. abs. div B |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, row in rows.items():
        m = row["shared_face_mismatches"]
        blocks, ghosts = name.split(", ")
        md.append(f"| {row['blocks']} × {blocks.split()[0]} | {ghosts.split()[0]} | "
                  f"{'yes' if row['cells_identical'] else 'no'} | {'yes' if row['faces_identical'] else 'no'} | "
                  f"{row['max_relative_difference']:.1e} | {m['x-faces'] + m['y-faces']} of {m['compared']} | "
                  f"{row['max_div_b']:.1e} |")
    (RESULTS / "E08.2b-ct-blocks.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E08.2b-ct-blocks.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
