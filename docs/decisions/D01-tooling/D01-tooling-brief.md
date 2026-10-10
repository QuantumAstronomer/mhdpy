# D01 — Tooling and project conventions

| | |
|---|---|
| Status | Decided (frozen); partly superseded |
| Decided | 2026-10-10 |
| Supersedes | — |
| Superseded by | D01.5 → D04.5 |

## 1. Introduction

Before any physics is written, the ground the project stands on has to be laid: where the code lives, which Python versions it targets, how it is packaged, how its dependencies are pinned, and which tools guard its quality. These choices sit at the very bottom of the architecture. Every later layer is written, tested, documented and shipped with them, so they are cheap to make now and increasingly expensive to change once code exists. This brief also settles how the experiments behind the briefs themselves are run, since every later brief depends on that.

Two parts of the purpose (architecture.md) bear directly on this brief. The usability criterion asks for installation through a single `pip` or `uv` command on macOS and Linux, with an automated test suite running on both platforms for every change. The learning goal asks for a large, multi-layered project built robustly, which is largely a matter of tooling and discipline from the first commit. Development itself is done with uv; that choice has already been made and is not revisited here.

The reference codes show three quite different levels of tooling (see the Pyro, Ulula and Athena syntheses in `References/`, and the files in each `Code/` folder):

| | Pyro | Ulula | Athena++ |
|---|---|---|---|
| Hosting | GitHub | Bitbucket | GitHub |
| Licence | BSD-3-Clause | MIT | BSD-3-Clause |
| Build | setuptools + setuptools-scm (version from git tags) | setuptools | `configure.py` + make |
| Layout | package at repository root | package at repository root | sources under `src/` |
| Formatting / linting | pylint (20 checks disabled), flake8, isort, codespell | none | cpplint, flake8 for the Python tools |
| Tests | pytest, notebook tests (nbval), coverage; regression against stored benchmarks | none; the example setups serve as tests | custom Python regression harness (`tst/regression`), style checks |
| CI | not in the provided copy | none | Jenkins (formerly Travis) |
| Documentation | Sphinx, numpydoc, notebooks | Sphinx | Doxygen configuration, GitHub wiki |
| Docstrings | NumPy style | NumPy style | Doxygen comments |

One detail in Athena++ is instructive. Its `CPPLINT.cfg` switches off whole categories of style checks with comments such as "As of 2018-12-12: … 5240 errors". Pyro's configuration likewise disables twenty pylint checks. Once a code base has grown without a rule, the rule can in practice no longer be introduced, only suppressed. Quality tooling is therefore worth settling before the first line of code, not after.

## 2. Evidence

### E01.1 — Ecosystem readiness on PyPI

**Question.** Which Python versions and platforms does the scientific Python stack actually support with prebuilt wheels? A dependency without a wheel for a platform must be compiled from source on install, which conflicts with the installation requirement.

**Method.** The script [`experiments/E01.1-wheel-availability.py`](experiments/E01.1-wheel-availability.py) queries the PyPI JSON API for the latest release of each candidate dependency. It records which combinations of Python version (3.13, 3.14, free-threaded 3.14t) and platform (macOS Intel, macOS Apple Silicon, Linux x86-64, Linux ARM) are served by a wheel. It also determines how long after each CPython release the first wheels appeared, and the latest release of each development tool. It uses only the standard library and was run on 2026-10-09 with Python 3.14.8 on the development machine (Intel Mac, macOS 26.7). Full output: [`experiments/results/E01.1-wheel-availability.md`](experiments/results/E01.1-wheel-availability.md).

**Result 1: wheel availability of the latest releases.** Condensed from the full table:

| Package | 3.13 | 3.14 | 3.14t | Exception |
|---|---|---|---|---|
| numpy, scipy, matplotlib, h5py, mpi4py | all four platforms | all four platforms | all four platforms | — |
| cython | all four platforms | all four platforms | pure-Python fallback | — |
| numba, llvmlite | Apple Silicon, Linux | Apple Silicon, Linux | Apple Silicon, Linux | **no Intel macOS** |
| jax / jaxlib | Apple Silicon, Linux | Apple Silicon, Linux | Apple Silicon, Linux | **no Intel macOS** |

The last releases with an Intel-macOS wheel were numba 0.63.0b1 and llvmlite 0.45.1 (both early October 2025), and jaxlib 0.4.38 (December 2024). llvmlite, which Numba requires, never shipped an Intel-macOS wheel for Python 3.14.

