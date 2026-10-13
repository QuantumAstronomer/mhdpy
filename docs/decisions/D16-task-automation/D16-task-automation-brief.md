# D16 — Task automation

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-13 |
| Supersedes | — |
| Extends | D01 (adds to its tooling, changing none of its decisions) |
| Superseded by | — |

## 1. Introduction

The checks that guard mhdpy's quality have grown with each brief. D01 introduced formatting and linting with ruff (D01.7), type checking with pyright (D01.8) and tests with pytest (D01.9). D02 added coverage, which must reach 100 % on the combined results of all test jobs (D02.8). D04 then made every test run come in two kinds: once with the kernels compiled and once with them uncompiled, as plain Python, chosen by the environment variable `MHDPY_KERNELS` (D04.3). Coverage only reaches 100 % when both kinds are combined, because coverage cannot look inside compiled code.

In CI, all of this is spelled out in the workflow, one job per combination. Locally it is not: checking a change the way CI will check it takes five commands, two of them with environment variables, plus combining the coverage files by hand. The kernel mode cannot be switched within one Python process, because it is fixed when mhdpy is first imported, so pytest alone cannot run both. In practice, the local check then becomes a single `uv run pytest`. That run sees only the compiled kernels, and reports a coverage of 96 % that says nothing about the combined figure CI enforces. Differences between the local check and CI are found only after a push, and a check that is tedious to run is run less often.

This brief decides how the checks are automated, so that one command runs everything CI checks on a single platform. It adds to D01's tooling rather than changing it: ruff, pyright and pytest stay as decided. D01 is frozen, so an addition to it is a brief of its own.

The reference codes show the range of approaches (see the syntheses in `References/`, and the files in each `Code/` folder). Athena++ has its own test runner, `tst/regression/run_tests.py`, with scripts per CI job in `tst/ci/`: a dedicated program, written and maintained by the project. Pyro and Ulula have no task automation in the provided copies; their Makefiles only build documentation. None of them has to run its suite in two configurations.

## 2. Evidence

### Feasibility checks

The proposed set-up (D16.2 and D16.3) was tried in a copy of the repository: nox 2026.8.17 (the current release), uv 0.12.23 and Python 3.14.8 on macOS 26.7.1 (Intel), with the 172 tests of the unit system.

- A `noxfile.py` with the four sessions of D16.3 ran with `uv run nox` in 13 s in total. The two test sessions took 4.4 s and 4.6 s of pytest time, about what the two runs take by hand; nox itself adds about a second per session. The coverage session combined the two kinds of run to 100 %, as in CI.
- Sessions ran in the project's own environment (`venv_backend = "none"`, D16.2): nothing was installed or rebuilt, and the editable install of mhdpy (D04) was used as it is.
- The lint session failed on the prototype `noxfile.py` itself, for its formatting and its missing docstrings, which shows that the checks apply to the new file too.
- Arguments after `--` reach pytest: `uv run nox -s tests -- -k TestRecords` ran 8 tests in each kernel mode. With identifiers for the parametrised session, the two test sessions are named `tests(compiled)` and `tests(uncompiled)`, and either can be run on its own, for example `uv run nox -s "tests(uncompiled)"`.

## 3. Decisions

### D16.1 — Task runner

Which tool runs the checks with a single command?

**Options**

- **A. nox.** **[GK]** A task runner configured in Python: a `noxfile.py` defines sessions as functions, each running commands. It is the runner recommended by the Scientific Python Development Guide and widely used in the scientific Python ecosystem, for example throughout scikit-hep. Sessions can be parametrised, so the two kernel modes are one session with two parameters, and arguments are passed through to pytest. Being Python, it runs the same on macOS, Linux and Windows, and the configuration follows the house style and is linted and type-checked like any other code. Drawback: one more development dependency.
- **B. tox (with tox-uv).** **[GK]** The older runner, configured in `tox.ini` or `pyproject.toml` as declarative settings rather than code. Well suited to running one suite against many Python versions; less natural for steps that differ in more than an environment variable, such as combining coverage after the test runs. Drawback: a configuration language of its own, and one more development dependency.
- **C. A script of the project's own**, for example `tools/check.py`, run with `uv run python tools/check.py`, as Athena++ does with its `run_tests.py`. No dependency. The project then writes and maintains a small task runner itself: selecting single steps, passing arguments through, reporting which steps failed.
- **D. make or just.** A Makefile (or a justfile) with a target per step. Familiar from compiled codes. make is not installed by default on Windows and just not at all; both are shell-based, so environment variables and coverage files are handled in shell syntax rather than Python.

**Recommendation.** A, nox. It does exactly what is needed with the least code of the project's own: parametrised sessions for the kernel modes, a session to combine coverage, and arguments passed through to pytest. Its configuration is Python, written in the house style and checked by the same tools as the package, so it needs no further language. C would rebuild a subset of nox by hand, and B and D fit the mixture of steps less well. This serves **correctness**: a check that is one command away is run before every commit, and it is the same check CI runs. It also serves **ease of use** for contributors, who learn one command.

**Decision.** *(2026-10-13)* **A, nox**, following the recommendation, as the most automated option.

