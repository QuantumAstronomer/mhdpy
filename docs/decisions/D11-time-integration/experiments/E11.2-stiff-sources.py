# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E11.2: how should a stiff source term, such as radiative cooling, be coupled to the hydrodynamics?

In the thesis problem, dense gas cools much faster than the flow crosses a cell: the cooling time can be orders of
magnitude below the hydrodynamic time step. This experiment uses a model with the same structure and an exact solution:
advection with relaxation towards an equilibrium, where both the rate and the equilibrium vary in space (gas cooling
fast in some places and slowly in others, towards a temperature that depends on where it is),

    q_t + v q_x = -k(x) (q - q_eq(x)),   k(x) = k0 (1 + 0.9 sin 2 pi x),   q_eq(x) = 1 + 0.5 cos 2 pi x,

with v = 1, periodic on [0, 1]. The flow keeps carrying gas from one equilibrium to another, so the solution never
settles, and because k and q_eq vary in space, advection and source do not commute: splitting errors are real. The exact
solution follows from the ODE along each characteristic x0 + t, integrated with an exponential midpoint rule in steps
of 2 x 10^-6 (exact for constant coefficients, second order otherwise; its error is far below the schemes'). The
stiffness is set by k0 = 1 (mild), 10^2 and 10^4 (the source 10^2 to 10^4 times faster than advection across the
domain).

Advection uses PLM with the MC limiter and upwind fluxes, advanced by SSP-RK2 at CFL 0.4. The couplings compared:

- **unsplit, CFL step:** the source added to the time derivative inside the SSP-RK2 stages, with the hydrodynamic step;
- **unsplit, limited step:** the same, with the step also limited to 1 / k_max (so that k dt <= 1);
- **Lie splitting:** an advection step, then the source over the whole step, integrated exactly per cell;
- **Strang splitting, exact source:** half a step of source, an advection step, half a step of source;
- **Strang splitting, subcycled source:** as Strang, but the source half steps integrated by SSP-RK2 substeps of at most
  0.5 / k_max, as a cooling function without an exact integral would be;
- **IMEX:** the implicit-explicit Runge-Kutta scheme IMEX-SSP2(2,2,2) of Pareschi & Russo (2005): inside each of two
  stages, advection explicit and the source implicit, solved per cell (here in closed form, since the source is linear in
  q; a cooling function would need a local Newton iteration). It keeps the hydrodynamic step.

It measures the L1 error against the exact cell averages at t = 0.5 for N = 64 ... 1024, with the number of advection
evaluations and of source evaluations per cell.

Run from this directory with:

    uv run --locked --script E11.2-stiff-sources.py

Results are written to results/.
"""

import json
import math
import platform
import sys
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).parent / "results"
T_END = 0.5
CFL = 0.4
RESOLUTIONS = [64, 128, 256, 512, 1024]
STIFFNESS = [1.0, 1.0e2, 1.0e4]
SCHEMES = ["unsplit, CFL step", "unsplit, limited step", "Lie splitting", "Strang, exact source",
           "Strang, subcycled source", "IMEX"]
IMEX_GAMMA = 1.0 - 1.0 / math.sqrt(2.0)
## Gauss-Legendre nodes and weights on [-1/2, 1/2] for exact cell averages.
NODES = np.array([-0.4305681557970263, -0.1699905217924281, 0.1699905217924281, 0.4305681557970263])
WEIGHTS = np.array([0.1739274225687269, 0.3260725774312731, 0.3260725774312731, 0.1739274225687269])


def initial(x):
    return 1.0 + 0.5 * np.sin(2 * np.pi * x) + 0.3 * np.cos(4 * np.pi * x)


def rate(x, k0):
    return k0 * (1.0 + 0.9 * np.sin(2 * np.pi * x))


def equilibrium(x):
    return 1.0 + 0.5 * np.cos(2 * np.pi * x)


def exact(x, t, k0, h=2.0e-6):
    """Integrate dq/ds = -k(x0 + s) (q - q_eq(x0 + s)) along the characteristics ending at x at time t."""
    x0 = (x - t) % 1.0
    q = initial(x0)
    steps = math.ceil(t / h)
    h = t / steps
    for m in range(steps):
        xm = x0 + (m + 0.5) * h
        q = equilibrium(xm) + (q - equilibrium(xm)) * np.exp(-rate(xm, k0) * h)
    return q


REFERENCES: dict = {}


def exact_cell_averages(n: int, k0: float, h: float = 2.0e-6):
    """Exact cell averages at T_END (Gauss quadrature over all cells at once), cached per (n, k0, h)."""
    key = (n, k0, h)
    if key not in REFERENCES:
        dx = 1.0 / n
        points = (np.arange(n) + 0.5)[:, None] * dx + NODES[None, :] * dx
        values = exact(points.ravel(), T_END, k0, h).reshape(points.shape)
        REFERENCES[key] = values @ WEIGHTS
    return REFERENCES[key]


def cell_average(function, n):
    dx = 1.0 / n
    centres = (np.arange(n) + 0.5) * dx
    return sum(w * function(centres + node * dx) for node, w in zip(NODES, WEIGHTS, strict=True))


def mc_slope(left, right):
    limited = np.minimum(np.minimum(2.0 * np.abs(left), 2.0 * np.abs(right)), 0.5 * np.abs(left + right))
    return np.where(left * right > 0.0, np.sign(left) * limited, 0.0)


class Counter:
    advection = 0
    source = 0


def advection_rate(q, dx, count: Counter):
    """-v dq/dx with PLM (MC) upwind fluxes, v = 1, periodic."""
    count.advection += 1
    slope = mc_slope(q - np.roll(q, 1), np.roll(q, -1) - q)
    face = q + 0.5 * slope  ## upwind state at face i + 1/2
    return -(face - np.roll(face, 1)) / dx


QEQ = None  ## the cell equilibria of the current run, set in run()


def source_rate(q, k, count: Counter):
    count.source += 1
    return -k * (q - QEQ)


def exact_source(q, k, dt, count: Counter):
    count.source += 1
    return QEQ + (q - QEQ) * np.exp(-k * dt)


def subcycled_source(q, k, dt, count: Counter):
    substeps = max(1, math.ceil(dt * np.max(k) / 0.5))
    h = dt / substeps
    for _ in range(substeps):
        s = q + h * source_rate(q, k, count)
        q = 0.5 * q + 0.5 * (s + h * source_rate(s, k, count))
    return q


def advect(q, dt, dx, count):
    s = q + dt * advection_rate(q, dx, count)
    return 0.5 * q + 0.5 * (s + dt * advection_rate(s, dx, count))


def run(scheme: str, n: int, k0: float) -> dict:
    dx = 1.0 / n
    centres = (np.arange(n) + 0.5) * dx
    global QEQ
    k = rate(centres, k0)
    QEQ = equilibrium(centres)
    q = cell_average(initial, n)
    count = Counter()
    dt_cfl = CFL * dx
    dt = min(dt_cfl, 1.0 / np.max(k)) if scheme == "unsplit, limited step" else dt_cfl
    t = 0.0
    with np.errstate(all="ignore"):
        while t < T_END - 1e-14:
            h = min(dt, T_END - t)
            if scheme.startswith("unsplit"):
                s = q + h * (advection_rate(q, dx, count) + source_rate(q, k, count))
                q = 0.5 * q + 0.5 * (s + h * (advection_rate(s, dx, count) + source_rate(s, k, count)))
            elif scheme == "IMEX":
                g = IMEX_GAMMA
                ## Stage 1: Q1 = q + h g S(Q1); stage 2: Q2 = q + h A(Q1) + h ((1 - 2g) S(Q1) + g S(Q2)).
                q1 = (q + h * g * k * QEQ) / (1.0 + h * g * k)
                a1, s1 = advection_rate(q1, dx, count), source_rate(q1, k, count)
                rhs = q + h * a1 + h * (1.0 - 2.0 * g) * s1
                q2 = (rhs + h * g * k * QEQ) / (1.0 + h * g * k)
                a2, s2 = advection_rate(q2, dx, count), source_rate(q2, k, count)
                q = q + 0.5 * h * (a1 + a2) + 0.5 * h * (s1 + s2)
            elif scheme == "Lie splitting":
                q = exact_source(advect(q, h, dx, count), k, h, count)
            elif scheme == "Strang, exact source":
                q = exact_source(advect(exact_source(q, k, 0.5 * h, count), h, dx, count), k, 0.5 * h, count)
            else:
                q = subcycled_source(advect(subcycled_source(q, k, 0.5 * h, count), h, dx, count), k, 0.5 * h, count)
            t += h
            if not np.all(np.isfinite(q)) or np.max(np.abs(q)) > 1e6:
                return {"l1_error": None, "advection_evaluations": count.advection, "source_evaluations": count.source}
    reference = exact_cell_averages(n, k0)
    return {"l1_error": float(np.mean(np.abs(q - reference))), "advection_evaluations": count.advection,
            "source_evaluations": count.source}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "cases": {}}
    ## The reference's own error: the same exact solution with twice the step, at the finest grid and stiffest case.
    check = float(np.max(np.abs(exact_cell_averages(1024, STIFFNESS[-1]) - exact_cell_averages(1024, STIFFNESS[-1], 4.0e-6))))
    results["reference_step_doubling_difference"] = check
    for k0 in STIFFNESS:
        for scheme in SCHEMES:
            rows = {n: run(scheme, n, k0) for n in RESOLUTIONS}
            results["cases"][f"k0 = {k0:g} | {scheme}"] = rows
            print(k0, scheme, {n: r["l1_error"] for n, r in rows.items()}, flush=True)

    md = [
        "# E11.2: coupling a stiff source to advection",
        "",
        f"q_t + q_x = -k(x)(q - q_eq(x)), k = k0 (1 + 0.9 sin 2πx), q_eq = 1 + 0.5 cos 2πx, t = {T_END}; PLM (MC), SSP-RK2, CFL {CFL}. Python "
        f"{platform.python_version()}, NumPy {np.__version__}. L1 error against the exact cell averages (— = the run "
        "blew up); order between the two finest grids; evaluations per cell at N = 1024 (advection / source). The "
        f"reference changes by at most {results['reference_step_doubling_difference']:.1e} when its step is doubled "
        "(N = 1024, k0 = 10⁴).",
        "",
        "| k0 | Coupling | " + " | ".join(f"N = {n}" for n in RESOLUTIONS) + " | Order | Evaluations at N = 1024 |",
        "|" + "---|" * (len(RESOLUTIONS) + 4),
    ]
    for key, rows in results["cases"].items():
        k0, scheme = key.split(" | ")
        errors = [rows[n]["l1_error"] for n in RESOLUTIONS]
        order = (f"{math.log2(errors[-2] / errors[-1]):.2f}"
                 if errors[-1] and errors[-2] and errors[-1] > 0 else "—")
        last = rows[RESOLUTIONS[-1]]
        md.append(f"| {k0.split('= ')[1]} | {scheme} | " + " | ".join("—" if e is None else f"{e:.1e}" for e in errors)
                  + f" | {order} | {last['advection_evaluations']} / {last['source_evaluations']} |")
    (RESULTS / "E11.2-stiff-sources.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E11.2-stiff-sources.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
