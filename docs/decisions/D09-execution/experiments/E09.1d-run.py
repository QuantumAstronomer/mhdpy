"""Experiment E09.1 (driver): run the orchestration benchmark natively and in a Linux container, then summarise.

``E09.1b-orchestration.py`` runs four times, one after the other: natively on macOS with the free-threaded (3.14t) and
the standard (3.14) interpreter on 1, 6 and 12 workers, and in a Linux container (Docker, 8 virtual CPUs) with both
interpreters on 1, 4 and 8 workers. The container is where E05.2 and E08.1 saw threads under the GIL slow down. Uses
only the standard library. Run from this directory with (Docker running, the machine otherwise idle):

    uv run --no-project --python 3.14 E09.1d-run.py

Results are written to results/.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
IMAGE = "mhdpy-e091"
## uv may reuse a cached free-threaded script environment for a plain "3.14" request; "3.14+gil" forces the GIL build.
RUNS = {
    "macos-native-3.14t": ("native", "3.14t", "1,6,12"),
    "macos-native-3.14": ("native", "3.14+gil", "1,6,12"),
    "linux-container-3.14t": ("container", "3.14t", "1,4,8"),
    "linux-container-3.14": ("container", "3.14+gil", "1,4,8"),
}
TITLES = {
    "macos-native-3.14t": "macOS, free-threaded",
    "macos-native-3.14": "macOS, with GIL",
    "linux-container-3.14t": "Linux container, free-threaded",
    "linux-container-3.14": "Linux container, with GIL",
}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    only = sys.argv[1:] or list(RUNS)
    if any(RUNS[label][0] == "container" for label in only):
        subprocess.run(["docker", "build", "--quiet", "-t", IMAGE, "-f", str(HERE / "E09.1c-Dockerfile"), str(HERE)],
                       check=True)
    for label in only:
        where, python, workers = RUNS[label]
        script = ["uv", "run", "--locked", "--python", python, "--script"]
        if where == "native":
            command = ["env", f"E091_WORKERS={workers}", *script, str(HERE / "E09.1b-orchestration.py"), label,
                       str(RESULTS / f"E09.1b-{label}.json")]
        else:
            command = [
                "docker", "run", "--rm", "--platform", "linux/amd64", "-e", f"E091_WORKERS={workers}",
                "-v", f"{HERE}:/work:ro", "-v", f"{RESULTS}:/out", "-v", "mhdpy-e091-uv-cache:/root/.cache/uv",
                "-w", "/work", IMAGE, *script, "E09.1b-orchestration.py", label, f"/out/E09.1b-{label}.json",
            ]
        subprocess.run(command, check=True)
    summarise()


def summarise() -> None:
    md = [
        "# E09.1: orchestrating a step over blocks and workers",
        "",
        "Thesis grid 4000 × 1000, periodic, D06 layout and kernel, Python threads as in D05. Million cell updates per "
        "second (one update = one full SSP-RK2 step of one cell). ✓ = bit-for-bit identical to the single-block serial "
        "reference after two steps; 'barriers only' gives the time per step of synchronisation alone.",
    ]
    for label, title in TITLES.items():
        path = RESULTS / f"E09.1b-{label}.json"
        if not path.exists():
            continue
        run = json.loads(path.read_text())
        counts = sorted({int(key.split(" | ")[2]) for key in run["rows"]})
        configs = list(dict.fromkeys(" | ".join(key.split(" | ")[:2]) for key in run["rows"]))
        md += [
            "",
            f"## {title}",
            "",
            f"{run['platform']}, {run['cpu_count']} logical CPUs; Python {run['python'].split()[0]}; GIL enabled after "
            f"importing the kernels: {run['gil_enabled_after_import']}.",
            "",
            "| Block | Orchestration | " + " | ".join(f"{t} worker{'s' if t > 1 else ''}" for t in counts) + " |",
            "|" + "---|" * (len(counts) + 2),
        ]
        for config in configs:
            block, mode = config.split(" | ")
            cells = []
            for t in counts:
                row = run["rows"][f"{config} | {t}"]
                if row["bitwise_identical"] is None:
                    cells.append(f"{1e6 * row['seconds_per_step']:.0f} µs/step")
                else:
                    cells.append(f"{row['cell_updates_per_second'] / 1e6:.1f} {'✓' if row['bitwise_identical'] else '✗'}")
            md.append(f"| {block.replace('x', ' × ')} | {mode} | " + " | ".join(cells) + " |")
    (RESULTS / "E09.1d-orchestration.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
