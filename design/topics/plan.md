# Plan of the topic summaries

This file records the topics of the second layer of the reference material (§4.1 of CLAUDE.md), the rules of their summaries, and the steps in which the summaries are written, with the steps that are done. The summaries draw on the five syntheses in `design/references/`, which are complete and reviewed. Section signs refer to CLAUDE.md. Plain numbers refer to the subsections of the syntheses, which the tables name by their references: Zingale for `computational-hydrodynamics-synthesis.md`, and pyro, Ulula, ZEUS and Athena for `pyro-synthesis.md`, `ulula-synthesis.md`, `zeus-synthesis.md` and `athena-synthesis.md`.

## Topics

A topic is one component, such as the Riemann solvers, across all the references that treat it. It is cut to what one decision brief would settle (§2.4), so that methods which a brief weighs against each other share a summary. Piecewise linear and piecewise parabolic reconstruction share one with their limiters, for instance, and the corner transport upwind method shares one with the method of lines. A large topic is split into steps rather than into further topics. The 33 topics fall into four groups: the core of the scheme (1 to 12), further physics (13 to 24), the tests (25 and 26) and the software architecture (27 to 33). The four modules that only Athena++ has, the shearing box with orbital advection, relativistic MHD, cosmic rays and the driving of turbulence, have topics of their own, so that the overview of the layers (§2.3) sees the whole scope of §1.2 through one layer. The topics are written in the order of the table, so that each summary can build on the ones before it.

Each summary is kept in `design/topics/`, in a file named after its topic in lower case, with hyphens and without articles or commas. Sizes are the words of the subsections of the syntheses that a topic draws on, with links stripped, rounded to hundreds.

| Topic | Subject | File | Steps | Size |
|---:|---|---|---|---:|
| 1 | The equations and their variables | `equations-and-their-variables.md` | 1 | 5,400 |
| 2 | Equations of state | `equations-of-state.md` | 2–3 | 6,100 |
| 3 | Grids and the finite-volume discretisation | `grids-and-finite-volume-discretisation.md` | 4 | 4,300 |
| 4 | Boundary conditions and ghost cells | `boundary-conditions-and-ghost-cells.md` | 5 | 3,700 |
| 5 | Reconstruction and limiting | `reconstruction-and-limiting.md` | 6–7 | 8,700 |
| 6 | Riemann solvers | `riemann-solvers.md` | 8–9 | 7,500 |
| 7 | Time integration | `time-integration.md` | 10–13 | 13,900 |
| 8 | Methods of higher order | `methods-of-higher-order.md` | 14–15 | 9,000 |
| 9 | Artificial viscosity | `artificial-viscosity.md` | 16 | 2,100 |
| 10 | Constrained transport | `constrained-transport.md` | 17–19 | 14,200 |
| 11 | Curvilinear coordinates | `curvilinear-coordinates.md` | 20–22 | 10,800 |
| 12 | Source terms | `source-terms.md` | 23 | 3,200 |
| 13 | Elliptic solvers | `elliptic-solvers.md` | 24–26 | 13,900 |
| 14 | Self-gravity | `self-gravity.md` | 27 | 5,500 |
| 15 | Diffusion | `diffusion.md` | 28 | 4,300 |
| 16 | Operator splitting and the coupling of processes | `operator-splitting-and-coupling-of-processes.md` | 29 | 3,100 |
| 17 | Reactions, chemistry and cooling | `reactions-chemistry-and-cooling.md` | 30 | 2,300 |
| 18 | Passive scalars | `passive-scalars.md` | 31 | 1,800 |
| 19 | Particles | `particles.md` | 32 | 5,400 |
| 20 | Radiation transport | `radiation-transport.md` | 33–34 | 10,800 |
| 21 | The shearing box and orbital advection | `shearing-box-and-orbital-advection.md` | 35–36 | 6,700 |
| 22 | Relativistic MHD | `relativistic-mhd.md` | 37–39 | 12,700 |
| 23 | Cosmic rays | `cosmic-rays.md` | 40 | 500 |
| 24 | The driving of turbulence | `driving-of-turbulence.md` | 41 | 800 |
| 25 | Verification and testing | `verification-and-testing.md` | 42 | 3,900 |
| 26 | Test problems | `test-problems.md` | 43–47 | 22,000 |
| 27 | Packaging, configuration and build | `packaging-configuration-and-build.md` | 48 | 1,900 |
| 28 | Data structures | `data-structures.md` | 49 | 5,000 |
| 29 | The driver and the control of a time step | `driver-and-control-of-time-step.md` | 50 | 3,800 |
| 30 | Problem setups and user functions | `problem-setups-and-user-functions.md` | 51 | 1,200 |
| 31 | Output, restarts and analysis | `output-restarts-and-analysis.md` | 52 | 2,600 |
| 32 | Mesh refinement | `mesh-refinement.md` | 53 | 4,500 |
| 33 | Parallelisation and performance | `parallelisation-and-performance.md` | 54 | 2,500 |