**Result 2: ecosystem lag.** The core stack (NumPy, SciPy, Matplotlib, jaxlib) publishes wheels for a new Python version during its release-candidate phase, so they are available on release day. h5py followed within a week. Numba and llvmlite took between one and three and a half months. Two lags in the table are not meaningful: Cython and JAX also ship pure-Python wheels, and mpi4py only started publishing wheels at all in June 2025.

**Result 3: tool maturity.** Most tools considered below are mature and actively released. The exceptions are young projects still before version 1.0: the type checker `ty` (0.0.85), the documentation generator `zensical` (0.0.69) and the hook runner `prek` (0.5.5). The core of MkDocs has had no release since August 2024.

**What this means.**

- Python 3.13 and 3.14 are equally well supported by everything mhdpy is likely to need. So is the free-threaded 3.14t build, which keeps that option open for the parallelism brief (05).
- **On the development machine, Numba and JAX cannot be installed from wheels for Python 3.14.** For 3.13 they are frozen at releases from 2024–2025. This does not decide anything here, but it is a hard constraint for the compute-backend brief (04). It also means that any dependency on them would break the installation requirement for Intel-Mac users.
- New Python versions can realistically be supported a few months after their release.

### E01.2 — The author's code style against the standard tools

**Question.** Does the preferred code style survive an automatic formatter, and do its docstrings work with the documentation tooling chosen in D01.10?

**Method.** A representative code sample (a `Grid.__init__` of about 190 lines, mostly validation logic, comments and a docstring) is stored verbatim in [`experiments/E01.2-style-sample.py`](experiments/E01.2-style-sample.py). The script [`experiments/E01.2-style-formatting.py`](experiments/E01.2-style-formatting.py) (ruff 0.16.10, numpydoc 1.11.0, own lockfile) does four things. It measures the sample's line lengths. It runs `ruff format` with four configurations and counts which style features survive. It runs the pycodestyle and pydocstyle lint rules. And it lets numpydoc, the parser Sphinx uses for NumPy-style docstrings, parse the docstring, once as written and once with the same content in the standard NumPy section layout. Full output: [`experiments/results/E01.2-style-formatting.md`](experiments/results/E01.2-style-formatting.md); the formatter diffs are in `experiments/results/E01.2-format-*.diff`.

**Result 1: line length.** The sample's longest line is 131 characters. 23 lines exceed 88 characters, 16 exceed 100, and 5 exceed 120. Comments and docstring text, by contrast, are wrapped by hand at about 80 characters.

**Result 2: the formatter.** Lines rewritten by `ruff format`, and the number of lines showing each style feature before and after:

| Configuration | Lines changed | Aligned `=` | Spaces around keyword `=` | Continuation aligned under `(` | Comments |
|---|---|---|---|---|---|
| original | — | 3 | 3 | 2 | 61 |
| line length 88 | 27 | 0 | 0 | 0 | 61 |
| line length 100 | 22 | 0 | 0 | 0 | 61 |
| line length 120 | 14 | 0 | 0 | 0 | 61 |
| line length 120, quotes preserved | 14 | 0 | 0 | 0 | 61 |

At every line length, the formatter removes three features of the sample:

- vertically aligned assignments (`n_cells     = ...` becomes `n_cells = ...`);
- spaces around keyword arguments (`is_integer(value = n)` becomes `is_integer(value=n)`);
- continuation lines aligned under the opening parenthesis, which become hanging indents with the closing parenthesis on its own line.

It leaves comments, docstring content, blank lines after docstrings and the (double) quotes untouched. Line length 120 changes the fewest lines, and mainly by wrapping the five lines that exceed it.

**Result 3: lint rules.** At line length 120, the sample triggers the pycodestyle rules for the features above: E221 (multiple spaces before operator, 3×), E251 (spaces around keyword `=`, 6×) and E501 (line too long, 5×). The pydocstyle rules flag the docstring layout: D406/D407 (section names without the standard underline, 3× each), plus D205/D400, which ask for a summary line.

**Result 4: docstring parsing.** numpydoc does **not** recognise the sample's docstring layout (`Parameters:` with a colon, underlined with `===`, and `name: type`). It reports "Unknown section" for all three sections and extracts no parameters and no exceptions. Sphinx would therefore render the docstring as plain text, without parameter tables or type links. The identical content in the standard layout (`Parameters` underlined with dashes, `name : type`) parses completely: all four parameters with their types and both exceptions, without warnings.

**What this means.**

