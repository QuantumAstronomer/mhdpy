# /// script
# requires-python = ">=3.13"
# dependencies = ["matplotlib"]
# ///
"""Figure of experiment E04.4, drawn from ``results/E04.4a-precision.json`` in the house figure style.

Run from this directory with:

    uv run --locked --script E04.4b-figure.py
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
SERIES = {
    "float64, amplitude 0.001": {"color": BLACK, "marker": "o", "label": "double precision, amplitude 10⁻³"},
    "float32, amplitude 0.001": {"color": DARK_GREY, "marker": "s", "label": "single precision, amplitude 10⁻³"},
    "float64, amplitude 1e-06": {"color": RED, "marker": "D", "label": "double precision, amplitude 10⁻⁶"},
    "float32, amplitude 1e-06": {"color": MAROON, "marker": "^", "label": "single precision, amplitude 10⁻⁶"},
}


def main() -> None:
    data = json.loads((RESULTS / "E04.4a-precision.json").read_text())
    plt.rcParams.update(STYLE)
    fig, ax = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
    for key, style in SERIES.items():
        rows = data["accuracy"][key]
        sizes = [int(n) for n in rows]
        ax.loglog(sizes, [rows[str(n)]["l1_error"] for n in sizes], **style)
    sizes = [int(n) for n in data["accuracy"]["float64, amplitude 1e-06"]]
    end = data["accuracy"]["float64, amplitude 1e-06"][str(sizes[-1])]["l1_error"] * 0.4
    guide = [end * (n / sizes[-1]) ** -2 for n in sizes]
    ax.loglog(sizes, guide, color=LIGHT_GREY, linewidth=0.8, zorder=1)
    ax.annotate(r"$N^{-2}$", (sizes[-1], guide[-1]), xytext=(4, 0), textcoords="offset points", va="center",
                fontsize=8, color=GREY)
    ax.set_xticks(sizes, labels=[str(n) for n in sizes])
    ax.minorticks_off()
    ax.set_xlim(right=sizes[-1] * 1.35)
    ax.set(xlabel="resolution N", ylabel="L1 error of density after one period",
           title="Linear sound wave in single and double precision")
    ax.legend(loc="center right")
    fig.savefig(RESULTS / "E04.4b-precision.png")


if __name__ == "__main__":
    main()