Tests are assigned by their aim. A test aimed at one component, whose known solution or reported outcome checks that component, joins its topic, such as the tests of the general equations of state, of multigrid or of the advection of a field loop. The tests of the whole scheme form topic 26, grouped by family. Topic 25 holds the methods of testing: norms, convergence and conservation, and the regression and unit tests of the codes.

Some parts of the syntheses enter no topic. The incompressible and low Mach number solvers (Zingale 2.10, pyro 2.8 and 2.9) and the shallow-water solver (pyro 2.5) lie outside the scope of §1.2, which follows codes such as Athena++. Of them, only multigrid with variable coefficients (Zingale 2.10.8) joins topic 13. The numerical foundations of Zingale's text join the topics that use them. Differentiation goes to the grids and quadrature to the methods of higher order, root finding to the equations of state and the Riemann solvers, and the integration of ODEs to time integration and reactions. Simulation and its approximations, round-off and norms go to verification, and discrete Fourier transforms to the elliptic solvers. The introductions of the parts and sections of the syntheses join the topics of what they introduce.

## Summaries

A summary condenses what the syntheses say of its component and compares the methods across the references. It assesses them but does not choose between them, as the choice is made in a brief (§2.4). It has six parts.

1. Overview: the role of the component in a scheme, the references that treat it, with a table of the subsections of the syntheses drawn on, each linked to its heading, and what each reference leaves out.
2. Methods: one subsection per method or family, compared across the references that use it, with its idea and equations, its variants and the results that the references report for it.
3. Implementation: how each code builds the component in, with its interfaces, data, options, defaults and cost.
4. Tests: the tests aimed at the component, each with its aim, its set-up in brief, the references and codes that run it, with their parameters where they differ, and the outcomes with the numbers that state them. The full initial data stay in the syntheses.
5. Assessment: the strengths and weaknesses of the methods in accuracy, robustness, cost, simplicity and extensibility, the points on which the references disagree, and the questions they leave open, marked **[GK]**.
6. Sources: anchored entries for the works and the code cited.

In the topics of the software architecture, part 2 compares the designs and part 3 their realisation in the code. In topic 26, part 2 holds the problems by family, part 3 their problem generators, input files and regression tests, and part 4 the outcomes.

A summary carries over the citations of the syntheses, each in the form its synthesis gives it. Zingale's text is cited by title and date, with the numbers of its sections, equations, figures and tables. Papers are cited by author and year, with the numbers of their sections, equations, figures and tables, and with their arXiv identifier, DOI or ADS bibcode at the first citation and in the list of sources. Code is cited by its path and the name of a function or class, at the version that its synthesis records: pyro 4.5.1, Ulula 1.0.2 and Athena++ v24.0, with the note in 1.1 of the Athena synthesis on the copy. The authors of each citation link to an anchored entry in the list of sources of the summary, and every identifier and address is a link to its target. A summary cites an earlier summary by its file and section.