- The preferred line length (well above 88) is fully supported, and 120 fits the sample best.
- Three spacing habits (aligned assignments, spaced keyword arguments, aligned continuations) cannot coexist with an automatic formatter. Either the formatter is adopted and the habits dropped, or the formatter is dropped and the style is kept by hand.
- The docstring layout is a separate matter: it conflicts with the choice of NumPy-style docstrings rendered by Sphinx (D01.10), not with the formatter.

### Feasibility checks

- uv 0.12.23 (installed) supports `uv lock --script`, which writes a lockfile for a single script with inline dependency metadata (PEP 723). This is relevant to D01.6. It was tested with a throwaway script depending on NumPy: `uv lock --script demo.py` produced `demo.py.lock`, and `uv run --script demo.py` ran in the locked environment.
- `uv init` supports the build backends `uv`, `hatch`, `flit`, `pdm`, `poetry`, `setuptools`, `maturin` and `scikit` (scikit-build-core).

## 3. Decisions

### D01.1 — Hosting and continuous integration

Where does the repository live, and where does continuous integration (CI) run? The usability criterion requires the test suite to run on macOS and Linux for every change. CI also builds the release packages.

**Options**

- **A. GitHub with GitHub Actions.** This is where most of the scientific Python ecosystem lives, including Pyro and Athena++. Hosted Linux and macOS runners are free for public repositories, and cibuildwheel (for building wheels) and PyPI's trusted publishing (releases without stored passwords) integrate directly. It also gives the best visibility for adoption. Drawbacks: a proprietary platform, and macOS minutes are expensive for private repositories. **[GK]** GitHub is phasing out its Intel macOS runners, so CI on Intel macOS may not be available for long. This should be verified when CI is set up.
- **B. GitLab with GitLab CI.** Mature and open-core, with good CI. **[GK]** Hosted macOS runners are, as far as is known, limited to paid tiers. It is less common in the scientific Python ecosystem.
- **C. Codeberg (Forgejo) with Forgejo Actions or Woodpecker.** Non-profit and fully open source. No hosted macOS runners, so the macOS half of the usability criterion could not be tested in CI.

**Recommendation.** A, GitHub with GitHub Actions. It is the only option that tests on both target platforms at no cost. That serves **correctness**, the first priority, because platform-specific failures are caught on every change. It also serves the installation exception, since wheel building and publishing are best supported there. A public repository from the start is advisable for the free macOS runners. The code can be clearly marked as pre-release until 1.0.

**Decision.** *(2026-10-09)* **A, GitHub with GitHub Actions**, following the recommendation. Besides the arguments above, GitHub is the de facto default for open-source scientific software and a platform the author already works with, so no new tooling has to be learned.

### D01.2 — Supported Python versions and policy

Which Python versions does mhdpy support, and how does that set change over time? The purpose fixes 3.14 as the primary version and keeps 3.13 open.

**Options**

- **A. 3.14 only** (`requires-python = ">=3.14"`). All 3.14 features are available: **[GK]** deferred evaluation of annotations (PEP 649/749), template strings (PEP 750), multiple interpreters in the standard library (PEP 734), and officially supported free-threading (PEP 779). CI needs only one Python version. Drawback: excludes users whose environments, often on clusters, are still on 3.13.
- **B. 3.13 and 3.14, with a rolling support window following SPEC 0.** **[GK]** SPEC 0 is the Scientific Python community's policy: support each Python version for three years after its release. As of now that window covers exactly 3.13 and 3.14. A new version is added once its dependencies have wheels; per E01.1 that takes a few months at most. The oldest version is dropped when it leaves the window. Drawbacks: a two-version CI matrix, and 3.14-only features cannot be used until 3.13 leaves the window (October 2027).
- **C. A wider range (3.11 or 3.12 and up).** Maximum reach, but a growing CI matrix and older language features. It also goes beyond what the purpose asks for.

**Recommendation.** B, 3.13 and 3.14 under SPEC 0. E01.1 shows that both versions are equally well served by the scientific stack, so supporting 3.13 costs little: a second CI column and some restraint in language features. None of the 3.14-only features listed is needed for numerical work. The one with architectural weight, free-threading, is a question for brief 05, and supporting it there would not require dropping 3.13. Since the first priorities, **correctness and performance**, are unaffected, the choice falls to **ease of use**, and in particular to the installation exception, which favours the wider reach. The policy also answers in advance when versions are added and dropped, so the question never has to be reopened. Development itself happens on 3.14.

