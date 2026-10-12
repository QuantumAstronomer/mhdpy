# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E13.2: what must a restart file contain for a restarted run to equal an uninterrupted one bit for bit?

D02.3 makes "a restart reproduces an uninterrupted run bit for bit" one of the invariants tested within an environment.
The state alone is not always enough: the time-step control of D11.5 bounds the growth of the step (here: dt <=
1.1 dt_previous) and shortens steps to hit output times exactly, so the next step depends on the previous one. This
experiment runs the Sod shock tube with the minimal solver of D02 (``E13.2a-hydro1d.py``, PLM with MC, HLL, SSP-RK2,
CFL 0.4, N = 400) to t = 0.2 with outputs every 0.025, once without interruption, and once interrupted at t = 0.1 and
continued in a *new process* from a restart file containing:

- **the state, time and previous step, in binary** (NumPy .npz);
- **the state and time only, in binary:** the previous step is not saved, so the first step after the restart is not
  bounded by it;
- **everything, written as text with 10 significant digits,** as a human-readable format might do.

Each continued run is compared with the uninterrupted one bit for bit.

Run from this directory with:

    uv run --locked --script E13.2b-restart.py

Results are written to results/.
"""

import importlib.util
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
N, CFL, GROWTH = 400, 0.4, 1.1
T_RESTART, T_END, OUTPUT_EVERY = 0.1, 0.2, 0.025


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


h = load("hydro1d", HERE / "E13.2a-hydro1d.py")


def advance(u, t, dt_previous, t_until):
    """Advance to t_until with CFL steps, bounded growth and outputs hit exactly; return the state, time, last step."""
    dx = 1.0 / N
    while t < t_until - 1e-15:
        dt = CFL * dx / h.max_signal_speed(u, 1.4)
        if dt_previous is not None:
            dt = min(dt, GROWTH * dt_previous)
        next_output = (np.floor(t / OUTPUT_EVERY + 1e-9) + 1) * OUTPUT_EVERY
        dt = min(dt, next_output - t, t_until - t)
        stage = u + dt * h.time_derivative(u, dx, "mc", "outflow", 1.4)
        u = 0.5 * u + 0.5 * (stage + dt * h.time_derivative(stage, dx, "mc", "outflow", 1.4))
        t += dt
        dt_previous = dt
    return u, t, dt_previous


def continue_from(path: str, out: str) -> None:
    """Run in a new process: read a restart file, continue to T_END, save the final state."""
    if path.endswith(".npz"):
        data = np.load(path)
        u, t = data["u"], float(data["t"])
        dt_previous = float(data["dt_previous"]) if "dt_previous" in data else None
    else:
        lines = Path(path).read_text().split("\n")
        t, dt_previous = float(lines[0]), float(lines[1])
        u = np.array([[float(v) for v in line.split()] for line in lines[2:] if line])
    u, _, _ = advance(u, t, dt_previous, T_END)
    np.save(out, u)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "continue":
        continue_from(sys.argv[2], sys.argv[3])
        return
    RESULTS.mkdir(exist_ok=True)
    u0 = h.shock_tube(N, h.SOD_LEFT, h.SOD_RIGHT)
    full, _, _ = advance(u0, 0.0, None, T_END)
    half, t_half, dt_half = advance(u0, 0.0, None, T_RESTART)
    rows = {}
    with tempfile.TemporaryDirectory() as tmp:
        files = {
            "state, time and previous step, binary": (Path(tmp) / "full.npz", "npz-all"),
            "state and time only, binary": (Path(tmp) / "state.npz", "npz-state"),
            "everything as text, 10 significant digits": (Path(tmp) / "text.txt", "text"),
        }
        for name, (path, kind) in files.items():
            if kind == "npz-all":
                np.savez(path, u=half, t=t_half, dt_previous=dt_half)
            elif kind == "npz-state":
                np.savez(path, u=half, t=t_half)
            else:
                lines = [f"{t_half:.10g}", f"{dt_half:.10g}"] + [" ".join(f"{v:.10g}" for v in row) for row in half]
                path.write_text("\n".join(lines) + "\n")
            out = Path(tmp) / f"{kind}.npy"
            subprocess.run([sys.executable, __file__, "continue", str(path), str(out)], check=True)
            result = np.load(out)
            rows[name] = {"bitwise_identical": bool(np.array_equal(result, full)),
                          "max_relative_difference": float(np.max(np.abs(result - full)) / np.max(np.abs(full)))}
            print(name, rows[name], flush=True)
    results = {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "rows": rows}
    md = ["# E13.2: what a restart must contain", "",
          f"Sod, N = {N}, SSP-RK2, CFL {CFL}, step growth ≤ {GROWTH}×, outputs every {OUTPUT_EVERY} hit exactly; "
          f"interrupted at t = {T_RESTART}, continued in a new process to t = {T_END}. Python "
          f"{platform.python_version()}, NumPy {np.__version__}.", "",
          "| Restart file | Bit for bit | Max. relative difference |", "|---|---|---|"]
    md += [f"| {name} | {'yes' if r['bitwise_identical'] else 'no'} | {r['max_relative_difference']:.1e} |"
           for name, r in rows.items()]
    (RESULTS / "E13.2b-restart.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E13.2b-restart.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
