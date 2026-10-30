# Plan of the reference syntheses

This file records how each synthesis of §4.1 of CLAUDE.md is split into steps, the decisions taken for it, and which of its steps are done. The steps of each synthesis are set when its work begins. Section signs refer to the reference, plain numbers to the sections of its synthesis.

## Zingale's text

The synthesis is kept in `computational-hydrodynamics-synthesis.md`. Its sources are `reference-works/Computational Hydrodynamics Book/CompHydroTutorial.pdf` and, in the subfolder `drafts/` there, the draft chapters `gravity.tex` and `radiation.tex` of the same version.

The text is cited by title and date, as Zingale, *Introduction to Computational Astrophysical Hydrodynamics*, version of 26 January 2025, and its sections, equations, figures and tables by their numbers in that version. A **[GK]** mark covers the rest of its paragraph or list item. Where a web source disagrees with the text, the disagreement is reported for a decision, not settled in the synthesis. Slips that a derivation exposes are noted as **[GK]** without asking, and listed in the review of their step. Slips in wording without consequence are paraphrased correctly and listed in the review, but not noted. Gap fills likewise go in without asking, and are listed in the review. A gap fill or correction that can be neither derived nor checked against an accessible source is left out and reported in the review. Such sources include the other folders of `reference-works/`. Exercises are not named, but a result of an exercise that the text relies on later is stated where it is used. Pointers to companion scripts are left out, and the overview names the three companion codes once. Test parameters that the text leaves out are not filled in from the companion codes. The tests that mhdpy reproduces come from the suites of the reference codes (§1.3 of CLAUDE.md), and pyro has a synthesis of its own.

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

The synthesis is kept in `pyro-synthesis.md`. Its sources are the pyro2 code with its documentation, in `reference-works/Pyro/Code`, and two papers in `reference-works/Pyro/Docs`: the pyro paper, Zingale (2014, `1306.6883v3.pdf`), and the paper in the Journal of Open Source Software (JOSS), Harpole et al. (2019, `1902.08702v1.pdf`). The copy of the code has no git metadata, and `pyproject.toml` takes the version from git tags, so the code is cited at version 4.5.1, the latest entry of `CHANGES.md`.

Code is cited by its path in the repository and the name of a function or class, as in (`pyro/compressible/riemann.py`, `riemann_hllc`), and the documentation by the path of its page. The papers are cited by arXiv identifier, with the numbers of sections, equations and figures in the local versions. A section sign without a named source refers to the pyro paper. The rules of the synthesis of Zingale's text carry over. A **[GK]** mark covers the rest of its paragraph or list item, and a disagreement with a web source is reported for a decision. Slips that a derivation exposes are noted as **[GK]** without asking. Slips in wording without consequence are paraphrased correctly without a note, and gap fills go in without asking. The review of each step lists all three. A gap fill or correction that can be neither derived nor checked against an accessible source, the other folders of `reference-works/` included, is left out and reported in the review. Exercises, explorations and extensions that the documentation and the paper suggest are left out. The two rules on the companion codes lapse, as pyro is itself a code. A disagreement between the paper, the documentation and the code is reported for a decision in the review of its step, before it enters the synthesis. A wording slip that misstates the code without bearing on what pyro does, such as a wrong path, is paraphrased correctly without a note and listed in the review. Each problem setup is digested with its initial data, its boundary conditions and the parameters of its main inputs file, and its variants, such as other resolutions, in a line.

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
| 6 | The five advection solvers | §3.1 | 1,420 | 2.2 | done |
| 7 | `burgers`, `burgers_viscous` | – | 970 | 2.3 | done |
| 8 | `compressible`: interface states, unsplit fluxes, sources, boundaries, equation of state | §3.2 (method) | 1,920 | 2.4 | done |
| 9 | `compressible`: Riemann solvers | §3.2 (Riemann solvers) | 1,180 | 2.4 | done |
| 10 | `compressible`: 18 problem setups, comparisons with Sod and Sedov | §3.2.1–3.2.3 | 1,810 | 2.4 | done |
| 11 | `compressible_rk`, `compressible_fv4`, `compressible_sdc`, `compressible_react` | – | 1,030 | 2.4 | done |
| 12 | `swe` | – | 1,950 | 2.5 | done |
| 13 | `multigrid` | §3.3 | 1,290, examples 2,230 | 2.6 | done |
| 14 | `diffusion` | §3.4 | 400 | 2.7 | done |
| 15 | `incompressible`, `incompressible_viscous` | §3.5 | 1,530 | 2.8 | done |
| 16 | `lm_atm` | – | 1,510 | 2.9 | done |
| 17 | `particles` | – | 360 | 2.10 | done |

Two checks concern the synthesis of Zingale's text. Step 18 of that synthesis left one attribution unchecked. Zingale's text says in §14.3.5 that Chorin found the lagged pressure gradient $Gp^{n-1/2}$ in the provisional velocity necessary for second-order accuracy when viscosity is modelled, and cites only Chorin (1968, doi:10.1090/S0025-5718-1968-0242392-2). This is doubtful, as the scheme of that paper is generally described as computing the provisional velocity without a pressure gradient. The paper could not be reached, so 2.10.4 of the synthesis of Zingale's text keeps the claim as the text's. pyro's own material does not settle it. The pyro paper cites Chorin (1968) only for projection methods in general (§3.5), and the code offers the provisional update both with and without the lagged gradient (`proj_type` 1 and 2) without attributing either. Step 15 settles it from Chorin (1968) itself or from a review of projection methods. Step 4 checks 3.5 of the synthesis of Zingale's text, which describes pyro from the text, against the code. Each outcome is recorded where the claim is made, as a note marked **[GK]** in 2.10.4 or 3.5 of that synthesis, written in the step that settles it, and in this paragraph. Step 4 found the description of 3.5 outdated in four respects: the language of the kernels, the solvers and grids, the defaults of problems and the running of the unit tests. A note in 3.5 records them. Step 15 could reach neither Chorin (1968) nor a review of projection methods, as the sites that hold them refuse automated access, and the author chose to leave the attribution open. A note in 2.10.4 records this, and the claim stays the text's.