**Decision.** *(2026-10-09)* **B, Python 3.13 and 3.14, with the SPEC 0 rolling three-year window.** The rolling window keeps mhdpy on Python versions that are themselves still supported. New versions are adopted early: support for a new release (3.15 is imminent) is added as soon as the dependencies provide wheels for it, rather than waiting.

### D01.3 — Licence

Under which licence is mhdpy published? The licence determines whether others can use, modify and redistribute it, and on what terms.

**Options**

- **A. BSD-3-Clause.** Permissive. Used by Pyro and Athena++, and by NumPy, SciPy and most of the scientific Python stack. Users may do almost anything, provided the copyright notice is kept.
- **B. MIT.** Permissive and functionally very close to BSD-3 (used by Ulula). It lacks BSD-3's clause forbidding use of the authors' names for endorsement.
- **C. Apache-2.0.** Permissive, with an explicit patent grant. More text, less common in astrophysics software.
- **D. GPL-3.0 or later.** Copyleft: derived works must be published under the same licence. This protects openness, but deters adoption by projects that cannot or do not want to adopt the GPL.

**[GK]** One practical point applies to every option. Algorithms may be studied and reimplemented freely, but where *code* from a reference is ported or translated, its copyright notice must be retained. Pyro, Athena++ (BSD-3) and Ulula (MIT) all permit this under any of the options above, but it needs to be recorded when it happens.

**Recommendation.** A, BSD-3-Clause. It matches the ecosystem mhdpy builds on and the two reference codes it is most likely to draw from. That keeps attribution of ported code simple, and it places no obstacle in the way of adoption by others. Licensing has no bearing on correctness, performance or readability, so the choice falls to **ease of use**. A permissive licence is the option that best serves the wish for others to adopt the code.

**Decision.** *(2026-10-09)* **A, BSD-3-Clause**, following the recommendation. A convention for third-party material is adopted with it, set out in [`LICENSES/README.md`](../../../LICENSES/README.md):

- The licence texts of the reference codes (Athena++, Pyro, Ulula) are kept in `LICENSES/`. Wherever their code is copied or adapted, in code, comments or documentation, a comment names the source file and points to the licence text.
- Figures are not copied from papers or from the CompHydro book. They are redrawn from mhdpy's own experiments, which also allows them to follow mhdpy's own visual style, and the original source is cited.

### D01.4 — Repository layout

How is the repository organised, and in particular where does the package source live relative to the repository root?

**Options**

- **A. Flat layout:** `mhdpy/` at the repository root, as in Pyro and Ulula. Simple. Drawback: Python imports the package from the working directory rather than from the installed package. Tests can then pass locally while the installed package is broken, for example when a data file or a compiled extension is missing from the build.
- **B. src layout:** the package lives under `src/mhdpy/`. The package can only be imported once installed, so tests always run against what users will actually get. This is the layout recommended by the Python Packaging Authority (PyPA), and the default of `uv init --lib`. Drawback: one extra directory level.

In both cases the proposed top level would be:

```
mhdpy/
├── src/mhdpy/        package source (or mhdpy/ in the flat layout)
├── tests/            test suite (organisation: brief 02)
├── docs/             architecture.md, decisions/, later the user documentation
├── pyproject.toml    metadata, dependencies, tool configuration
├── uv.lock           locked development environment
├── README.md, LICENSE, CHANGELOG.md
└── References/       reference material (see note)
```

*Note on `References/`.* The reference folder (about 130 MB) contains third-party code and papers. Its code is permissively licensed, but the papers are generally not redistributable. It should therefore be kept out of version control, for example via `.gitignore`, or moved outside the repository.

**Recommendation.** B, the src layout. It removes a whole class of "works on my machine" errors, those where the installed package differs from the source tree. That class becomes especially likely if compiled code enters in brief 04. That serves **correctness**, the first priority, at the cost of a single directory level.

**Decision.** *(2026-10-09)* **B, the src layout, with one change to the proposed tree: tests live next to the component they test** instead of in a single top-level `tests/` folder:

```
src/mhdpy/
├── <component>/
│   ├── ...           component source
│   └── tests/        tests of this component
└── ...
```

Each component is thereby self-contained and easy to navigate: its code and its tests sit side by side. The tests **ship with the package**, as in NumPy, SciPy and Astropy, so users can see what has been tested and can verify their own installation with `pytest --pyargs mhdpy`. Large test data, such as stored reference solutions, is kept outside the package so it does not inflate the installed size. What that data is, and where it lives, follows from brief 02.

### D01.5 — Build backend and versioning

