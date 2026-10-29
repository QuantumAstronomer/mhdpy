# Plan of the reference syntheses

This file records how each synthesis of §4.1 of CLAUDE.md is split into steps, the decisions taken for it, and which of its steps are done. The steps of each synthesis are set when its work begins. Section signs refer to the reference, plain numbers to the sections of its synthesis.

## Zingale's text

The synthesis is kept in `computational-hydrodynamics-synthesis.md`. Its sources are `References/Computational Hydrodynamics Book/CompHydroTutorial.pdf` and, in the subfolder `drafts/` there, the draft chapters `gravity.tex` and `radiation.tex` of the same version.

The text is cited by title and date, as Zingale, *Introduction to Computational Astrophysical Hydrodynamics*, version of 26 January 2025, and its sections, equations, figures and tables by their numbers in that version. A **[GK]** mark covers the rest of its paragraph or list item. Where a web source disagrees with the text, the disagreement is reported for a decision, not settled in the synthesis. Slips that a derivation exposes are noted as **[GK]** without asking, and listed in the review of their step. Slips in wording without consequence are paraphrased correctly and listed in the review, but not noted. Gap fills likewise go in without asking, and are listed in the review. A gap fill or correction that can be neither derived nor checked against an accessible source is left out and reported in the review. Such sources include the other folders of `References/`. Exercises are not named, but a result of an exercise that the text relies on later is stated where it is used. Pointers to companion scripts are left out, and the overview names the three companion codes once. Test parameters that the text leaves out are not filled in from the companion codes. The tests that mhdpy reproduces come from the suites of the reference codes (§1.3 of CLAUDE.md), and pyro has a synthesis of its own.

The numerical methods are grouped into ten subjects, each fed by one or two consecutive chapters. The drafts join subject 2.6, marked as drafts. The software architecture draws on §3.4, §13.6, §13.7 and the appendices.

| Subsection | Subject | Chapters |
|---|---|---|
| 2.1 | Numerical foundations | 1, 2 |
| 2.2 | Finite-volume grids | 3 |
| 2.3 | Advection | 4, 5 |
| 2.4 | Burgers' equation | 6 |
| 2.5 | The Euler equations | 7, 8 |
| 2.6 | Elliptic equations and multigrid | 9, drafts |
| 2.7 | Diffusion | 10 |
| 2.8 | Multiphysics and reactive flow | 11, 12 |
| 2.9 | Planning a simulation | 13 |
| 2.10 | Low-speed flow | 14, 15 |

Each chapter is one step, and the two chapters longer than 25 pages are cut at section boundaries. The drafts follow in a step of their own at the end. The pages are those printed in the text; for the chapters, the page of the PDF is the printed page plus 22.

| Step | Part of the text | Pages | Feeds | Status |
|---:|---|---|---|---|
| 1 | Front matter: overview, scope, companion codes, notation | i–xxi | 1 | done |
| 2 | Ch. 1, Simulation Overview | 3–20 | 2.1 | done |
| 3 | Ch. 2, Classification of PDEs | 21–23 | 2.1 | done |
| 4 | Ch. 3, Finite-Volume Grids | 25–33 | 2.2, 3 | done |
| 5 | Ch. 4, Advection Basics | 37–47 | 2.3 | done |
| 6 | §5.1–5.3: finite-volume advection, limiting, method of lines | 49–62 | 2.3 | done |
| 7 | §5.4–5.7: multi-dimensional advection, high-order methods, WENO | 62–80 | 2.3 | done |
| 8 | Ch. 6, Burgers' Equation | 81–91 | 2.4 | done |
| 9 | Ch. 7, Euler Equations: Theory | 93–113 | 2.5 | done |
| 10 | §8.1–8.5: reconstruction, Riemann solvers, conservative update, boundary conditions | 115–131 | 2.5 | done |
| 11 | §8.6–8.9: multi-dimensional problems, source terms, geometries, test problems | 131–148 | 2.5 | done |
| 12 | §8.10–8.12: method of lines, thermodynamics, WENO | 148–159 | 2.5 | done |
| 13 | Ch. 9, Elliptic Equations and Multigrid | 163–184 | 2.6 | done |
| 14 | Ch. 10, Diffusion | 185–199 | 2.7 | done |
| 15 | Ch. 11, Model Multiphysics Problems | 203–208 | 2.8 | done |
| 16 | Ch. 12, Reactive Flow | 209–216 | 2.8 | done |
| 17 | Ch. 13, Planning a Simulation | 217–221 | 2.9, 3 | done |
| 18 | Ch. 14, Incompressible Flow and Projection Methods | 225–241 | 2.10 | done |
| 19 | Ch. 15, Low Mach Number Methods | 243–252 | 2.10 | done |
| 20 | App. A–C: the companion codes | 255–266 | 3 | done |
| 21 | Drafts: `gravity.tex` and `radiation.tex` | – | 2.6 | done |