## ZEUS

The synthesis is kept in `zeus-synthesis.md`. Its sources are the three papers on ZEUS-2D in `reference-works/Zeus/Docs`, which describe its hydrodynamic, magnetohydrodynamic and radiation hydrodynamic algorithms and tests in ApJS 80 of June 1992: Stone and Norman (1992a, doi:10.1086/191680, `1992ApJS80753S.pdf`), Stone and Norman (1992b, doi:10.1086/191681, `1992ApJS80791S.pdf`), and Stone, Mihalas and Norman (1992, doi:10.1086/191682, `1992ApJS80819S.pdf`). The papers call one another Paper I, II and III, and this section names them I, II and III. The local copies are scans from the ADS. Their text layer, made by optical character recognition, garbles the equations, which are therefore read from the page images. The code of ZEUS-2D is not among the sources.

Each paper is cited by author and year, with the numbers of its sections, equations, figures and tables, as in Stone and Norman (1992b, §3.2.2, eq. 22). Its DOI is given at its first citation and in the list of sources. Within a paragraph, later citations of the same paper give the numbers alone. The rules of the synthesis of Pyro carry over. A **[GK]** mark covers the rest of its paragraph or list item, and a disagreement with a web source is reported for a decision. Slips that a derivation exposes are noted as **[GK]** without asking. Slips in wording without consequence are paraphrased correctly without a note, and gap fills go in without asking. The review of each step lists all three. A gap fill or correction that can be neither derived nor checked against an accessible source, the other folders of `reference-works/` included, is left out and reported in the review. A disagreement between the three papers is reported for a decision in the review of its step, before it enters the synthesis. The rules on code, exercises and companion codes lapse. A later paper on the methods of ZEUS enters only as a **[GK]** note where it corrects or qualifies a claim of the papers. In step 4, at the author's request, two later copies of the code from the Internet Archive settled a question the papers leave open: release 2.0.3 of the Laboratory for Computational Astrophysics (2007) and Stone's version 2.0 (2003). They are not among the sources, and like later papers they enter only in notes marked **[GK]**. After step 6 the author decided that they may also confirm slips that a derivation finds, without replacing the derivation. Each test problem is digested with its initial data, boundary conditions, grid, parameters and stopping time, and with the outcome that the paper reports and the numbers that state it. Its variants, such as other resolutions or algorithms, take a line, and the content of a table is restated in prose.

The numerical methods are grouped into twelve subjects by component. The software architecture draws on the solution procedure of I §4 and §4.8, and on how II §3.5 and III §5 add the modules for magnetohydrodynamics and radiation.

| Subsection | Subject | Sections |
|---|---|---|
| 2.1 | The equations and the split solution procedure | I §2, §4 (introduction) |
| 2.2 | The staggered mesh and the covariant formalism | I §4.1, §4.2, App. A, App. C |
| 2.3 | The source step and artificial viscosity | I §4.3, App. B |
| 2.4 | The transport step | I §4.4 |
| 2.5 | Boundary conditions and the time step | I §4.5, §4.6 |
| 2.6 | Self-gravity | I §4.7 |
| 2.7 | Hydrodynamic tests | I §5 |
| 2.8 | Magnetohydrodynamics | II §2, §3 |
| 2.9 | Magnetohydrodynamic tests | II §4 |
| 2.10 | The radiation moment equations | III §2, §3, App. A |
| 2.11 | The transfer equation and the Eddington factors | III §4 |
| 2.12 | Radiation hydrodynamic tests | III §6, §7 |

Each step takes consecutive sections of one paper, at most about 4,000 words, cut at section boundaries. An appendix joins the step on the section that it serves. The introduction of each paper opens its first step and its summary closes its last, and both feed the overview. Paper I takes eight steps, II and III five each. Once a step is committed with the author's approval, the next step begins without a further request, while every commit, merge and push still needs an approval of its own. A review of the whole synthesis follows the last step. The pages are those printed in ApJS 80, and the page of the PDF is the printed page minus 752 for I, 790 for II and 818 for III. Sizes are words of the text layer, rounded to hundreds.

