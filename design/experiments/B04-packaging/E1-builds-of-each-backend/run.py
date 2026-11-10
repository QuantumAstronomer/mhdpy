# pyright: strict
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""B4E1: whether setuptools, meson-python and scikit-build-core build a kernel in the pure mode of Cython into a wheel
and an editable installation on Python 3.14, 3.14t, 3.15 and 3.15t, and what a change to a kernel takes.

Run without arguments, it builds every case in results/raw/ and gathers the results in results/.
Run with a backend and a version, as `uv run run.py meson-python 3.14`, it builds that case alone, as a trial.
"""

import csv
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tarfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
RESULTS = HERE / "results"
RAW = RESULTS / "raw"
BACKENDS = ["setuptools", "meson-python", "scikit-build-core"]
PYTHONS = ["3.14", "3.14t", "3.15", "3.15t"]
## the build tools that an editable installation without build isolation needs beside the package
TOOLS = {"setuptools": ["setuptools>=77", "cython>=3.1"],
         "meson-python": ["meson-python>=0.18", "meson>=1.5", "ninja", "cython>=3.1"],
         "scikit-build-core": ["scikit-build-core>=1.1", "cython>=3.1", "cython-cmake>=0.3", "cmake", "ninja"]}
REPORTED = ["setuptools", "cython", "meson-python", "meson", "ninja", "scikit-build-core", "cython-cmake", "cmake",
            "numpy", "import-linter", "grimp"]
UPDATES = 9e10  ## the cell updates of the production run, topic 42, §4
THREADS = {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                  "VECLIB_MAXIMUM_THREADS")}
GIT = ["git", "-c", "user.name=B4E1", "-c", "user.email=b4e1@example.invalid"]

## the package of B4E1 beside its two kernels, by path from the root of a case
PROJECT: dict[str, str] = {
    "src/mhdpy/__init__.py": '"""The package of B4E1, in the layout of B1D4."""\n',
    "src/mhdpy/infrastructure/__init__.py": "",
    "src/mhdpy/infrastructure/units.py": '"""A module of the infrastructure, which the core imports."""\n\nGRAM = 1.0\n',
    "src/mhdpy/core/__init__.py": "",
    "src/mhdpy/core/eos.py": ('"""A module of the core that imports one of the infrastructure."""\n\n'
                              "import mhdpy.infrastructure.units\n\nMASS = mhdpy.infrastructure.units.GRAM\n"),
    ".gitignore": "build/\ndist/\n*.so\n*.c\n",
}
METADATA = ('[project]\nname = "mhdpy"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n'
            'dependencies = ["numpy>=2.1"]\n\n')
LINTER = ('\n[tool.importlinter]\nroot_package = "mhdpy"\n\n[[tool.importlinter.contracts]]\n'
          'name = "The core above the infrastructure"\ntype = "layers"\nlayers = ["mhdpy.core", "mhdpy.infrastructure"]\n')
## the two changes of steps 4 and 5: the file, the text replaced, its replacement and the print that shows it
CHANGES = [("py", "src/mhdpy/core/loops.py", "    return 1\n", "    return 2\n", "2.0"),
           ("pxd", "src/mhdpy/core/loops.pxd", "cpdef double marker()", "cpdef long marker()", "2")]


def run(command: list[str], cwd: Path, log: Path, env: dict[str, str] | None = None) -> tuple[int, float, str]:
    """Run a command, append its output to the log, and return its code, its seconds and its output."""
    start = time.perf_counter()
    done = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    seconds = time.perf_counter() - start
    output = done.stdout + done.stderr
    with open(log, "a") as file:
        file.write(f"$ {' '.join(command)}\n[{done.returncode}, {seconds:.2f} s]\n{output}\n")
    return done.returncode, seconds, done.stdout


def last_json(stdout: str) -> dict[str, Any] | None:
    """Return the object of JSON on the last line of an output, or None."""
    lines = stdout.strip().splitlines()
    try:
        value: dict[str, Any] | None = json.loads(lines[-1]) if lines else None
        return value
    except json.JSONDecodeError:
        return None


def make_project(backend: str, folder: Path, log: Path) -> Path:
    """Write the package of the case with the configuration of its backend, as a repository of git."""
    project = folder / "project"
    for name, text in PROJECT.items():
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        (project / name).write_text(text)
    for kernel in ("loops", "loops2"):
        for suffix in (".py", ".pxd"):
            shutil.copy(HERE / f"loops{suffix}", project / "src/mhdpy/core" / f"{kernel}{suffix}")
    for path in (HERE / "configs" / backend).iterdir():
        if path.name == "pyproject.toml":
            (project / "pyproject.toml").write_text(METADATA + path.read_text() + LINTER)
        else:
            shutil.copy(path, project / path.name)
    run(["git", "init", "-q"], project, log)
    run(GIT + ["add", "-A"], project, log)
    run(GIT + ["commit", "-q", "-m", "The package of B4E1"], project, log)
    return project


def contents(dist: Path) -> dict[str, list[str]]:
    """Return the files of the source distribution and of the wheel in a folder."""
    found: dict[str, list[str]] = {}
    for wheel in dist.glob("*.whl"):
        with zipfile.ZipFile(wheel) as archive:
            found["wheel"] = sorted(n for n in archive.namelist() if ".dist-info/" not in n)
    for sdist in dist.glob("*.tar.gz"):
        with tarfile.open(sdist) as archive:
            found["sdist"] = sorted(m.name.split("/", 1)[1] for m in archive.getmembers() if m.isfile())
    return found


def activated(env: Path) -> dict[str, str]:
    """Return the variables of a shell in which the environment is activated, as `uv run` or `activate` set them."""
    return os.environ | {"VIRTUAL_ENV": str(env), "PATH": f"{env / 'bin'}:{os.environ['PATH']}"}


def marker(env: Path, worker: Path, log: Path) -> tuple[dict[str, Any] | None, float]:
    """Run the worker that reports marker() in a new process, and return its report and seconds."""
    _, seconds, stdout = run([str(env / "bin/python"), "worker.py", "marker"], worker, log, activated(env))
    return last_json(stdout), seconds


def case(backend: str, python: str) -> dict[str, Any]:
    """Build one backend on one version of Python through the six steps of the method."""
    folder = RAW / f"{backend}-{python}"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    log = folder / "log.txt"
    project = make_project(backend, folder, log)
    worker = folder / "worker"
    worker.mkdir()
    for name in ("worker.py", "vectorised.py"):
        shutil.copy(HERE / name, worker)
    result: dict[str, Any] = {"backend": backend, "python": python}
    ## 1. the source distribution and, from it, the wheel
    code, seconds, _ = run(["uv", "build", "--python", python, "--out-dir", str(folder / "dist"), str(project)],
                           folder, log)
    wheels = list((folder / "dist").glob("*.whl"))
    result["build"] = {"code": code, "seconds": seconds, "contents": contents(folder / "dist"),
                       "wheel": wheels[0].name if wheels else ""}
    ## 2. the wheel in an environment of its own, checked and timed
    if wheels:
        env = folder / "wheel-env"
        run(["uv", "venv", "-q", "--python", python, str(env)], folder, log)
        run(["uv", "pip", "install", "-q", "--python", str(env / "bin/python"), str(wheels[0]), "numpy"], folder, log)
        _, _, stdout = run([str(env / "bin/python"), "worker.py", "check"], worker, log, activated(env) | THREADS)
        result["check"] = last_json(stdout)
    ## 3. the editable installation, without build isolation, beside the build tools
    env = folder / "edit-env"
    run(["uv", "venv", "-q", "--python", python, str(env)], folder, log)
    run(["uv", "pip", "install", "-q", "--python", str(env / "bin/python"), "numpy", "import-linter",
         *TOOLS[backend]], folder, log)
    editable = ["uv", "pip", "install", "-q", "--python", str(env / "bin/python"), "--no-build-isolation", "-e",
                str(project)]
    code, seconds, _ = run(editable, folder, log)
    first, _ = marker(env, worker, log)
    result["editable"] = {"code": code, "seconds": seconds, "first": first}
    ## 4 and 5. a change to the module .py, then to its file .pxd
    changes: list[dict[str, Any]] = []
    for kind, name, old, new, expected in CHANGES:
        before, _ = marker(env, worker, log)
        path = project / name
        text = path.read_text()
        cut = text.rindex(old)
        path.write_text(text[:cut] + new + text[cut + len(old):])
        report, seconds = marker(env, worker, log)
        change: dict[str, Any] = {"change": kind, "expected": expected, "without_step": report, "seconds": seconds}
        if report is None or report["marker"] != expected:
            code, step_seconds, _ = run(editable + ["--reinstall-package", "mhdpy"], folder, log)
            report, seconds = marker(env, worker, log)
            change |= {"step": "new editable installation", "step_code": code, "step_seconds": step_seconds,
                       "after_step": report, "after_seconds": seconds}
        change["before"] = before
        changes.append(change)
    result["changes"] = changes
    ## 6. Import Linter on the editable installation
    code, _, stdout = run([str(env / "bin/lint-imports"), "--no-cache"], project, log, activated(env))
    result["linter"] = {"code": code, "report": stdout.strip().splitlines()[-6:]}
    _, _, listing = run(["uv", "pip", "list", "--python", str(env / "bin/python"), "--format", "json"], folder, log)
    versions: list[dict[str, str]] = json.loads(listing)
    result["versions"] = {p["name"]: p["version"] for p in versions if p["name"] in REPORTED}
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


## ---- the experiment ----

def lines(backend: str) -> dict[str, int]:
    """Count the lines of each file of configuration without blank lines, comments and docstrings."""
    counts: dict[str, int] = {}
    for path in sorted((HERE / "configs" / backend).iterdir()):
        kept = [line for line in path.read_text().splitlines()
                if line.strip() and not line.strip().startswith(("#", '"""'))]
        counts[path.name] = len(kept)
    counts["total"] = sum(counts.values())
    return counts