The rules of the syntheses on **[GK]** marks carry over. A mark covers the rest of its paragraph or list item, so that each paragraph of the assessment carries one, and a mark in a synthesis carries over with the claim it covers. Anything else that the syntheses do not provide is marked as well. A part of a topic that no reference covers, such as the integration of radiative cooling, is named in one line as a gap and not filled. Whether a reference is added or experiments answer the question is decided in the brief that needs it (§2.4). Where the references differ on a method, the summary states the difference.

A summary takes its content from the syntheses, not from the sources. Where a synthesis falls short or proves wrong, the work on the summary stops and the source is read again. The synthesis is completed or corrected first, in a commit of its own with the author's approval, which its section of `design/references/plan.md` records, so that the two layers agree (§4.1). The summary then goes on.

## Steps

Each step takes one method or family of a topic, across all the references that treat it, with its implementation and its tests. It draws on about 5,000 words of the syntheses, cut at the boundaries of methods, and a topic within that size is one step. The overview and the assessment are written in the last step of a topic, and the list of sources grows with each step. Where a step takes part of a subsection, a parenthesis names the part, and the size counts the paragraphs of that part. A subsection or paragraph that serves two steps counts in both.

Each step is put to the author with its review and is committed once the author approves. The review lists what the step found in the syntheses and how it was settled, the gaps it named and the notes it marked **[GK]**. Once a step is committed, the next step begins without a further request, while every commit and every push needs an approval of its own. A review of the whole layer follows the last step. It is done in parts and checks the claims of each summary against the syntheses, the citations carried over and the consistency between the topics.