> Superseded by D04.5 (2026-10-10): meson-python with cibuildwheel, because mhdpy's kernels are compiled with Cython.

Which build backend turns the source into installable packages (wheels and sdists), and where does the version number come from? The answer depends on whether mhdpy will contain compiled code, which is decided in brief 04. This sub-decision is therefore explicitly provisional: it covers the period until brief 04, and may be superseded there.

**Options**

- **A. uv_build.** uv's own backend: zero configuration, fast, and consistent with the uv workflow. Pure Python only. The version is written in `pyproject.toml` and bumped with `uv version --bump`.
- **B. hatchling (+ hatch-vcs).** Mature and widely used; pure Python only. With hatch-vcs, the version is derived from git tags, so it never has to be edited by hand.
- **C. setuptools (+ setuptools-scm).** What Pyro and Ulula use. Can build C and Cython extensions, but its configuration for extensions is the least transparent of the options.
- **D. meson-python.** **[GK]** What NumPy and SciPy moved to for their compiled code; first-class support for Cython, C and C++. Unnecessary overhead as long as the package is pure Python.
- **E. scikit-build-core.** **[GK]** The CMake-based counterpart of D; natural for C++ extensions.

**Recommendation.** A, uv_build, explicitly as an interim choice. As long as mhdpy is pure Python, the backend is a few lines in `pyproject.toml`. The simplest option integrated with the chosen workflow is preferable to anticipating brief 04. If brief 04 introduces compiled code, D01.5 is superseded there by D or E, and the switch costs only those few lines. The static version number of A is sufficient before the first release. This serves **readability** (in the sense of a simple, transparent setup); the higher priorities are not affected.

**Decision.** *(2026-10-09)* **A, uv_build, as an interim choice**, following the recommendation. It fits the uv workflow already chosen for development, and none of the alternatives offers an advantage while mhdpy is pure Python. The choice is to be revisited in brief 04.

### D01.6 — Dependency management and experiment environments

How are dependencies declared and locked, both for the package and for the experiments in the decision briefs? The decision briefs are frozen once decided, so their experiments must stay reproducible even after the project's own dependencies have moved on.

**Options for the package**

- **A. Runtime dependencies with lower bounds only, development tools in dependency groups, lockfile committed.** `pyproject.toml` lists what users need, with minimum versions but no upper caps. Upper caps on a library cause unsolvable conflicts in users' environments. Tools for testing, linting and documentation go into dependency groups (PEP 735), which are never installed for users. `uv.lock` is committed, so every developer and every CI run uses identical versions. CI additionally tests against the *lowest* allowed versions (`uv sync --resolution lowest-direct`), so the declared minimum versions are known to be true.
- **B. As A, but with development tools as optional extras** (`pip install mhdpy[dev]`). Extras are published to PyPI and visible to users, although they serve only developers.

**Options for the experiments**

- **C. A shared `experiments` dependency group in the project.** Simple, but the environment changes whenever the project lock changes. Experiments of a frozen brief may then no longer reproduce.
- **D. Each experiment is a self-contained script with inline dependencies (PEP 723) and its own lockfile** (`script.py.lock`, created with `uv lock --script`). It is rerun with `uv run script.py` and gets exactly the environment it was run with, independent of the project. Verified to work with the installed uv.
- **E. A separate uv project (`pyproject.toml` + `uv.lock`) per brief folder.** Also reproducible, but heavier, and it shares one environment between all experiments of a brief.

**Recommendation.** A for the package and D for the experiments. A is standard practice for libraries and keeps the published metadata clean. The lowest-version CI run adds a cheap check that the declared requirements are actually correct. D is the only option that matches the freezing rule exactly: each experiment carries its full environment with it, and a brief can be re-verified years later. Both serve **correctness**, here in the sense of reproducibility, the first priority. Under D, the experiment convention in `decisions/README.md` changes from "the pinned uv environment" to "the script's own lockfile". The experiment of this brief needs no third-party packages and already runs this way.

**Decision.** *(2026-10-09)* **A for the package and D for the experiments**, following the recommendation. Experiments are to be as self-contained as possible. For the runtime dependencies, one refinement is made: the lower bound of each dependency is set to the version current at the time it is added. This guarantees that no feature is used that the minimum version does not provide. Bounds are raised deliberately when a newer feature is needed. The CI job against the lowest allowed versions keeps checking that the declared bounds hold.

### D01.7 — Formatting, linting and code style