### D16.2 — Environment of the sessions

In which Python environment do the sessions run?

**Options**

- **A. The project's own environment.** nox runs with `venv_backend = "none"` and is started with `uv run nox`, so uv first brings the environment in line with `uv.lock`, and every session uses that environment as it is, including the editable install of mhdpy. Nothing is installed or rebuilt per session, and local runs use exactly the locked versions CI uses. Drawback: only the Python version of the project environment is tested locally; other versions are left to CI.
- **B. A fresh environment per session, created by nox (with uv as its backend).** Each session installs mhdpy and its test dependencies into its own environment, which can also be created for several Python versions. Drawbacks: mhdpy, with its compiled extension, is built once per session and Python version, which takes minutes rather than seconds, and the environments drift from `uv.lock` unless the session reproduces the lock itself.

**Recommendation.** A, the project's own environment. The purpose of the single command is a fast local check of a change, and the locked environment is the one CI tests with. Testing other Python versions and the lowest dependency versions stays in CI, which has the matrix for it (D01.2, D01.6). This serves **correctness**, since local and CI runs use the same locked versions, and keeps the check fast enough to run often.

**Decision.** *(2026-10-13)* **A, the project's own environment**, following the recommendation: nox runs with `venv_backend = "none"` and is started with `uv run nox`.

### D16.3 — Sessions

Which sessions are there, and which run by default?

**Options**

- **A. Every check of a CI test job, all run by default.** Four sessions:
  - `lint`: `ruff format --check`, `ruff check` and `pyright` (D01.7, D01.8);
  - `tests(compiled)` and `tests(uncompiled)`: pytest with coverage, one per kernel mode (D04.3), each writing its own coverage file; arguments after `--` go to pytest;
  - `coverage`: combines the coverage of both test sessions and requires 100 % (D02.8).

  `uv run nox` runs all four in order; `uv run nox -s <name>` runs one. The test tier stays selected by `MHDPY_TEST_TIER` (D02.5), which passes through to the sessions unchanged.
- **B. The same sessions, with only the tests run by default.** Faster by the few seconds of linting and type checking, but `uv run nox` would no longer mean "everything CI checks", and the lint session would be run less often.

**Recommendation.** A. A single command that covers everything CI checks on one platform is the point of this brief; the lint session adds only a few seconds. A test session run with a selection of tests (`-- -k ...`) naturally leaves the combined coverage below 100 %, so the coverage session is meaningful only after full test runs, as in CI. Formatting is checked, not applied: the session never changes files, so that a check cannot alter what is about to be committed. This serves **correctness**.

**Decision.** *(2026-10-13)* **A, every check of a CI test job, all run by default**, following the recommendation: the sessions `lint`, `tests(compiled)`, `tests(uncompiled)` and `coverage`.

### D16.4 — Continuous integration

Does CI use the same sessions?

**Options**

- **A. CI runs the nox sessions.** The workflow keeps its jobs and matrix (operating systems, Python versions and kernel modes), but each job runs its step as a session: `uv run nox -s lint` in the checks job, `uv run nox -s "tests(<mode>)"` in each test job, `uv run nox -s coverage` after the coverage files of all jobs have been collected. A check is then defined once, in `noxfile.py`, and local runs and CI cannot drift apart. The jobs against the lowest dependency versions and against the built wheel stay as they are, since they test installations that differ from the project environment on purpose.
- **B. CI stays as it is; nox is for local use only.** No change to the workflow, but each check is defined twice, once in `noxfile.py` and once in the workflow, and the two can drift apart unnoticed.

**Recommendation.** A. Defining each check once is the only way to guarantee that the local command checks what CI checks. The coverage session must then combine the coverage files it finds, rather than only the two a local run writes, so that it works on the files collected from all CI jobs as well. This serves **correctness**.

**Decision.** *(2026-10-13)* **A, CI runs the nox sessions**, following the recommendation. The jobs against the lowest dependency versions and against the built wheel keep their own commands.

## 4. Consequences for higher layers

**For development**

- `uv run nox` is the check before every commit: formatting, linting, type checking, the fast test tier in both kernel modes, and the combined coverage, as CI checks them on one platform. Single sessions run with `-s`, and arguments for pytest follow `--`.
- nox joins the `dev` dependency group, with its current version as the lower bound (D01.6). `noxfile.py` lives at the root of the repository and follows the house style; it is linted and type-checked like the package.
- Every new kind of check, for example a documentation build or a benchmark run, is added as a session of `noxfile.py`, and CI runs it through nox. A check is defined in one place only.

**For continuous integration**

- The workflow keeps its matrix of operating systems, Python versions and kernel modes, and calls a session in each job. The coverage session combines every coverage file present, so that it serves for the two files of a local run and for the files collected from all CI jobs alike.
- The jobs against the lowest dependency versions and against the built wheel deliberately use other environments than the project's, and keep their own commands.

**For the kernels (D04)**

- Running both kernel modes is now one command, so the equivalence of compiled and uncompiled kernels, and the coverage that depends on the uncompiled run, are checked locally as routinely as in CI.
