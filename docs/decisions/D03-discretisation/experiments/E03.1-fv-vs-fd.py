# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E03.1: finite-volume Godunov against ZEUS-type finite differences, and total against internal energy.

Compares the two discretisation families of the reference codes on the same problems, using the minimal solvers in
``E03.1-godunov1d.py`` (finite volume, total energy, HLL, MC limiter, SSP-RK2) and ``E03.1-zeus1d.py`` (staggered finite
differences, internal energy, artificial viscosity, operator splitting):

1. Shock tubes against their exact solutions: the Sod problem and Toro's test 3, a strong shock (pressure ratio 10^5).
   Measured: L1 error of the density, error of the post-shock pressure plateau, and the change of total mass and total
   energy, which an exact solution conserves until waves reach the boundaries.
2. A sound wave carried by a uniform bulk flow at Mach numbers 0 to 100. The flow is isentropic, so the exact specific
   entropy p / rho^gamma stays uniform; and by Galilean invariance the physics is the same at every Mach number. Any
   growth of the entropy error with Mach number is numerical. It tests how accurately the thermal state is kept when the
   kinetic energy dominates: the regime of cold, dense clouds moving supersonically through a hot medium.

Run from this directory with:

    uv run --locked --script E03.1-fv-vs-fd.py

Results are written to results/; the figure is drawn from them by E03.1-figure.py.
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


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fv = load("godunov1d", "E03.1-godunov1d.py")
fd = load("zeus1d", "E03.1-zeus1d.py")

GAMMA = 1.4
G = fd.N_GHOST
SHOCK_TUBES = {
    "Sod": {"left": (1.0, 0.0, 1.0), "right": (0.125, 0.0, 0.1), "t_end": 0.2},
    "Toro test 3": {"left": (1.0, 0.0, 1000.0), "right": (1.0, 0.0, 0.01), "t_end": 0.012},
}
SHOCK_RESOLUTIONS = [128, 256, 512, 1024]
MACH_NUMBERS = [0, 1, 3, 10, 30, 100]
WAVE_N, WAVE_TIME, WAVE_AMPLITUDE = 128, 0.25, 1.0e-3


def run_fv_shock(left, right, n, t_end):
    cons = fv.shock_tube(n, left, right, gamma=GAMMA)
    final, steps = fv.evolve(cons, 1.0 / n, t_end, limiter="mc", boundary="outflow", gamma=GAMMA)
    rho, vel, pres = fv.cons_to_prim(final, GAMMA)
    return {"rho": rho, "vel": vel, "pres": pres, "mass": final[0].sum() / n, "energy": final[2].sum() / n, "steps": steps}


def run_fd_shock(left, right, n, t_end):
    x = fv.cell_centres(n)
    rho = np.where(x < 0.5, left[0], right[0])
    pres = np.where(x < 0.5, left[2], right[2])
    r, e, v, steps = fd.evolve(
        fd.pad(rho), fd.pad(pres / (GAMMA - 1.0)), fd.pad(np.zeros(n)), 1.0 / n, t_end, gamma=GAMMA, boundary="outflow"
    )
    rho, eint = r[G:-G], e[G:-G]
    vel = 0.5 * (v[G:-G] + v[G + 1 : -G + 1])  ## face velocities averaged to zone centres
    energy = eint + 0.5 * rho * vel * vel
    return {
        "rho": rho, "vel": vel, "pres": (GAMMA - 1.0) * eint,
        "mass": rho.sum() / n, "energy": energy.sum() / n, "steps": steps,
    }


def plateau_error(pres, exact, p_star, margin=8):
    """Mean relative pressure error in the star region, away from its edges, against the exact star pressure."""
    inside = np.isclose(exact[2], p_star, rtol=1e-12)
    idx = np.flatnonzero(inside)
    core = idx[(idx > idx.min() + margin) & (idx < idx.max() - margin)]
    return float(np.mean(pres[core]) / p_star - 1.0)


def simple_wave(x, mach):
    """Exact isentropic simple wave on a uniform flow: rho, u, p with uniform entropy p / rho^gamma = 1 / gamma."""
    rho = 1.0 + WAVE_AMPLITUDE * np.sin(2.0 * np.pi * x)
    sound = rho ** (0.5 * (GAMMA - 1.0))  ## c = sqrt(gamma p / rho) with p = rho^gamma / gamma
    vel = mach + 2.0 / (GAMMA - 1.0) * (sound - 1.0)  ## Riemann invariant of a right-moving simple wave
    return rho, vel, rho**GAMMA / GAMMA