Which conventions does the code follow, and which tools enforce them? The tool is in practice ruff: **[GK]** a single fast tool that replaces black, isort, flake8, pyupgrade and many pylint and docstring checks, configured in `pyproject.toml`. It is still versioned 0.x, but has become the de facto standard. The four-tool combination Pyro uses (black, isort, flake8, pylint) does the same job with four configurations. The real question, raised by E01.2, is whether an *automatic formatter* is used at all, given a personal style it would partly overwrite.

**Options**

- **A. ruff format and ruff check, without exceptions.** All code is formatted automatically, so style never has to be discussed or reviewed, and code from other contributors conforms by itself. The cost, per E01.2: aligned assignments, spaced keyword arguments and continuations aligned under parentheses disappear.
- **B. ruff format and ruff check, with local exemptions.** As A, but blocks whose alignment carries meaning may be exempted with `# fmt: off` / `# fmt: on`, or `# fmt: skip` on a single line. Examples are coefficient tables, Butcher tableaux, stencil weights, or a group of related assignments. Everything else is formatted automatically. The cost is that exemptions must be used sparingly, or the benefit of A erodes.
- **C. ruff check only, no automatic formatter; a written style guide instead.** The personal style is kept in full: the lint rules that object to it (E221, E251) are simply not enabled. Formatting is done by hand and checked in review. The cost is that consistency rests on discipline, and other contributors must learn the style from a document rather than having a tool apply it.

Settings common to all options:

- **Line length:** 100 or 120 for code; E01.2 shows 120 fits the sample best. Optionally, a separate, shorter limit for comments and docstrings can be enforced (W505, `max-doc-length`), matching the habit of wrapping prose at about 80 characters.
- **Quotes:** double. That is the sample's style, so "preserve" makes no difference.
- **Comments:** the sample uses single `#`. A `##` style is left untouched by the formatter, and the only lint rule that would object (E266) is not enabled.
- **Names:** PEP 8 (`snake_case` for functions and variables, `CapWords` for classes), unlike Ulula's `camelCase`. Physics notation (`rho`, `vx`, `gamma`) is welcome where it mirrors the equations.
- **Lint rules** are active from the first commit. A starting set: pycodestyle (E, W), pyflakes (F), import sorting (I), bugbear (B), pyupgrade (UP), NumPy-specific checks (NPY) and docstring checks (D, NumPy convention).
- **Enforcement:** binding in CI on every change. Optionally also locally through git hooks, with pre-commit or its younger re-implementation prek.

**Recommendation.** B, with line length 120 for code and double quotes. The formatter takes away decisions that would otherwise be made by hand on every line and in every review. For a project that others should be able to pick up easily, that is the stronger argument: contributed code conforms without anyone having to learn a style document. The exemptions keep alignment exactly where it carries meaning, which in numerical code is mainly coefficient and stencil tables, rather than as a general habit. Of the three spacing habits, alignment is the only one with a real readability argument; keyword spacing and parenthesis-aligned continuations are matters of taste. Linting from the first commit, rather than later, follows from the evidence of Athena++ and Pyro: rules not adopted at the start end up suppressed. This serves **correctness**, since linting catches a class of bugs mechanically, and **readability**, through one consistent style. Neither costs performance.

**Decision.** *(2026-10-10)* **B, ruff format and ruff check, with local `# fmt: off` exemptions** for blocks whose alignment carries meaning, following the recommendation. The style review prompted by E01.2 also fixes the following house style:

- **Line length 120** for everything: code, comments and docstrings wrap at the same limit, checked by E501.
- **Double quotes** for strings.
- **Comments start with a double hash** (`## comment`). Rule E266, which objects to this, is disabled.
- PEP 8 names, the starting lint rule set listed above, and enforcement in CI on every change.

The sample used in E01.2 predates this review and does not follow the house style in every respect, for example in its single-`#` comments.

### D01.8 — Static type checking

Are type annotations checked statically, and with which tool? Annotations document the interfaces between the layers of mhdpy, which the extensibility criterion depends on. A checker verifies that those interfaces are used consistently.

**Options**

- **A. No static type checking.** Annotations, if any, serve only as documentation and can silently drift from the code.
- **B. mypy.** The reference implementation of Python typing; NumPy's type stubs are tested against it. Can be made strict for the framework layers and relaxed for numerical kernels, per module.
- **C. pyright.** Faster, with stronger type inference, and the engine behind VS Code's Python support. It runs on Node.js, which the `pyright` package from PyPI downloads behind the scenes.
- **D. A new Rust-based checker: ty or pyrefly.** Very fast. E01.1 shows ty is still pre-release (0.0.85); pyrefly has reached 1.x but is about a year and a half old.

