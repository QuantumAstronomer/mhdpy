"""Experiment E04.1 (driver): run the kernel benchmark in a Linux container and natively, then summarise.

Numba and JAX publish no wheels for macOS on Intel (E01.1), so the complete comparison runs in a Linux container
(Docker, on the same CPU). The technologies that are available natively (NumPy, Cython, C without OpenMP, since Apple's
compiler lacks it) also run directly on macOS, which shows the overhead of the container. Uses only the standard library.

Run from this directory with (Docker must be running):

    uv run --no-project --python 3.14 E04.1h-run.py

Results are written to results/; the figure is drawn from them by E04.1j-figure.py.
"""

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
IMAGE = "mhdpy-e041"


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    subprocess.run(["docker", "build", "--quiet", "-t", IMAGE, "-f", str(HERE / "E04.1g-Dockerfile"), str(HERE)],
                   check=True)
    subprocess.run(
        [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "-v", f"{HERE}:/work:ro", "-v", f"{RESULTS}:/out", "-v", "mhdpy-e041-uv-cache:/root/.cache/uv",
            "-w", "/work", IMAGE,
            "uv", "run", "--locked", "--script", "E04.1f-benchmark.py", "linux-container",
            "/out/E04.1f-benchmark-linux-container.json",
        ],
        check=True,
    )
    subprocess.run(
        ["uv", "run", "--locked", "--script", str(HERE / "E04.1f-benchmark.py"), "macos-native",
         str(RESULTS / "E04.1f-benchmark-macos-native.json")],
        check=True,
    )
    summarise()


def summarise() -> None:
    linux = json.loads((RESULTS / "E04.1f-benchmark-linux-container.json").read_text())
    mac = json.loads((RESULTS / "E04.1f-benchmark-macos-native.json").read_text())
    sizes = list(next(iter(linux["throughput"].values())).keys())
    md = [
        "# E04.1: the representative hydro kernel in five technologies",
        "",
        f"Linux container: {linux['platform']}, {linux['cpu_count']} CPUs, {linux['build']['compiler']}, "
        f"versions {linux['versions']}. macOS: {mac['platform']}, {mac['build']['compiler']}.",
        "",
        "## Correctness after five steps, against NumPy",
        "",
        "| Technology | Linux: bit-for-bit | Linux: max. relative difference | macOS: bit-for-bit |",
        "|---|---|---|---|",
    ]
    for name, res in linux["correctness"].items():
        native = mac["correctness"].get(name, {}).get("bitwise_identical", "—")
        md.append(f"| {name} | {res['bitwise_identical']} | {res['max_relative_difference']:.1e} | {native} |")
    md += [
        "",
        "## Throughput on one thread (cell updates per second; one update = one full SSP-RK2 step)",
        "",
        "| Technology | " + " | ".join(f"Linux {n}²" for n in sizes) + " | macOS 1024² | Speed-up over NumPy (Linux, 1024²) |",
        "|" + "---|" * (len(sizes) + 3),
    ]
    numpy_rate = linux["throughput"]["NumPy"]["1024"]
    for name, rates in linux["throughput"].items():
        native = mac["throughput"].get(name, {}).get("1024")
        native_text = f"{native:.2e}" if native else "—"
        md.append(
            f"| {name} | " + " | ".join(f"{rates[n]:.2e}" for n in sizes) + f" | {native_text} | "
            f"{rates['1024'] / numpy_rate:.1f}× |"
        )
    md += ["", "## Thread scaling on 1024² cells (Linux)", ""]
    threads = list(next(iter(linux["scaling"].values())).keys())
    md += ["| Technology | " + " | ".join(f"{t} thr." for t in threads) + " |", "|" + "---|" * (len(threads) + 1)]
    for name, rates in linux["scaling"].items():
        md.append(f"| {name} | " + " | ".join(f"{rates[t]:.2e}" for t in threads) + " |")
    md += ["", "## Start-up cost (Linux)", "", "| Item | Seconds |", "|---|---|"]
    md += [f"| {k} | {v:.2f} |" for k, v in linux["build"].items() if k.startswith("build")]
    md += [f"| first call, {k} | {v:.2f} |" for k, v in linux["first_call_seconds"].items()]
    md += ["", "![E04.1](E04.1j-benchmark.png)", ""]
    (RESULTS / "E04.1h-benchmark.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
