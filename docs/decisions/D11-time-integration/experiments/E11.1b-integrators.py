# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E11.1: which time integrator for the hyperbolic part?

The method of lines (D03) leaves the integrator open. This experiment compares the candidates that Athena++ offers for
second-order schemes, on the minimal 1D solver of D02 (``E11.1a-hydro1d.py``: PLM with the MC limiter on primitive
variables, HLL fluxes):

- **SSP-RK2** (Shu & Osher): two full evaluations of the time derivative per step;
- **SSP-RK3** (Shu & Osher): three evaluations per step;
- **VL2** (the van Leer predictor-corrector of Stone & Gardiner 2009, Athena++'s default): a half step with first-order
  (donor-cell) fluxes, then a full step with PLM fluxes evaluated at the half-step state.

For each it measures:

1. the L1 error of a linear sound wave after one period (amplitude 10^-6, N = 32 ... 512, CFL 0.4) and its order;
2. the largest stable CFL number in 1D: the linear wave (N = 64, four periods, so that an instability has time to grow)
   and the Sod shock tube (N = 200) are run at CFL numbers from 0.1 to 1.5. A run counts as stable if it stays finite,
   keeps the pressure positive, its linear-wave error stays below 50 times that at CFL 0.1 (the time error grows only
   as a power of the CFL number, an instability exponentially), and the total variation of the Sod density stays within
   5 % of the exact solution's (HLL with PLM overshoots by about 2 % at every CFL number);
3. the largest stable CFL number in 2D, where unsplit schemes are more restricted: the smooth periodic flow of D04
   (``E11.1c-hydro2d.py``, the 2D NumPy solver of E04.1, 64^2 cells) is run to t = 0.5 at CFL numbers from 0.1 to 1.5,
   with the time step set by the fastest signal over both directions; a run counts as stable if it stays finite and its
   mean density difference from a reference run (SSP-RK3 at CFL 0.05) stays below 0.01, 5 % of the flow's density
   variation (unstable runs blow up to infinity; stable ones stay below 10^-3). VL2's first-order half step
   is obtained by setting the module's slopes to zero for that evaluation;
4. the cost per unit of simulated time at the largest stable CFL in 2D: evaluations of the time derivative per step
   divided by that CFL number (VL2's first evaluation is first order and cheaper; it is counted as a full one);
5. the L1 density error of the Sod problem (N = 256) at CFL 0.4 and at each integrator's largest stable CFL.

Run from this directory with:

    uv run --locked --script E11.1b-integrators.py

Results are written to results/.
"""

import importlib.util
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RESULTS = HERE / "results"
GAMMA = 1.4
INTEGRATORS = {"SSP-RK2": 2, "SSP-RK3": 3, "VL2": 2}
CFLS = [round(0.1 + 0.05 * k, 2) for k in range(29)]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


h = load("hydro1d", HERE / "E11.1a-hydro1d.py")
h2 = load("hydro2d", HERE / "E11.1c-hydro2d.py")


def step(name: str, u: np.ndarray, dt: float, dx: float, boundary: str) -> np.ndarray:
    def rhs(state, limiter="mc"):
        return h.time_derivative(state, dx, limiter, boundary, GAMMA)

    if name == "SSP-RK2":
        s = u + dt * rhs(u)
        return 0.5 * u + 0.5 * (s + dt * rhs(s))
    if name == "SSP-RK3":
        s1 = u + dt * rhs(u)
        s2 = 0.75 * u + 0.25 * (s1 + dt * rhs(s1))
        return u / 3.0 + 2.0 / 3.0 * (s2 + dt * rhs(s2))
    half = u + 0.5 * dt * rhs(u, "constant")
    return u + dt * rhs(half)


def evolve(name: str, u: np.ndarray, dx: float, t_end: float, cfl: float, boundary: str):
    t, steps = 0.0, 0
    with np.errstate(all="ignore"):
        while t < t_end:
            speed = h.max_signal_speed(u, GAMMA)
            if not np.isfinite(speed):
                return None, steps
            dt = min(cfl * dx / speed, t_end - t)
            u = step(name, u, dt, dx, boundary)
            t += dt
            steps += 1
            if not np.all(np.isfinite(u)) or np.any(h.cons_to_prim(u, GAMMA)[2] <= 0.0) or steps > 200_000:
                return None, steps
    return u, steps


def wave_error(name: str, n: int, cfl: float, periods: float = 1.0) -> float | None:
    u0 = h.sound_wave(n, 1.0e-6, GAMMA)
    u, _ = evolve(name, u0, 1.0 / n, periods, cfl, "periodic")
    return None if u is None else float(np.mean(np.abs(u[0] - u0[0])))


def sod(name: str, n: int, cfl: float):
    u0 = h.shock_tube(n, h.SOD_LEFT, h.SOD_RIGHT, GAMMA)
    u, _ = evolve(name, u0, 1.0 / n, 0.2, cfl, "outflow")
    if u is None:
        return None
    exact = h.exact_riemann(h.SOD_LEFT, h.SOD_RIGHT, (h.cell_centres(n) - 0.5) / 0.2, GAMMA)
    error = float(np.mean(np.abs(u[0] - exact[0])))
    tv, tv_exact = float(np.sum(np.abs(np.diff(u[0])))), float(np.sum(np.abs(np.diff(exact[0]))))
    return {"l1_error": error, "total_variation_ratio": tv / tv_exact}


def step2d(name: str, u: np.ndarray, dt: float, dx: float) -> np.ndarray:
    """One step of the 2D solver; VL2's half step uses zero slopes (donor cell)."""
    g = h2.N_GHOST
    inner = (slice(None), slice(g, -g), slice(g, -g))

    def advance(base, state, factor, first_order=False):
        if first_order:
            saved, h2.mc_slope = h2.mc_slope, lambda left, right: np.zeros_like(left)
        try:
            new = base.copy()
            new[inner] = base[inner] + factor * dt * h2.rhs(state, dx)
        finally:
            if first_order:
                h2.mc_slope = saved
        h2.fill_ghosts(new)
        return new

    if name == "SSP-RK2":
        return h2.ssp_rk2_step(u, dt, dx, h2.rhs)
    if name == "SSP-RK3":
        s1 = advance(u, u, 1.0)
        s2 = u.copy()
        s2[inner] = 0.75 * u[inner] + 0.25 * (s1[inner] + dt * h2.rhs(s1, dx))
        h2.fill_ghosts(s2)
        new = u.copy()
        new[inner] = u[inner] / 3.0 + 2.0 / 3.0 * (s2[inner] + dt * h2.rhs(s2, dx))
        h2.fill_ghosts(new)
        return new
    half = advance(u, u, 0.5, first_order=True)
    return advance(u, half, 1.0)


def evolve2d(name: str, n: int, cfl: float, t_end: float = 0.5):
    u, dx, t = h2.initial_state(n), 1.0 / n, 0.0
    with np.errstate(all="ignore"):
        while t < t_end:
            w = h2.cons_to_prim(u)
            c = np.sqrt(h2.GAMMA * w[3] / w[0])
            speed = float(np.max(np.maximum(np.abs(w[1]) + c, np.abs(w[2]) + c)))
            if not np.isfinite(speed):
                return None
            dt = min(cfl * dx / speed, t_end - t)
            u = step2d(name, u, dt, dx)
            t += dt
            if not np.all(np.isfinite(u)):
                return None
    return u


def largest_stable_2d(name: str, n: int = 64) -> float:
    reference = evolve2d("SSP-RK3", n, 0.05)
    g = h2.N_GHOST

    def error(u):
        return float(np.mean(np.abs(u[0, g:-g, g:-g] - reference[0, g:-g, g:-g])))

    largest = 0.0
    for cfl in CFLS:
        u = evolve2d(name, n, cfl)
        if u is None or error(u) > 1.0e-2:
            break
        largest = cfl
    return largest


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "integrators": {}}
    for name, evaluations in INTEGRATORS.items():
        row = {"evaluations_per_step": evaluations, "convergence": {}}
        for n in (32, 64, 128, 256, 512):
            row["convergence"][n] = wave_error(name, n, 0.4)
        base = wave_error(name, 64, 0.1, 4.0)
        stable = []
        for cfl in CFLS:
            err = wave_error(name, 64, cfl, 4.0)
            shock = sod(name, 200, cfl)
            ok = (err is not None and err < 50.0 * base and shock is not None
                  and shock["total_variation_ratio"] < 1.05)
            stable.append((cfl, ok))
        cfl_max = 0.0
        for cfl, ok in stable:
            if not ok:
                break
            cfl_max = cfl
        row["stability_scan"] = {str(c): ok for c, ok in stable}
        row["largest_stable_cfl"] = cfl_max
        row["largest_stable_cfl_2d"] = largest_stable_2d(name)
        row["evaluations_per_unit_cfl_time"] = (evaluations / row["largest_stable_cfl_2d"]
                                                if row["largest_stable_cfl_2d"] else math.inf)
        row["sod_cfl_0.4"] = sod(name, 256, 0.4)
        row["sod_cfl_max"] = sod(name, 256, cfl_max) if cfl_max else None
        results["integrators"][name] = row
        print(name, cfl_max, row["convergence"], flush=True)

    md = [
        "# E11.1: time integrators for the hyperbolic part",
        "",
        f"1D Euler, PLM (MC limiter) on primitive variables, HLL; Python {platform.python_version()}, NumPy "
        f"{np.__version__}.",
        "",
        "## Linear sound wave after one period (amplitude 10⁻⁶, CFL 0.4): L1 density error and order",
        "",
        "| Integrator | " + " | ".join(f"N = {n}" for n in (32, 64, 128, 256, 512)) + " | Order 256 → 512 |",
        "|" + "---|" * 7,
    ]
    for name, row in results["integrators"].items():
        errs = [row["convergence"][n] for n in (32, 64, 128, 256, 512)]
        order = math.log2(errs[3] / errs[4]) if errs[3] and errs[4] else float("nan")
        md.append(f"| {name} | " + " | ".join(f"{e:.2e}" for e in errs) + f" | {order:.2f} |")
    md += [
        "",
        "## Stability and cost",
        "",
        "| Integrator | Evaluations per step | Largest stable CFL, 1D | Largest stable CFL, 2D | Evaluations per unit "
        "of CFL time, 2D | Sod L1 error, CFL 0.4 | Sod L1 error at largest 1D CFL | Sod total variation / exact, "
        "largest 1D CFL |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, row in results["integrators"].items():
        sod_max = row["sod_cfl_max"] or {"l1_error": float("nan"), "total_variation_ratio": float("nan")}
        md.append(f"| {name} | {row['evaluations_per_step']} | {row['largest_stable_cfl']:.2f} | "
                  f"{row['largest_stable_cfl_2d']:.2f} | "
                  f"{row['evaluations_per_unit_cfl_time']:.2f} | {row['sod_cfl_0.4']['l1_error']:.2e} | "
                  f"{sod_max['l1_error']:.2e} | {sod_max['total_variation_ratio']:.3f} |")
    (RESULTS / "E11.1b-integrators.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E11.1b-integrators.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
