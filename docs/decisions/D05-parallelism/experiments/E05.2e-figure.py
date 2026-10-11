# /// script
# requires-python = ">=3.13"
# dependencies = ["matplotlib"]
# ///
"""Figure of experiment E05.2, drawn from ``results/E05.2b-*.json`` in the house figure style.

Run from this directory with:

    uv run --locked --script E05.2e-figure.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESULTS = HERE / "results"
BLOCK = 64

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
## (run label, configuration, legend label, style)
SERIES = [
    ("3.14t", f"blocks of {BLOCK}², Python threads", f"threads over blocks of {BLOCK}², free-threaded Python",
     {"color": BLACK, "marker": "o"}),
    ("3.14", f"blocks of {BLOCK}², processes", f"processes over blocks of {BLOCK}²", {"color": RED, "marker": "s"}),
    ("3.14", f"blocks of {BLOCK}², Python threads", f"threads over blocks of {BLOCK}², Python with GIL",
     {"color": DARK_GREY, "marker": "^"}),
    ("3.14", "single block, loop-level OpenMP", "OpenMP inside the kernels, one block", {"color": MAROON, "marker": "D"}),
]
PANELS = [("macos-native", "macOS natively (6 cores, 12 hardware threads)", 6),
          ("linux-container", "Linux container (8 virtual CPUs)", None)]


def main() -> None:
    plt.rcParams.update(STYLE)
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8), constrained_layout=True, sharey=True)
    for ax, (prefix, title, cores) in zip(axes, PANELS, strict=True):
        runs = {}
        for python in ("3.14", "3.14t"):
            path = RESULTS / f"E05.2b-{prefix}-{python}.json"
            if path.exists():
                runs[python] = json.loads(path.read_text())
        base = runs["3.14"]["configurations"]["single block, one thread"]["1"]["cell_updates_per_second"]
        counts = []
        for python, configuration, label, style in SERIES:
            rows = runs.get(python, {}).get("configurations", {}).get(configuration)
            if not rows:
                continue
            workers = sorted(int(t) for t in rows)
            counts = sorted(set(counts) | set(workers))
            ax.plot(workers, [rows[str(t)]["cell_updates_per_second"] / 1e6 for t in workers], label=label, **style)
        ax.plot(counts, [base * t / 1e6 for t in counts], color=LIGHT_GREY, linewidth=0.8, zorder=1,
                label="ideal scaling of one thread")
        if cores:
            ax.axvline(cores, color=LIGHT_GREY, linewidth=0.8, zorder=0)
            ax.annotate("physical cores", (cores, 0.02), xycoords=("data", "axes fraction"), xytext=(3, 0),
                        textcoords="offset points", fontsize=8, color=GREY)
        ax.set_xticks(counts)
        ax.set_ylim(0, None)
        ax.set(xlabel="workers (threads or processes)", title=title)
    axes[0].set_ylabel("million cell updates per second")
    axes[1].legend(loc="upper left")
    fig.savefig(RESULTS / "E05.2e-scaling.png")


if __name__ == "__main__":
    main()