def environment(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Return what produced the results: date, Python, uv, machine, compiler, commit and the versions of the tools."""
    def output(command: list[str]) -> str:
        return subprocess.run(command, capture_output=True, text=True).stdout.strip()
    dirty = output(["git", "status", "--porcelain", "--untracked-files=no"])
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "uv": output(["uv", "--version"]),
        "machine": f"{platform.system()} {platform.release()}, {platform.machine()}, "
                   f"{output(['sysctl', '-n', 'machdep.cpu.brand_string'])}",
        "cores": "6 cores, 12 threads, 32 GB",
        "compiler": output(["clang", "--version"]).splitlines()[0],
        "commit": output(["git", "rev-parse", "--short", "HEAD"]) + (" (modified)" if dirty else ""),
        "pythons": {r["python"]: output([str(RAW / f"{r['backend']}-{r['python']}" / "edit-env/bin/python"),
                                         "-c", "import sys; print(sys.version.split()[0])"])
                    for r in results if r["backend"] == BACKENDS[0]},
        "tools": {f"{r['backend']} {r['python']}": r["versions"] for r in results},
    }


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    """Write rows of equal keys to a file of results."""
    with open(RESULTS / name, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def report(value: dict[str, Any] | None) -> dict[str, Any]:
    """Return a report of the worker, or an empty one where the worker gave none."""
    empty: dict[str, Any] = {}
    return value if value is not None else empty


def summarise(results: list[dict[str, Any]]) -> None:
    """Write the tables of results/ from the reports of the cases."""
    builds: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    linter: list[dict[str, Any]] = []
    for r in results:
        key = {"backend": r["backend"], "python": r["python"]}
        found = r["build"]["contents"]
        builds.append(key | {"sdist": str("sdist" in found), "wheel": r["build"]["wheel"],
                             "build_s": f"{r['build']['seconds']:.1f}", "editable": str(r["editable"]["code"] == 0),
                             "editable_s": f"{r['editable']['seconds']:.1f}",
                             "first_marker": report(r["editable"]["first"]).get("marker", "")})
        check = r.get("check")
        if check:
            times: list[float] = check["times"]
            median = statistics.median(times) if times else float("nan")
            checks.append(key | {"loaded": " ".join(Path(f).name for f in check["files"]),
                                 "agreement": " ".join(f"{a:.3g}" for a in check["agreement"]),
                                 "gil": str(check["gil"]), "median_s": f"{median:.4f}",
                                 "min_s": f"{min(times):.4f}" if times else "", "max_s": f"{max(times):.4f}" if times else "",
                                 "rate_per_s": f"{check['cells'] / median:.4g}",
                                 "hours": f"{UPDATES * median / check['cells'] / 3600:.3g}"})
        for c in r["changes"]:
            seen = c["without_step"] and c["without_step"]["marker"] == c["expected"]
            after = report(c.get("after_step") or c["without_step"])
            before = report(c["before"])
            changes.append(key | {
                "change": c["change"], "marker_before": before.get("marker", ""), "marker_after": after.get("marker", ""),
                "seen_without_step": str(bool(seen)), "step": c.get("step", "none"),
                "step_s": f"{c['step_seconds']:.1f}" if "step_seconds" in c else "",
                "process_s": f"{c['after_seconds'] if 'after_seconds' in c else c['seconds']:.1f}",
                "loops2_compiled_again": str(bool(after.get("mtimes")) and bool(before.get("mtimes"))
                                             and after["mtimes"][1] != before["mtimes"][1])})
        linter.append(key | {"passed": str(r["linter"]["code"] == 0), "report": " | ".join(r["linter"]["report"])})
    write_csv("builds.csv", builds)
    if checks:
        write_csv("checks.csv", checks)
    write_csv("changes.csv", changes)
    write_csv("linter.csv", linter)
    first = {b: next(r for r in results if r["backend"] == b)["build"]["contents"] for b in BACKENDS
             if any(r["backend"] == b for r in results)}
    (RESULTS / "contents.json").write_text(json.dumps(first, indent=2) + "\n")
    (RESULTS / "lines.json").write_text(json.dumps({b: lines(b) for b in BACKENDS}, indent=2) + "\n")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) == 3:
        result = case(sys.argv[1], sys.argv[2])
        print(json.dumps({k: result[k] for k in ("check", "editable", "changes", "linter") if k in result}, indent=1))
        return
    results: list[dict[str, Any]] = []
    for backend in BACKENDS:
        for python in PYTHONS:
            start = time.perf_counter()
            results.append(case(backend, python))
            print(f"{backend} {python} done in {time.perf_counter() - start:.0f} s", flush=True)
    summarise(results)
    (RESULTS / "environment.json").write_text(json.dumps(environment(results), indent=2) + "\n")
    for name in ("builds.csv", "checks.csv", "changes.csv", "linter.csv"):
        if (RESULTS / name).exists():
            print((RESULTS / name).read_text())


if __name__ == "__main__":
    main()