## Pyro

The synthesis is kept in `pyro-synthesis.md`. Its sources are the pyro2 code with its documentation, in `References/Pyro/Code`, and two papers in `References/Pyro/Docs`: the pyro paper, Zingale (2014, `1306.6883v3.pdf`), and the paper in the Journal of Open Source Software (JOSS), Harpole et al. (2019, `1902.08702v1.pdf`). The copy of the code has no git metadata, and `pyproject.toml` takes the version from git tags, so the code is cited at version 4.5.1, the latest entry of `CHANGES.md`.

Code is cited by its path in the repository and the name of a function or class, as in (`pyro/compressible/riemann.py`, `riemann_hllc`), and the documentation by the path of its page. The papers are cited by arXiv identifier, with the numbers of sections, equations and figures in the local versions. A section sign without a named source refers to the pyro paper. The rules of the synthesis of Zingale's text carry over. A **[GK]** mark covers the rest of its paragraph or list item, and a disagreement with a web source is reported for a decision. Slips that a derivation exposes are noted as **[GK]** without asking. Slips in wording without consequence are paraphrased correctly without a note, and gap fills go in without asking. The review of each step lists all three. A gap fill or correction that can be neither derived nor checked against an accessible source, the other folders of `References/` included, is left out and reported in the review. Exercises, explorations and extensions that the documentation and the paper suggest are left out. The two rules on the companion codes lapse, as pyro is itself a code. A disagreement between the paper, the documentation and the code is reported for a decision in the review of its step, before it enters the synthesis. A wording slip that misstates the code without bearing on what pyro does, such as a wrong path, is paraphrased correctly without a note and listed in the review. Each problem setup is digested with its initial data, its boundary conditions and the parameters of its main inputs file, and its variants, such as other resolutions, in a line.

The numerical methods are grouped into ten subjects by solver family, following the packages of the code and its documentation. The software architecture draws on steps 1 to 4.

| Subsection | Subject | Packages |
|---|---|---|
| 2.1 | Grids, reconstruction and time integration | `mesh` |
| 2.2 | Advection | `advection`, `advection_rk`, `advection_fv4`, `advection_weno`, `advection_nonuniform` |
| 2.3 | Burgers' equation | `burgers`, `burgers_viscous` |
| 2.4 | Compressible hydrodynamics | `compressible`, `compressible_rk`, `compressible_fv4`, `compressible_sdc`, `compressible_react` |
| 2.5 | Shallow water | `swe` |
| 2.6 | Multigrid | `multigrid` |
| 2.7 | Diffusion | `diffusion` |
| 2.8 | Incompressible flow | `incompressible`, `incompressible_viscous` |
| 2.9 | Low Mach number atmospheric flow | `lm_atm` |
| 2.10 | Tracer particles | `particles` |

Each step takes one package, or a family of solvers that build on one another. With it come its pages of the documentation, its notebooks, problems and tests, the analysis scripts that check its output, and the sections of the pyro paper on it. Parts of more than about 2,000 lines, problems, tests and examples aside, are cut at module boundaries: `mesh`, the driver with its utilities, and `compressible`, whose problems take a step of their own. The framework comes first, then the shared kernels, then the solvers, with multigrid before the solvers that use it. Once a step is committed and pushed with the author's approval, the next step begins without a further request, while every commit and every push still needs an approval of its own.

Step 1 takes the README, licence, citation notes and change log, the introductory pages of the documentation, the JOSS paper, and §1, §4 and the acknowledgements of the pyro paper. Steps 2 to 4 share §2 of the pyro paper, step 2 also takes the introduction of its §3, and step 4 its §2.1. Its §3.1 to §3.5 join the steps on their solvers, with the Riemann solvers of §3.2 in step 9 and its tests, §3.2.1 to §3.2.3, in step 10. The pages `design`, `running` and `problems` of the documentation join step 3, with the notebooks on adding a problem and on running pyro. The pages `output`, `analysis` and `testing` join step 4, with the two notebooks for testing and the sections of the README on working with data and on testing. A review of the whole synthesis follows the last step. Left out are `presentations/`, `www/`, `logo/`, the API pages and build scripts of the documentation, and the files for continuous integration and the community. `paper/`, the source of the JOSS paper, serves only to check the PDF. Sizes are lines of Python without the tests, except in step 1.

