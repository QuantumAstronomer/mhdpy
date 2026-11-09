# pyright: strict
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""B1E1: which planted violations of the rule of B1 Import Linter and a test of its own report."""

import ast
import csv
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import sysconfig
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results"
RAW = RESULTS / "raw"
PYTHONS = ["3.13", "3.14", "3.14t"]
STRATA = ["infrastructure", "mesh", "core", "physics", "driver"]  ## from the bottom up

## the clean package, by path from the root of a variant
CLEAN: dict[str, str] = {
    "src/toy/__init__.py": '"""A toy package in the strata of B1."""\n',
    "src/toy/infrastructure/__init__.py": "",
    "src/toy/infrastructure/units.py": "def unit() -> float:\n    return 1.0\n",
    "src/toy/infrastructure/params.py": "import toy.infrastructure.units\n",
    "src/toy/mesh/__init__.py": "",
    "src/toy/mesh/grid.py": "import toy.infrastructure.units\n",
    "src/toy/mesh/state.py": "import toy.mesh.grid\n",
    "src/toy/core/__init__.py": "",
    "src/toy/core/eos.py": "import toy.mesh.state\n",
    "src/toy/core/riemann.py": "import toy.core.eos\n",
    "src/toy/core/a/__init__.py": "",
    "src/toy/core/a/x.py": "import toy.core.b.y\n",
    "src/toy/core/a/w.py": "",
    "src/toy/core/b/__init__.py": "",
    "src/toy/core/b/y.py": "",
    "src/toy/core/b/z.py": "",
    "src/toy/physics/__init__.py": "",
    "src/toy/physics/cooling.py": "import toy.core.eos\n",
    "src/toy/physics/conduction.py": "import toy.physics.cooling\n",
    "src/toy/driver/__init__.py": "",
    "src/toy/driver/run.py": "import toy.core.riemann\nimport toy.physics.conduction\n",
    "src/toy/driver/outputs.py": "import toy.driver.run\n",
    "tests/__init__.py": "",
    "tests/infrastructure/__init__.py": "",
    "tests/infrastructure/test_units.py": "import toy.infrastructure.units\n",
    "tests/mesh/__init__.py": "",
    "tests/mesh/test_grid.py": "import toy.mesh.grid\n",
    "tests/core/__init__.py": "",
    "tests/core/test_eos.py": "import toy.core.eos\n",
    "tests/physics/__init__.py": "",
    "tests/physics/test_cooling.py": "import toy.physics.cooling\n",
    "tests/driver/__init__.py": "",
    "tests/driver/test_run.py": "import toy.driver.run\n",
}

## each variant: the file changed, the text appended to it, and the names that a report must mention
VARIANTS: dict[str, tuple[str, str, list[str], str]] = {
    "V0": ("", "", [], "none"),
    "V1": ("src/toy/mesh/grid.py", "import toy.driver.run\n", ["toy.mesh.grid", "toy.driver"], "B1D2"),
    "V2": ("src/toy/core/riemann.py", "from ..driver import run\n", ["toy.core.riemann", "toy.driver"], "B1D2"),
    "V3": ("src/toy/mesh/grid.py", "\n\ndef late() -> None:\n    import toy.driver.run\n",
           ["toy.mesh.grid", "toy.driver"], "B1D2"),
    "V4": ("src/toy/mesh/grid.py", "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    import toy.driver.run\n",
           ["toy.mesh.grid", "toy.driver"], "B1D2"),
    "V5": ("src/toy/core/eos.py", "import toy.core.riemann\n", ["toy.core.eos", "toy.core.riemann"], "B1D3"),
    "V6": ("src/toy/core/b/z.py", "import toy.core.a.w\n", ["toy.core.a", "toy.core.b"], "B1D3"),
    "V7": ("src/toy/infrastructure/units.py", "\n\ndef late() -> None:\n    import toy.infrastructure.params\n",
           ["toy.infrastructure.units", "toy.infrastructure.params"], "B1D3"),
    "V8": ("tests/core/test_eos.py", "import toy.driver.run\n", ["tests.core.test_eos", "toy.driver"], "B1D4"),
    "V9": ("src/toy/__init__.py", "import toy.driver\n", ["toy -> toy.driver"], "B1D2"),
    "V10": ("src/toy/mesh/grid.py", "import importlib\n\n\ndef late() -> None:\n    importlib.import_module('toy.driver.run')\n",
            ["toy.mesh.grid", "toy.driver"], "B1D2"),
}

## the contracts of Import Linter: the strata in order, no cycles below each, the top package, the tests
CONFIG = """[importlinter]
root_packages =
    toy
    tests

[importlinter:contract:strata]
name = The strata import only those below them
type = layers
layers =
    toy.driver
    toy.physics
    toy.core
    toy.mesh
    toy.infrastructure

[importlinter:contract:cycles]
name = The modules of a stratum form no cycle
type = acyclic_siblings
ancestors =
    toy.infrastructure
    toy.mesh
    toy.core
    toy.physics
    toy.driver

