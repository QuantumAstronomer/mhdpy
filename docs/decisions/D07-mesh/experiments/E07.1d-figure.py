# /// script
# requires-python = ">=3.13"
# dependencies = ["matplotlib"]
# ///
"""Figure of experiment E07.1, drawn from ``results/E07.1b-*.json`` in the house figure style (square blocks only).

Run from this directory with:

    uv run --locked --script E07.1d-figure.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESULTS = HERE / "results"

## House figure style (agreed in brief D02).
BLACK = "#000000"
RED = "#cc0000"
MAROON = "#7a0000"
DARK_GREY = "#555555"
GREY = "#8c8c8c"
LIGHT_GREY = "#bdbdbd"
STYLE = {
    "font.size": 9,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 10,
    "axes.titlelocation": "left",
    "lines.linewidth": 1.4,
    "lines.markersize": 4,
    "legend.frameon": False,
    "legend.fontsize": 8,
    "savefig.dpi": 150,
    "figure.facecolor": "white",
}
## (run, grid, workers, label, style)
SERIES = [
    ("macos-native-3.14t", "4000x1000", 6, "4000 × 1000, free-threaded, 6 workers", {"color": BLACK, "marker": "o"}),
    ("macos-native-3.14t", "4096x1024", 6, "4096 × 1024, free-threaded, 6 workers", {"color": MAROON, "marker": "D"}),
    ("macos-native-3.14", "4000x1000", 6, "4000 × 1000, with GIL, 6 workers", {"color": RED, "marker": "s"}),
    ("macos-native-3.14t", "4000x1000", 1, "4000 × 1000, free-threaded, 1 worker", {"color": DARK_GREY, "marker": "^"}),
    ("macos-native-3.14t", "4096x1024", 1, "4096 × 1024, free-threaded, 1 worker", {"color": GREY, "marker": "v"}),
]


def main() -> None:
    plt.rcParams.update(STYLE)
    fig, ax = plt.subplots(figsize=(6.4, 4.6), constrained_layout=True)
    sizes = set()
    for run, grid, workers, label, style in SERIES:
        path = RESULTS / f"E07.1b-{run}.json"
        if not path.exists():
            continue
        rows = json.loads(path.read_text())["cases"][grid]
        points = []
        for key, row in rows.items():
            shape, count = key.split(", ")
            bx, by = (int(n) for n in shape.split("x"))
            if bx == by and int(count.split()[0]) == workers and row["blocks"] > 1:
                points.append((bx, row["cell_updates_per_second"] / 1e6))
        points.sort()
        sizes.update(p[0] for p in points)
        ax.plot([p[0] for p in points], [p[1] for p in points], label=label, **style)
    ax.set_xscale("log")
    ## Label the sizes that tile the thesis grid, plus 32 and 64; 128 and 256 lie too close to 125 and 250.
    ticks = sorted(n for n in sizes if n not in (128, 256))
    ax.set_xticks(ticks, labels=[f"{n}²" for n in ticks])
    ax.minorticks_off()
    ax.set_ylim(0, None)
    ax.set(xlabel="block size (cells)", ylabel="million cell updates per second",
           title="Throughput against block size on thesis-sized grids")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncols=2)
    fig.savefig(RESULTS / "E07.1d-block-size.png")


if __name__ == "__main__":
    main()
