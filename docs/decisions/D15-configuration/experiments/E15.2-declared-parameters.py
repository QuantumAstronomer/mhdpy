# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Experiment E15.2: can declared parameters catch a user's mistakes before a run starts, with the standard library alone?

Modules declare their parameters at set-up (D12.1): name, type, default, an optional check, and whether the parameter
may change on restart (D14.7). This experiment is a prototype of the layer that resolves the values a run uses, in
order of increasing precedence:

1. the declared defaults;
2. a parameter file (TOML, E15.1);
3. overrides given on the command line as ``section.key=value`` (the value read as TOML, so ``hydro.cfl=0.3`` is a
   float and ``output.variables=["rho"]`` a list) or as a dictionary from Python;
4. on restart: the values recorded in the restart file take the place of the defaults; a parameter file and overrides
   may then change only the parameters declared changeable (a value equal to the recorded one is no change).

It runs a set of scenarios, correct and mistaken, and records for each whether the run would start and the message
the user would see. Every mistake must be reported before the run starts, with the parameter, the problem and, for
misspelt names, a suggestion. The resolved parameters are also written to JSON (the record each output carries, D14)
and read back, which must be exact.

Run from this directory with:

    uv run --locked --script E15.2-declared-parameters.py

Results are written to results/.
"""

import difflib
import json
import platform
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).parent
RESULTS = HERE / "results"


class ParameterError(ValueError):
    pass


@dataclass(frozen=True)
class Parameter:
    """A declared parameter: what a module states about it at set-up."""

    name: str
    kind: type
    default: Any
    check: Callable[[Any], bool] | None = None
    requirement: str = ""
    on_restart: str = "fixed"  # or "changeable"
    doc: str = ""


DECLARED = [
    Parameter("mesh.nx1", int, 256, lambda v: v > 0, "positive", doc="cells in x1"),
    Parameter("mesh.nx2", int, 64, lambda v: v > 0, "positive", doc="cells in x2"),
    Parameter("mesh.block", int, 50, lambda v: v > 0, "positive", on_restart="changeable", doc="cells per block side"),
    Parameter("hydro.gamma", float, 5 / 3, lambda v: v > 1, "greater than 1", doc="adiabatic index"),
    Parameter("hydro.cfl", float, 0.4, lambda v: 0 < v <= 1, "in (0, 1]", on_restart="changeable", doc="CFL number"),
    Parameter("time.tlim", float, 1.0, lambda v: v > 0, "positive", on_restart="changeable", doc="end time"),
    Parameter("cooling.enabled", bool, True, doc="radiative cooling on or off"),
    Parameter("output.variables", list, ["rho", "press"], lambda v: all(isinstance(x, str) for x in v),
              "a list of names", on_restart="changeable", doc="variables in snapshots"),
]
BY_NAME = {p.name: p for p in DECLARED}


def flatten(tree: dict, prefix: str = "") -> dict:
    out = {}
    for key, value in tree.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, f"{name}."))
        else:
            out[name] = value
    return out


def parse_override(text: str) -> tuple[str, Any]:
    """``section.key=value``, the value read as TOML; a bare word is taken as a string."""
    name, _, raw = text.partition("=")
    try:
        value = tomllib.loads(f"v = {raw}")["v"]
    except tomllib.TOMLDecodeError:
        value = raw
    return name.strip(), value


def validate(name: str, value: Any, source: str) -> Any:
    if name not in BY_NAME:
        close = difflib.get_close_matches(name, BY_NAME, n=1)
        hint = f"; did you mean '{close[0]}'?" if close else ""
        raise ParameterError(f"{source}: unknown parameter '{name}'{hint}")
    p = BY_NAME[name]
    if p.kind is float and type(value) is int:
        value = float(value)
    if type(value) is not p.kind:
        raise ParameterError(f"{source}: '{name}' must be {p.kind.__name__}, got {type(value).__name__} {value!r}")
    if p.check is not None and not p.check(value):
        raise ParameterError(f"{source}: '{name}' must be {p.requirement}, got {value!r}")
    return value


def resolve(file_text: str | None = None, overrides: list[str] = (), restart: dict | None = None) -> dict:
    """The parameters of a run: defaults (or a restart file's record), then the parameter file, then overrides."""
    values = dict(restart) if restart is not None else {p.name: p.default for p in DECLARED}
    changes = []
    if file_text is not None:
        changes += [(name, value, "parameter file") for name, value in flatten(tomllib.loads(file_text)).items()]
    changes += [(*parse_override(text), "override") for text in overrides]
    for name, value, source in changes:
        value = validate(name, value, source)
        if restart is not None and BY_NAME[name].on_restart == "fixed" and value != restart[name]:
            raise ParameterError(f"{source}: '{name}' cannot change on restart (it is fixed by the restart file)")
        values[name] = value
    return values


THESIS = """\
[mesh]
nx1 = 4000
nx2 = 1000

[hydro]
cfl = 0.4

[time]
tlim = 1e5
"""

SCENARIOS = [
    ("a correct parameter file", dict(file_text=THESIS)),
    ("a correct file with overrides", dict(file_text=THESIS, overrides=["hydro.cfl=0.3", 'output.variables=["rho"]'])),
    ("a misspelt name in the file", dict(file_text=THESIS.replace("cfl", "cfll"))),
    ("a misspelt section in an override", dict(file_text=THESIS, overrides=["hdyro.cfl=0.3"])),
    ("a float where an integer is required", dict(file_text=THESIS.replace("nx1 = 4000", "nx1 = 4000.0"))),
    ("an integer where a float is required", dict(file_text=THESIS.replace("cfl = 0.4", "cfl = 1"))),
    ("a value out of range", dict(file_text=THESIS, overrides=["hydro.cfl=1.5"])),
    ("a quoted number", dict(file_text=THESIS.replace("cfl = 0.4", 'cfl = "0.4"'))),
    ("a bare word for a boolean", dict(file_text=THESIS, overrides=["cooling.enabled=no"])),
    ("restart with a later end time", dict(overrides=["time.tlim=2e5"], restart="thesis")),
    ("restart with another block size", dict(overrides=["mesh.block=25"], restart="thesis")),
    ("restart changing the mesh", dict(overrides=["mesh.nx1=8000"], restart="thesis")),
    ("restart with the original parameter file and a later end time",
     dict(file_text=THESIS.replace("tlim = 1e5", "tlim = 2e5"), restart="thesis")),
    ("restart with a parameter file that changes the mesh",
     dict(file_text=THESIS.replace("nx2 = 1000", "nx2 = 2000"), restart="thesis")),
]


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    recorded = resolve(THESIS)
    record = json.dumps(recorded)
    exact = json.loads(record) == recorded
    results = {"python": sys.version, "platform": platform.platform(), "record_round_trip_exact": exact,
               "scenarios": {}}
    for title, kwargs in SCENARIOS:
        if kwargs.get("restart") == "thesis":
            kwargs = {**kwargs, "restart": json.loads(record)}
        try:
            values = resolve(**kwargs)
            changed = {k: v for k, v in values.items() if v != recorded.get(k)}
            outcome = {"starts": True, "message": f"resolved; differs from the thesis record in {changed}"
                       if changed else "resolved"}
        except ParameterError as error:
            outcome = {"starts": False, "message": str(error)}
        results["scenarios"][title] = outcome
        print(f"{title}: {outcome}", flush=True)
    md = ["# E15.2: declared parameters catch mistakes before the run", "",
          f"Python {platform.python_version()}, standard library only (dataclasses, tomllib, difflib, json). "
          f"The record of resolved parameters, written to JSON and read back: "
          f"{'exact' if exact else 'NOT exact'}.", "",
          "| Scenario | Run starts | Message |", "|---|---|---|"]
    md += [f"| {title} | {'yes' if o['starts'] else 'no'} | {o['message']} |" for title, o in results["scenarios"].items()]
    (RESULTS / "E15.2-declared-parameters.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E15.2-declared-parameters.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
