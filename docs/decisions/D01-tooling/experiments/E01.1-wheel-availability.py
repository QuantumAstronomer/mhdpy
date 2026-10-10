"""Experiment E01.1: ecosystem readiness of candidate dependencies.

For each candidate dependency, query PyPI and determine:

1. whether its latest release ships a prebuilt wheel for each combination of
   Python version (3.13, 3.14, free-threaded 3.14t) and platform (macOS Intel,
   macOS Apple Silicon, Linux x86-64, Linux ARM);
2. how long after the Python 3.13.0 and 3.14.0 releases the first wheels for
   those versions appeared (the "lag" of the ecosystem);
3. for development tools: the latest version and its release date, as an
   indication of maturity.

Uses only the standard library, so it presupposes none of the decisions in
brief 01. Run from this directory with:

    uv run --no-project --python 3.14 E01.1-wheel-availability.py

Results are written to results/.
"""

import datetime as dt
import json
import platform
import re
import sys
import urllib.request
from pathlib import Path

RESULTS = Path(__file__).parent / "results"

# Scientific stack that later briefs may draw on (backend, parallelism, I/O).
SCIENTIFIC = [
    "numpy", "scipy", "cython", "numba", "llvmlite", "jax", "jaxlib",
    "h5py", "mpi4py", "matplotlib",
]
# Development tools considered in brief 01.
TOOLS = [
    "ruff", "black", "flake8", "pylint", "mypy", "pyright", "ty", "pyrefly",
    "pytest", "pre-commit", "prek", "sphinx", "mkdocs", "mkdocs-material",
    "zensical", "meson-python", "scikit-build-core", "hatchling", "uv-build",
    "setuptools",
]

PYTHONS = {"3.13": "cp313", "3.14": "cp314", "3.14t": "cp314t"}
PYTHON_RELEASES = {"3.13": dt.date(2024, 10, 7), "3.14": dt.date(2025, 10, 7)}
PLATFORMS = {
    "macOS x86-64": ("macosx", ("x86_64", "universal2", "intel")),
    "macOS arm64": ("macosx", ("arm64", "universal2")),
    "Linux x86-64": ("linux", ("x86_64",)),
    "Linux aarch64": ("linux", ("aarch64",)),
}


def fetch(package: str) -> dict:
    url = f"https://pypi.org/pypi/{package}/json"
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def parse_wheel(filename: str) -> tuple[list[str], list[str], list[str]] | None:
    """Return (python tags, abi tags, platform tags) of a wheel file name."""
    if not filename.endswith(".whl"):
        return None
    parts = filename[:-4].split("-")
    py, abi, plat = parts[-3], parts[-2], parts[-1]
    return py.split("."), abi.split("."), plat.split(".")


def wheel_covers(filename: str, python: str, plat_key: str) -> str | None:
    """Return the matching platform tag if the wheel serves this target."""
    parsed = parse_wheel(filename)
    if parsed is None:
        return None
    pys, abis, plats = parsed
    cp = PYTHONS[python]
    free_threaded = python.endswith("t")

    if "none" in abis and "any" in plats:  # pure-Python wheel
        return "any (pure Python)"

    py_ok = False
    if cp in abis:  # e.g. cp314-cp314 or cp314-cp314t
        py_ok = True
    elif not free_threaded and "abi3" in abis:
        # Stable-ABI wheel: valid for its own version and every later one.
        # (The free-threaded build does not support the stable ABI.)
        minor = int(PYTHONS[python][3:].rstrip("t"))
        for tag in pys:
            m = re.fullmatch(r"cp3(\d+)", tag)
            if m and int(m.group(1)) <= minor:
                py_ok = True
    elif not free_threaded and "none" in abis and any(
        p in ("py3", cp) for p in pys
    ):
        py_ok = True  # platform-specific but Python-independent (e.g. ruff)
    if not py_ok:
        return None

    os_prefix, arches = PLATFORMS[plat_key]
    for tag in plats:
        if os_prefix == "linux" and ("linux" in tag) and tag.endswith(arches):
            return tag
        if os_prefix == "macosx" and tag.startswith("macosx") and tag.endswith(arches):
            return tag
    return None


def latest_release_files(info: dict) -> tuple[str, str, list[dict]]:
    version = info["info"]["version"]
    files = info["releases"].get(version, [])
    uploaded = min((f["upload_time"] for f in files), default="")[:10]
    return version, uploaded, files


def first_wheel_date(info: dict, python: str) -> tuple[str, str] | None:
    """Earliest (date, version) of a release with a wheel for this Python."""
    best = None
    for version, files in info["releases"].items():
        for f in files:
            if f.get("yanked"):
                continue
            for plat_key in ("Linux x86-64", "macOS arm64"):
                if wheel_covers(f["filename"], python, plat_key):
                    date = f["upload_time"][:10]
                    if best is None or date < best[0]:
                        best = (date, version)
    return best


