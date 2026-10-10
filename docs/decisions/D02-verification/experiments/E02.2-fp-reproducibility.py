# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Experiment E02.2: are floating-point results bit-for-bit reproducible across environments?

Runs ``E02.2-workload.py`` in several environments and compares every result bit for bit with a reference environment
(macOS, Python 3.14, NumPy 2.5.3: the current development environment). The environments vary:

- the NumPy version (every minor release with wheels for the development machine, on Python 3.13 and 3.14);
- the Python version (same NumPy on 3.13 and 3.14);
- the SIMD instruction set: NumPy's AVX2 and FMA3 code paths are switched off with NPY_DISABLE_CPU_FEATURES, which
  imitates running the same code on a CPU without them. NumPy 2.1 accepts the individual features ("AVX2 FMA3");
  NumPy 2.5 only accepts the feature group that contains them ("X86_V3");
- the operating system: Linux x86-64 in a Docker container on the same CPU, which changes the C library and its
  maths functions but not the hardware;
- the CPU architecture: Linux on 64-bit ARM, emulated by QEMU inside Docker. The emulator reproduces the ARM
  instruction set, including its floating-point semantics, but not the speed; it is the closest available stand-in for
  ARM hardware such as the Apple Silicon CI runners (which run macOS, not Linux).

Each environment is created on the fly by uv, with exactly pinned NumPy versions. The Linux environments use the
official uv image named in DOCKER_IMAGE; its exact digest is recorded in the metadata.

Run from this directory with (Docker must be running):

    uv run --locked --script E02.2-fp-reproducibility.py

Results are written to results/. The raw arrays are kept in a temporary directory only (they are tens of megabytes).
"""

import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RESULTS = HERE / "results"
WORKLOAD = "E02.2-workload.py"
DOCKER_IMAGE = "ghcr.io/astral-sh/uv:python3.14-bookworm-slim"

## (platform, Python version, NumPy version, value of NPY_DISABLE_CPU_FEATURES or None). The platform is "macos" for
## the development machine itself, or a Docker platform string.
type Environment = tuple[str, str, str, str | None]

REFERENCE: Environment = ("macos", "3.14", "2.5.3", None)
ENVIRONMENTS: list[Environment] = [
    ("macos", "3.13", "2.1.3", None),
    ("macos", "3.13", "2.1.3", "AVX2 FMA3"),
    ("macos", "3.13", "2.2.6", None),
    ("macos", "3.13", "2.3.5", None),
    ("macos", "3.13", "2.4.6", None),
    ("macos", "3.13", "2.5.3", None),
    ("macos", "3.14", "2.3.5", None),
    ("macos", "3.14", "2.4.6", None),
    REFERENCE,
    ("macos", "3.14", "2.5.3", "X86_V3"),
    ("linux/amd64", "3.13", "2.1.3", None),
    ("linux/amd64", "3.14", "2.5.3", None),
    ("linux/arm64", "3.14", "2.5.3", None),
]

PLATFORM_NAMES = {"macos": "macOS x86-64", "linux/amd64": "Linux x86-64", "linux/arm64": "Linux ARM64 (emulated)"}


def label(env: Environment) -> str:
    system, python, numpy, disabled = env
    return f"{PLATFORM_NAMES[system]}, Python {python}, NumPy {numpy}" + (f", {disabled} off" if disabled else "")


def run(env: Environment, out_dir: Path, name: str) -> dict[str, object]:
    system, python, numpy, disabled = env
    uv_run = ["uv", "run", "--quiet", "--no-project", "--isolated", "--python", python, "--with", f"numpy=={numpy}"]
    environ = dict(os.environ)
    if system == "macos":
        if disabled:
            environ["NPY_DISABLE_CPU_FEATURES"] = disabled
        command = [*uv_run, str(HERE / WORKLOAD), str(out_dir / name)]
    else:
        command = [
            "docker", "run", "--rm", "--platform", system,
            "-v", f"{HERE}:/work:ro", "-v", f"{out_dir}:/out", "-w", "/work",
            *(["-e", f"NPY_DISABLE_CPU_FEATURES={disabled}"] if disabled else []),
            DOCKER_IMAGE, *uv_run, WORKLOAD, f"/out/{name}",
        ]
    result = subprocess.run(command, capture_output=True, text=True, env=environ, check=True)
    return json.loads(result.stdout.strip().splitlines()[-1])


def max_ulps(a: np.ndarray, b: np.ndarray) -> float:
    """Largest difference between two arrays, in units of the last place of the reference value."""
    return float(np.max(np.abs(a - b) / np.spacing(np.abs(b))))


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    subprocess.run(["docker", "pull", "--quiet", DOCKER_IMAGE], check=True, capture_output=True)
    digest = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", DOCKER_IMAGE],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        files, info = {}, {}
        for env in ENVIRONMENTS:
            name = f"{len(files)}.npz"
            info[env] = run(env, Path(tmp), name)
            files[env] = Path(tmp) / name
            print(f"done: {label(env)} -> {info[env]}")
        reference = dict(np.load(files[REFERENCE]))
        table = {}
        for env in ENVIRONMENTS:
            data = dict(np.load(files[env]))
            row = {}
            for key, ref in reference.items():
                if np.array_equal(data[key].view(np.int64), ref.view(np.int64)):
                    row[key] = "identical"
                else:
                    differing = int(np.count_nonzero(data[key] != ref))
                    row[key] = f"{differing}/{ref.size} differ, ≤ {max_ulps(data[key], ref):.0f} ulp"
            table[env] = row

    names = list(reference)
    md = [
        "# E02.2: bit-for-bit reproducibility across environments",
        "",
        f"Host: {platform.platform()}, {platform.machine()}. Linux environments: Docker image {digest}. "
        f"Reference: {label(REFERENCE)}. Every entry compares that environment's result with the reference bit for "
        "bit; where they differ, the number of differing values and the largest difference in units of the last "
        "place (ulp) are given.",
        "",
        "| Environment | SIMD active | " + " | ".join(names) + " |",
        "|" + "---|" * (len(names) + 2),
    ]
    for env in ENVIRONMENTS:
        simd = ", ".join(info[env]["simd"]) or "baseline only"
        md.append(f"| {label(env)} | {simd} | " + " | ".join(table[env][n] for n in names) + " |")
    (RESULTS / "E02.2-fp-reproducibility.md").write_text("\n".join(md) + "\n")
    (RESULTS / "E02.2-metadata.json").write_text(
        json.dumps(
            {label(env): info[env] for env in ENVIRONMENTS} | {"host": platform.platform(), "docker_image": digest},
            indent=2,
        )
        + "\n"
    )
    print("\n".join(md))


if __name__ == "__main__":
    main()
