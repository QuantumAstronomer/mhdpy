# mhdpy: A Python-first Package for (Magneto)Hydrodynamics

> This document gives an architectural overview of the mhdpy package. Decision briefs are constructed based on reference (M)HD-codes (like Athena++), larger bodies of text (like the Computational Astrophysical Hydrodynamics book and Pyro-code by Michael Zingale), and experiments that provide, e.g., performance indications of crucial choices within the code. The decisions live in [`decisions/`](decisions/README.md), with each file stating clearly **what** was decided and **why**. The brief on each choice provides background from the reference codes ([Pyro](https://python-hydro.github.io/pyro2/index.html), [Ulula](https://bdiemer.bitbucket.io/ulula/index.html), and [Athena(++)](https://www.athena-astro.app/)) and evidence from the experiments. Based on this the different options are presented with a recommendation that fits the purpose of this code.

## 1. Purpose

### 1.1 Goals

The goal with mhdpy is to build a framework for astrophysical (magneto)hydrodynamical simulations within Python. It is meant for use in educational and scientific work: from standard verification problems to production-scale runs of the size used in published studies. It is recognised that these are ambitious targets that might lead to conflicts needing proper prioritisation of goals. However, the most important point (to the author) of building mhdpy is **learning**: 
- learning how to write *scientifically applicable*, i.e. accurate, code (physics that is demonstrably correct and extensible);
- learning to build a *large, multi-layered* software project robustly, in a form that others can pick up easily.

Besides learning, the other goal is **production-scale** runs. The inspiration for this coding project arose from prior work with production-grade MHD simulation software. This experience is on simulations of the scale of work by [Armillotta, Fraternali, and Marinacci 2016](https://ui.adsabs.harvard.edu/abs/2016MNRAS.462.4157A/abstract) (Galactic fountain clouds leading to coronal condensation to feed star formation), i.e. a simulation grid of roughly 4000x1000 cells without mesh refinement.

### 1.2 Scope

The *eventual* scope of mhdpy encapsulates all physics-modules that are implemented by state-of-the-art (magneto-)hydrodynamics codes (like Athena++), with a focus on astrophysical applications. This ranges from compressible hydrodynamics with general equations of state all the way to the inclusion of lagrangian particles for dust simulations. The whole scope shapes the architecture from the start, even for parts that will be implemented much later. In particular, the lower layers must be able to accommodate them without significant redesign.

### 1.3 Success criteria

The success of mhdpy is judged against four criteria, each formulated such that it can be checked rather than asserted. The learning goal is deliberately not among them. It is not a property of the finished code that could be measured, but is served by the way mhdpy is developed: every architectural choice is made explicitly in a decision brief, grounded in the reference material and supported by experiments.

**Correctness:** No physics module is considered complete before it is verified against problems with known (analytic) solutions. For smooth problems, the measured order of convergence must match the formal order of the scheme. For problems with discontinuities, results are compared with exact or reference solutions. Conserved quantities must be conserved to round-off error wherever the boundary conditions permit. Test problems are identical to the suites used by state-of-the-art reference codes. A capability counts as implemented once the corresponding reference tests are reproduced.

**Production Capability:** As a performance target a run at research-scale (similar to [Armillotta, Fraternali, and Marinacci 2016](https://ui.adsabs.harvard.edu/abs/2016MNRAS.462.4157A/abstract)) should finish overnight (within roughly twelve hours) on the development machine and within an hour on a small multi-core server. Such a run is two-dimensional, about 4 million cells (4000x1000), and includes hydrodynamics with radiative cooling, thermal conduction, and a passive scalar (in the form of metallicity). The cost of a run is roughly set by the total number of cell updates. This means that the runtime (barring any overhead) is simply the total number of cell updates divided by the cell update rate, i.e. cell updates per second. This is a criterion that can be easily tracked during development and a goal is set: A first estimate places the number of required cell updates at approximately $10^{11}$. This means that the overnight run on the development machine requires roughly $2 x 10^6$ cell updates per second and $3x10^7$ in the performance target of the small server. This estimate must be refined once representative runs exist.

**Extensibility:** New physics modules, like alternative cooling function, or a new Riemann solver can be added without changes to the framework. Every module beyond the hydrodynamics core serves as a test of this criterion: it must plug-in through the same interfaces.

**Usability:** Ease-of-use ties in with the extensibility criterion. However, it goes further than just being able to extend the code. mhdpy should install on macOS and Linux with a singular `pip` or `uv` command such that a newcomer can run a standard test problem within minutes by just following the documentation.

### 1.4 Priorities

The above-mentioned goals will, at times, pull in different directions. The decision briefs need a consistent way to resolve such conflicts of interest. Therefore, a ranking is made to apply priorities to criteria: Correctness always comes first: in scientific work, a result that is fast, code that is readable or convenient to work with holds no value if the result is simply wrong. Performance comes second, production-scale runs are a clear target and will contribute to the adoption of mhdpy. Therefore, it is decided that performance takes precedence over extensibility and usability. Sacrifices in terms of readability must be made if performance is to be achieved at times. Readability follows, since the code must remain understandable to serve the learning goal. Moreover, readable code improves its maintainability as it grows and writing extensions becomes very hard if the code to interface with is difficult to understand. Finally extensibility and ease-of-use come in. This means that less focus will be placed on the API, but it is not ignored completely. One exception is made to this ordering: installation must be as simple as possible, preferably through a single `pip` or `uv` command, whatever the ranking would otherwise imply. Every recommendation within a decision brief states where it falls in this ordering.

## 2. Decision briefs

The briefs below record the architectural decisions, layer by layer from the bottom up. Each row summarises what was decided; the brief itself gives the options, evidence and reasoning.

| Brief | Status | Summary of decisions |
|---|---|---|
| [D01 — Tooling and project conventions](decisions/D01-tooling/D01-tooling-brief.md) | Decided 2026-10-10 | GitHub with GitHub Actions; Python 3.13 and 3.14 under a rolling three-year window (SPEC 0); BSD-3-Clause, with third-party licences kept in `LICENSES/`; src layout with tests next to each component, shipped with the package; uv_build (interim, until brief 04); committed lockfile, lower bounds at current versions, self-contained experiment scripts with their own lockfiles; ruff format and ruff check at 120 characters, double quotes, `##` comments, `# fmt: off` only for meaningful alignment; pyright; pytest; standard NumPy-layout docstrings and Sphinx with MyST. |