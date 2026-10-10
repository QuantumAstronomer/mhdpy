# /// script
# requires-python = ">=3.13"
# dependencies = ["matplotlib"]
# ///
"""Figure of experiment E02.1: convergence of the minimal solver, drawn from ``results/E02.1b-errors.json``.

Kept separate from ``E02.1b-convergence.py`` so that the figure's style can be changed without rerunning the experiment.
The style is a proposal for all figures of the decision briefs. Colours are black, red, darker reds and greys, taken in
the order of the palette below, so lighter reds are a last resort. Series are told apart by colour and marker and drawn
as solid lines; other line styles are used only where colour and marker are not enough. Reference lines are thin grey,
labelled at their end, and the frame is minimal.

Run from this directory with:

    uv run --locked --script E02.1c-figure.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESULTS = HERE / "results"

## Palette, in order of use: black and red first, then darker reds, then greys; lighter reds only as a last resort.
BLACK = "#000000"
RED = "#cc0000"
MAROON = "#7a0000"
DARK_MAROON = "#450000"
DARK_GREY = "#555555"
GREY = "#8c8c8c"
LIGHT_GREY = "#bdbdbd"
LIGHT_RED = "#e57373"

## One fixed appearance per reconstruction, identical in every panel: solid lines, told apart by colour and marker.
## As in the book synthesis, black and grey mark lower-order or reference results and red the main result.
SERIES = {
    "constant": {"color": BLACK, "marker": "o", "label": "first order"},
    "none": {"color": DARK_GREY, "marker": "s", "label": "no limiter"},
    "minmod": {"color": MAROON, "marker": "^", "label": "minmod"},
    "mc": {"color": RED, "marker": "D", "label": "MC"},
}

STYLE = {
    "font.size": 9,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 10,
    "axes.titlelocation": "left",
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.minor.visible": False,
    "lines.linewidth": 1.4,
    "lines.markersize": 4,
    "legend.frameon": False,
    "legend.fontsize": 8,
    "savefig.dpi": 150,
    "figure.facecolor": "white",
}


def guide(ax, ns, end, slope, text):
    """Draw a thin grey reference slope ending at ``(ns[-1], end)`` and label it there."""
    values = [end * (n / ns[-1]) ** slope for n in ns]
    ax.loglog(ns, values, color=LIGHT_GREY, linewidth=0.8, zorder=1)
    ax.annotate(
        text, (ns[-1], values[-1]), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=GREY
    )


def series(ax, ns, values, key, **overrides):
    style = SERIES[key] | overrides
    ax.loglog(ns, values, **style)


def main() -> None:
    data = json.loads((RESULTS / "E02.1b-errors.json").read_text())
    plt.rcParams.update(STYLE)
    fig, (left, right) = plt.subplots(1, 2, figsize=(10, 3.9), constrained_layout=True)

    ns = data["wave_resolutions"]
    for key in SERIES:
        series(left, ns, data["wave"][key]["l1"], key)
    series(
        left, ns[:-1], data["self_convergence"]["mc"], "mc",
        linewidth=0.9, markerfacecolor="white", label="MC, self-convergence",
    )
    guide(left, ns, data["wave"]["none"]["l1"][-1] * 0.4, -2, r"$N^{-2}$")
    guide(left, ns, data["wave"]["constant"]["l1"][-1] * 2.5, -1, r"$N^{-1}$")
    left.set(xlabel="resolution N", ylabel="L1 error of density", title="Linear sound wave, one period")
    left.legend(loc="lower left")

    ns = data["sod_resolutions"]
    for key in ("constant", "minmod", "mc"):
        series(right, ns, data["sod"][key], key)
    guide(right, ns, data["sod"]["constant"][-1] * 1.8, -0.5, r"$N^{-1/2}$")
    guide(right, ns, data["sod"]["mc"][-1] * 0.45, -1, r"$N^{-1}$")
    right.set(xlabel="resolution N", ylabel="L1 error of density", title=f"Sod shock tube, t = {data['sod_time']}")
    right.legend(loc="lower left")

    for ax in (left, right):
        ax.set_xticks(ns if ax is right else data["wave_resolutions"])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.minorticks_off()
        ax.set_xlim(right=ax.get_xlim()[1] * 1.35)  ## room for the slope labels

    fig.savefig(RESULTS / "E02.1c-convergence.png")


if __name__ == "__main__":
    main()
