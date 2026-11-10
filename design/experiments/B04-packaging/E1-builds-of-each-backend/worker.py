# pyright: strict
# /// script
# requires-python = ">=3.14"
# dependencies = ["numpy>=2.1"]
# ///
"""B4E1: the checks that run in an environment into which a backend has installed the package of B4E1.

`python worker.py check` compares both kernels with plain NumPy, reports the GIL and times the step;
`python worker.py marker` reports what marker() returns and the files from which both kernels were loaded.
"""

import importlib
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
from numpy.typing import NDArray

import vectorised

type Array = NDArray[np.float64]
type Stage = Callable[[Array, Array], None]

KERNELS = ("mhdpy.core.loops", "mhdpy.core.loops2")
CHECK = 128
SIZE = 2048
REPEATS = 7
GAMMA = 5.0 / 3.0
COURANT = 0.4


## ---- the problem and the step of B2E2 ----

def initial_state(n: int) -> Array:
    """Return the conserved variables of a Kelvin-Helmholtz layer on n by n cells with two ghost cells a side."""
    x = (np.arange(-2, n + 2) + 0.5) / n
    xx, yy = np.meshgrid(x, x)
    band = 0.5 * (np.tanh((yy - 0.25) / 0.05) - np.tanh((yy - 0.75) / 0.05))
    rho = 1.0 + band
    vx = -0.5 + band
    vy = 0.01 * np.sin(4.0 * np.pi * xx) * (np.exp(-((yy - 0.25) / 0.1) ** 2) + np.exp(-((yy - 0.75) / 0.1) ** 2))
    u = np.empty((4, n + 4, n + 4))
    u[0] = rho
    u[1] = rho * vx
    u[2] = rho * vy
    u[3] = 2.5 / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy)
    return u


def fill_ghosts(u: Array) -> None:
    """Fill the two ghost cells on each side from the periodic interior, rows first and columns after."""
    u[:, :2, :] = u[:, -4:-2, :]
    u[:, -2:, :] = u[:, 2:4, :]
    u[:, :, :2] = u[:, :, -4:-2]
    u[:, :, -2:] = u[:, :, 2:4]


def time_step(u: Array) -> float:
    """Return the step that the Courant number allows on the initial state, with dx = dy = 1/n."""
    n = u.shape[1] - 4
    rho = u[0]
    vx, vy = u[1] / rho, u[2] / rho
    c = np.sqrt(GAMMA * (GAMMA - 1.0) * (u[3] - 0.5 * rho * (vx * vx + vy * vy)) / rho)
    fastest = max(float(np.max(np.abs(vx) + c)), float(np.max(np.abs(vy) + c)))
    return COURANT / (n * fastest)


def step(u: Array, u1: Array, du: Array, stage: Stage) -> None:
    """Advance u by one step of Heun's method, u1 and du as scratch."""
    fill_ghosts(u)
    stage(u, du)
    np.add(u, du, out=u1)
    fill_ghosts(u1)
    stage(u1, du)
    np.add(u1, du, out=u1)
    np.add(u, u1, out=u)
    np.multiply(u, 0.5, out=u)


def make_stage(module: ModuleType | None, n: int, dt: float) -> Stage:
    """Return the stage of the compiled module, or of plain NumPy without one, on n by n cells."""
    dtdx = dtdy = dt * n
    if module is None:
        return lambda u, du: vectorised.stage(u, du, GAMMA, dtdx, dtdy)
    kernel: Callable[..., None] = module.stage
    w = np.empty((4, n + 4, n + 4))
    fx, fy = np.empty((4, n, n + 1)), np.empty((4, n + 1, n))
    return lambda u, du: kernel(u, w, fx, fy, du, GAMMA, dtdx, dtdy)


def advanced(module: ModuleType | None, n: int) -> Array:
    """Return the state after one step from the initial state on n by n cells."""
    u = initial_state(n)
    stage = make_stage(module, n, time_step(u))
    u1, du = np.empty_like(u), np.zeros_like(u)
    step(u, u1, du, stage)
    return u


def timings(module: ModuleType, n: int) -> list[float]:
    """Return the times of REPEATS steps on n by n cells, each timed alone, after one step to warm up."""
    u = initial_state(n)
    stage = make_stage(module, n, time_step(u))
    u1, du = np.empty_like(u), np.zeros_like(u)
    step(u, u1, du, stage)
    times: list[float] = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        step(u, u1, du, stage)
        times.append(time.perf_counter() - start)
    return times


## ---- the two modes ----

def check() -> dict[str, Any]:
    """Compare both kernels with plain NumPy, report the GIL after their imports, and time the first."""
    modules = [importlib.import_module(name) for name in KERNELS]
    probe: Callable[[], bool] | None = getattr(sys, "_is_gil_enabled", None)
    start = time.perf_counter()
    reference = advanced(None, CHECK)
    numpy_s = time.perf_counter() - start
    agreement: list[float] = []
    seconds: list[float] = []
    for module in modules:
        start = time.perf_counter()
        result = advanced(module, CHECK)
        seconds.append(time.perf_counter() - start)
        agreement.append(max(float(np.max(np.abs(result[k] - reference[k])) / np.max(np.abs(reference[k])))
                             for k in range(4)))
    ## a kernel run from its source, or compiled without its declarations, falls behind plain NumPy and would take
    ## up to an hour to time on SIZE cells, while every kernel compiled with them ran far ahead of it in B2E1
    typed = max(seconds) < numpy_s
    return {"files": [str(m.__file__) for m in modules], "agreement": agreement,
            "gil": None if probe is None else probe(), "check_s": seconds, "numpy_s": numpy_s,
            "times": timings(modules[0], SIZE) if typed else [], "cells": SIZE * SIZE}


def marker() -> dict[str, Any]:
    """Report what marker() of the first kernel returns, and the files and times of change of both kernels."""
    modules = [importlib.import_module(name) for name in KERNELS]
    value: Callable[[], float] = modules[0].marker
    files = [Path(str(m.__file__)) for m in modules]
    return {"marker": repr(value()), "files": [str(f) for f in files], "mtimes": [f.stat().st_mtime for f in files]}


if __name__ == "__main__":
    print(json.dumps(check() if sys.argv[1:] == ["check"] else marker()))
