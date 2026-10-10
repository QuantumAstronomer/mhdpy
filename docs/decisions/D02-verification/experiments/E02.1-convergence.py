# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E02.1: how convergence tests behave, and what they cost.

Uses the solver in ``E02.1-hydro1d.py`` to answer the questions behind brief D02's sub-decisions on reference
solutions, convergence criteria and test tiers:

1. Linear sound wave (smooth, exact solution known): L1 and L-infinity errors and measured order of convergence for
   first-order reconstruction and for second-order reconstruction without limiter, with minmod and with MC.
2. Self-convergence of the same problem, measured without using the exact solution (book section 13.5), compared with
   the convergence against the exact solution.
3. Sod shock tube: L1 error against the exact Riemann solution, computed by ``exact_riemann`` rather than stored.
4. Mirror symmetry: the mirrored Sod problem must give the mirrored solution (book section 8.9).
5. Cost: wall time and cell updates per second of every run, extrapolated to convergence series in 2D and 3D.

Run from this directory with:

    uv run --locked --script E02.1-convergence.py

Results are written to results/. The figure is drawn from the results by E02.1-figure.py.
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

## Load the solver module by path: its file name is not a valid module name.
_spec = importlib.util.spec_from_file_location("hydro1d", HERE / "E02.1-hydro1d.py")
assert _spec is not None and _spec.loader is not None
hydro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hydro)

GAMMA = 1.4
WAVE_RESOLUTIONS = [16, 32, 64, 128, 256, 512, 1024]
SOD_RESOLUTIONS = [64, 128, 256, 512, 1024]
SOD_TIME = 0.2


def timed_evolve(cons, n, t_end, limiter, boundary):
    start = time.perf_counter()
    final, steps = hydro.evolve(cons, 1.0 / n, t_end, limiter=limiter, boundary=boundary, gamma=GAMMA)
    elapsed = time.perf_counter() - start
    return final, steps, elapsed


def orders(errors):
    return [float(np.log2(errors[i] / errors[i + 1])) for i in range(len(errors) - 1)]