def min_macos(tag: str) -> str:
    m = re.match(r"macosx_(\d+)_(\d+)_", tag)
    return f"{m.group(1)}.{m.group(2)}" if m else ""


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    today = dt.date.today()
    meta = {
        "date": today.isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "source": "https://pypi.org/pypi/<package>/json",
    }

    lines = [
        "# E01.1: wheel availability on PyPI",
        "",
        f"Queried {today.isoformat()} with Python {platform.python_version()} "
        f"on {platform.platform()}.",
        "",
        "## Latest release: prebuilt wheel available?",
        "",
        "`✓` = wheel exists (minimum macOS version in brackets where stated), "
        "`any` = pure-Python wheel, `—` = no wheel (would need to build from source).",
        "",
    ]
    header = "| Package | Version | Released | " + " | ".join(
        f"{py} {pk}" for py in PYTHONS for pk in PLATFORMS
    ) + " |"
    lines += [header, "|" + "---|" * (3 + len(PYTHONS) * len(PLATFORMS))]

    lag_rows = []
    csv_rows = ["package,version,released,python,platform,available,tag"]

    for package in SCIENTIFIC:
        info = fetch(package)
        version, uploaded, files = latest_release_files(info)
        cells = []
        for python in PYTHONS:
            for plat_key in PLATFORMS:
                tags = [t for f in files if (t := wheel_covers(f["filename"], python, plat_key))]
                if not tags:
                    cells.append("—")
                    csv_rows.append(f"{package},{version},{uploaded},{python},{plat_key},no,")
                elif tags[0].startswith("any"):
                    cells.append("any")
                    csv_rows.append(f"{package},{version},{uploaded},{python},{plat_key},pure,")
                else:
                    macs = sorted({min_macos(t) for t in tags if min_macos(t)},
                                  key=lambda v: tuple(map(int, v.split("."))))
                    cells.append(f"✓ ({macs[0]})" if macs else "✓")
                    csv_rows.append(f"{package},{version},{uploaded},{python},{plat_key},yes,{tags[0]}")
        lines.append(f"| {package} | {version} | {uploaded} | " + " | ".join(cells) + " |")

        for python, released in PYTHON_RELEASES.items():
            first = first_wheel_date(info, python)
            if first:
                lag = (dt.date.fromisoformat(first[0]) - released).days
                lag_rows.append((package, python, first[1], first[0], lag))
            else:
                lag_rows.append((package, python, "—", "—", None))

    lines += [
        "",
        "## Ecosystem lag: first wheel after a new Python release",
        "",
        "Days between the CPython release (3.13.0: 2024-10-07, 3.14.0: 2025-10-07) "
        "and the first release of the package with a wheel for that version "
        "(Linux x86-64 or macOS arm64). Negative values mean wheels were "
        "published for release candidates, before the final CPython release.",
        "",
        "| Package | Python | First version | Date | Lag (days) |",
        "|---|---|---|---|---|",
    ]
    for package, python, version, date, lag in lag_rows:
        lines.append(f"| {package} | {python} | {version} | {date} | "
                     f"{'—' if lag is None else lag} |")

    lines += [
        "",
        "## Last release with an Intel-macOS wheel",
        "",
        "For packages whose latest release has no macOS x86-64 wheel: the most "
        "recent release that still had one, and the Python versions it covered.",
        "",
        "| Package | Last version | Date | Python tags of its macOS x86-64 wheels |",
        "|---|---|---|---|",
    ]
    for package in SCIENTIFIC:
        info = fetch(package)
        _, _, files = latest_release_files(info)
        if any(wheel_covers(f["filename"], "3.14", "macOS x86-64") for f in files):
            continue
        best = None
        for version, vfiles in info["releases"].items():
            intel = [
                f for f in vfiles
                if f["filename"].endswith(".whl") and not f.get("yanked")
                and any(t.startswith("macosx") and t.endswith(("x86_64", "intel", "universal2"))
                        for t in parse_wheel(f["filename"])[2])
            ]
            if intel:
                date = min(f["upload_time"] for f in intel)[:10]
                if best is None or date > best[1]:
                    tags = sorted({parse_wheel(f["filename"])[1][0] for f in intel})
                    best = (version, date, tags)
        if best:
            lines.append(f"| {package} | {best[0]} | {best[1]} | {', '.join(best[2])} |")
        else:
            lines.append(f"| {package} | never | — | — |")

    lines += [
        "",
        "## Development tools: latest release",
        "",
        "| Tool | Latest version | Released | Project first released |",
        "|---|---|---|---|",
    ]
    for tool in TOOLS:
        try:
            info = fetch(tool)
        except Exception as exc:  # noqa: BLE001 - report and continue
            lines.append(f"| {tool} | (not found: {exc}) | | |")
            continue
        version, uploaded, _ = latest_release_files(info)
        first = min(
            (f["upload_time"][:10] for fs in info["releases"].values() for f in fs),
            default="",
        )
        lines.append(f"| {tool} | {version} | {uploaded} | {first} |")

    (RESULTS / "E01.1-wheel-availability.md").write_text("\n".join(lines) + "\n")
    (RESULTS / "E01.1-wheel-availability.csv").write_text("\n".join(csv_rows) + "\n")
    (RESULTS / "E01.1-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
