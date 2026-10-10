# /// script
# requires-python = ">=3.13"
# dependencies = ["ruff", "numpydoc"]
# ///
"""Experiment E01.2: does the author's code style fit the standard tools?

Takes the style sample in ``E01.2-style-sample.py`` and determines:

1. its line-length profile;
2. what ``ruff format`` changes in it, for several candidate configurations
   (line length 88/100/120, quote style double/preserve), and which of the
   sample's characteristic style features survive formatting;
3. which lint rules (pycodestyle E/W, pydocstyle D with the NumPy convention)
   the sample triggers;
4. whether numpydoc, which Sphinx uses to render NumPy-style docstrings, can
   parse the sample's docstring, compared with the same content written in
   the standard NumPy section format.

Run from this directory with:

    uv run --script E01.2-style-formatting.py

Results are written to results/.
"""

import ast
import difflib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
import warnings
from collections import Counter
from pathlib import Path

from numpydoc.docscrape import NumpyDocString

HERE = Path(__file__).parent
SAMPLE = HERE / "E01.2-style-sample.py"
RESULTS = HERE / "results"

CONFIGS = {
    "88-double": ["line-length=88", "format.quote-style='double'"],
    "100-double": ["line-length=100", "format.quote-style='double'"],
    "120-double": ["line-length=120", "format.quote-style='double'"],
    "120-preserve": ["line-length=120", "format.quote-style='preserve'"],
}

## Characteristic features of the sample, as regular expressions on lines.
FEATURES = {
    "aligned '=' in assignments": re.compile(r"^\s*[\w.\[\]]+ {2,}= "),
    "spaces around keyword '='": re.compile(r"\(\w+ = "),
    "'##' comments": re.compile(r"^\s*## "),
    "'#' comments": re.compile(r"^\s*# "),
}
VISUAL_INDENT = "continuation aligned under '('"

## The sample's docstring content, rewritten in the standard NumPy format
## (sections underlined with dashes, "name : type"). Content is unchanged,
## except that "Returns: None" is dropped, as the convention prescribes for
## functions that return nothing.
STANDARD_DOCSTRING = '''
Parameters
----------
n_cells : int | Sequence[int] | NDArray[np.integer]
    Number of interior (non-ghost) cells per direction. A plain int
    (or 0-d numpy array) gives a 1-D grid; a sequence or 1-D numpy
    array of length 1, 2, or 3 sets ndim to its length. Must be >= 1
    in every direction, and must match the form (scalar or sequence)
    and length of bound_lower and bound_upper.
bound_lower : float | Sequence[float] | NDArray[np.integer | np.floating]
    Lower edge of the interior domain per direction, in coordinate
    space. Same form and length as n_cells.
bound_upper : float | Sequence[float] | NDArray[np.integer | np.floating]
    Upper edge of the interior domain per direction, in coordinate
    space. Same form and length as n_cells. Must be strictly greater
    than bound_lower in every direction.
n_ghost : int, default 2
    Number of ghost cells padding the interior on each side, shared by
    every direction. Must be >= 0.

Raises
------
TypeError
    If an argument has the wrong type: a string anywhere, a
    non-integer (or bool) n_cells or n_ghost, or a non-real (or
    bool) bound (R9.3).
ValueError
    If any argument violates a constraint listed under Parameters,
    or an array argument has more than one axis (R1.1). The message
    names the offending argument and, where relevant, the direction
    (R2.2 / R9.1).
'''


def ruff(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruff", *args], input=stdin, capture_output=True, text=True
    )


def config_args(config: list[str]) -> list[str]:
    return [arg for item in config for arg in ("--config", item)]


def line_profile(lines: list[str]) -> dict[str, int]:
    lengths = [len(line) for line in lines]
    return {
        "lines": len(lines),
        "max length": max(lengths),
        "> 88": sum(n > 88 for n in lengths),
        "> 100": sum(n > 100 for n in lengths),
        "> 120": sum(n > 120 for n in lengths),
    }


def visual_indents(lines: list[str]) -> int:
    """Count continuation lines indented to just after the previous line's last '('."""
    count = 0
    for previous, line in zip(lines, lines[1:]):
        stripped = line.lstrip()
        if "(" in previous and not previous.rstrip().endswith("(") and stripped:
            if len(line) - len(stripped) == previous.rindex("(") + 1:
                count += 1
    return count


