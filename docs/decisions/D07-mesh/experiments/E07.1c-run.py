"""Experiment E07.1 (driver): run the block-size benchmark natively with both interpreters, then summarise.

``E07.1b-block-size.py`` runs twice, one after the other: with the free-threaded interpreter (Python 3.14t) on 1 and 6
workers, and with the standard interpreter (3.14) on 6 workers. Uses only the standard library. Run from this
directory with (the machine otherwise idle):

    uv run --no-project --python 3.14 E07.1c-run.py

Results are written to results/; the figure is drawn from them by E07.1d-figure.py.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
RUNS = {"macos-native-3.14t": ("3.14t", "1,6"), "macos-native-3.14": ("3.14", "6")}
TITLES = {"macos-native-3.14t": "Python 3.14t (free-threaded)", "macos-native-3.14": "Python 3.14 (with GIL)"}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    for label in sys.argv[1:] or list(RUNS):
        python, workers = RUNS[label]
        subprocess.run(
            ["uv", "run", "--locked", "--python", python, "--script", str(HERE / "E07.1b-block-size.py"), label,
             str(RESULTS / f"E07.1b-{label}.json")],
            check=True, env={**os.environ, "E071_WORKERS": workers},
        )
    summarise()


def summarise() -> None:
    runs = {label: json.loads((RESULTS / f"E07.1b-{label}.json").read_text()) for label in RUNS
            if (RESULTS / f"E07.1b-{label}.json").exists()}
    first = next(iter(runs.values()))
    md = [
        "# E07.1: block sizes on the thesis grid",
        "",
        f"Natively on {first['platform']}; NumPy {first['numpy']}. Million cell updates per second (one update = one "
        "full SSP-RK2 step of one cell), periodic grid, D06 layout and kernel, Python threads as in D05. ✓ = bit-for-bit "
        "identical to the single-block serial reference after two steps. 'Cells with ghosts' is the number of cells a "
        "block stores (and partly computes) per interior cell.",
    ]
    for grid in first["cases"]:
        columns = []
        for label, run in runs.items():
            for key in run["cases"][grid]:
                column = (label, key.split(", ")[1])
                if column not in columns:
                    columns.append(column)
        md += ["", f"## Grid {grid.replace('x', ' × ')}", "",
               "| Block | Blocks | Cells with ghosts | " + " | ".join(f"{TITLES[l]}, {w}" for l, w in columns) + " |",
               "|" + "---|" * (3 + len(columns))]
        shapes = []
        for run in runs.values():
            for key in run["cases"][grid]:
                shape = key.split(", ")[0]
                if shape not in shapes:
                    shapes.append(shape)
        for shape in shapes:
            cells, info = [], None
            for label, workers in columns:
                row = runs[label]["cases"][grid].get(f"{shape}, {workers}")
                if row is None:
                    cells.append("")
                    continue
                info = row
                mark = "✓" if row["bitwise_identical"] else "✗"
                cells.append(f"{row['cell_updates_per_second'] / 1e6:.1f} {mark}")
            md.append(f"| {shape.replace('x', ' × ')} | {info['blocks']} | {info['cells_with_ghosts_per_cell']:.2f} | "
                      + " | ".join(cells) + " |")
    md += ["", "![E07.1](E07.1d-block-size.png)", ""]
    (RESULTS / "E07.1c-block-size.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
