# /// script
# requires-python = ">=3.13"
# dependencies = ["matplotlib"]
# ///
"""Figure of experiment E04.1, drawn from the benchmark results in the house figure style.

Run from this directory with:

    uv run --locked --script E04.1j-figure.py
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
DARK_MAROON = "#450000"
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
SERIES = {
    "NumPy": {"color": BLACK, "marker": "o"},
    "Numba": {"color": RED, "marker": "D"},
    "Cython": {"color": MAROON, "marker": "^"},
    "C (generic CPU)": {"color": DARK_MAROON, "marker": "s"},
    "C (-march=native)": {"color": GREY, "marker": "v"},
    "JAX": {"color": DARK_GREY, "marker": "P"},
}
LAPTOP_TARGET = 2.3e6  ## cell updates per second for the whole machine (architecture.md section 1.3)


def main() -> None:
    linux = json.loads((RESULTS / "E04.1f-benchmark-linux-container.json").read_text())
    mac = json.loads((RESULTS / "E04.1f-benchmark-macos-native.json").read_text())
    plt.rcParams.update(STYLE)
    fig, (left, middle, right) = plt.subplots(1, 3, figsize=(13, 3.9), constrained_layout=True)

    for name, style in SERIES.items():
        rates = linux["throughput"].get(name)
        if rates:
            sizes = [int(n) for n in rates]
            left.semilogx(sizes, list(rates.values()), label=name, **style)
    left.set(xlabel="cells per side N (grid N × N)", ylabel="cell updates per second",
             title="One thread, Linux container", ylim=(0, None))
    left.set_xticks([64, 256, 1024, 2048], labels=["64", "256", "1024", "2048"])
    left.minorticks_off()
    left.legend(loc="lower right", bbox_to_anchor=(1.0, 0.26), ncols=2)

    for name, rates in linux["scaling"].items():
        threads = [int(t) for t in rates]
        middle.plot(threads, list(rates.values()), label=name, **SERIES[name])
    middle.axhline(LAPTOP_TARGET, color=LIGHT_GREY, linewidth=0.8, zorder=1)
    middle.annotate("laptop target, whole run", (8, LAPTOP_TARGET), xytext=(0, -11), textcoords="offset points",
                    fontsize=8, color=GREY, ha="right")
    middle.set(xlabel="threads", ylabel="cell updates per second", title="Thread scaling at 1024², Linux container",
               ylim=(0, None))
    middle.legend(loc="center right")

    names = [n for n in SERIES if n in mac["throughput"]]
    positions = range(len(names))
    width = 0.38
    right.bar([p - width / 2 for p in positions], [linux["throughput"][n]["1024"] for n in names], width,
              color=DARK_GREY, label="Linux container")
    right.bar([p + width / 2 for p in positions], [mac["throughput"][n]["1024"] for n in names], width,
              color=RED, label="macOS, native")
    right.set_xticks(list(positions), labels=[n.replace(" (", "\n(") for n in names], fontsize=8)
    right.set(ylabel="cell updates per second", title="Container against native, one thread, 1024²")
    right.legend(loc="upper left")

    fig.savefig(RESULTS / "E04.1j-benchmark.png")


if __name__ == "__main__":
    main()
