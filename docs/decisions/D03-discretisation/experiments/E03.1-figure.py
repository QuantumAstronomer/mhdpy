# /// script
# requires-python = ">=3.13"
# dependencies = ["matplotlib"]
# ///
"""Figure of experiment E03.1, drawn from ``results/E03.1-fv-vs-fd.json`` in the house figure style.

Run from this directory with:

    uv run --locked --script E03.1-figure.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESULTS = HERE / "results"

## House figure style (agreed in brief D02): black and red first, then darker reds, then greys; solid lines, told apart
## by colour and marker; reference curves thin and grey; minimal frame.
BLACK = "#000000"
RED = "#cc0000"
MAROON = "#7a0000"
DARK_GREY = "#555555"
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
FV = {"color": RED, "marker": "D", "label": "finite volume (total energy)"}
FD = {"color": DARK_GREY, "marker": "o", "label": "ZEUS-type finite differences (internal energy)"}


def profile(ax, data, name, xlim, ylim, title):
    prof = data["profiles"][name]
    x = prof["x"]
    ax.plot(x, prof["exact"], color=BLACK, linewidth=0.9, label="exact")
    ax.plot(x, prof["FV"], color=FV["color"], marker=FV["marker"], markersize=2.5, linewidth=1.0, label="finite volume")
    ax.plot(x, prof["FD"], color=FD["color"], marker=FD["marker"], markersize=2.5, linewidth=1.0, label="ZEUS-type")
    ax.set(xlim=xlim, ylim=ylim, xlabel="x", ylabel="density", title=title)
    ax.legend(loc="upper right")


def main() -> None:
    data = json.loads((RESULTS / "E03.1-fv-vs-fd.json").read_text())
    plt.rcParams.update(STYLE)
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), constrained_layout=True)

    profile(axes[0], data, "Sod", (0.55, 0.95), (0.1, 0.5), "Sod, N = 256, t = 0.2")
    profile(axes[1], data, "Toro test 3", (0.65, 0.85), (0.0, 7.0), "Toro test 3, N = 256, t = 0.012")

    machs = [int(m) for m in data["mach"] if int(m) > 0]
    for scheme, style in (("FV", FV), ("FD", FD)):
        errors = [data["mach"][str(m)][scheme]["entropy_error"] for m in machs]
        axes[2].loglog(machs, errors, **style)
    reference = [data["mach"]["1"]["FV"]["entropy_error"] * 0.4 * m for m in machs]
    axes[2].loglog(machs, reference, color=LIGHT_GREY, linewidth=0.8, zorder=1)
    axes[2].annotate(r"$\propto M$", (machs[-1], reference[-1]), xytext=(4, 0), textcoords="offset points",
                     va="center", fontsize=8, color=DARK_GREY)
    axes[2].set(xlabel="Mach number of the bulk flow", ylabel="max. relative entropy error",
                title="Sound wave on a supersonic flow, N = 128")
    axes[2].set_xlim(right=machs[-1] * 2.0)
    axes[2].legend(loc="center left")

    fig.savefig(RESULTS / "E03.1-fv-vs-fd.png")


if __name__ == "__main__":
    main()