| Step | Part of the reference | Pages | Size | Feeds | Status |
|---:|---|---|---|---|---|
| 1 | I §1–§3: introduction to the series, the equations of hydrodynamics, the origin of ZEUS | 753–755 | 1,900 | 1, 2.1 | done |
| 2 | I §4 (introduction), §4.1: operator splitting into source and transport steps, the staggered mesh | 755–759 | 2,500 | 2.1, 2.2, 3 | done |
| 3 | I §4.2, App. A, App. C: the covariant formalism, its operators and difference formulae | 759–761, 785–788, 789–790 | 2,800 | 2.2, 3 | done |
| 4 | I §4.3, App. B: the source step, the tensor artificial viscosity | 761–763, 788–789 | 2,200 | 2.3 | done |
| 5 | I §4.4: the transport step, its interpolation schemes and directional splitting | 763–766 | 2,700 | 2.4 | done |
| 6 | I §4.5–§4.8: boundary conditions, stability and accuracy, the Poisson equation, program control | 766–772 | 3,200 | 2.5, 2.6, 3 | done |
| 7 | I §5.1–§5.4: advection tests, pressure-free collapse, the Sod shock tube | 772–776 | 2,300 | 2.7 | done |
| 8 | I §5.5–§6: tests with strong shocks, tests of the Poisson solver, summary | 776–785 | 3,500 | 2.7, 1 | done |
| 9 | II §1–§3.1: the equations of magnetohydrodynamics, the divergence constraint and the wave families, the centring of variables | 791–793 | 2,700 | 1, 2.8 | done |
| 10 | II §3.2–§3.2.2: the poloidal field by constrained transport, the EMFs by the method of characteristics | 793–797 | 3,200 | 2.8 | done |
| 11 | II §3.2.3–§3.5: the Lorentz force, the toroidal field, boundary conditions, incorporation into ZEUS-2D | 797–801 | 2,900 | 2.8, 3 | done |
| 12 | II §4.1–§4.3: advection tests, an MHD Riemann problem, the Weber–Davis wind | 801–811 | 4,300 | 2.9 | done |
| 13 | II §4.4–§5: the coronal transient models of Low, magnetic braking of an aligned rotator, shear Alfvén waves, summary | 811–818 | 4,100 | 2.9, 1 | done |
| 14 | III §1–§2: the equations of radiation hydrodynamics, the comoving moment equations, their coupling to the hydrodynamics | 819–823 | 3,900 | 1, 2.10 | done |
| 15 | III §3, App. A: solving the moment equations in the source and transport steps | 823–828, 843–845 | 3,700 | 2.10 | done |
| 16 | III §4–§4.2: the transfer equation, the radiation grid, the method of short characteristics | 828–834 | 3,400 | 2.11 | done |
| 17 | III §4.3–§6: the Eddington factors, incorporation of the radiation module, tests of the moment solver | 834–838 | 2,700 | 2.11, 3, 2.12 | done |
| 18 | III §7–§8: tests of the transfer solver, summary | 838–843 | 2,200 | 2.12, 1 | done |

## Ulula

The synthesis is kept in `ulula-synthesis.md`. Its sources are the `ulula` package with its `pyproject.toml`, README and documentation, in `reference-works/Ulula/Code`, and the Ulula paper in `reference-works/Ulula/Docs`, Diemer (2025, `2505.20399v1.pdf`). arXiv holds only this first version of the paper. The copy of the code has no git metadata. `pyproject.toml` takes the version from `ulula/utils/version.py`, so the code is cited at version 1.0.2, which is also the latest entry of the version history in the documentation. The paper appeared on the day of release 1.0.1, and by that history 1.0.2 changed only the build system. The text layer of the PDF renders the prose well but scrambles the displayed equations, which are therefore read from the page images.

Code is cited by its path in the repository and the name of a function or class, as in (`ulula/core/simulation.py`, `Simulation.riemannSolverHLLC`), and the documentation by the path of its page. The paper is cited by arXiv identifier, with the numbers of its sections, equations, figures and tables. A section sign without a named source refers to the paper. The rules of the synthesis of Pyro carry over unchanged. A **[GK]** mark covers the rest of its paragraph or list item, and a disagreement with a web source is reported for a decision. Slips that a derivation exposes are noted as **[GK]** without asking. Slips in wording without consequence are paraphrased correctly without a note, and gap fills go in without asking. The review of each step lists all three. A gap fill or correction that can be neither derived nor checked against an accessible source, the other folders of `reference-works/` included, is left out and reported in the review. A disagreement between the paper, the documentation and the code is reported for a decision in the review of its step, before it enters the synthesis. A wording slip that misstates the code without bearing on what Ulula does, such as a wrong list of parameters in a docstring, is paraphrased correctly without a note and listed in the review. Explorations and extensions that the paper and the documentation suggest are left out, such as the open questions that close §4.1 and the developments that §5 proposes. The limits of Ulula's scope that §5 names enter the overview. Each problem setup is digested with its initial data, boundary conditions, equation of state and gravity, its default parameters, and the resolution, final time and scheme of its example in `examples.py`. With them come its known solution and how the code computes it, and the outcome that the paper and the documentation report, with the numbers that state it. Its variants take a line.

The numerical methods are grouped into eight subjects by component, following §2 to §4 of the paper and its Table 1. The software architecture draws on steps 1 to 3 and 8 to 10, and takes up §4.3 on performance as a property of the implementation in NumPy.

| Subsection | Subject | Sections |
|---|---|---|
| 2.1 | The equations and equations of state | §2 |
| 2.2 | The grid and boundary conditions | §3.6 (boundary conditions) |
| 2.3 | The time step and source terms | §3 (introduction), §3.1 |
| 2.4 | Riemann solvers | §3.2 |
| 2.5 | Reconstruction and slope limiting | §3.3 |
| 2.6 | Time interpolation | §3.4 |
| 2.7 | Gravity | §3.5 |
| 2.8 | Problem setups and tests | §4.1, §4.2 |

Each step takes one part of the code with the sections of the paper and the pages of the documentation on it. `simulation.py`, which holds the whole numerical method, is cut at the boundaries of its functions into six steps, one per component: the equations and the domain first, then the components in the order of §3. The driver, input and output, plotting and units take one step. The setups take two, first the base class with the six setups in one dimension, then the nine in two, each setup with its example from `examples.py` and its image from the documentation. Step 1 takes the README, the licence, `pyproject.toml` and the pages `index`, `installation` and `versions` of the documentation, and the abstract, §1, §5 and the acknowledgements of the paper. The page `simulation` joins step 2, except its section on input and output, which joins step 8 with the pages `run` and `plots`. Table 1 joins step 2, as the class `HydroScheme` holds the choices it lists. The pages `setups`, `setups_base` and `setups_1d` join step 9, and `setups_2d` joins step 10. Figs. 1 and 2 join step 6, Fig. 6 step 9, and the other figures step 10, with their setups and with §4.2 and §4.3. Left out are the build files of the documentation, `conf.py` and `Makefile`, and its logo and icon. Once a step is committed with the author's approval, the next step begins without a further request, while every commit and every push still needs an approval of its own. A review of the whole synthesis follows the last step. Sizes are lines of Python, except in step 1.