def coarsen(field):
    """Average pairs of neighbouring cells: the coarsening operator of a factor-two self-convergence test."""
    return 0.5 * (field[0::2] + field[1::2])


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    runs = []  ## every run, for the cost analysis
    md = [
        "# E02.1: convergence tests on a minimal 1D solver",
        "",
        f"numpy {np.__version__}, Python {platform.python_version()}, {platform.platform()}, "
        f"{platform.processor() or platform.machine()}. Solver: piecewise-linear reconstruction of primitive "
        "variables, HLL, SSP-RK2, CFL 0.4, gamma 1.4.",
        "",
    ]

    ## 1 and 2: linear sound wave, against the exact solution and self-convergence.
    wave = {}
    density = {}
    for limiter in hydro.LIMITERS:
        l1, linf = [], []
        for n in WAVE_RESOLUTIONS:
            initial = hydro.sound_wave(n, gamma=GAMMA)
            final, steps, elapsed = timed_evolve(initial, n, 1.0, limiter, "periodic")
            error = final[0] - initial[0]
            l1.append(float(np.mean(np.abs(error))))
            linf.append(float(np.max(np.abs(error))))
            density[(limiter, n)] = final[0]
            runs.append({"problem": "sound wave", "limiter": limiter, "n": n, "steps": steps, "seconds": elapsed})
        wave[limiter] = {"l1": l1, "linf": linf}

    md += [
        "## 1. Linear sound wave (amplitude 1e-6, one period)",
        "",
        "L1 error of the density against the exact solution, and the measured order between successive resolutions.",
        "",
        "| Reconstruction | " + " | ".join(f"N={n}" for n in WAVE_RESOLUTIONS) + " | Orders (L1) | Orders (L∞) |",
        "|" + "---|" * (len(WAVE_RESOLUTIONS) + 3),
    ]
    for limiter, data in wave.items():
        md.append(
            f"| {limiter} | "
            + " | ".join(f"{e:.2e}" for e in data["l1"])
            + " | "
            + ", ".join(f"{o:.2f}" for o in orders(data["l1"]))
            + " | "
            + ", ".join(f"{o:.2f}" for o in orders(data["linf"]))
            + " |"
        )

    self_errors = {}
    for limiter in hydro.LIMITERS:
        self_errors[limiter] = [
            float(np.mean(np.abs(density[(limiter, n)] - coarsen(density[(limiter, 2 * n)]))))
            for n in WAVE_RESOLUTIONS[:-1]
        ]
    md += [
        "",
        "## 2. Self-convergence of the same problem",
        "",
        "Difference between the run at N and the run at 2N coarsened to N, without using the exact solution. Orders "
        "from successive differences, compared with the orders against the exact solution above.",
        "",
        "| Reconstruction | Self-convergence orders | Orders against exact solution |",
        "|---|---|---|",
    ]
    for limiter in hydro.LIMITERS:
        md.append(
            f"| {limiter} | "
            + ", ".join(f"{o:.2f}" for o in orders(self_errors[limiter]))
            + " | "
            + ", ".join(f"{o:.2f}" for o in orders(wave[limiter]["l1"])[1:])
            + " |"
        )

    ## 3: Sod shock tube against the exact Riemann solution.
    sod = {}
    for limiter in ("constant", "minmod", "mc"):
        l1 = []
        for n in SOD_RESOLUTIONS:
            initial = hydro.shock_tube(n, hydro.SOD_LEFT, hydro.SOD_RIGHT, gamma=GAMMA)
            final, steps, elapsed = timed_evolve(initial, n, SOD_TIME, limiter, "outflow")
            xi = (hydro.cell_centres(n) - 0.5) / SOD_TIME
            exact = hydro.exact_riemann(hydro.SOD_LEFT, hydro.SOD_RIGHT, xi, gamma=GAMMA)
            l1.append(float(np.mean(np.abs(final[0] - exact[0]))))
            runs.append({"problem": "Sod", "limiter": limiter, "n": n, "steps": steps, "seconds": elapsed})
        sod[limiter] = l1
    md += [
        "",
        f"## 3. Sod shock tube (t = {SOD_TIME})",
        "",
        "L1 error of the density against the exact Riemann solution, evaluated at cell centres.",
        "",
        "| Reconstruction | " + " | ".join(f"N={n}" for n in SOD_RESOLUTIONS) + " | Orders |",
        "|" + "---|" * (len(SOD_RESOLUTIONS) + 2),
    ]
    for limiter, l1 in sod.items():
        md.append(
            f"| {limiter} | "
            + " | ".join(f"{e:.2e}" for e in l1)
            + " | "
            + ", ".join(f"{o:.2f}" for o in orders(l1))
            + " |"
        )

    ## Athena++-style acceptance ratios for comparison: error ratio per doubling of resolution.
    md += [
        "",
        "Error ratio per doubling, as Athena++'s regression tests check it (thresholds there: linear wave <= 0.33 "
        "at 32 -> 64, Sod <= 0.6 at 128 -> 256):",
        "",
        f"- linear wave, MC, 32 -> 64: {wave['mc']['l1'][2] / wave['mc']['l1'][1]:.3f}",
        f"- Sod, MC, 128 -> 256: {sod['mc'][2] / sod['mc'][1]:.3f}",
    ]

    ## 4: mirror symmetry.
    n = 256
    mirrored_left = (hydro.SOD_RIGHT[0], -hydro.SOD_RIGHT[1], hydro.SOD_RIGHT[2])
    mirrored_right = (hydro.SOD_LEFT[0], -hydro.SOD_LEFT[1], hydro.SOD_LEFT[2])
    md += [
        "",
        "## 4. Mirror symmetry (Sod, N = 256)",
        "",
        "The mirrored problem (left and right states swapped, velocity negated) is run, and its density and momentum "
        "are mirrored back and compared with the original run.",
        "",
        "| Reconstruction | Density identical (bitwise) | Momentum identical (bitwise, sign flipped) | Max difference |",
        "|---|---|---|---|",
    ]
    for limiter in ("constant", "minmod", "mc"):
        original, _ = hydro.evolve(
            hydro.shock_tube(n, hydro.SOD_LEFT, hydro.SOD_RIGHT, GAMMA), 1.0 / n, SOD_TIME,
            limiter=limiter, boundary="outflow", gamma=GAMMA,
        )
        mirrored, _ = hydro.evolve(
            hydro.shock_tube(n, mirrored_left, mirrored_right, GAMMA), 1.0 / n, SOD_TIME,
            limiter=limiter, boundary="outflow", gamma=GAMMA,
        )
        same_rho = bool(np.array_equal(original[0], mirrored[0][::-1]))
        same_mom = bool(np.array_equal(original[1], -mirrored[1][::-1]))
        diff = float(max(np.max(np.abs(original[0] - mirrored[0][::-1])), np.max(np.abs(original[1] + mirrored[1][::-1]))))
        md.append(f"| {limiter} | {same_rho} | {same_mom} | {diff:.1e} |")

    ## 5: cost.
    for run in runs:
        run["cell_updates_per_s"] = run["n"] * run["steps"] / run["seconds"]
    large = [r for r in runs if r["n"] >= 512]
    rate = float(np.median([r["cell_updates_per_s"] for r in large]))
    md += [
        "",
        "## 5. Cost",
        "",
        f"Median throughput at N >= 512: **{rate:.2e} cell updates per second** (one core, NumPy, two stages per "
        "step). Wall time of the largest runs:",
        "",
        "| Problem | Reconstruction | N | Steps | Seconds |",
        "|---|---|---|---|---|",
    ]
    for r in runs:
        if r["n"] == 1024:
            md.append(f"| {r['problem']} | {r['limiter']} | {r['n']} | {r['steps']} | {r['seconds']:.2f} |")

    ## Extrapolation: a convergence series N = 16 ... N_max in d dimensions, run to a crossing time, at the measured
    ## rate. Steps scale as N / CFL, cells as N^d, so a series is dominated by its finest run.
    md += [
        "",
        "Extrapolated wall time of one convergence series (N = 16 ... N_max, one wave crossing time, CFL 0.4) at "
        "this rate, assuming the cost per cell update stays the same in more dimensions (in practice it grows with "
        "the number of directions):",
        "",
        "| N_max | 1D | 2D | 3D |",
        "|---|---|---|---|",
    ]
    for n_max in (64, 128, 256, 512):
        series = [2**k for k in range(4, int(np.log2(n_max)) + 1)]
        row = []
        for dim in (1, 2, 3):
            updates = sum(n**dim * (n / 0.4) for n in series)
            seconds = updates / rate
            row.append(f"{seconds:.1f} s" if seconds < 120 else f"{seconds / 60:.0f} min")
        md.append(f"| {n_max} | " + " | ".join(row) + " |")

    ## The measured errors are written to JSON; the figure is drawn from that file by E02.1-figure.py, so that its style
    ## can be changed without rerunning (and re-timing) the experiment.
    (RESULTS / "E02.1-errors.json").write_text(
        json.dumps(
            {
                "wave_resolutions": WAVE_RESOLUTIONS,
                "sod_resolutions": SOD_RESOLUTIONS,
                "sod_time": SOD_TIME,
                "wave": wave,
                "self_convergence": self_errors,
                "sod": sod,
            },
            indent=2,
        )
        + "\n"
    )

    md += ["", "![Convergence](E02.1-convergence.png)", ""]
    (RESULTS / "E02.1-convergence.md").write_text("\n".join(md) + "\n")
    (RESULTS / "E02.1-runs.json").write_text(json.dumps(runs, indent=2) + "\n")
    (RESULTS / "E02.1-metadata.json").write_text(
        json.dumps(
            {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()}, indent=2
        )
        + "\n"
    )
    print("\n".join(md))


if __name__ == "__main__":
    main()
