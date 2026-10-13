# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml", "tomli-w"]
# ///
"""Experiment E15.1: do parameter files in common formats read back what their author meant?

The same set of parameters, a simplified version of the thesis run, is written by hand in five formats, the way a user
would naturally write them in each:

- **TOML,** read with the standard library (``tomllib``);
- **YAML,** read with PyYAML (``safe_load``), the most widely used reader;
- **INI,** read with the standard library (``configparser``), with and without inferring types from the text as Pyro
  does (int, else float, else string);
- **Athena++'s input format** (``<block>`` headers, ``key = value # comment``), read as strings with a parser of a few
  lines, as Athena++ does before converting a value at the point where the code asks for it;
- **JSON,** read with the standard library, for comparison (it has no comments).

Each file is read and every value is compared with what the author meant, in type and value. The parameters include
cases known to be delicate: an exponent without a decimal point (``1e5``), a float with all its digits (5/3), a
boolean switch, a string that looks like a boolean (the country code ``NO``), and a list. Each format is also written
back from the values read (the record of resolved parameters that every output carries, D14) and read again, to check
that the round trip is exact.

Run from this directory with:

    uv run --locked --script E15.1-parameter-formats.py

Results are written to results/.
"""

import configparser
import json
import platform
import sys
import tomllib
from pathlib import Path

import tomli_w
import yaml

HERE = Path(__file__).parent
RESULTS = HERE / "results"

INTENDED = {
    "mesh": {"nx1": 4000, "nx2": 1000, "x1max": 4.0},
    "hydro": {"gamma": 5 / 3, "cfl": 0.4},
    "time": {"tlim": 1e5},
    "cooling": {"enabled": False},
    "conduction": {"kappa": 1e-10},
    "problem": {"name": "cloud", "country": "NO"},
    "output": {"variables": ["rho", "press"]},
}

FILES = {
    "TOML": """\
# Thesis-like cloud
[mesh]
nx1 = 4000
nx2 = 1000
x1max = 4.0

[hydro]
gamma = 1.6666666666666667
cfl = 0.4

[time]
tlim = 1e5

[cooling]
enabled = false

[conduction]
kappa = 1.0e-10

[problem]
name = "cloud"
country = "NO"

[output]
variables = ["rho", "press"]
""",
    "YAML": """\
# Thesis-like cloud
mesh:
  nx1: 4000
  nx2: 1000
  x1max: 4.0
hydro:
  gamma: 1.6666666666666667
  cfl: 0.4
time:
  tlim: 1e5
cooling:
  enabled: no
conduction:
  kappa: 1.0e-10
problem:
  name: cloud
  country: NO
output:
  variables: [rho, press]
""",
    "INI": """\
; Thesis-like cloud
[mesh]
nx1 = 4000
nx2 = 1000
x1max = 4.0

[hydro]
gamma = 1.6666666666666667
cfl = 0.4

[time]
tlim = 1e5

[cooling]
enabled = false

[conduction]
kappa = 1.0e-10

[problem]
name = cloud
country = NO

[output]
variables = rho, press
""",
    "Athena++ input": """\
# Thesis-like cloud
<mesh>
nx1 = 4000       # cells in x1
nx2 = 1000
x1max = 4.0

<hydro>
gamma = 1.6666666666666667
cfl = 0.4

<time>
tlim = 1e5

<cooling>
enabled = false

<conduction>
kappa = 1.0e-10

<problem>
name = cloud
country = NO

<output>
variables = rho,press
""",
    "JSON": json.dumps(INTENDED, indent=1),
}


def infer(text: str):
    """Pyro's rule: an int if it parses as one, else a float, else the string itself."""
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


def read_ini(text: str, typed: bool) -> dict:
    parser = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    parser.read_string(text)
    return {s: {k: infer(v) if typed else v for k, v in parser[s].items()} for s in parser.sections()}


def read_athinput(text: str) -> dict:
    out, block = {}, None
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("<") and line.endswith(">"):
            block = out.setdefault(line[1:-1], {})
        else:
            key, value = (part.strip() for part in line.split("=", 1))
            block[key] = value
    return out


def write_ini(values: dict) -> str:
    parser = configparser.ConfigParser()
    for section, entries in values.items():
        parser[section] = {k: ", ".join(v) if isinstance(v, list) else str(v) for k, v in entries.items()}
    lines = []
    for section in parser.sections():
        lines += [f"[{section}]"] + [f"{k} = {v}" for k, v in parser[section].items()] + [""]
    return "\n".join(lines)


def write_athinput(values: dict) -> str:
    lines = []
    for block, entries in values.items():
        lines += [f"<{block}>"] + [f"{k} = {','.join(v) if isinstance(v, list) else v}" for k, v in entries.items()]
    return "\n".join(lines)


READERS = {
    "TOML": (tomllib.loads, tomli_w.dumps),
    "YAML": (yaml.safe_load, yaml.safe_dump),
    "INI": (lambda t: read_ini(t, False), write_ini),
    "INI, types inferred (Pyro)": (lambda t: read_ini(t, True), write_ini),
    "Athena++ input": (read_athinput, write_athinput),
    "JSON": (json.loads, json.dumps),
}


def compare(values: dict) -> dict:
    """Per parameter: what was read, and whether it is what was meant (same type and value)."""
    rows = {}
    for section, entries in INTENDED.items():
        for key, meant in entries.items():
            got = values.get(section, {}).get(key)
            rows[f"{section}.{key}"] = {"read": repr(got), "type": type(got).__name__,
                                        "as_meant": type(got) is type(meant) and got == meant}
    return rows


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {"python": sys.version, "pyyaml": yaml.__version__, "platform": platform.platform(), "formats": {}}
    for name, (read, write) in READERS.items():
        text = FILES["INI" if name.startswith("INI") else name]
        values = read(text)
        again = read(write(values))
        results["formats"][name] = {"parameters": compare(values), "round_trip_exact": again == values}
        print(name, json.dumps(results["formats"][name]), flush=True)

    keys = [f"{s}.{k}" for s, e in INTENDED.items() for k in e]
    md = ["# E15.1: do parameter files read back what their author meant?", "",
          f"Python {platform.python_version()} (tomllib, configparser, json), PyYAML {yaml.__version__}. Each cell: the "
          "value as read; marked ✗ where its type or value differs from what was meant. Last row: whether writing the "
          "values back and reading them again gives the same values.", "",
          "| Parameter (meant) | " + " | ".join(results["formats"]) + " |",
          "|---|" + "---|" * len(results["formats"])]
    for key in keys:
        section, name = key.split(".")
        cells = []
        for fmt in results["formats"].values():
            p = fmt["parameters"][key]
            cells.append(f"`{p['read']}`" + ("" if p["as_meant"] else " ✗"))
        md.append(f"| {key} (`{INTENDED[section][name]!r}`) | " + " | ".join(cells) + " |")
    md.append("| **as meant** | " + " | ".join(
        f"**{sum(p['as_meant'] for p in fmt['parameters'].values())} / {len(keys)}**"
        for fmt in results["formats"].values()) + " |")
    md.append("| round trip exact | " + " | ".join(
        "yes" if fmt["round_trip_exact"] else "no" for fmt in results["formats"].values()) + " |")
    (RESULTS / "E15.1-parameter-formats.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E15.1-parameter-formats.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