A limitation applies to all of B–D. NumPy's typing describes the element type of an array (`NDArray[np.float64]`) but not its shape. Typing therefore checks the *interfaces* between components well and the numerical *contents* of kernels hardly at all. Compiled kernels (brief 04) would be opaque to every checker.

**Recommendation** *(revised 2026-10-09)*. C, pyright, strict for the framework and package interfaces and relaxed inside numerical kernels. Pyright supports this split directly, through per-directory `strict` settings and per-file `# pyright: strict` comments. The first draft recommended mypy as the most established option. That was revised on learning that development happens in VS Code, whose built-in type checking (Pylance) is built on pyright. With pyright in CI, the editor and the CI run report exactly the same errors. With mypy, two checkers would occasionally disagree, which costs time and teaches little. The Node.js dependency is handled transparently by the `pyright` package from PyPI. ty can be reconsidered once it reaches a stable release, which would be a superseding decision. This serves **correctness**, because inconsistent use of interfaces between layers is found before it runs, and **extensibility**, because typed interfaces are the documentation an extension author relies on.

**Decision.** *(2026-10-09)* **C, pyright**, following the revised recommendation: strict for framework and package interfaces, relaxed inside numerical kernels, and applied at all times, in the editor as well as in CI. The deciding argument is that the editor (VS Code with Pylance) and CI then always agree.

### D01.9 — Test runner

Which framework runs the tests? What is tested, and how correctness is demonstrated, is the subject of brief 02. This sub-decision only fixes the runner, since brief 02 builds on it.

**Options**

- **A. pytest.** The de facto standard, used by Pyro, with plain `assert` statements, fixtures and parametrisation, and a large plugin ecosystem: coverage (pytest-cov), parallel runs (pytest-xdist), property-based testing (Hypothesis), benchmarks. Athena++'s custom regression harness (prepare/run/analyse per test) maps naturally onto pytest fixtures.
- **B. unittest** (standard library). No dependency, but more verbose and without pytest's ecosystem.

**Recommendation.** A, pytest. It is the standard every Python contributor knows, and its parametrisation and plugins make the convergence studies of brief 02 straightforward to express. Serves **correctness** and **readability**.

**Decision.** *(2026-10-09)* **A, pytest**, following the recommendation, as the established standard for testing in Python.

### D01.10 — Documentation

Which docstring convention does the code use, and which tool will generate the documentation? The convention is needed from the first line of code; the documentation site can follow later.

**Options for docstrings**

- **A. NumPy style.** Used by Pyro, Ulula, NumPy, SciPy and Astropy. Well suited to describing array arguments, units and equations, and checkable by ruff (`D` rules) and numpydoc.
- **B. Google style.** More compact, less common in scientific Python.

**Options for the generator**

- **C. Sphinx with MyST.** The standard of the scientific Python ecosystem (Pyro, Ulula, NumPy, SciPy), and actively maintained (9.1, December 2025). With MyST, pages are written in Markdown, so `architecture.md` and the briefs can be included as they are. Strong support for API reference, cross-references, mathematics and bibliographies.
- **D. MkDocs with Material and mkdocstrings.** Pleasant to write and to look at. E01.1, however, shows the MkDocs core without a release since August 2024, and Material in maintenance with a pre-1.0 successor (Zensical, 0.0.69).

**Recommendation.** A and C: NumPy-style docstrings, and Sphinx with MyST when the documentation site is built. Both follow the reference codes and the wider ecosystem, so contributors meet familiar conventions. Sphinx is the only mature generator here whose future is not in question. This serves **readability** and **ease of use**; for documentation, ease of use for newcomers is the main point.

**Decision.** *(2026-10-09)* **A and C: NumPy-style docstrings, and Sphinx with MyST**, following the recommendation. A division of labour between docstrings and comments is adopted along with it:

- **Docstrings** are elaborate. They explain *what* a function, method or class does and *why*: its role in the algorithm, its assumptions, and its relation to the equations.
- **Comments** in the code explain *how* that goal is achieved, step by step.

### D01.11 — Docstring layout

*Added after experiment E01.2.* D01.10 chose NumPy-style docstrings rendered by Sphinx. E01.2 shows that the preferred docstring layout (`Parameters:` with a colon, a full-width `===` rule, `name: type, no default`) is not recognised by numpydoc, the parser Sphinx uses for NumPy-style docstrings. Which layout do the docstrings follow?

**Options**

