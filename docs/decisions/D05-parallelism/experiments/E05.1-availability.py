"""Experiment E05.1: can each parallel runtime be installed with a single command?

The installation exception of architecture.md §1.4 outranks performance, so every parallelism option must be checked for
what it asks of a user's installation. Wheel availability of NumPy, Cython and mpi4py, including the free-threaded build
of Python 3.14 (3.14t), was already measured in E01.1. This experiment adds what E01.1 did not cover:

1. the free-threaded interpreter itself: does uv offer a download of CPython 3.14t for every target platform?
2. MPI implementations: which MPI libraries are published on PyPI as wheels (mpich, openmpi, impi-rt), for which
   platforms? mpi4py needs one of them at run time, and without such a wheel the user must install MPI separately;
3. a live test of the installation route a user would take: a fresh virtual environment, one ``uv pip install mpi4py
   <mpi>``, and an allreduce over two processes started with that environment's ``mpiexec``, natively and in a Linux
   container (Docker, on the same machine), for the standard and the free-threaded interpreter. (A first version used
   ``uv run --with``, whose layered temporary environments hide the MPI library from mpi4py; that failure says nothing
   about the packages, so a plain environment is used.)

Uses only the standard library, plus uv and Docker as external commands. Run from this directory with (Docker must be
running):

    uv run --no-project --python 3.14 E05.1-availability.py

Results are written to results/.
"""

import datetime as dt
import json
import platform
import shlex
import subprocess
import time
import urllib.request
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
IMAGE = "ghcr.io/astral-sh/uv:python3.14-bookworm-slim"
MPI_PACKAGES = ["mpich", "openmpi", "impi-rt"]
PLATFORMS = {
    "macOS x86-64": ("macosx", ("x86_64", "universal2", "intel")),
    "macOS arm64": ("macosx", ("arm64", "universal2")),
    "Linux x86-64": ("linux", ("x86_64",)),
    "Linux aarch64": ("linux", ("aarch64",)),
}
UV_PLATFORMS = {
    "macOS x86-64": ("macos", "x86_64"),
    "macOS arm64": ("macos", "aarch64"),
    "Linux x86-64": ("linux", "x86_64"),
    "Linux aarch64": ("linux", "aarch64"),
}
PROGRAM = (
    "import sys; from mpi4py import MPI; c = MPI.COMM_WORLD; "
    "total = c.allreduce(c.rank + 1); "
    "print(c.rank, c.size, total, MPI.Get_library_version().splitlines()[0].strip(), "
    "'gil' if getattr(sys, '_is_gil_enabled', lambda: True)() else 'free-threaded', sep='|')"
)


def fetch(package: str) -> dict:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/json", timeout=60) as response:
        return json.load(response)


def platform_of(filename: str) -> list[str]:
    """Return the target platforms that a wheel file serves."""
    if not filename.endswith(".whl"):
        return []
    tags = filename[:-4].split("-")[-1].split(".")
    found = []
    for key, (prefix, arches) in PLATFORMS.items():
        for tag in tags:
            if prefix == "linux" and "linux" in tag and tag.endswith(arches):
                found.append(key)
            if prefix == "macosx" and tag.startswith("macosx") and tag.endswith(arches):
                found.append(key)
    return sorted(set(found))


def mpi_wheels() -> dict:
    rows = {}
    for package in MPI_PACKAGES:
        info = fetch(package)
        version = info["info"]["version"]
        files = info["releases"].get(version, [])
        served = sorted({p for f in files for p in platform_of(f["filename"])})
        rows[package] = {
            "version": version,
            "released": min((f["upload_time"] for f in files), default="")[:10],
            "platforms": served,
        }
    return rows


def free_threaded_interpreters() -> dict:
    listing = subprocess.run(
        ["uv", "python", "list", "--all-platforms", "--all-arches", "--only-downloads", "--output-format", "json"],
        capture_output=True, text=True, check=True,
    )
    entries = json.loads(listing.stdout)
    rows = {}
    for key, (os_name, arch) in UV_PLATFORMS.items():
        versions = sorted(
            {
                e["version"] for e in entries
                if e["variant"] == "freethreaded" and e["os"] == os_name and e["arch"] == arch
                and e["version"].startswith(("3.13.", "3.14."))
            },
            key=lambda v: tuple(map(int, v.split("."))),
        )
        rows[key] = versions[-1] if versions else None
    return rows


