"""Experiment E04.2 (driver): installation footprint and coverage measurability of each technology.

1. Footprint: the size of the wheels a user downloads for each technology's runtime, from PyPI, for Python 3.14 on Linux
   x86-64 and macOS on Apple Silicon. Technologies compiled ahead of time (Cython, C) have no runtime dependency: their
   kernels ship inside mhdpy's own wheel.
2. Coverage: runs ``E04.2a-coverage.py`` in the E04.1 Linux container (build it first with E04.1h-run.py).

Uses only the standard library. Run from this directory with (Docker must be running):

    uv run --no-project --python 3.14 E04.2b-run.py

Results are written to results/.
"""

import json
import subprocess
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
RUNTIMES = {
    "NumPy (needed by every option)": ["numpy"],
    "Numba": ["numba", "llvmlite"],
    "JAX": ["jax", "jaxlib", "ml-dtypes", "opt-einsum"],
    "Cython / C (compiled into mhdpy's wheel)": [],
}
PLATFORMS = {"Linux x86-64": "manylinux", "macOS Apple Silicon": "macosx"}


def wheel_size(package: str, platform_tag: str) -> int:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/json", timeout=60) as response:
        data = json.load(response)
    files = data["releases"][data["info"]["version"]]
    candidates = []
    for f in files:
        name = f["filename"]
        if not name.endswith(".whl"):
            continue
        if "none-any" in name:
            return f["size"]
        if ("cp314-cp314-" in name or "abi3" in name) and platform_tag in name and (
            "x86_64" in name if platform_tag == "manylinux" else "arm64" in name
        ):
            candidates.append(f["size"])
    return min(candidates) if candidates else 0


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    footprint = {}
    for runtime, packages in RUNTIMES.items():
        footprint[runtime] = {
            platform: sum(wheel_size(p, tag) for p in packages) for platform, tag in PLATFORMS.items()
        }
    subprocess.run(
        [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "-v", f"{HERE}:/work:ro", "-v", f"{RESULTS}:/out", "-v", "mhdpy-e041-uv-cache:/root/.cache/uv",
            "-w", "/work", "mhdpy-e041",
            "uv", "run", "--locked", "--script", "E04.2a-coverage.py", "/out/E04.2a-coverage.json",
        ],
        check=True,
    )
    coverage = json.loads((RESULTS / "E04.2a-coverage.json").read_text())

    md = [
        "# E04.2: installation footprint and coverage measurability",
        "",
        "## Download size of the runtime packages (latest releases, Python 3.14 wheels)",
        "",
        "| Runtime | " + " | ".join(PLATFORMS) + " |",
        "|---|" + "---|" * len(PLATFORMS),
    ]
    for runtime, sizes in footprint.items():
        md.append(f"| {runtime} | " + " | ".join(f"{sizes[p] / 1e6:.1f} MB" for p in PLATFORMS) + " |")
    md += [
        "",
        "## Can coverage.py measure the kernel?",
        "",
        "| Technology | Measured | Line coverage of the kernel file | Branches covered | Notes |",
        "|---|---|---|---|---|",
    ]
    for tech, res in coverage.items():
        notes = ""
        if "slowdown" in res:
            notes = (f"tracing build {res['slowdown']}× slower than a normal build (tracing inactive); "
                     "Cython's coverage plugin measures lines only, not branches")
        elif "seconds_for_one_step_at_16x16" in res:
            notes = f"one step at 16² takes {res['seconds_for_one_step_at_16x16']} s as plain Python"
        elif "note" in res:
            notes = res["note"]
        md.append(
            f"| {tech} | {res['measured']} | {res.get('line_coverage_percent', '—')} % | "
            f"{res.get('branches_covered', '—')} | {notes} |"
        )
    (RESULTS / "E04.2b-footprint.json").write_text(json.dumps(footprint, indent=1) + "\n")
    (RESULTS / "E04.2b-footprint-and-coverage.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