- **A. The standard NumPy layout.** Section names without a colon, underlined with dashes of the same length (`Parameters` / `----------`), and parameters as `name : type, default 2`. Content and level of detail are unaffected: everything in the sample carries over unchanged (see `STANDARD_DOCSTRING` in the E01.2 script). In return, Sphinx renders parameter tables with linked types, ruff checks the layout (D rules), and editors such as VS Code show the docstrings formatted on hover. Two conventions come with it:
  - **[GK]** The NumPy convention documents a class's constructor parameters in the *class* docstring rather than in `__init__`.
  - Every docstring opens with a one-line summary, followed by an extended summary. The extended summary is the natural place for the elaborate *what* and *why* of D01.10.
- **B. The author's own layout.** Kept exactly as in the sample. Rendered documentation would show it as plain text, without parameter tables or type links, unless a custom Sphinx extension is written to parse it. The pydocstyle layout rules would have to be disabled, and contributors would meet a format they don't know.
- **C. Standard structure with personal touches that numpydoc tolerates.** As A, but with deviations the parser accepts, for example writing "no default" for required parameters. Whether a given deviation is tolerated has to be checked case by case, as was done for the full layout in E01.2.

**Recommendation.** A, the standard NumPy layout. The difference from the preferred layout is purely notational: colons and underline characters, not content. In exchange, the docstrings work with every tool chosen so far: Sphinx (D01.10), ruff's docstring checks (D01.7) and the editor. The elaborate *what* and *why* fits naturally in the extended summary that the standard layout prescribes. Option B would undo much of what D01.10 was chosen for. This serves **readability**, through documentation that renders properly, and **ease of use**, through a layout every scientific Python user recognises. Correctness and performance are unaffected.

**Decision.** *(2026-10-10)* **A, the standard NumPy layout**, following the recommendation, so that the docstrings can be rendered by Sphinx once the documentation is built. This includes its two conventions: constructor parameters are documented in the class docstring, and every docstring opens with a one-line summary followed by an extended summary.

## 4. Consequences for higher layers

**For every layer**

- All code is formatted by ruff at 120 characters, lint-clean from the first commit, and type-checked by pyright. Interfaces between layers must be fully annotated, and strictly checked. Numerical kernels may be checked more loosely.
- NumPy typing covers the element type of an array but not its shape. Shape and layout contracts between layers must therefore be stated in docstrings, and checked at runtime where it matters. This applies in particular to the data model (brief 06).
- Every component carries its own `tests/` folder inside `src/mhdpy/`, and the tests ship with the package.
- Every dependency is added with its current version as the lower bound, and the lowest-version CI job keeps those bounds honest. A dependency therefore has to earn its place, because it raises the minimum version users must have.
- Code features that exist only in Python 3.14 cannot be used until 3.13 leaves the support window, around October 2027.
- Code adapted from the reference codes carries an attribution comment and its licence in `LICENSES/`. Figures are always redrawn.

**For brief 02 (verification strategy)**

- The runner is pytest, and CI runs on macOS and Linux for Python 3.13 and 3.14, plus a job with the lowest allowed dependency versions. The verification strategy must fit within that matrix in run time.
- Tests ship with the package, but large reference data does not. Brief 02 has to decide what reference data is needed, where it lives, and how tests find it.

**For brief 04 (compute backend and kernel model)**

- Per E01.1, Numba and JAX have no wheels for Intel macOS, and none at all for Python 3.14 on that platform. On the development machine they cannot be installed with a single command, which conflicts with the installation exception of architecture.md §1.4 for every Intel-Mac user.
- If compiled code (for example Cython) is introduced, D01.5 (uv_build) is superseded by a backend for compiled extensions, such as meson-python or scikit-build-core. Wheels must then be built in CI for every supported platform and Python version, for example with cibuildwheel. Cython files are not covered by ruff (cython-lint would fill that gap) and are opaque to pyright.

**For brief 05 (parallelism)**

- The whole scientific stack offers wheels for free-threaded Python 3.14t (E01.1), so free-threading is a realistic option. It is officially supported only from 3.14, while 3.13 remains in the support window.
- MPI and parallel HDF5 are system libraries that uv does not manage. Their installation has to be addressed separately for macOS and Linux.

**For the documentation**

- Docstrings use the standard NumPy layout: a one-line summary, an extended summary explaining *what* and *why*, and constructor parameters in the class docstring. Comments explain *how*. The documentation site, once built, uses Sphinx with MyST, so `architecture.md` and the briefs can be included as they are.