def smoke_command(python: str, mpi: str) -> list[str]:
    """A shell command that creates a fresh environment, installs mpi4py and the MPI wheel, and runs two processes."""
    script = (
        f"cd \"$(mktemp -d)\" && uv venv -q --python {python} env && uv pip install -q --python env mpi4py {mpi} "
        f"&& env/bin/mpiexec -n 2 env/bin/python -c {shlex.quote(PROGRAM)}"
    )
    return ["sh", "-c", script]


def run_smoke(command: list[str]) -> dict:
    start = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    seconds = time.perf_counter() - start
    lines = sorted(line for line in result.stdout.splitlines() if line.count("|") == 4)
    ok = result.returncode == 0 and len(lines) == 2 and all(line.split("|")[2] == "3" for line in lines)
    return {
        "success": ok,
        "seconds": seconds,
        "library": " ".join(lines[0].split("|")[3].split(",")[0].split()) if lines else None,
        "interpreter": lines[0].split("|")[4] if lines else None,
        "error": None if ok else (result.stderr.strip().splitlines() or ["(no output)"])[-1][:300],
    }


def smoke_tests() -> dict:
    rows = {}
    for python in ("3.14", "3.14t"):
        for mpi in ("mpich", "openmpi"):
            rows[f"macOS native, Python {python}, {mpi}"] = run_smoke(smoke_command(python, mpi))
            print(python, mpi, "native", rows[f"macOS native, Python {python}, {mpi}"], flush=True)
            ## Open MPI refuses to run as root, the default user in the container, unless told otherwise.
            container = [
                "docker", "run", "--rm", "--platform", "linux/amd64",
                "-e", "OMPI_ALLOW_RUN_AS_ROOT=1", "-e", "OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1",
                IMAGE, *smoke_command(python, mpi),
            ]
            rows[f"Linux container, Python {python}, {mpi}"] = run_smoke(container)
            print(python, mpi, "container", rows[f"Linux container, Python {python}, {mpi}"], flush=True)
    return rows


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {
        "date": dt.date.today().isoformat(),
        "platform": platform.platform(),
        "uv": subprocess.run(["uv", "--version"], capture_output=True, text=True).stdout.strip(),
        "free_threaded_interpreters": free_threaded_interpreters(),
        "mpi_wheels": mpi_wheels(),
        "smoke_tests": smoke_tests(),
    }
    md = [
        "# E05.1: installing the parallel runtimes",
        "",
        f"Queried and run on {results['date']} with {results['uv']} on {results['platform']}; the Linux container is "
        f"`{IMAGE}` (linux/amd64) on the same machine.",
        "",
        "## Free-threaded CPython offered by uv (newest 3.13/3.14 version per platform)",
        "",
        "| Platform | Free-threaded download |",
        "|---|---|",
    ]
    md += [f"| {k} | {v or '—'} |" for k, v in results["free_threaded_interpreters"].items()]
    md += [
        "",
        "## MPI implementations published as wheels on PyPI (latest release)",
        "",
        "| Package | Version | Released | " + " | ".join(PLATFORMS) + " |",
        "|" + "---|" * (3 + len(PLATFORMS)),
    ]
    for package, row in results["mpi_wheels"].items():
        cells = ["✓" if p in row["platforms"] else "—" for p in PLATFORMS]
        md.append(f"| {package} | {row['version']} | {row['released']} | " + " | ".join(cells) + " |")
    md += [
        "",
        "## Two MPI processes after `uv pip install mpi4py <mpi>` into a fresh environment",
        "",
        "The time includes creating the environment, resolving, downloading (or taking from uv's cache) and installing.",
        "",
        "| Environment | Works | Seconds | MPI library | Interpreter | Error |",
        "|---|---|---|---|---|---|",
    ]
    for name, row in results["smoke_tests"].items():
        md.append(
            f"| {name} | {'yes' if row['success'] else 'no'} | {row['seconds']:.0f} | {row['library'] or '—'} | "
            f"{row['interpreter'] or '—'} | {row['error'] or ''} |"
        )
    (RESULTS / "E05.1-availability.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E05.1-availability.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