[importlinter:contract:top]
name = The top package imports no stratum
type = forbidden
source_modules =
    toy
forbidden_modules =
    toy.infrastructure
    toy.mesh
    toy.core
    toy.physics
    toy.driver
as_packages = False
"""


def tests_contracts() -> str:
    """Return one forbidden contract for each folder of tests below the driver."""
    text = ""
    for i, stratum in enumerate(STRATA[:-1]):
        above = "\n".join(f"    toy.{s}" for s in STRATA[i + 1:])
        text += (f"\n[importlinter:contract:tests-{stratum}]\nname = The tests of {stratum} import no stratum above it\n"
                 f"type = forbidden\nsource_modules =\n    tests.{stratum}\nforbidden_modules =\n{above}\n")
    return text


def write_variant(name: str) -> Path:
    """Write the clean package with the change of one variant, and the configuration of Import Linter."""
    root = RAW / "variants" / name
    shutil.rmtree(root, ignore_errors=True)
    path, extra, _, _ = VARIANTS[name]
    for relative, text in CLEAN.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + (extra if relative == path else ""))
    (root / ".importlinter").write_text(CONFIG + tests_contracts())
    return root


## ---- the test of its own: every function whose name begins with own_ ----

def own_modules(root: Path) -> dict[str, Path]:
    """Return every module of the package and of its tests by its dotted name."""
    modules: dict[str, Path] = {}
    for base, top in ((root / "src", "toy"), (root, "tests")):
        for path in (base / top).rglob("*.py"):
            parts = path.relative_to(base).with_suffix("").parts
            modules[".".join(parts[:-1] if parts[-1] == "__init__" else parts)] = path
    return modules


def own_imports(name: str, path: Path, known: set[str]) -> list[tuple[str, bool]]:
    """Return what a module imports, each with whether the import runs when the module is loaded."""
    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
    found: list[tuple[str, bool]] = []

    def visit(node: ast.AST, loaded: bool) -> None:
        for child in ast.iter_child_nodes(node):
            inner = loaded and not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
            if isinstance(child, ast.Import):
                found.extend((alias.name, inner) for alias in child.names)
            elif isinstance(child, ast.ImportFrom):
                base = child.module or ""
                if child.level:
                    stem = package.split(".")[: package.count(".") + 2 - child.level]
                    base = ".".join(stem + ([child.module] if child.module else []))
                for alias in child.names:
                    full = f"{base}.{alias.name}"
                    found.append((full if full in known else base, inner))
            visit(child, inner)

    visit(ast.parse(path.read_text()), True)
    return found


def own_stratum(name: str) -> int | None:
    """Return the index of the stratum of a module of the package or of its tests, or None above them."""
    parts = name.split(".")
    return STRATA.index(parts[1]) if len(parts) > 1 and parts[1] in STRATA else None


def own_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Return one simple cycle for each set of nodes that a path leads round."""
    cycles: list[list[str]] = []
    seen: set[frozenset[str]] = set()
    for start in sorted(graph):
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for following in sorted(graph.get(node, set())):
                if following == start and frozenset(path) not in seen:
                    seen.add(frozenset(path))
                    cycles.append(path + [start])
                elif following not in path:
                    stack.append((following, path + [following]))
    return cycles


def own_check(root: Path) -> list[str]:
    """Return the violations of the rule of B1 in a package and its tests."""
    modules = own_modules(root)
    edges = {name: own_imports(name, path, set(modules)) for name, path in modules.items()}
    violations: list[str] = []
    for name, imports in edges.items():
        here = own_stratum(name)
        for target, loaded in imports:
            there = own_stratum(target) if target.startswith("toy.") else None
            if there is not None and name == "toy" and loaded:
                violations.append(f"{name} -> {target}: the top package imports a stratum when it is loaded")
            elif there is not None and here is not None and there > here:
                violations.append(f"{name} -> {target}: an import from a stratum above")
    ## the siblings below each package of a stratum, with the imports of their descendants
    for parent in sorted({n.rpartition(".")[0] for n in edges if n.count(".") >= 2 and n.startswith("toy.")}):
        depth = parent.count(".") + 2
        graph: dict[str, set[str]] = {}
        for name, imports in edges.items():
            if not name.startswith(parent + "."):
                continue
            source = ".".join(name.split(".")[:depth])
            for target, _ in imports:
                sink = ".".join(target.split(".")[:depth])
                if target.startswith(parent + ".") and sink != source:
                    graph.setdefault(source, set()).add(sink)
        violations += [f"cycle in {parent}: {' -> '.join(cycle)}" for cycle in own_cycles(graph)]
    return violations


## ---- the experiment ----

def own_lines() -> int:
    """Count the lines of the test of its own without blank lines, comments and docstrings."""
    tree = ast.parse(Path(__file__).read_text())
    lines = Path(__file__).read_text().splitlines()
    count = 0
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("own_"):
            skipped: set[int] = set()
            for inner in ast.walk(node):
                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)) and inner.body:
                    first = inner.body[0]
                    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                        skipped.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
            for number in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                text = lines[number - 1].strip()
                if text and not text.startswith("#") and number not in skipped:
                    count += 1
    return count


