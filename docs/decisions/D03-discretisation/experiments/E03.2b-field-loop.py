# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E03.2: divergence control for MHD on the field-loop advection test.

Runs the field-loop test of Gardiner & Stone (2005), as set up by Athena++ (``inputs/mhd/athinput.field_loop``: domain
[-1, 1] x [-0.5, 0.5], 128 x 64 cells, v = (2, 1), CFL 0.4, until t = 2, when the loop is back at its starting point), with
the four divergence treatments of ``E03.2a-mhd2d.py``: none, GLM cleaning, and constrained transport with averaged or with
upwinded (Gardiner & Stone) edge EMFs. Everything else (reconstruction, Riemann solver, integrator) is identical.

Measured over time: magnetic energy relative to its initial value, and the largest discrete divergence of B, scaled by
the cell size and the largest field strength (so 1 means a divergence as large as the field's own gradients). At the end:
the L1 error of the in-plane field against the exact solution, which equals the initial field. Maps of the magnetic
pressure at the start and at the end are stored for the figure.

Run from this directory with:

    uv run --locked --script E03.2b-field-loop.py

Results are written to results/; the figure is drawn from them by E03.2c-figure.py.
"""

import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RESULTS = HERE / "results"
_spec = importlib.util.spec_from_file_location("mhd2d", HERE / "E03.2a-mhd2d.py")
assert _spec is not None and _spec.loader is not None
mhd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mhd)

NX, NY, T_END, CFL, GAMMA = 128, 64, 2.0, 0.4, 5.0 / 3.0
OUTPUT_EVERY = 0.05


def magnetic_energy(state) -> float:
    return float(0.5 * np.sum(state.cons[mhd.BX] ** 2 + state.cons[mhd.BY] ** 2))


def scaled_divergence(state, dx, dy, b_max) -> float:
    return float(np.max(np.abs(mhd.divergence(state, dx, dy))) * dx / b_max)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results, maps = {}, {}
    for scheme in mhd.SCHEMES:
        state, dx, dy = mhd.field_loop(NX, NY, scheme, GAMMA)
        initial_field = state.cons[[mhd.BX, mhd.BY]].copy()
        b_max = float(np.max(np.hypot(*initial_field)))
        energy0 = magnetic_energy(state)
        maps["initial"] = 0.5 * np.sum(initial_field**2, axis=0)
        times, energies, divergences = [0.0], [1.0], [scaled_divergence(state, dx, dy, b_max)]
        t, steps, next_output = 0.0, 0, OUTPUT_EVERY
        start = time.perf_counter()
        while t < T_END:
            dt = min(mhd.time_step(state.cons, dx, dy, GAMMA, CFL), T_END - t, next_output - t)
            state = mhd.advance(state, scheme, dt, dx, dy, GAMMA, CFL)
            t += dt
            steps += 1
            if t >= next_output - 1e-12:
                times.append(t)
                energies.append(magnetic_energy(state) / energy0)
                divergences.append(scaled_divergence(state, dx, dy, b_max))
                next_output += OUTPUT_EVERY
        seconds = time.perf_counter() - start
        final_field = state.cons[[mhd.BX, mhd.BY]]
        maps[scheme] = 0.5 * np.sum(final_field**2, axis=0)
        results[scheme] = {
            "times": times,
            "energy": energies,
            "divergence": divergences,
            "l1_field_error": float(np.mean(np.abs(final_field - initial_field)) / b_max),
            "steps": steps,
            "seconds": seconds,
        }
        print(f"done: {scheme} ({seconds:.1f} s)")

    names = {
        "none": "none",
        "glm": "GLM cleaning",
        "ct-average": "CT, averaged EMFs",
        "ct-contact": "CT, upwinded EMFs (Gardiner & Stone)",
    }
    md = [
        "# E03.2: divergence control on the field-loop advection test",
        "",
        f"numpy {np.__version__}, Python {platform.python_version()}, {platform.platform()}. {NX} x {NY} cells, "
        f"t = {T_END}, CFL {CFL}, gamma = 5/3; PLM (MC) on primitives, HLL, SSP-RK2 for every scheme.",
        "",
        "| Divergence treatment | Magnetic energy at t = 2 | Scaled div B at t = 0 | Scaled div B at t = 2 "
        "| L1 field error at t = 2 | Steps | Seconds |",
        "|---|---|---|---|---|---|---|",
    ]
    for scheme, res in results.items():
        md.append(
            f"| {names[scheme]} | {res['energy'][-1]:.3f} | {res['divergence'][0]:.1e} | {res['divergence'][-1]:.1e} | "
            f"{res['l1_field_error']:.2e} | {res['steps']} | {res['seconds']:.1f} |"
        )
    md += ["", "Magnetic energy is relative to its initial value; the exact solution keeps it at 1. The divergence is "
           "each scheme's own discrete divergence (face-centred for CT, central differences of the cell-centred field "
           "otherwise), scaled by the cell size and the largest initial field strength. The cell-centred schemes start "
           "from a non-zero value because their divergence operator differs from the face-centred one the initial "
           "field was constructed with.",
           "", "![E03.2](E03.2c-field-loop.png)", ""]

    (RESULTS / "E03.2b-field-loop.json").write_text(json.dumps(results, indent=1) + "\n")
    np.savez_compressed(RESULTS / "E03.2b-maps.npz", **{k: v.astype(np.float32) for k, v in maps.items()})
    (RESULTS / "E03.2b-field-loop.md").write_text("\n".join(md))
    (RESULTS / "E03.2b-metadata.json").write_text(
        json.dumps({"python": sys.version, "numpy": np.__version__, "platform": platform.platform()}, indent=2) + "\n"
    )
    print("\n".join(md))


if __name__ == "__main__":
    main()