| Step | Part of the reference | Ulula paper | Size | Feeds | Status |
|---:|---|---|---|---|---|
| 1 | Front matter: README, licence, packaging, introductory pages and version history | Abstract, §1, §5 | 1,500 words | 1, 3 | done |
| 2 | `simulation.py`: the hydro scheme, the fields of a simulation, equations of state, conversion between primitive and conserved variables, the flux vector, the sound speed | §2, Table 1 | 500 | 2.1, 3 | done |
| 3 | `simulation.py`: the domain, its ghost cells and indexing, standard and user-defined boundary conditions, user-defined updates | §3.6 (boundary conditions) | 390 | 2.2, 3 | done |
| 4 | `simulation.py`: the time step, the order of the sweeps, the CFL condition and its violations, the half-steps of the source terms | §3 (introduction), §3.1 | 200 | 2.3 | done |
| 5 | `simulation.py`: the HLL and HLLC Riemann solvers | §3.2 | 160 | 2.4 | done |
| 6 | `simulation.py`: piecewise-constant and piecewise-linear reconstruction, slope limiters, the Hancock step in conserved and in primitive variables | §3.3, §3.4 | 270 | 2.5, 2.6 | done |
| 7 | `simulation.py`: the modes of gravity, the Poisson solver by fast Fourier transform, the gravitational source terms | §3.5 | 200 | 2.7 | done |
| 8 | Saving and loading, the runtime function, plotting, code units and the units of plots, physical constants, utilities | §3.6 | 1,680 | 3 | done |
| 9 | The base class of setups and the six setups in one dimension, with their examples | §4 (introduction), §4.1 (setups in one dimension) | 1,620 | 2.8, 3 | done |
| 10 | The nine setups in two dimensions, with their examples | §4.1 (setups in two dimensions), §4.2, §4.3 | 1,710 | 2.8, 3 | done |

Two claims of the sources concern other references. §1 describes pyro as many times larger than Ulula and as speeding up certain routines by just-in-time compilation, and step 1 checks this against the synthesis of Pyro. The docstring of `Simulation.solveGravity` refers to §9.2 of Zingale's text for the derivation of the Green's function of the discrete Laplacian, and step 7 checks this against 2.6.2 of the synthesis of Zingale's text. Each outcome is recorded in the synthesis of Ulula, as a note marked **[GK]** where a claim does not hold.

## Athena and Athena++

The synthesis is kept in `athena-synthesis.md`. Its sources are the code of Athena++ in `reference-works/Athena/Code` and thirteen papers in `reference-works/Athena/Docs`, each named by its arXiv identifier and each the latest version on arXiv. Seven describe Athena, the predecessor of Athena++ written in C, whose code is not among the sources: Gardiner and Stone (2005, `0501557v1.pdf`; 2008, `0712.2634v1.pdf`) on the unsplit integrator with constrained transport (CT) in two and three dimensions, Stone et al. (2008, `0804.0402v1.pdf`) on the code, Skinner and Ostriker (2010, `1004.2487v1.pdf`) on cylindrical coordinates, Stone and Gardiner (2010, `1006.0139v1.pdf`) on the shearing box, Bai and Stone (2010, `1005.4980v2.pdf`) on particles, and Beckwith and Stone (2011, `1101.3573v1.pdf`) on relativistic MHD. Six describe Athena++: Stone et al. (2020, `2005.06651v1.pdf`) on the code, Felker and Stone (2018, `1711.07439v2.pdf`) on its fourth-order method, White, Stone and Gammie (2016, `1511.00943v2.pdf`) on general relativistic MHD, Tomida and Stone (2023, `2302.13903v1.pdf`) on multigrid, Coleman (2020, `1909.05274v3.pdf`) on general equations of state, and Mullen, Hanawa and Gammie (2021, `2012.01340v1.pdf`) on self-gravity. The last five come from the list of publications on the website of Athena++, athena-astro.app/publications.html, as the papers on modules that the synthesis digests in full. The others on that list describe modules digested in outline, a relativistic radiation module that this copy lacks, or codes outside it. The wiki of Athena++ is not a source, but its pages may be consulted as web sources.

One paper that the documentation of Athena lists among its method papers is not among the sources: Stone and Gardiner (2009), A simple unsplit Godunov method for multidimensional MHD, New Astronomy 14, 139–148, doi:10.1016/j.newast.2008.06.003, on the van Leer integrator. No legitimate free copy could be found. arXiv holds no version of it, the ADS links only to the publisher, and OpenAlex and Semantic Scholar mark it as closed. The research portal of Princeton University and the documentation of Athena also link only to the publisher and to the ADS. Its integrator is still covered. Beckwith and Stone (2011, §3.5) set out its steps and use its §4.3 for the electric fields of CT, Stone et al. (2020, §3.2.3) give its coefficients and its limits of stability, and `src/task_list/time_integrator.cpp` implements it as VL2. Its derivation, its comparison with the corner transport upwind (CTU) integrator and its tests are not available.

The copy of the code has no git metadata. It is cited at release v24.0 of 1 April 2024, the latest entry of `CHANGELOG.md`, while `CITATION.cff` still names release 21.0. The copy is later than v24.0. It agrees with commit 823614c of 13 August 2026 on the branch `main` in all of its 655 files, and lacks only the hidden files of the repository. It differs from v24.0 in 82 files and holds four files that v24.0 lacks: `weno.cpp`, `ppm_fast.cpp` and `ppm_simple_fast.cpp` in `src/reconstruct/`, and `src/chemistry/network/none.cpp`. A note in 1.1 records this, and the synthesis describes these files as they are in the copy. The text layers of the PDFs render the prose well but can scramble the displayed equations, which are then read from the page images.