def mentions(output: str, name: str) -> bool:
    """Tell whether a report names a module in full, or by its parent and its name relative to it, as `.b`."""
    parent, _, last = name.rpartition(".")
    return name in output or (parent in output and re.search(rf"(?<![\w.])\.{last}\b", output) is not None)


def run(command: list[str], root: Path) -> tuple[int, str]:
    """Run a command in the root of a variant, with the package and its tests on the path of Python."""
    env = os.environ | {"PYTHONPATH": f"{root / 'src'}{os.pathsep}{root}"}
    done = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def linter(python: str) -> list[str]:
    """Return the command that runs Import Linter under a version of Python, from wheels alone."""
    return ["uvx", "--no-build", "--python", python, "--from", "import-linter", "lint-imports", "--no-cache"]


def own(python: str, root: Path) -> list[str]:
    """Return the command that runs the test of its own under a version of Python."""
    return ["uv", "run", "--quiet", "--python", python, str(Path(__file__).resolve()), "--own-check", str(root)]


def installs() -> list[dict[str, str]]:
    """Record for each version of Python whether Import Linter installs from wheels alone, and its versions."""
    probe = ("import importlib.metadata as m, json, sys, sysconfig; print(json.dumps({'python': sys.version.split()[0], "
             "'free_threaded': str(bool(sysconfig.get_config_var('Py_GIL_DISABLED'))), "
             "'import_linter': m.version('import-linter'), 'grimp': m.version('grimp')}))")
    rows: list[dict[str, str]] = []
    for python in PYTHONS:
        done = subprocess.run(["uvx", "--no-build", "--python", python, "--from", "import-linter", "python", "-c", probe],
                              capture_output=True, text=True)
        row = {"requested": python, "from_wheels": str(done.returncode == 0)}
        if done.returncode == 0:
            row |= json.loads(done.stdout.strip().splitlines()[-1])
        rows.append(row)
    return rows


def timed(command: list[str], root: Path) -> tuple[float, float, float]:
    """Return the median, minimum and maximum of five runs of a command, after one run to warm up."""
    run(command, root)
    times: list[float] = []
    for _ in range(5):
        start = time.perf_counter()
        run(command, root)
        times.append(time.perf_counter() - start)
    return statistics.median(times), min(times), max(times)


def environment() -> dict[str, str]:
    """Return what produced the results: date, Python and its build, uv, machine and commit."""
    ## the commit of the repository, marked when the working tree differs from it
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout
    ## the processor by name, which platform.processor() does not give on macOS
    cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    uv = subprocess.run(["uv", "--version"], capture_output=True, text=True).stdout.strip()
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "free_threaded": str(bool(sysconfig.get_config_var("Py_GIL_DISABLED"))),
        "uv": uv,
        "machine": f"{platform.system()} {platform.release()}, {platform.machine()}, {cpu}",
        "commit": commit + (" (modified)" if dirty else ""),
    }


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--own-check":
        violations = own_check(Path(sys.argv[2]))
        print("\n".join(violations))
        sys.exit(1 if violations else 0)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "outputs").mkdir(exist_ok=True)
    roots = {name: write_variant(name) for name in VARIANTS}
    rows: list[dict[str, str]] = []
    for check in ("import-linter", "own"):
        for python in PYTHONS:
            for name, root in roots.items():
                command = linter(python) if check == "import-linter" else own(python, root)
                code, output = run(command, root)
                (RAW / "outputs" / f"{check}-{python}-{name}.txt").write_text(output)
                marks = VARIANTS[name][2]
                reported = code != 0 and all(mentions(output, mark) for mark in marks)
                rows.append({"check": check, "python": python, "variant": name, "rule": VARIANTS[name][3],
                             "exit_code": str(code), "reported": str(reported) if name != "V0" else "",
                             "passed": str(code == 0) if name == "V0" else ""})
    with open(RESULTS / "reports.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with open(RESULTS / "installs.csv", "w", newline="") as file:
        records = installs()
        writer = csv.DictWriter(file, fieldnames=sorted({key for record in records for key in record}))
        writer.writeheader()
        writer.writerows(records)
    with open(RESULTS / "timings.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["check", "python", "median_s", "min_s", "max_s"])
        for check, command in (("import-linter", linter("3.14")), ("own", own("3.14", roots["V0"]))):
            writer.writerow([check, "3.14", *(f"{value:.3f}" for value in timed(command, roots["V0"]))])
    (RESULTS / "own_check.json").write_text(json.dumps({"lines": own_lines()}, indent=2) + "\n")
    (RESULTS / "environment.json").write_text(json.dumps(environment(), indent=2) + "\n")
    print((RESULTS / "reports.csv").read_text())


if __name__ == "__main__":
    main()
