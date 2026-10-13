# D15 — Configuration and user interface

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-13 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how users meet mhdpy:

- whether a simulation is described in Python or in files;
- how parameters are declared, supplied, checked and recorded;
- the format of parameter files;
- how a problem is set up, and which problems come with the package;
- the command line;
- what a run shows in the terminal and what it writes to its log file;
- which interface is public, and how its changes are versioned.

It is the last of the planned briefs. Its measure is the usability criterion of architecture.md §1.3: a newcomer installs mhdpy with one command and runs a standard test problem within minutes by following the documentation.

**What earlier briefs leave to this one:**

- **D12.1 and D12.3.** Modules declare their parameters (type, default, check); this brief decides how values are supplied and recorded. A problem set-up is a user module under the same contract.
- **D13.** A `Simulation` object with explicit stages, `step()` and `run(until=…)`; hook points between steps; schedules per output; a wall-clock limit. The command-line entry point creates the object and calls `run()`, with options for at least a parameter file, a restart file, the output directory, the number of workers and a wall-clock limit. Stopping conditions, schedules and hooks are configured like module parameters.
- **D13.7, open question.** Which information goes to the terminal and which to log files, at which verbosity, and how this is set.
- **D14.5 and D14.7.** How outputs are requested (kind, schedule, variables, derived quantities, precision, compression), and how parameters are changed on restart: every parameter declares whether it may change; those that would make the restart file inconsistent may not.
- **D02.7.** The tests are run with `pytest --pyargs mhdpy` after installing the `test` extra.

**What the references do** (syntheses in `References/`):

- **Athena++** splits configuration along a clear line:
  - **Compile time** (`configure.py`): which problem generator, coordinates, equation of state and Riemann solver are compiled in, and the constants that change the data layout.
  - **Run time:** an input file (`athinput.*`) of `<block>` sections with `key = value` lines, overridden on the command line by `block/key=value`. Values are untyped text, converted where the code asks for them.
  - **Command line:** input file, restart file, run directory, a dry run of the decomposition, a wall-time limit, and a display of the configuration.
  - **Problems:** a problem generator is one C++ file per problem that sets the initial state and enrols user functions (boundary conditions, sources, time-step limits, refinement criteria, history quantities); default hooks do nothing.
- **Pyro** offers a command-line script and a `Pyro` class side by side.
  - **Parameters:** INI-like files in layers: global defaults, the solver's, the problem's, the input file (which may only override keys that exist), then the command line or a dictionary from Python. Types are inferred from the text.
  - **Records:** the resolved set is written to a file at start-up, parameters never read are reported at the end, and every output stores them.
  - **Problems:** modules with their parameters and defaults, found by name or registered at run time.
- **Ulula** is used from Python only.
  - **Running:** a `run(setup, scheme, nx, tmax, …)` function with keyword arguments.
  - **Problems:** a problem is a `Setup` class that owns the physics (domain, equation of state, gravity, boundaries) and initial conditions, and may provide an exact solution for plots. The numerical scheme is chosen separately, so any problem runs with any scheme.
- **ZEUS** fixed its modules with preprocessor macros and could be controlled interactively during a run.

## 2. Evidence

### E15.1 — Do parameter files read back what their author meant?

**Method.** [`experiments/E15.1-parameter-formats.py`](experiments/E15.1-parameter-formats.py) writes the same eleven parameters, a simplified thesis run, by hand in each format, the way a user would naturally write them there:

- TOML (read with the standard library);
- YAML (PyYAML, the most widely used reader);
- INI (the standard library's `configparser`, as strings and with Pyro's inference of types);
- Athena++'s input format (as strings, as Athena++ reads them);
- JSON.

Every value read is compared with what was meant, in type and value. The set includes known delicate cases: an exponent without a decimal point (`1e5`), a float with all its digits, a boolean switch, a string that looks like a boolean (the country code `NO`), and a list. Each format is also written back from the values read and read again. Full output: [`results/E15.1-parameter-formats.md`](experiments/results/E15.1-parameter-formats.md).

**Results.**