| Step | Part of the reference | Pyro paper | Size | Feeds | Status |
|---:|---|---|---|---|---|
| 1 | Front matter, introductory pages, JOSS paper | §1, §4 | 3,440 words, 2 pp. | 1, 3 | done |
| 2 | `mesh`: grids, cell- and face-centred data, `ArrayIndexer`, boundary conditions | §2, §3 (introduction) | 1,810 | 3, 2.1 | done |
| 3 | Driver, `Pyro` and `NullSimulation` classes, runtime parameters | §2 | 1,150 | 3 | done |
| 4 | Output, plotting, profiling, testing, general analysis scripts | §2, §2.1 | 1,170 | 3 | done |
| 5 | `mesh`: limiters, flattening, WENO, fourth-order states, conversion between averages and centres, Runge-Kutta integration | – | 760 | 2.1 | done |
| 6 | The five advection solvers | §3.1 | 1,420 | 2.2 | |
| 7 | `burgers`, `burgers_viscous` | – | 970 | 2.3 | |
| 8 | `compressible`: interface states, unsplit fluxes, sources, boundaries, equation of state | §3.2 (method) | 1,920 | 2.4 | |
| 9 | `compressible`: Riemann solvers | §3.2 (Riemann solvers) | 1,180 | 2.4 | |
| 10 | `compressible`: 18 problem setups, comparisons with Sod and Sedov | §3.2.1–3.2.3 | 1,810 | 2.4 | |
| 11 | `compressible_rk`, `compressible_fv4`, `compressible_sdc`, `compressible_react` | – | 1,030 | 2.4 | |
| 12 | `swe` | – | 1,950 | 2.5 | |
| 13 | `multigrid` | §3.3 | 1,290, examples 2,230 | 2.6 | |
| 14 | `diffusion` | §3.4 | 400 | 2.7 | |
| 15 | `incompressible`, `incompressible_viscous` | §3.5 | 1,530 | 2.8 | |
| 16 | `lm_atm` | – | 1,510 | 2.9 | |
| 17 | `particles` | – | 360 | 2.10 | |

Two checks concern the synthesis of Zingale's text. Step 18 of that synthesis left one attribution unchecked. Zingale's text says in §14.3.5 that Chorin found the lagged pressure gradient $Gp^{n-1/2}$ in the provisional velocity necessary for second-order accuracy when viscosity is modelled, and cites only Chorin (1968, doi:10.1090/S0025-5718-1968-0242392-2). This is doubtful, as the scheme of that paper is generally described as computing the provisional velocity without a pressure gradient. The paper could not be reached, so 2.10.4 of the synthesis of Zingale's text keeps the claim as the text's. pyro's own material does not settle it. The pyro paper cites Chorin (1968) only for projection methods in general (§3.5), and the code offers the provisional update both with and without the lagged gradient (`proj_type` 1 and 2) without attributing either. Step 15 settles it from Chorin (1968) itself or from a review of projection methods. Step 4 checks 3.5 of the synthesis of Zingale's text, which describes pyro from the text, against the code. Each outcome is recorded where the claim is made, as a note marked **[GK]** in 2.10.4 or 3.5 of that synthesis, written in the step that settles it, and in this paragraph. Step 4 found the description of 3.5 outdated in four respects: the language of the kernels, the solvers and grids, the defaults of problems and the running of the unit tests. A note in 3.5 records them.

## Athena and Athena++

The steps of this synthesis are set when its work begins. In step 10 of the synthesis of Zingale's text, the edge values of the piecewise parabolic method and their limiter were left to this synthesis. Stone et al. (2008, arXiv:0804.0402, §4.2.3) state them, but both lines of their eq. 46 put a plus sign between the slope terms, as in $(\delta w^m_i + \delta w^m_{i-1})/6$, where a minus is right. With the plus sign, the edge value of a linear profile is wrong, and the interpolation of smooth data is first-order instead of fourth-order accurate. Athena++ uses the minus sign, in `src/reconstruct/reconstruction.cpp`.
