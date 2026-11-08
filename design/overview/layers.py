# pyright: strict
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Draw the diagram of the layers of `design/overview.md` into `layers.svg` beside this script."""

from pathlib import Path
from xml.sax.saxutils import escape

## The strata from the top down, each with its components and whether a component belongs to the first pass.
STRATA: list[tuple[str, list[tuple[str, bool]]]] = [
    ("5 Driver and problems", [
        ("main loop and step", True), ("problem setups", True), ("outputs and restarts", True),
        ("verification problems", True),
    ]),
    ("4 Physics", [
        ("diffusion", True), ("thermal conduction", True), ("radiative cooling", True), ("stiff local sources", True),
        ("elliptic solvers", False), ("self-gravity", False), ("particles", False), ("radiation", False),
        ("shearing box", False), ("cosmic rays", False), ("driven turbulence", False), ("chemical networks", False),
    ]),
    ("3 Numerical core", [
        ("variables", True), ("equations of state", True), ("reconstruction", True), ("Riemann solvers", True),
        ("integrator", True), ("source terms", True), ("coupling of processes", True), ("passive scalar", True),
        ("open boundaries", True), ("MHD", False), ("higher order", False), ("artificial viscosity", False),
        ("relativistic MHD", False),
    ]),
    ("2 Mesh and data", [
        ("grid and geometry", True), ("state arrays", True), ("ghost cells and boundaries", True),
        ("curvilinear coordinates", False), ("mesh refinement", False),
    ]),
    ("1 Infrastructure", [
        ("package", True), ("parameters and units", True), ("kernels", True), ("parallel execution", True),
        ("testing tools", True),
    ]),
]

## Colours of §3.3 of CLAUDE.md: black for the frame, red for the main result, greys after it.
BLACK = "#000000"
FIRST_PASS = "#cc0000"
EXTENSION = "#555555"
RULE = "#bdbdbd"

WIDTH = 960
LABEL_WIDTH = 200
MARGIN = 16
FONT = "Helvetica, Arial, sans-serif"
SIZE = 13
BOX_HEIGHT = 26
GAP = 8
BAND_PAD = 12


def box_width(name: str) -> float:
    """Return the width of the box of a component, from generous widths of its characters at SIZE."""
    return sum(9.5 if c.isupper() else 3.6 if c == " " else 6.8 for c in name) + 16


def rows_of(components: list[tuple[str, bool]]) -> list[list[tuple[str, bool]]]:
    """Return the components in rows that fit beside the label of their stratum."""
    room = WIDTH - LABEL_WIDTH - MARGIN
    rows: list[list[tuple[str, bool]]] = [[]]
    used = 0.0
    for component in components:
        width = box_width(component[0])
        if rows[-1] and used + width > room:
            rows.append([])
            used = 0.0
        rows[-1].append(component)
        used += width + GAP
    return rows


def text(x: float, y: float, content: str, colour: str, weight: str = "normal") -> str:
    """Return an SVG text element whose baseline starts at (x, y)."""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{SIZE}" '
            f'font-weight="{weight}" fill="{colour}">{escape(content)}</text>')


def component(x: float, y: float, name: str, first: bool) -> str:
    """Return the box and label of one component with its top left corner at (x, y)."""
    colour = FIRST_PASS if first else EXTENSION
    rect = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{box_width(name):.1f}" height="{BOX_HEIGHT}" '
            f'fill="none" stroke="{colour}" stroke-width="1.2"/>')
    return rect + text(x + 8, y + 17.5, name, colour)


def draw() -> str:
    """Return the whole diagram as SVG."""
    parts: list[str] = []
    y = 34.0
    parts.append(text(MARGIN, 22, "The five strata of mhdpy, each resting on those below it", BLACK, "bold"))
    for label, components in STRATA:
        rows = rows_of(components)
        height = 2 * BAND_PAD + len(rows) * BOX_HEIGHT + (len(rows) - 1) * GAP
        parts.append(f'<line x1="{MARGIN}" y1="{y:.1f}" x2="{WIDTH - MARGIN}" y2="{y:.1f}" stroke="{RULE}"/>')
        parts.append(text(MARGIN, y + BAND_PAD + 17.5, label, BLACK, "bold"))
        for i, row in enumerate(rows):
            x = float(LABEL_WIDTH)
            top = y + BAND_PAD + i * (BOX_HEIGHT + GAP)
            for name, first in row:
                parts.append(component(x, top, name, first))
                x += box_width(name) + GAP
        y += height
    parts.append(f'<line x1="{MARGIN}" y1="{y:.1f}" x2="{WIDTH - MARGIN}" y2="{y:.1f}" stroke="{RULE}"/>')
    ## The key.
    y += 14
    parts.append(component(LABEL_WIDTH, y, "first pass", True))
    parts.append(component(LABEL_WIDTH + box_width("first pass") + 2 * GAP, y, "extension", False))
    height = y + BOX_HEIGHT + MARGIN
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height:.0f}" '
            f'viewBox="0 0 {WIDTH} {height:.0f}">')
    background = f'<rect width="{WIDTH}" height="{height:.0f}" fill="#ffffff"/>'
    return "\n".join([head, background, *parts, "</svg>"]) + "\n"


if __name__ == "__main__":
    Path(__file__).with_name("layers.svg").write_text(draw(), encoding="utf-8")