| Format | Read as meant | Where it differs | Comments | Standard library |
|---|---|---|---|---|
| TOML | **11 / 11** | — | yes | reads (`tomllib`) |
| YAML (PyYAML) | 9 / 11 | `1e5` read as the string `'1e5'`; `NO` read as `False` | yes | no |
| INI | 2 / 11 | everything is a string | yes | reads and writes |
| INI, types inferred (Pyro) | 9 / 11 | `false` stays a string; a list is one string | yes | reads and writes |
| Athena++ input | 2 / 11 | everything is a string, converted where the code asks | yes | — (a few lines) |
| JSON | 11 / 11 | — | **no** | reads and writes |

- **TOML reads every value as meant.** It has types of its own (integer, float, boolean, string, list, table), so the file says what it means.
- **YAML's widely used reader changes two values silently.** It follows an older version of YAML, in which `1e5` is not a number and `no`, `NO`, `off` are booleans.
- **Untyped formats leave types to the reader.** With declared types (D12.1), conversion becomes possible, but every list and boolean needs a convention of its own.
- **JSON is exact but has no comments,** which makes it a poor format for files people write; it serves well as a record written by the program.
- **Writing the values back and reading them again is exact in every format.** Python writes floats with all the digits they need.

### E15.2 — Declared parameters catch mistakes before the run

**Method.** [`experiments/E15.2-declared-parameters.py`](experiments/E15.2-declared-parameters.py) is a prototype, in the standard library alone (about 70 lines), of the layer that resolves a run's parameters:

- **declarations:** each parameter has a name, type, default, check, and whether it may change on restart;
- **layers:** the declared defaults (or, on restart, the restart file's record), then a TOML parameter file, then overrides `section.key=value` whose values are read as TOML.

It runs correct and mistaken scenarios and records whether the run would start, and the message the user would see. Full output: [`results/E15.2-declared-parameters.md`](experiments/results/E15.2-declared-parameters.md).

**Results.**

| Scenario | Starts | Message |
|---|---|---|
| a correct file, with overrides | yes | — |
| a misspelt name (`cfll`) | no | unknown parameter 'hydro.cfll'; did you mean 'hydro.cfl'? |
| a misspelt section in an override (`hdyro.cfl`) | no | unknown parameter 'hdyro.cfl'; did you mean 'hydro.cfl'? |
| `nx1 = 4000.0` | no | 'mesh.nx1' must be int, got float 4000.0 |
| `cfl = 1` | yes | (an integer is accepted where a float is declared) |
| `hydro.cfl=1.5` | no | 'hydro.cfl' must be in (0, 1], got 1.5 |
| `cfl = "0.4"` | no | 'hydro.cfl' must be float, got str '0.4' |
| `cooling.enabled=no` | no | 'cooling.enabled' must be bool, got str 'no' |
| restart with a later end time | yes | — |
| restart with another block size | yes | — (D13.5) |
| restart changing the mesh, by override or by file | no | 'mesh.nx1' cannot change on restart (it is fixed by the restart file) |

- **Every mistake is reported before the run starts,** with the parameter, the problem and, for misspelt names, a suggestion. Pyro reports unread parameters only at the end of a run, and Athena++ does not check for parameters that no part of the code reads; in both, a run with a misspelt `cfl` would go ahead with the default.
- **Changing parameters on restart (D14.7) follows directly from the declarations:** changeable ones change, fixed ones are refused with a reason.
- **No dependency is needed:** dataclasses, `tomllib`, `difflib` and `json` suffice. The record of resolved parameters, written to JSON and read back, is exact.

**What the two experiments mean together.** A typed file format and typed declarations check each other. TOML makes the file say what it means, and the declarations reject what the module cannot use, before the run starts. Both come with the standard library.

## 3. Decisions

### D15.1 — Python or files

Is a simulation described in Python, in files, or both?

**Options**

- **A. Python only,** as Ulula: a script creates the simulation with keyword arguments.
  - **Advantage:** fully flexible.
  - **Drawback:** the parameters of a production run are scattered through code, a parameter scan means editing code, and the record of what was run is a script.
- **B. Files first,** as Athena++: a parameter file plus a problem module, with the Python interface secondary. Familiar for batch runs, but notebooks and tests would need files.
- **C. One Python interface, with parameter files as one way to supply its values,** as Pyro does.
  - **The interface:** `Simulation(problem, parameters=…)` takes its parameters from a dictionary, from a parameter file, or from both.
  - **The command line** (D15.5) is a thin layer over the same calls.
  - **Underneath:** the same declared parameters (D15.2) are used, and are recorded in every output (D14).

**Recommendation.** C. mhdpy is a Python package first (architecture.md), and tests, notebooks and scripts use the Python interface directly. Production runs and parameter scans are better served by files that can be versioned, compared and varied without touching code. Option C gives both without two configuration systems. Ulula's flexibility remains, since a script can always build the dictionary itself. This serves **ease of use**.

**Decision.** *(2026-10-13)* **C, one Python interface, with parameter files as one way to supply its values**, following the recommendation.

### D15.2 — Parameters: declared, layered, checked and recorded

How do parameters get their values?

**Options**

- **A. Declared parameters, resolved in layers, checked before the run.**
  - **Declarations:** every module (a problem included) declares its parameters, with type, default, check, unit where relevant, documentation, and whether it may change on restart. Names are namespaced by module: `hydro.cfl`, `cooling.table`, `output.snapshot.dt`.
  - **Layers:** the defaults, a parameter file, then overrides from the command line or a dictionary. On restart, the restart file's record replaces the defaults, and the file and overrides may change only what is declared changeable (D14.7).
  - **Checks:** unknown names, wrong types and values out of range are errors before the run starts, with suggestions for misspelt names (E15.2).
  - **Records:** the resolved set is written to the output directory at start-up and stored in every output (D14.2).

  Implemented with the standard library (dataclasses).
- **B. Untyped parameters,** as in Pyro or Athena++: values are text, typed where the code reads them; unread parameters are reported at the end or ignored. Simpler, but a misspelt parameter runs silently with its default.
- **C. A validation library** such as pydantic: the same as A with richer checks, at the cost of a dependency for something the standard library does (E15.2).

**Recommendation.** A. A misspelt parameter that silently falls back to its default produces a wrong result that looks right, the worst kind of error. Declarations already exist (D12.1), so checking against them costs nothing more. Pyro's record of resolved parameters is kept. This serves **correctness** first and **ease of use** with it.

**Decision.** *(2026-10-13)* **A, declared parameters, resolved in layers and checked before the run**, following the recommendation.

### D15.3 — The format of parameter files

In which format are parameter files written?

**Options**

- **A. TOML.** Read by the standard library (`tomllib`); typed values, lists and tables; comments; and the format of `pyproject.toml`, familiar to Python users. Every value in E15.1 read as meant. Writing it needs a small writer of its own or a small dependency; the record of resolved parameters can equally be JSON (D14).
- **B. YAML.** Widely used and flexible, but a dependency, and its common reader changed two of eleven values silently (E15.1).
- **C. INI** (Pyro) or **Athena++'s input format.** Familiar to users of those codes, but untyped: every list and boolean needs a convention (E15.1).
- **D. Python files** executed as configuration. Anything is possible, which also means a parameter file can do anything; that is what problem modules are for (D15.4).

**Recommendation.** A. It is the only hand-written format that read every value as meant, and it needs nothing beyond the standard library to read. Overrides on the command line use the same syntax for their values (E15.2). This serves **correctness** (files mean what they say) and **ease of use**.

**Decision.** *(2026-10-13)* **A, TOML**, following the recommendation.

### D15.4 — Problem set-ups and the problem library

How is a problem set up, and which problems come with mhdpy?

**Options**

- **A. A problem is a module (D12),** as Ulula's `Setup`. It declares:
  - its parameters (D15.2);
  - the modules it needs (equation system, equation of state, cooling, …);
  - its initial conditions, as a function of the coordinates over ranges of blocks (D12.4), in primitive variables;
  - optionally its own boundary conditions, sources, hooks, history quantities, refinement criteria and an exact solution for comparison.

  Numerical choices (Riemann solver, reconstruction, integrator) are parameters, so that any problem runs with any scheme, as in Ulula. Problems are found by name in a library that comes with mhdpy, or loaded from a user's file or module.

  **The library** contains the verification and benchmark problems of D02:
  - shock tubes, Sedov blast, linear waves, Kelvin–Helmholtz;
  - Orszag–Tang, field-loop advection;
  - in time, the thesis cloud.

  So `mhdpy run sod` works straight after installation.
- **B. Problem generators** as Athena++'s: a function that sets the initial state and enrols user functions. Proven, but enrolment calls duplicate what module declarations already state.
- **C. Problems from configuration alone:** initial conditions assembled from shapes and profiles in the parameter file. No code for simple problems, but too limited for real ones, and a second way to do what modules do.

**Recommendation.** A. It is the integration contract of D12 applied to problems: one mechanism for built-in modules, user modules and problems. Ulula's separation of problem and scheme makes every problem a test of every scheme. An exact solution with the problem makes comparison part of the problem rather than of a script. A library made of the D02 problems serves the usability criterion and the test suite at once. This serves **ease of use** and **extensibility**.

**Decision.** *(2026-10-13)* **A, a problem is a module, with a library of the D02 problems**, following the recommendation.

### D15.5 — The command line

What does the command line offer?

**Options**

- **A. One `mhdpy` command with subcommands,** built on the standard library (`argparse`):
  - `mhdpy run <problem or file> [parameters.toml] [section.key=value …]`, with `--restart`, `--output-dir`, `--workers`, `--wall-time`, `--verbose` and `--quiet`;
  - `mhdpy problems`: the library's problems, with a line on each;
  - `mhdpy parameters <problem>`: a complete parameter file with every default and its documentation, as a template;
  - `mhdpy plan <problem> [parameters.toml]`: the resolved parameters, the decomposition and the integration contract (D12), without running, as Athena++'s dry run and configuration display;
  - `mhdpy info`: version, interpreter (free-threaded or not), build (generic or native, D04.6), number of CPUs, and the versions of NumPy, h5py and HDF5. It is the first thing to ask for in a bug report.

  Tests stay `pytest --pyargs mhdpy` (D02.7).
- **B. A single command with flags,** as Athena++ (`-i`, `-r`, `-d`, `-m`, `-t`). Compact, but without the listing, template and installation commands.
- **C. No command line:** users run Python scripts.

**Recommendation.** A. The subcommands beyond `run` are what a newcomer needs to get from installation to a first run without reading code:
- what problems there are;
- what parameters a problem has;
- what a run will do;
- whether the installation is what they think it is.

`argparse` keeps it free of dependencies. This serves **ease of use**, the usability criterion directly.

**Decision.** *(2026-10-13)* **A, one `mhdpy` command with subcommands**, following the recommendation.

### D15.6 — The terminal and the log file

What does a run show in the terminal, and what does it write to its log file? (The open question of D13.7.)

**Options**

- **A. Python's `logging`,** with a logger hierarchy under `mhdpy` and three levels in use:
  - **warning:** whatever needs attention (floors or flux corrections increasing, a restart in another environment, D14.2);
  - **info:** the set-up summary, the run's log line at its cadence (D13.7), output notices and the end-of-run summary;
  - **debug:** details (the full integration contract, the resolved parameters, phase groups, timings per output).

  **Where it goes:**
  - **Terminal:** info and above by default (`--verbose` adds debug, `--quiet` leaves warnings only).
  - **Log file** in the output directory: debug and above, always.

  **As a library,** mhdpy adds no handlers when imported, as Python libraries should. The command line does, and one call (`mhdpy.log_to_terminal()`) does it in scripts and notebooks.
- **B. Everything to both,** terminal and file alike: simple, but the terminal fills with detail, or the file lacks it.
- **C. Print statements with a verbosity flag,** as Pyro: simple, but not redirectable or filterable by users, and not composable with other libraries' logging.

**Recommendation.** A. The terminal is for following a run, the log file for understanding it afterwards; levels separate the two without two mechanisms. `logging` is the standard and lets users redirect or filter mhdpy's messages like any other library's. Per-step numbers belong in the history (D14.4), not in the log. This serves **ease of use**.

**Decision.** *(2026-10-13)* **A, Python's `logging`: info to the terminal, debug to the log file**, following the recommendation.

### D15.7 — The public interface and its versioning

What is public, and how do changes to it reach users?

**Options**

- **A. An explicit public interface with semantic versioning.**
  - **Public** is what is documented and exported, through `__all__`, by `mhdpy` and its public subpackages. Internal modules start with an underscore.
  - **What counts as interface:**
    - the Python interface;
    - the command line;
    - parameter names;
    - the file format (D14.2, with its format version);
    - the `.pxd` declarations for compiled modules (D12 §4).
  - **Versioning:** before 1.0, a minor version may break the interface, with notes in the changelog. From 1.0, semantic versioning: breaking changes only in major versions, and deprecations warn for at least one minor version first.
  - **File compatibility:** files of every earlier format version stay readable, and restarts are supported across minor versions (bit for bit only within one environment, D02.3).
- **B. No policy until 1.0.** Less work now, but users and external modules learn what is stable only by breakage, and file compatibility is left to chance.

**Recommendation.** A. External modules (D12) and long production runs depend on a stable interface and readable files; stating what is public costs little now and much later. Before 1.0 the policy leaves room to change, but changes are announced. Readable old files protect users' data. This serves **ease of use** and **extensibility**.

**Decision.** *(2026-10-13)* **A, an explicit public interface with semantic versioning**, following the recommendation.

## 4. Consequences for higher layers

This is the last planned brief, so its consequences fall on the implementation and its documentation rather than on later briefs.

**For the implementation**

- **One interface:** `Simulation(problem, parameters=…)` accepts a dictionary, a TOML file, or both (D15.1). The command line and every script go through it; there is no second configuration path.
- **Parameters** (D15.2):
  - **Declared** with dataclasses in the standard library: name (namespaced by module, `hydro.cfl`), type, default, check, unit where relevant, documentation, and whether it may change on restart.
  - **Resolved in layers:** defaults; on restart, the restart file's record instead; then the parameter file; then overrides as `section.key=value` with TOML values, or a dictionary.
  - **Checked at set-up:** unknown names (with suggestions), wrong types and values out of range are errors before anything is allocated. An integer is accepted where a float is declared.
  - **Recorded:** the resolved set is written to the output directory at start-up and into every output (D14.2).

  Outputs (kind, schedule, variables, derived quantities, precision, compression; D14), stopping conditions and hooks (D13) are parameters like any other.
- **Parameter files** are TOML, read with `tomllib` (D15.3). Writing the template of `mhdpy parameters` needs a small TOML writer of mhdpy's own for simple values, or a small dependency; the record in outputs is JSON.
- **Problems** (D15.4):
  - **A problem is a module (D12):** it declares parameters, the modules it needs, initial conditions as a function over ranges of blocks in primitive variables, and optionally boundary conditions, sources, hooks, history quantities, refinement criteria and an exact solution.
  - **Numerical choices are parameters,** so every problem runs with every scheme.
  - **Finding a problem:** by name in `mhdpy.problems`, or from a user's file or module.
  - **The library** holds the D02 verification and benchmark problems and serves the test suite as well as users.
- **Command line** (D15.5): one console script `mhdpy`, on `argparse`, with the subcommands `run`, `problems`, `parameters`, `plan` and `info`. `run` takes a problem or file, a parameter file and overrides, with `--restart`, `--output-dir`, `--workers`, `--wall-time`, `--verbose` and `--quiet` (D13 §4).
- **Logging** (D15.6): loggers under `mhdpy` with three levels in use (warning, info, debug).
  - **Command line:** shows info and above in the terminal, adjustable with `--verbose` and `--quiet`, and writes debug and above to the log file in the output directory.
  - **Library:** importing mhdpy adds no handlers; `mhdpy.log_to_terminal()` does it in scripts and notebooks.
  - **Numbers:** per-step numbers go to the history (D14.4), not to the log.
- **The public interface** (D15.7): `__all__` in `mhdpy` and its public subpackages; internal modules start with an underscore. A changelog records every change to the interface. Readers keep every earlier file-format version readable.

**For the verification of D02**

- The parameter layer is tested against the scenarios of E15.2: every mistake is refused before the run with its message, and the resolved record reads back exactly.
- Every problem in the library runs from the command line and from Python with the same result, bit for bit.
- `mhdpy parameters <problem>` writes a template that `mhdpy run` accepts unchanged, for every problem in the library.
- Files of every earlier format version are kept as small test fixtures and must remain readable.

**For the documentation**

- **The getting-started guide:** installation with one command, `mhdpy info`, `mhdpy run sod`, and a look at the result. It is the usability criterion of architecture.md §1.3 written out, and is tested as such.
- **The user guide:** parameter files and overrides, the problem library, writing a problem of one's own (the module guide of D12 §4 applied to problems), restarts with changed parameters, outputs and reading them back (D14), and logging.
- **The reference:** every declared parameter, generated from the declarations, so that it cannot drift from the code.
- **The changelog and the versioning policy,** stated once and followed from the first release.