Code is cited by its path in the repository and the name of a function or class, as in (`src/hydro/rsolvers/mhd/hlld.cpp`, `Hydro::RiemannSolver`). The papers are cited by author and year, with the numbers of their sections, equations, figures and tables in the local versions, as in Stone et al. (2008, §4.2.3, eq. 46). The arXiv identifier is given at the first citation and in the list of sources, which adds the DOI. This section abbreviates the papers by the initials of their authors and the year: GS05, GS08, S08, SO10, SG10, BS10, BS11, S20, FS18, WSG16, TS23, C20 and MHG21.

The rules of the synthesis of Ulula carry over. A **[GK]** mark covers the rest of its paragraph or list item, and a disagreement with a web source is reported for a decision. Slips that a derivation exposes are noted as **[GK]** without asking. Slips in wording without consequence are paraphrased correctly without a note, and gap fills go in without asking. The review of each step lists all three. A gap fill or correction that can be neither derived nor checked against an accessible source, the other folders of `reference-works/` included, is left out and reported in the review. A wording slip that misstates the code without bearing on what it does, such as a wrong parameter in a comment, is paraphrased correctly without a note and listed in the review. Explorations and extensions that the papers suggest are left out. The synthesis gives one account of each method, drawn from the papers and the code together. The papers on Athena describe what Athena does, and the code and the papers on Athena++ what Athena++ does. Where the two codes differ, the account says so as a difference between them. Where a paper on Athena++ and the code differ, the difference is reported for a decision in the review of its step, before it enters the synthesis. Two such differences are known already. The fourth-order CT of FS18 (§4, §5, App. A) is not part of the copy, whose reconstruction refuses the fourth order with MHD as not yet merged, and `src/hydro/srcterms/self_gravity.cpp` implements the conservative source terms of MHG21 for the momentum only. After batch 1 the author decided that the slips of S20 eqs. 6b and 6c and of WSG16 eq. 32, which a derivation exposes and the code avoids, are corrected in the text without a note and listed in the review.

The framework and the non-relativistic hydrodynamics and MHD are digested in full, with diffusion, passive scalars, self-gravity, input and output, and their tests. Relativity, radiation transport, cosmic rays, chemistry, orbital advection and the driving of turbulence are digested in outline: the equations that a module solves, its method in brief, its options and parameters, how it enters the task lists and the boundary classes, and its tests by name. The papers are digested in full throughout, also where they describe a module whose code is outlined, so that relativity takes six steps. Each problem is digested with its initial data, boundary conditions, grid, parameters and stopping time, from the papers and from its problem generator and input file. With them come its known solution, where it has one, and the outcome that the papers and the regression tests report, with the numbers that state it. Its variants take a line, and the content of a table is restated in prose.

The numerical methods are grouped into sixteen subjects by component, and the software architecture into nine.

| Subsection | Subject | Steps |
|---|---|---|
| 2.1 | The equations and the finite-volume discretisation | 2 |
| 2.2 | Equations of state | 3, 9 |
| 2.3 | Constrained transport | 4, 5 |
| 2.4 | Reconstruction | 6, 7, 18 |
| 2.5 | Riemann solvers | 8 |
| 2.6 | Time integration | 10–13 |
| 2.7 | The fourth-order method | 14–16 |
| 2.8 | Curvilinear coordinates | 17–19 |
| 2.9 | Source terms, the shearing box and orbital advection | 20–23 |
| 2.10 | Self-gravity | 24–29 |
| 2.11 | Diffusion and super time-stepping | 30, 31 |
| 2.12 | Passive scalars | 32 |
| 2.13 | Particles | 33, 34 |
| 2.14 | Relativistic MHD | 35–40 |
| 2.15 | Radiation, cosmic rays, chemistry and the driving of turbulence | 41–44 |
| 2.16 | Tests of hydrodynamics and MHD | 57–62 |
| 3.1 | Configuration, build and the main loop | 51 |
| 3.2 | Arrays, the mesh and its blocks | 2, 45 |
| 3.3 | Boundaries and their communication | 22, 46, 47 |
| 3.4 | Mesh refinement | 27, 48, 49 |
| 3.5 | Task lists and parallelisation | 26, 31, 41–44, 50 |
| 3.6 | Problem generators and user functions | 52 |
| 3.7 | Output, restarts and visualisation | 53, 54 |
| 3.8 | Regression tests | 55 |
| 3.9 | Performance | 56 |

Each step takes one component, with the sections of the papers on it and the code that implements it. Steps have no limit of size, but a component that would bring more than a review can absorb is cut into several steps at the boundaries of sections and files (§2.2 of CLAUDE.md). The numerical methods come first, then the modules in outline, then the framework, and last the tests. The tests of hydrodynamics and MHD are grouped by family of problems, each drawing on every paper that runs it, with its problem generator, its input files and its regression tests. Tests aimed at one component, such as those of the equations of state, the fourth-order method, the curvilinear coordinates, the shearing box, multigrid, the particles, relativity and mesh refinement, follow that component. The abstracts, introductions, summaries and acknowledgements of the two papers on the codes, S08 and S20, join step 1, as they describe a code as a whole. The abstract, introduction and acknowledgements of each other paper join the first step on its main subject, and its summary the last. Each input file joins the step of its problem generator. Left out are the FFT library of Plimpton in `src/fft/plimpton/`, which has a licence of its own, the scripts for style and continuous integration in `tst/style/` and `tst/ci/`, the configuration of Doxygen in `doc/`, `CPPLINT.cfg` and `setup.cfg`. The reference data in `tst/regression/data/` are only named. The steps are worked in batches of five, steps 1 to 5 first, and each step keeps a commit of its own. A batch is digested completely before any of its steps is committed. If no step of a batch raises a point for the author's decision, its steps are committed without asking, and its reviews are reported to the author while the work goes on with the next batch. The author has granted this standing approval for the steps of this synthesis only, as an exception to §2.1 of CLAUDE.md. Otherwise the five steps are put to the author together, with their reviews and open points, and the work waits until these are decided, after which the steps are committed. A point that the rules leave out and report does not hold a batch. Each batch that is put to the author also asks whether to push the commits so far. A review of the whole synthesis follows the last step. Sizes are words of the text layers of the papers, rounded to hundreds, and lines of the files of the code, its tests and scripts included, rounded to tens.