def entropy_error(rho, pres):
    return float(np.max(np.abs(pres / rho**GAMMA * GAMMA - 1.0)))


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {"shock_tubes": {}, "mach": {}, "profiles": {}}
    md = [
        "# E03.1: finite-volume Godunov against ZEUS-type finite differences",
        "",
        f"numpy {np.__version__}, Python {platform.python_version()}, {platform.platform()}. gamma = {GAMMA}. "
        "FV: total energy, PLM (MC) on primitives, HLL, SSP-RK2, CFL 0.4. FD: internal energy, staggered velocity, "
        "artificial viscosity C2 = 2, van Leer transport, Courant 0.5.",
        "",
    ]

    ## 1. Shock tubes.
    for name, spec in SHOCK_TUBES.items():
        rows = []
        for n in SHOCK_RESOLUTIONS:
            xi = (fv.cell_centres(n) - 0.5) / spec["t_end"]
            exact = fv.exact_riemann(spec["left"], spec["right"], xi, gamma=GAMMA)
            ## The star pressure is the exact pressure halfway between the contact and the shock.
            p_star = float(exact[2][np.argmin(np.abs(exact[1] - np.max(exact[1])))])
            mass0 = 0.5 * (spec["left"][0] + spec["right"][0])
            energy0 = 0.5 * (spec["left"][2] + spec["right"][2]) / (GAMMA - 1.0)
            for scheme, runner in (("FV", run_fv_shock), ("FD", run_fd_shock)):
                start = time.perf_counter()
                out = runner(spec["left"], spec["right"], n, spec["t_end"])
                rows.append({
                    "scheme": scheme, "n": n, "steps": out["steps"], "seconds": time.perf_counter() - start,
                    "l1_density": float(np.mean(np.abs(out["rho"] - exact[0]))),
                    "plateau_pressure_error": plateau_error(out["pres"], exact, p_star),
                    "mass_change": float(out["mass"] / mass0 - 1.0),
                    "energy_change": float(out["energy"] / energy0 - 1.0),
                })
                if n == 256:
                    results["profiles"].setdefault(name, {"x": fv.cell_centres(n).tolist(), "exact": exact[0].tolist()})
                    results["profiles"][name][scheme] = out["rho"].tolist()
        results["shock_tubes"][name] = rows
        md += [
            f"## 1. {name} (t = {spec['t_end']})",
            "",
            "| Scheme | N | L1 error of density | Plateau pressure error | Mass change | Total-energy change | Steps |",
            "|---|---|---|---|---|---|---|",
        ]
        md += [
            f"| {r['scheme']} | {r['n']} | {r['l1_density']:.2e} | {r['plateau_pressure_error']:+.2e} | "
            f"{r['mass_change']:+.1e} | {r['energy_change']:+.1e} | {r['steps']} |"
            for r in rows
        ]
        md.append("")

    ## 2. Sound wave on a supersonic bulk flow.
    n = WAVE_N
    for mach in MACH_NUMBERS:
        x = fv.cell_centres(n)
        rho, vel, pres = simple_wave(x, mach)
        cons = fv.prim_to_cons(np.array([rho, vel, pres]), GAMMA)
        start = time.perf_counter()
        final, steps_fv = fv.evolve(cons, 1.0 / n, WAVE_TIME, limiter="mc", boundary="periodic", gamma=GAMMA)
        seconds_fv = time.perf_counter() - start
        r_fv, _, p_fv = fv.cons_to_prim(final, GAMMA)

        faces = np.arange(n) / n
        _, vel_faces, _ = simple_wave(faces, mach)
        start = time.perf_counter()
        r_fd, e_fd, _, steps_fd = fd.evolve(
            fd.pad(rho), fd.pad(pres / (GAMMA - 1.0)), fd.pad(vel_faces), 1.0 / n, WAVE_TIME, gamma=GAMMA
        )
        seconds_fd = time.perf_counter() - start
        results["mach"][mach] = {
            "FV": {"entropy_error": entropy_error(r_fv, p_fv), "steps": steps_fv, "seconds": seconds_fv},
            "FD": {
                "entropy_error": entropy_error(r_fd[G:-G], (GAMMA - 1.0) * e_fd[G:-G]),
                "steps": steps_fd, "seconds": seconds_fd,
            },
        }
    md += [
        f"## 2. Sound wave on a bulk flow (N = {n}, amplitude {WAVE_AMPLITUDE}, t = {WAVE_TIME})",
        "",
        "Maximum relative error of the specific entropy p / rho^gamma, which is exactly uniform in the true solution.",
        "",
        "| Bulk Mach number | FV (total energy) | FD (internal energy) | Steps FV / FD |",
        "|---|---|---|---|",
    ]
    for mach, res in results["mach"].items():
        md.append(
            f"| {mach} | {res['FV']['entropy_error']:.2e} | {res['FD']['entropy_error']:.2e} | "
            f"{res['FV']['steps']} / {res['FD']['steps']} |"
        )

    (RESULTS / "E03.1-fv-vs-fd.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E03.1-fv-vs-fd.md").write_text("\n".join(md) + "\n\n![E03.1](E03.1-fv-vs-fd.png)\n")
    (RESULTS / "E03.1-metadata.json").write_text(
        json.dumps({"python": sys.version, "numpy": np.__version__, "platform": platform.platform()}, indent=2) + "\n"
    )
    print("\n".join(md))


if __name__ == "__main__":
    main()
