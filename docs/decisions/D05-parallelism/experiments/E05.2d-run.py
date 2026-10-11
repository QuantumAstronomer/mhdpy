"""Experiment E05.2 (driver): run the scaling benchmark natively and in a Linux container, then summarise.

``E05.2b-scaling.py`` runs four times, one after the other so that the runs do not compete for the CPU:

- natively on macOS, with the standard interpreter (Python 3.14) and the free-threaded one (3.14t). Apple's compiler
  has no OpenMP, so the loop-level variant is absent here;
- in a Linux container (Docker, on the same machine), again with both interpreters; GCC provides OpenMP there.

Uses only the standard library. Run from this directory with (Docker must be running, the machine otherwise idle):

    uv run --no-project --python 3.14 E05.2d-run.py

Results are written to results/; the figure is drawn from them by E05.2e-figure.py.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
IMAGE = "mhdpy-e052"
RUNS = {
    "macos-native-3.14": ("native", "3.14"),
    "macos-native-3.14t": ("native", "3.14t"),
    "linux-container-3.14": ("container", "3.14"),
    "linux-container-3.14t": ("container", "3.14t"),
}
TITLES = {
    "macos-native-3.14": "macOS natively, Python 3.14 (with GIL)",
    "macos-native-3.14t": "macOS natively, Python 3.14t (free-threaded)",
    "linux-container-3.14": "Linux container, Python 3.14 (with GIL)",
    "linux-container-3.14t": "Linux container, Python 3.14t (free-threaded)",
}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    only = sys.argv[1:] or list(RUNS)
    if any(RUNS[label][0] == "container" for label in only):
        subprocess.run(["docker", "build", "--quiet", "-t", IMAGE, "-f", str(HERE / "E05.2c-Dockerfile"), str(HERE)],
                       check=True)
    for label in only:
        where, python = RUNS[label]
        script = ["uv", "run", "--locked", "--python", python, "--script"]
        if where == "native":
            command = [*script, str(HERE / "E05.2b-scaling.py"), label, str(RESULTS / f"E05.2b-{label}.json")]
        else:
            command = [
                "docker", "run", "--rm", "--platform", "linux/amd64", "--shm-size", "1g",
                "-v", f"{HERE}:/work:ro", "-v", f"{RESULTS}:/out", "-v", "mhdpy-e052-uv-cache:/root/.cache/uv",
                "-w", "/work", IMAGE, *script, "E05.2b-scaling.py", label, f"/out/E05.2b-{label}.json",
            ]
        subprocess.run(command, check=True)
    summarise()


def summarise() -> None:
    md = [
        "# E05.2: shared-memory parallelism on the 2048 × 512 grid",
        "",
        "Cell updates per second (one update = one full SSP-RK2 step of one cell), and in brackets the speed-up over the "
        "single block on one thread of the same run. ✓ = bit-for-bit identical to the single-block serial reference "
        "after four steps, ✗ = not.",
    ]
    for label in RUNS:
        path = RESULTS / f"E05.2b-{label}.json"
        if not path.exists():
            continue
        run = json.loads(path.read_text())
        base = run["configurations"]["single block, one thread"]["1"]["cell_updates_per_second"]
        counts = sorted({int(t) for rows in run["configurations"].values() for t in rows})
        md += [
            "",
            f"## {TITLES[label]}",
            "",
            f"{run['platform']}, {run['cpu_count']} logical CPUs; Python {run['python'].split()[0]}, NumPy "
            f"{run['numpy']}; GIL enabled after importing the kernels: {run['gil_enabled_after_import']}; "
            f"OpenMP: {run['openmp']}.",
            "",
            "| Configuration | " + " | ".join(f"{t} worker{'s' if t > 1 else ''}" for t in counts) + " |",
            "|" + "---|" * (len(counts) + 1),
        ]
        for name, rows in run["configurations"].items():
            cells = []
            for t in counts:
                row = rows.get(str(t))
                if row is None:
                    cells.append("")
                    continue
                rate = row["cell_updates_per_second"]
                mark = "✓" if row["bitwise_identical"] else "✗"
                cells.append(f"{rate:.2e} ({rate / base:.1f}×) {mark}")
            md.append(f"| {name} | " + " | ".join(cells) + " |")
    md += ["", "![E05.2](E05.2e-scaling.png)", ""]
    (RESULTS / "E05.2d-scaling.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
