# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "matplotlib"]
# ///
"""Figure of experiment E03.2, drawn from ``results/E03.2b-field-loop.json`` and ``results/E03.2b-maps.npz``.

Run from this directory with:

    uv run --locked --script E03.2c-figure.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

HERE = Path(__file__).parent
RESULTS = HERE / "results"

## House figure style (agreed in brief D02).
BLACK = "#000000"
RED = "#cc0000"
MAROON = "#7a0000"
DARK_MAROON = "#450000"
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
## Sequential colour map for field strength, from white through red to dark maroon.
PRESSURE_MAP = LinearSegmentedColormap.from_list("white-red", ["#ffffff", RED, DARK_MAROON])
SCHEMES = {
    "none": {"color": DARK_GREY, "marker": "o", "label": "no control"},
    "glm": {"color": BLACK, "marker": "s", "label": "GLM cleaning"},
    "ct-average": {"color": MAROON, "marker": "^", "label": "CT, averaged EMFs"},
    "ct-contact": {"color": RED, "marker": "D", "label": "CT, upwinded EMFs"},
}


def main() -> None:
    data = json.loads((RESULTS / "E03.2b-field-loop.json").read_text())
    maps = np.load(RESULTS / "E03.2b-maps.npz")
    plt.rcParams.update(STYLE)
    fig = plt.figure(figsize=(13, 6.4), constrained_layout=True)
    top, bottom = fig.subfigures(2, 1, height_ratios=[1.0, 1.55])

    scale = 1.0e-7  ## B^2/2 is of order 10^-7 for a loop of amplitude 10^-3
    vmax = float(maps["initial"].max()) / scale
    panels = [("initial", "initial state (= exact at t = 2)")] + [(k, v["label"]) for k, v in SCHEMES.items()]
    map_axes = top.subplots(1, 5)
    for ax, (key, title) in zip(map_axes, panels, strict=True):
        image = ax.imshow(
            maps[key].T / scale, origin="lower", extent=(-1.0, 1.0, -0.5, 0.5), cmap=PRESSURE_MAP, vmin=0.0, vmax=vmax
        )
        ax.set_title(title, fontsize=8.5)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(LIGHT_GREY)
    colorbar = top.colorbar(image, ax=map_axes, location="right", shrink=0.8, pad=0.01)
    colorbar.set_label(r"$B^2/2$ $(10^{-7})$", fontsize=8)
    colorbar.ax.tick_params(labelsize=7)

    energy_ax, div_ax = bottom.subplots(1, 2, width_ratios=[2, 3])
    for key, style in SCHEMES.items():
        res = data[key]
        energy_ax.plot(res["times"], res["energy"], markevery=5, **style)
        div_ax.semilogy(res["times"], np.maximum(res["divergence"], 1e-17), markevery=5, **style)
    energy_ax.axhline(1.0, color=LIGHT_GREY, linewidth=0.8, zorder=1)
    energy_ax.set(xlabel="time", ylabel="magnetic energy / initial", title="Magnetic energy (exact: constant)")
    energy_ax.legend(loc="upper left")
    div_ax.set(xlabel="time", ylabel=r"max $|\nabla\cdot B|\,\Delta x\,/\,B_{max}$",
               title="Largest divergence of B", ylim=(1e-16, 2.0))

    fig.savefig(RESULTS / "E03.2c-field-loop.png")


if __name__ == "__main__":
    main()