| Step | Component | Papers | Code | Size | Feeds | Status |
|---:|---|---|---|---|---|---|
| 1 | Overview of Athena and Athena++ | S08 abstract, §1, §9; S20 abstract, §1, §5, §6 | `README.md`, `LICENSE`, `CITATION.cff`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` | 5,800 words, 1,110 lines | 1, 3 | done |
| 2 | The equations and the finite-volume discretisation; variables and arrays | S08 §2, §3 (introduction), §3.1; S20 §3 (introduction), §3.1 | `athena.hpp`, `athena_arrays.hpp`, `hydro/hydro.*` | 1,900 words, 1,110 lines | 2.1, 3.2 | done |
| 3 | Equations of state: adiabatic, isothermal and general, with tables | C20 abstract, §1–§3.2, App. B | `eos/` without the relativistic, high-order and scalar files, `utils/eos_table_class.cpp`, `utils/interp_table.*` | 3,000 words, 1,980 lines | 2.2 | done |
| 4 | Constrained transport: the field as area averages, consistency with the finite volumes | GS05 abstract, §1, §2; GS08 §2; S08 §3.2 | `field/field.*`, `field/ct.cpp` | 4,200 words, 500 lines | 2.3 | done |
| 5 | The electric fields at cell corners | GS05 §3.2, §6; GS08 §4; S08 §5.3; WSG16 §3.5 | `field/calculate_corner_e.cpp` | 4,700 words, 250 lines | 2.3 | done |
| 6 | Reconstruction of first and second order, characteristic variables | S08 §4.2–§4.2.2, App. A; S20 §3.2 (introduction), §3.2.1 | `reconstruct/reconstruction.*` (options), `dc.cpp`, `plm.cpp`, `characteristic.cpp` | 3,000 words, 1,630 lines | 2.4 | done |
| 7 | The piecewise parabolic method and WENO | S08 §4.2.3 | `reconstruct/ppm.cpp`, `ppm_fast.cpp`, `weno.cpp` | 700 words, 2,060 lines | 2.4 | – |
| 8 | Riemann solvers, the carbuncle and its cures | S08 §4.3–§4.3.2, App. B, App. C; S20 §3.2.2; C20 §3.3, App. A | `hydro/rsolvers/` without the relativistic solvers, `hydro/calculate_velocity_differences.cpp`, `pgen/quirk.cpp`, tests of the carbuncle | 5,200 words, 3,360 lines | 2.5 | – |
| 9 | Tests of general equations of state | C20 §4–§6, App. C | `pgen/eos_test.cpp`, tests `eos/`, `tst/regression/scripts/utils/EquationOfState/` | 6,700 words, 1,290 lines | 2.2 | – |
| 10 | The one-dimensional algorithm of Athena and its first-order unsplit scheme with CT | S08 §4 (introduction), §4.1; GS05 §3 (introduction), §3.1 | – | 2,400 words | 2.6 | – |
| 11 | The CTU integrator in two dimensions | GS05 §4; S08 §5–§5.2 | – | 3,700 words | 2.6 | – |
| 12 | The CTU integrator in three dimensions | GS08 abstract, §1, §3, §5, §7; S08 §6 | – | 7,500 words | 2.6 | – |
| 13 | The van Leer and Runge–Kutta integrators, the fluxes and the time step | S20 §3.2.3; BS11 §3.5; WSG16 §3.7 | `task_list/time_integrator.cpp` (integrators), `mesh/weighted_ave.cpp`, `hydro/calculate_fluxes.cpp`, `hydro/add_flux_divergence.cpp`, `hydro/new_blockdt.cpp`, `Mesh::NewTimeStep` | 1,900 words, 2,630 lines | 2.6 | – |
| 14 | The fourth-order method for hydrodynamics | FS18 abstract, §1–§3 | `eos/eos_high_order.cpp`, the fourth-order initial conditions in `mesh/mesh.cpp`, tests `hydro4/` | 5,800 words, 600 lines | 2.7 | – |
| 15 | Upwind CT of fourth order, not part of the copy | FS18 §4, App. A | – | 7,700 words | 2.7 | – |
| 16 | Tests of the fourth-order method for MHD | FS18 §5, §6 | – | 6,000 words | 2.7 | – |
| 17 | Curvilinear coordinates: geometry, finite volumes and CT | SO10 abstract, §1–§3, §7–§9; S20 §2.3, §3.2.4 | `coordinates/` without the relativistic files | 6,100 words, 2,670 lines | 2.8 | – |
| 18 | Reconstruction and characteristic evolution on curvilinear and nonuniform grids | SO10 §4–§6; WSG16 §3.2 | the curvilinear weights in `reconstruct/reconstruction.cpp`, `dc_simple.cpp`, `plm_simple.cpp`, `ppm_simple.cpp`, `ppm_simple_fast.cpp`, the tests after Mignone | 5,800 words, 4,440 lines | 2.4, 2.8 | – |
| 19 | Tests in curvilinear coordinates | SO10 §10, §11; S20 §3.5 | `pgen/mignone_advection.cpp`, `slotted_cylinder.cpp`, `field_loop_poles.cpp`, `disk.cpp`, `utils/gl_quadrature.*`, tests `curvilinear/` | 5,600 words, 3,350 lines | 2.8 | – |
| 20 | Source terms: constant acceleration, point mass, rotating frame | – | `hydro/srcterms/hydro_srcterms.*`, `constant_acc.cpp`, `pointmass.cpp`, `rotating_system_srcterms.cpp` | 460 lines | 2.9 | – |
| 21 | The shearing box: equations and source terms | SG10 abstract, §1–§3; S20 §3.2.6 | `hydro/srcterms/shearing_box.cpp`, `pgen/ssheet.cpp` | 5,800 words, 770 lines | 2.9 | – |
| 22 | Shearing-periodic boundaries | SG10 §4 | the shearing boundaries in `bvals/`, `pgen/hb3.cpp`, `hgb.cpp`, `jgg.cpp`, tests `shearingbox/` | 1,000 words, 3,210 lines | 2.9, 3.3 | – |
| 23 | Orbital advection, its code in outline | SG10 §5, §6 | `orbital_advection/`, `bvals/orbital/`, `hydro/srcterms/orbital_advection_srcterms.cpp`, `pgen/strat.cpp` | 3,900 words, 6,530 lines | 2.9 | – |
| 24 | Self-gravity by fast Fourier transform | – | `gravity/` without multigrid, `fft/athena_fft.*`, `fft/fft_driver.cpp`, `task_list/grav_task_list.*`, `pgen/jeans.cpp`, `fft.cpp`, tests | 2,520 lines | 2.10 | – |
| 25 | Multigrid: the hierarchy of grids and its operators | TS23 abstract, §1, §2, §3 (introduction)–§3.2.2 | `multigrid/multigrid.*` | 6,400 words, 1,750 lines | 2.10 | – |
| 26 | Multigrid: the driver, its boundaries and its parallelisation | TS23 §3.2.4, §3.2.5, §3.4, App. A | `multigrid/multigrid_driver.cpp`, `multigrid/mgbval_*.cpp`, `bvals/cc/mg/bvals_mg.*`, `task_list/mg_task_list.*` | 1,500 words, 5,290 lines | 2.10, 3.5 | – |
| 27 | Multigrid on refined meshes, self-gravity by multigrid | TS23 §3.2.3, §3.3, App. B | `gravity/mg_gravity.*`, `bvals/cc/mg/bvals_mg_gravity.cpp`, `bvals/bvals_refine_postmg.cpp` | 3,500 words, 1,020 lines | 2.10, 3.4 | – |
| 28 | Tests of multigrid | TS23 §4, §5 | `pgen/poisson.cpp`, `collapse.cpp`, `binary_gravity.cpp`, its test | 6,100 words, 1,070 lines | 2.10 | – |
| 29 | Conservative source terms of self-gravity | MHG21 | `hydro/srcterms/self_gravity.cpp` | 8,700 words, 90 lines | 2.10 | – |
| 30 | Viscosity, thermal conduction and non-ideal MHD | S20 §3.2.5, §3.3.2, §3.3.4 | `hydro/hydro_diffusion/`, `field/field_diffusion/`, `pgen/visc.cpp`, `resist.cpp`, tests `diffusion/` | 1,000 words, 2,760 lines | 2.11 | – |
| 31 | Super time-stepping | – | `task_list/sts_task_list.cpp`, its tests | 1,390 lines | 2.11, 3.5 | – |
| 32 | Passive scalars | – | `scalars/`, `eos/eos_scalars.cpp`, `pgen/scalar_diff.cpp` | 1,630 lines | 2.12 | – |
| 33 | Particles and their coupling to the gas | BS10 abstract, §1–§3 | – | 5,400 words | 2.13 | – |
| 34 | Tests of the particle method, convergence of the streaming instability | BS10 §4–§6, App. A | – | 6,800 words | 2.13 | – |
| 35 | Relativistic MHD: equations, primitive variables and corrections, the code in outline | BS11 abstract, §1–§3.2, §3.4; S20 §4–§4.2.1, §4.2.3; WSG16 §3.1 | the relativistic files of `eos/` | 6,800 words, 2,340 lines | 2.14 | – |
| 36 | Relativistic Riemann solvers, the code in outline | BS11 §3.3; S20 §4.2.2; WSG16 §3.3, §3.4, App. | the relativistic solvers of `hydro/rsolvers/` | 3,900 words, 4,610 lines | 2.14 | – |
| 37 | General relativity, the code in outline | WSG16 abstract, §1, §2, §3 (introduction), §3.6, §3.8 | the relativistic files of `coordinates/` | 2,500 words, 5,460 lines | 2.14 | – |
| 38 | Tests of special relativistic MHD, the code in outline | BS11 §4; S20 §4.3–§4.3.3 | `pgen/gr_blast.cpp`, `gr_linear_wave.cpp`, `gr_shock_tube.cpp`, tests `sr/` | 7,500 words, 2,590 lines | 2.14 | – |
| 39 | Tests of general relativistic MHD, the code in outline | WSG16 §4 | `pgen/gr_bondi.cpp`, `gr_geodesic_infall.cpp`, `gr_mhd_inflow.cpp`, tests `gr/` | 3,300 words, 1,620 lines | 2.14 | – |
| 40 | Applications of relativistic MHD, the code in outline | BS11 §5, §6; S20 §4.3.4; WSG16 §5, §7 | `pgen/gr_torus.cpp` | 6,400 words, 1,480 lines | 2.14 | – |
| 41 | Radiation transport, in outline | – | `nr_radiation/` with its boundaries, task lists, utilities, problems and tests | 12,710 lines | 2.15, 3.5 | – |
| 42 | Cosmic rays, in outline | – | `cr/`, `crdiffusion/` with their task list, problems and tests | 3,270 lines | 2.15, 3.5 | – |
| 43 | Chemistry, in outline | – | `chemistry/`, `chem_rad/`, `bvals/sixray/` with their task list, utilities, problems and tests | 12,970 lines | 2.15, 3.5 | – |
| 44 | The driving of turbulence, in outline | – | `fft/turbulence.*`, `pgen/turb.cpp`, tests `turb/` | 780 lines | 2.15, 3.5 | – |
| 45 | The mesh, its blocks and the tree of blocks | S20 §2 (introduction), §2.1–§2.1.2 | `mesh/mesh.*`, `mesh/meshblock.cpp`, `mesh/meshblock_tree.*` | 1,700 words, 3,660 lines | 3.2 | – |
| 46 | Communication of boundary values between blocks | – | the framework of `bvals/` with its cell- and face-centred variables, `utils/buffer_utils.*` | 6,360 lines | 3.3 | – |
| 47 | Physical boundary conditions | – | the outflow, reflecting and polar boundaries in `bvals/`, `bvals/utils/` | 1,480 lines | 3.3 | – |
| 48 | Mesh refinement: communication between levels, restriction, prolongation, correction of fluxes and electric fields | S20 §2.1.3–§2.1.5; BS11 §3.6 | `mesh/mesh_refinement.*`, `bvals/bvals_refine.cpp`, the flux corrections in `bvals/` | 2,700 words, 4,540 lines | 3.4 | – |
| 49 | Adaptive mesh refinement, load balancing and their tests | S20 §2.1.6, §2.1.7, §2.2, §3.4 | `mesh/amr_loadbalance.cpp`, tests `amr/` | 3,800 words, 1,550 lines | 3.4 | – |
| 50 | Task lists and parallelisation | S20 §2.4, §2.5 | `task_list/task_list.*`, `task_list/task_id.cpp`, the tasks in `time_integrator.cpp`, tests `mpi/`, `omp/`, `hybrid/` | 1,500 words, 2,990 lines | 3.5 | – |
| 51 | Configuration, build, the main loop, the input file and units | S08 §7; S20 §2.6 | `configure.py`, `Makefile.in`, `defs.hpp.in`, `main.cpp`, `parameter_input.*`, `units/` | 2,200 words, 3,700 lines | 3.1 | – |
| 52 | Problem generators and user functions | – | `pgen/default_pgen.cpp`, `pgen/from_array.cpp`, the enrolment functions in `mesh/mesh.cpp`, tests `pgen/` | 1,010 lines | 3.6 | – |
| 53 | Output and restarts | – | `outputs/`, `inputs/`, tests `outputs/` | 5,100 lines | 3.7 | – |
| 54 | Visualisation and analysis | – | `vis/` | 4,180 lines | 3.7 | – |
| 55 | Regression tests | – | `tst/regression/run_tests.py`, `tst/regression/scripts/utils/` | 2,030 lines | 3.8 | – |
| 56 | Performance and scaling | S20 §3.6; WSG16 §6 | – | 4,100 words | 3.9 | – |
| 57 | Linear waves | GS05 §5 (introduction), §5.4, App. A; GS08 §6 (introduction), §6.2, App. A; S08 §8 (introduction and linear waves); S20 §3.3 (introduction), §3.3.1 | `pgen/linear_wave.cpp`, its tests | 4,000 words, 1,620 lines | 2.16 | – |
| 58 | Circularly polarised Alfvén waves | GS05 §3.3 (introduction), §3.3.2, §5.2; GS08 §6.3; S08 §8.4 (Alfvén waves) | `pgen/cpaw.cpp`, its test | 3,200 words, 480 lines | 2.16 | – |
| 59 | Advection of a field loop | GS05 §3.3.1, §5.1; GS08 §6.1; S08 §8.4, §8.6 (field loops) | `pgen/field_loop.cpp` | 2,700 words, 280 lines | 2.16 | – |
| 60 | Shock tubes | S08 §8.1, §8.2, §8.6 (shock tubes); GS05 §5.3; GS08 §6.4; S20 §3.3.3 | `pgen/shock_tube.cpp`, `shu_osher.cpp`, `twoibw.cpp`, their tests | 4,400 words, 940 lines | 2.16 | – |
| 61 | Hydrodynamics in two and three dimensions | S08 §8.3, §8.5; S20 §3.3.5, §3.3.6 | `pgen/dmr.cpp`, `lw_implode.cpp`, `kh.cpp`, `noh.cpp`, `rt.cpp`, `blast.cpp`, `shk_cloud.cpp`, `jet.cpp` | 2,600 words, 2,610 lines | 2.16 | – |
| 62 | MHD in two and three dimensions | S08 §8.4, §8.6 (the others); GS05 §5.5; GS08 §6.5 | `pgen/orszag_tang.cpp`, `rotor.cpp`, `magnoh.cpp` | 2,800 words, 450 lines | 2.16 | – |

In step 10 of the synthesis of Zingale's text, the edge values of the piecewise parabolic method and their limiter were left to this synthesis. Stone et al. (2008, arXiv:0804.0402, §4.2.3) state them, but both lines of their eq. 46 put a plus sign between the slope terms, as in $(\delta w^m_i + \delta w^m_{i-1})/6$, where a minus is right. With the plus sign, the edge value of a linear profile is wrong, and the interpolation of smooth data is first-order instead of fourth-order accurate. Athena++ uses the minus sign, in `src/reconstruct/reconstruction.cpp`. Step 7 takes this up. It states the edge values and their limiter from §4.2.3 and from `src/reconstruct/ppm.cpp`, and notes the slip as **[GK]**.