| Step | Topic | Part | Drawn from | Size | Status |
|---:|---:|---|---|---:|---|
| 1 | 1 | The equations of hydrodynamics and MHD in conservative, primitive and characteristic form; conserved and primitive variables; the forms of the energy equation | Zingale 2.1.9, 2.4.1, 2.5.1–2.5.3, 2.5.9; pyro 2.4.1; Ulula 2.1.1, 2.1.3, 2.1.4; ZEUS 2.1.1, 2.3.3, 2.8.1, 2.8.2; Athena 2.1.1, 2.1.4 | 5,400 | open |
| 2 | 2 | Ideal and isothermal gases, the general EOS and its interface, floors | Zingale 2.1.5, 2.5.21, 2.5.22; pyro 2.4.1; Ulula 2.1.2; ZEUS 2.1.1; Athena 2.2.1, 2.2.2 | 2,600 | open |
| 3 | 2 | Tables, the EOS of hydrogen and the tests of general equations of state | Athena 2.2.3, 2.2.4 | 3,500 | open |
| 4 | 3 | Discretisation, averages and point values, cell-centred and staggered placement, the conservative update, nonuniform and moving grids | Zingale 2.1.3, 2.2.1–2.2.4, 2.2.6, 2.3.5, 2.3.7, 2.3.13; pyro 2.1.1; Ulula 2.2.1, 2.3.1; ZEUS 2.2.1, 2.2.2, 2.4.3; Athena 2.1.3 | 4,300 | open |
| 5 | 4 | Ghost cells, physical boundary conditions, boundaries of the user, the exchange between blocks | Zingale 2.2.5, 2.5.15; pyro 2.1.3, 2.4.6 (boundaries); Ulula 2.2.2, 2.2.3; ZEUS 2.5.1, 2.8.8 (boundaries); Athena 3.3 | 3,700 | open |
| 6 | 5 | Piecewise linear reconstruction, slope limiters, primitive and characteristic variables | Zingale 2.3.9–2.3.11, 2.3.21, 2.5.11 (reconstruction); pyro 2.1.5; Ulula 2.5; ZEUS 2.4.2 (donor cell, van Leer); Athena 2.4.1–2.4.4 | 4,900 | open |
| 7 | 5 | The piecewise parabolic method, flattening and contact steepening, WENO, and the advection tests that compare the reconstructions | Zingale 2.3.19, 2.5.12, 2.5.13; pyro 2.1.6, 2.1.7; ZEUS 2.4.2 (PPA), 2.7.1 (advection); Athena 2.4.5, 2.4.6 | 3,800 | open |
| 8 | 6 | The Riemann problem, its exact solution and two-shock solvers | Zingale 2.1.5, 2.4.2, 2.5.4–2.5.8, 2.5.14 (two-shock solvers); pyro 2.4.7 (the problem, CGF) | 2,600 | open |
| 9 | 6 | The HLL family, Roe's method and the carbuncle | Zingale 2.5.14 (HLL); pyro 2.4.7 (HLLC); Ulula 2.4; Athena 2.5 | 4,900 | open |
| 10 | 7 | Upwind differencing, stability, implicit differencing, the Godunov update and the time step | Zingale 2.1.7, 2.3.1–2.3.4, 2.3.16, 2.5.10; pyro 2.4.6 (time step); Ulula 2.3.1, 2.3.3; ZEUS 2.5.2, 2.8.8 (time step); Athena 2.6.5 (time step) | 3,000 | open |
| 11 | 7 | Single-step schemes of second order: predictor–corrector, characteristic tracing, MUSCL–Hancock | Zingale 2.3.8, 2.4.3, 2.4.5, 2.5.11 (tracing); pyro 2.3.1, 2.4.2; Ulula 2.6; Athena 2.6.1 | 3,000 | open |
| 12 | 7 | Several dimensions: dimensional splitting and corner transport upwind | Zingale 2.3.13–2.3.15, 2.3.21, 2.5.16; pyro 2.2.1, 2.2.4, 2.4.3; Ulula 2.3.2; ZEUS 2.1.2 (directional splitting), 2.4.1; Athena 2.6.3, 2.6.4 (hydrodynamics) | 4,900 | open |
| 13 | 7 | The method of lines, Runge–Kutta and van Leer integrators, spectral deferred corrections | Zingale 2.3.12, 2.3.17, 2.5.20; pyro 2.1.10, 2.2.2 (advection_rk), 2.4.8, 2.4.10; Athena 2.6.5 | 3,100 | open |
| 14 | 8 | Finite-difference WENO with flux splitting; fourth-order finite volumes for hydrodynamics | Zingale 2.1.4, 2.3.18, 2.3.20, 2.4.6, 2.4.7, 2.5.23; pyro 2.1.8, 2.1.9, 2.2.2 (advection_weno), 2.2.3, 2.4.9; Athena 2.7.1, 2.7.2 | 5,000 | open |
| 15 | 8 | Upwind CT of fourth order and the tests of the fourth-order method for MHD | Athena 2.7.3, 2.7.4 | 3,900 | open |
| 16 | 9 | Artificial viscosity in finite-difference and Godunov schemes | Zingale 2.5.13 (artificial viscosity); pyro 2.4.4; ZEUS 2.1.2 (the source step), 2.3.2, 2.3.4 | 2,100 | open |
| 17 | 10 | The divergence constraint, the staggered field and its update by CT, the advection of fields | ZEUS 2.8.2–2.8.4, 2.9.1; Athena 2.3.1–2.3.4 | 4,000 | open |
| 18 | 10 | The electric fields: the method of characteristics of ZEUS, the corner fields of Athena, the advection of a field loop | ZEUS 2.8.5; Athena 2.3.5, 2.16.3 | 4,900 | open |
| 19 | 10 | The field in the integrators, the Lorentz force and the toroidal field | ZEUS 2.8.6–2.8.8; Athena 2.6.2, 2.6.3, 2.6.4 (MHD) | 5,200 | open |
| 20 | 11 | Geometry, the equations, finite volumes and geometric source terms | Zingale 2.2.6, 2.5.18; pyro 2.1.2; ZEUS 2.2.3, 2.2.4; Athena 2.8.1, 2.8.2, 2.8.4 | 4,400 | open |
| 21 | 11 | Reconstruction on nonuniform and curvilinear grids, CT and the integrator of Athena in curvilinear coordinates | Athena 2.8.3, 2.8.5, 2.8.6 | 2,900 | open |
| 22 | 11 | Tests in curvilinear coordinates | ZEUS 2.7.1 (curvilinear advection); Athena 2.8.7 | 3,500 | open |
| 23 | 12 | External gravity, rotating frames, energy sources, the coupling of sources to the update, and their tests | Zingale 2.5.17; pyro 2.4.3 (sources), 2.4.5, 2.4.12 (hse, heating); Ulula 2.3.4, 2.7.1, 2.7.2, 2.7.4, 2.8.5, 2.8.6, 2.8.14, 2.8.15; ZEUS 2.3.1; Athena 2.9.1 | 3,200 | open |
| 24 | 13 | The discrete Poisson problem, Fourier methods, relaxation and the iterative solver of ZEUS | Zingale 2.1.8, 2.6.1–2.6.4, 2.6.7; Ulula 2.7.3; ZEUS 2.6, 2.7.5; Athena 2.10.1 (FFT) | 4,100 | open |
| 25 | 13 | Multigrid: cycles, restriction and prolongation, variable coefficients | Zingale 2.6.5, 2.6.6, 2.6.8, 2.10.8; pyro 2.1.4, 2.6.1–2.6.3; Athena 2.10.2 | 4,500 | open |
| 26 | 13 | Multigrid in parallel and on refined meshes, the tests of the solvers | pyro 2.6.4; Athena 2.10.3, 2.10.4 (refined meshes), 2.10.5 | 5,300 | open |
| 27 | 14 | The potential of self-gravity, its boundaries, its coupling to the fluid and conservative source terms, with their tests | Zingale 2.6.9 (self-gravity); Ulula 2.7.1, 2.7.3, 2.7.4, 2.8.7, 2.8.16; ZEUS 2.6, 2.7.2, 2.7.5; Athena 2.10.1, 2.10.4 (self-gravity), 2.10.6 | 5,500 | open |
| 28 | 15 | Viscosity, thermal conduction, resistivity and ambipolar diffusion; explicit and implicit differencing, super time-stepping | Zingale 2.4.8, 2.7; pyro 2.3.2, 2.7; Athena 2.1.2, 2.11, 2.12.2 (diffusion) | 4,300 | open |
| 29 | 16 | Operator splitting, its order and convergence, spectral deferred corrections, the coupling of modules in the task lists | Zingale 2.8.1–2.8.3, 2.8.6; pyro 2.4.10, 2.4.11; Ulula 2.3.4; ZEUS 2.1.2; Athena 2.11.2, 3.5 (the integrator) | 3,100 | open |
| 30 | 17 | Reactive flow, reaction networks, chemistry with heating and cooling, stiff sources | Zingale 2.1.7, 2.8.4, 2.8.5, 2.8.7; pyro 2.4.11; Athena 2.15.3 | 2,300 | open |
| 31 | 18 | Passive scalars: advection, reconstruction, floors and diffusion | Zingale 2.8.4 (species); pyro 2.4.1 (scalars); Athena 2.12 | 1,800 | open |
| 32 | 19 | Tracer particles and particles coupled to the gas by drag | pyro 2.10; Athena 2.13 | 5,400 | open |
| 33 | 20 | The moment equations, their closure and their solution, with the tests of the moment solver | Zingale 2.6.9 (radiation); ZEUS 2.10, 2.12.1, 2.12.2 | 5,800 | open |
| 34 | 20 | The transfer equation, short characteristics and the Eddington factors, with their tests; the module of Athena++ | ZEUS 2.11, 2.12.3, 2.12.4; Athena 2.15.1 | 5,100 | open |
| 35 | 21 | The shearing box, its source terms and shearing-periodic boundaries | Athena 2.9.1 (rotating frame), 2.9.2, 2.9.3 | 3,800 | open |
| 36 | 21 | Orbital advection | Athena 2.9.4 | 2,900 | open |
| 37 | 22 | The equations of relativistic MHD, primitive variables, equations of state and Riemann solvers | Athena 2.14.1–2.14.4 | 4,600 | open |
| 38 | 22 | Tests of special relativistic MHD | Athena 2.14.6 | 3,100 | open |
| 39 | 22 | General relativity, its tests and the applications | Athena 2.14.5, 2.14.7, 2.14.8 | 5,000 | open |
| 40 | 23 | Two-moment transport of cosmic rays and their diffusion by multigrid | Athena 2.15.2 | 500 | open |
| 41 | 24 | The driving of turbulence | Athena 2.15.4 | 800 | open |
| 42 | 25 | Norms, convergence and conservation, the approaches to testing, regression and unit tests | Zingale 2.1.1, 2.1.2, 2.1.6, 2.3.6, 2.9.1, 2.9.2; pyro 2.4.12 (test), 3.4 (convergence, testing); Ulula 2.8.17; ZEUS 2.7.1 (approach), 2.7.6, 2.9.1 (approach), 2.9.8, 2.12.1 (approach), 2.12.4; Athena 3.1 (reproducibility), 3.8 | 3,900 | open |
| 43 | 26 | Advection and linear waves | Zingale 2.5.19 (advection); pyro 2.2.5, 2.4.12 (advect, acoustic_pulse); Ulula 2.8.1–2.8.3, 2.8.8; ZEUS 2.9.4, 2.9.7; Athena 2.16.1, 2.16.2 | 5,300 | open |
| 44 | 26 | Shock tubes and interacting blast waves | Zingale 2.4.4, 2.5.19 (shock tubes); pyro 2.3.3, 2.4.12 (sod); Ulula 2.8.4; ZEUS 2.7.3, 2.7.4 (blast waves), 2.9.2; Athena 2.16.4 | 5,400 | open |
| 45 | 26 | Blast waves, implosions and shock reflections in several dimensions | Zingale 2.5.19 (Sedov); pyro 2.4.12 (sedov, quad, ramp, logo); Ulula 2.8.10, 2.8.11; ZEUS 2.7.4 (wind tunnel, double Mach reflection); Athena 2.16.5 (shocks) | 3,900 | open |
| 46 | 26 | Instabilities, vortices and convection | pyro 2.4.12 (gresho, kh, rt, rt2, rt_multimode, bubble, convection, plume); Ulula 2.8.9, 2.8.12, 2.8.13; Athena 2.16.5 (instabilities) | 2,600 | open |
| 47 | 26 | MHD in two and three dimensions; the astrophysical tests of ZEUS | ZEUS 2.9.3, 2.9.5, 2.9.6; Athena 2.16.6 | 4,700 | open |
| 48 | 27 | Languages and dependencies, packaging and installation, configuration and build | Zingale 3.4, 3.5; pyro 3.1; Ulula 3.1; Athena 3.1 (versions, releases, configuration) | 1,900 | open |
| 49 | 28 | Variables and arrays, grids, the mesh and its blocks | Zingale 3.1, 3.6; pyro 3.2; Ulula 3.2; ZEUS 3.1; Athena 2.1.4, 3.2 | 5,000 | open |
| 50 | 29 | The main loop, simulation objects, task lists, runtime parameters and units | pyro 3.3 (driver, parameters); Ulula 3.3, 3.5; ZEUS 3.2; Athena 3.1 (main loop, input, units), 3.5 (task lists) | 3,800 | open |
| 51 | 30 | Problem setups, their base classes and the functions of the user | pyro 3.3 (problems); Ulula 2.2.3, 2.8.1, 3.6; Athena 3.6 | 1,200 | open |
| 52 | 31 | Output and its formats, restarts, plotting and analysis | Zingale 3.3; pyro 3.4 (output, plotting); Ulula 3.4; Athena 3.7 | 2,600 | open |
| 53 | 32 | Static and adaptive refinement by blocks, communication between levels, restriction, prolongation and the correction of fluxes, load balancing | Zingale 2.2.6, 2.6.5; pyro 2.1.4; Athena 3.4 | 4,500 | open |
| 54 | 33 | Computational cost, optimisation, parallelisation by MPI and OpenMP, scaling | Zingale 2.9.1, 3.2; Ulula 3.7; Athena 3.1 (optimisation), 3.5 (parallelisation), 3.9 | 2,500 | open |