def feature_counts(lines: list[str]) -> dict[str, int]:
    counts = {name: sum(bool(rx.search(line)) for line in lines) for name, rx in FEATURES.items()}
    counts[VISUAL_INDENT] = visual_indents(lines)
    return counts


def parse_docstring(text: str) -> dict[str, object]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        doc = NumpyDocString(text)
    return {
        "warnings": [str(w.message) for w in caught],
        "parameters": [(p.name, p.type) for p in doc["Parameters"]],
        "raises": [p.name if p.name else p.type for p in doc["Raises"]],
    }


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    source = SAMPLE.read_text()
    original = source.splitlines()
    md: list[str] = [
        "# E01.2: the author's style against ruff and numpydoc",
        "",
        f"ruff {importlib.metadata.version('ruff')}, numpydoc "
        f"{importlib.metadata.version('numpydoc')}, Python {platform.python_version()}, "
        f"{platform.platform()}.",
        "",
        "## 1. Line lengths of the sample",
        "",
        "| " + " | ".join(line_profile(original)) + " |",
        "|" + "---|" * len(line_profile(original)),
        "| " + " | ".join(str(v) for v in line_profile(original).values()) + " |",
        "",
        "## 2. What `ruff format` changes",
        "",
        "Lines of the sample that the formatter rewrites, and how many lines "
        "show each style feature before and after formatting. Full diffs: "
        "`results/E01.2-format-<config>.diff`.",
        "",
    ]

    before = feature_counts(original)
    names = list(before)
    header = "| Configuration | Lines changed | " + " | ".join(names) + " |"
    md += [header, "|" + "---|" * (2 + len(names))]
    md.append("| *original* | — | " + " | ".join(str(before[f]) for f in names) + " |")
    for name, config in CONFIGS.items():
        result = ruff("format", "--isolated", *config_args(config), "-", stdin=source)
        formatted = result.stdout.splitlines()
        diff = list(difflib.unified_diff(original, formatted, "original", f"formatted ({name})", lineterm=""))
        (RESULTS / f"E01.2-format-{name}.diff").write_text("\n".join(diff) + "\n")
        changed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
        after = feature_counts(formatted)
        md.append(f"| {name} | {changed} | " + " | ".join(str(after[f]) for f in names) + " |")

    md += [
        "",
        "## 3. Lint rules triggered (line length 120)",
        "",
        "`ruff check --preview --select E,W,D` with the NumPy docstring "
        "convention. Preview mode is needed for the pycodestyle whitespace rules.",
        "",
        "| Rule | Count | Message (first occurrence) |",
        "|---|---|---|",
    ]
    lint = ruff(
        "check", "--isolated", "--preview", "--select", "E,W,D",
        "--config", "line-length=120", "--config", "lint.pydocstyle.convention='numpy'",
        "--output-format", "json", "--exit-zero", str(SAMPLE),
    )
    findings = json.loads(lint.stdout)
    counts = Counter(f["code"] for f in findings)
    first = {}
    for f in findings:
        first.setdefault(f["code"], f["message"])
    for code, count in sorted(counts.items()):
        md.append(f"| {code} | {count} | {first[code]} |")

    md += [
        "",
        "## 4. numpydoc parsing of the docstring",
        "",
        "numpydoc is what Sphinx uses to render NumPy-style docstrings.",
        "",
    ]
    tree = ast.parse(source)
    init = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    for label, text in (("Sample format", ast.get_docstring(init) or ""),
                        ("Standard NumPy format", STANDARD_DOCSTRING)):
        parsed = parse_docstring(text)
        md += [f"**{label}**", ""]
        md.append(f"- Warnings: {parsed['warnings'] or 'none'}")
        md.append(f"- Parameters recognised (name, type): {parsed['parameters'] or 'none'}")
        md.append(f"- Exceptions recognised: {parsed['raises'] or 'none'}")
        md.append("")

    (RESULTS / "E01.2-style-formatting.md").write_text("\n".join(md) + "\n")
    (RESULTS / "E01.2-metadata.json").write_text(json.dumps({
        "python": sys.version,
        "platform": platform.platform(),
        "ruff": importlib.metadata.version("ruff"),
        "numpydoc": importlib.metadata.version("numpydoc"),
    }, indent=2) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
