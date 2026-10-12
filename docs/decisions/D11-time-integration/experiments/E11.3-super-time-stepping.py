# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E11.3: explicit diffusion steps, or super-time-stepping, for thermal conduction?

An explicit step of a diffusion term is limited to dt_par = dx^2 / (2 kappa) in 1D, which shrinks with the square of the
cell size, and in the hot corona of the thesis problem it can be far below the hydrodynamic step dt_hyp. Advancing the
diffusion over each hydrodynamic step then takes R = dt_hyp / dt_par explicit substeps. Runge-Kutta-Legendre super
time steps (RKL1 and RKL2, Meyer, Balsara & Aslam 2014, as Athena++ uses) take one step of s stages over the whole
dt_hyp, with s growing only as the square root of R: stable for dt_hyp <= dt_par (s^2 + s) / 2 (RKL1, first order) and
dt_hyp <= dt_par (s^2 + s - 2) / 4 (RKL2, second order).

This experiment advances u_t = kappa u_xx (kappa = 1, periodic on [0, 1], N = 256, u = 1 + 0.5 sin 2 pi x + 0.2 sin 6 pi
x) to t = 0.05 with "hydrodynamic" steps of R dt_par for R = 1, 10, 100 and 1000, each step covered by:

- **explicit substeps:** forward Euler at dt_par (the stability limit), ceil(R) substeps per step;
- **RKL1:** one super step with the smallest stable s;
- **RKL2:** one super step with the smallest stable s.

It reports the L1 error against the exact cell averages (each Fourier mode decays as exp(-kappa k^2 t)) and the number
of evaluations of the diffusion operator. Each evaluation is also one exchange of ghost cells between blocks (D08), so
the count measures communication as well as computation.

Run from this directory with:

    uv run --locked --script E11.3-super-time-stepping.py

Results are written to results/.
"""

import json
import math
import platform
import sys
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).parent / "results"
N = 256
KAPPA = 1.0
T_END = 0.05
RATIOS = [1, 10, 100, 1000]
MODES = [(1, 0.5), (3, 0.2)]  ## (wavenumber / 2 pi, amplitude)


def exact_average(t: float) -> np.ndarray:
    dx = 1.0 / N
    centres = (np.arange(N) + 0.5) * dx
    u = np.ones(N)
    for m, a in MODES:
        k = 2 * np.pi * m
        u += a * np.sin(k * centres) * np.sin(k * dx / 2) / (k * dx / 2) * np.exp(-KAPPA * k * k * t)
    return u


class Operator:
    def __init__(self) -> None:
        self.evaluations = 0

    def __call__(self, u: np.ndarray) -> np.ndarray:
        self.evaluations += 1
        dx = 1.0 / N
        return KAPPA * (np.roll(u, -1) - 2.0 * u + np.roll(u, 1)) / (dx * dx)


def explicit(u, dt, dt_par, L):
    substeps = math.ceil(dt / dt_par - 1e-12)
    h = dt / substeps
    for _ in range(substeps):
        u = u + h * L(u)
    return u


def stages_rkl1(dt, dt_par):
    s = 1
    while dt > dt_par * (s * s + s) / 2 * (1 + 1e-12):
        s += 1
    return s


def stages_rkl2(dt, dt_par):
    s = 3
    while dt > dt_par * (s * s + s - 2) / 4 * (1 + 1e-12):
        s += 1
    return s


def rkl1(u, dt, dt_par, L):
    s = stages_rkl1(dt, dt_par)
    w1 = 2.0 / (s * s + s)
    y_prev, y = u, u + w1 * dt * L(u)
    for j in range(2, s + 1):
        mu, nu = (2 * j - 1) / j, -(j - 1) / j
        y_prev, y = y, mu * y + nu * y_prev + mu * w1 * dt * L(y)
    return y


def rkl2(u, dt, dt_par, L):
    s = stages_rkl2(dt, dt_par)
    w1 = 4.0 / (s * s + s - 2)

    def b(j):
        return 1.0 / 3.0 if j < 2 else (j * j + j - 2) / (2.0 * j * (j + 1))

    l0 = L(u)
    y_prev, y = u, u + b(1) * w1 * dt * l0
    for j in range(2, s + 1):
        mu = (2 * j - 1) / j * b(j) / b(j - 1)
        nu = -(j - 1) / j * b(j) / b(j - 2)
        mu_t = mu * w1
        gamma_t = -(1.0 - b(j - 1)) * mu_t
        y_new = mu * y + nu * y_prev + (1.0 - mu - nu) * u + mu_t * dt * L(y) + gamma_t * dt * l0
        y_prev, y = y, y_new
    return y


def run(method: str, ratio: float) -> dict:
    dx = 1.0 / N
    dt_par = dx * dx / (2.0 * KAPPA)
    dt = ratio * dt_par
    u = exact_average(0.0)
    L = Operator()
    t, steps = 0.0, 0
    while t < T_END - 1e-15:
        h = min(dt, T_END - t)
        u = {"explicit substeps": explicit, "RKL1": rkl1, "RKL2": rkl2}[method](u, h, dt_par, L)
        t += h
        steps += 1
    stages = {"explicit substeps": math.ceil(ratio - 1e-12), "RKL1": stages_rkl1(dt, dt_par),
              "RKL2": stages_rkl2(dt, dt_par)}[method]
    return {"l1_error": float(np.mean(np.abs(u - exact_average(T_END)))), "evaluations": L.evaluations,
            "steps": steps, "stages_per_step": stages}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "rows": {}}
    for ratio in RATIOS:
        for method in ("explicit substeps", "RKL1", "RKL2"):
            results["rows"][f"{ratio} | {method}"] = run(method, ratio)
            print(ratio, method, results["rows"][f"{ratio} | {method}"], flush=True)
    md = [
        "# E11.3: explicit substeps against super-time-stepping for diffusion",
        "",
        f"u_t = κ u_xx, κ = {KAPPA}, N = {N}, t = {T_END}; each step of R × dt_par (dt_par = dx² / 2κ) covered by explicit "
        f"substeps or one RKL super step. Python {platform.python_version()}, NumPy {np.__version__}.",
        "",
        "| R = dt_hyp / dt_par | Method | Stages per step | Evaluations in total | L1 error |",
        "|---|---|---|---|---|",
    ]
    for key, row in results["rows"].items():
        ratio, method = key.split(" | ")
        md.append(f"| {ratio} | {method} | {row['stages_per_step']} | {row['evaluations']} | {row['l1_error']:.2e} |")
    (RESULTS / "E11.3-super-time-stepping.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E11.3-super-time-stepping.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
