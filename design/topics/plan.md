# Plan of the topic summaries

This file records the topics of the second layer of the reference material (§4.1 of CLAUDE.md), the rules of their summaries, and the steps in which the summaries are written, with the steps that are done. The summaries draw on the five syntheses in `design/references/`, which are complete and reviewed. Section signs refer to CLAUDE.md. Plain numbers refer to the subsections of the syntheses, which the table names by their references: Zingale for `computational-hydrodynamics-synthesis.md`, and pyro, Ulula, ZEUS and Athena for `pyro-synthesis.md`, `ulula-synthesis.md`, `zeus-synthesis.md` and `athena-synthesis.md`.

## Topics

A topic is one component, such as the Riemann solvers, across all the references that treat it. It is cut to what one decision brief would settle (§2.4), so that methods which a brief weighs against each other share a summary. Piecewise linear and piecewise parabolic reconstruction share one with their limiters, for instance, and the corner transport upwind method shares one with the method of lines. The 37 topics fall into four groups: the core of the scheme (1 to 12), further physics (13 to 24), the tests (25 to 30) and the software architecture (31 to 37). The four modules that only Athena++ has, the shearing box with orbital advection, relativistic MHD, cosmic rays and the driving of turbulence, have topics of their own, so that the overview of the layers (§2.3) sees the whole scope of §1.2 through one layer. The topics are written in the order of the table, so that each summary can build on the ones before it.

Tests are assigned by their aim. A test aimed at one component, whose known solution or reported outcome checks that component, joins its topic, such as the tests of the general equations of state, of multigrid or of the advection of a field loop. The tests of the whole scheme form topics 26 to 30, one for each family. Topic 25 holds the methods of testing: norms, convergence and conservation, and the regression and unit tests of the codes.

Some parts of the syntheses enter no topic. The incompressible and low Mach number solvers (Zingale 2.10, pyro 2.8 and 2.9) and the shallow-water solver (pyro 2.5) lie outside the scope of §1.2, which follows codes such as Athena++. Of them, only multigrid with variable coefficients (Zingale 2.10.8) joins topic 13. The numerical foundations of Zingale's text join the topics that use them. Differentiation goes to the grids and quadrature to the methods of higher order, root finding to the equations of state and the Riemann solvers, and the integration of ODEs to time integration and reactions. Simulation and its approximations, round-off and norms go to verification, and discrete Fourier transforms to the elliptic solvers. The introductions of the parts and sections of the syntheses join the topics of what they introduce.

## Summaries

A summary sets out, conceptually and in formulas, the mathematical framework of its component and the steps of each method, and compares the methods across the references. It assesses them but does not choose between them, as the choice is made in a brief (§2.4). It runs to between 1,000 and 2,000 words, not counting formulas and the list of sources, so that it can be read in one sitting. A topic with little material, such as cosmic rays, gets a shorter summary, as nothing is added for the sake of length (§2.7). A summary has five parts.

1. Overview: the role of the component in a scheme, the methods compared and the codes that use them, and what the references leave out.
2. Methods: one subsection per method or family. It gives the idea in prose and the key formulas, derived where a few lines show their origin and otherwise stated with their source. The algorithm follows as numbered steps, one operation and its formula per step, and the codes that use the method are named.
3. Tests: the tests aimed at the component, each in one paragraph of three to five sentences at most, with its set-up, its purpose and the references that run it.
4. Assessment: a short paragraph or small table on the accuracy, robustness and cost of the methods, with the questions that the references leave open, marked **[GK]**.
5. Sources: anchored entries for the key sources cited.

In topics 26 to 30, part 2 holds the problems of the family, each in one paragraph as in part 3, part 3 is left out, and part 4 assesses how well the problems tell the methods apart. In the topics of the software architecture, part 2 describes the designs conceptually, with numbered steps where a design has an algorithm, such as the main loop, and part 4 weighs the designs by performance, readability and extensibility (§1.4). Part 3 is left out wherever the references test nothing of a topic.

All summaries share one notation. The notation page, `notation.md`, fixes it in step 0 and is agreed with the author before the first summary is written. The page is short, and sets the symbols for the variables, the indices of cells, faces and time levels, the states on either side of a face and the fluxes. A symbol that the page does not fix is defined in the summary where it first appears, and later summaries keep it. Key formulas may be displayed as `$$...$$`, an exception that §3.1 makes for the summaries alone, while other formulas stay inline.

Codes are named only, as in "HLLC is used by pyro, Ulula and Athena++", without paths, functions, options or versions. A summary cites only its key sources. Each method or test cites the paper or text that it comes from, as its synthesis records it, with the numbers of its key equations, and links to the subsections of the syntheses that hold the detail and the further citations. Papers are cited by author and year, and Zingale's text by title and date. The authors of each citation link to an anchored entry in the list of sources, where the arXiv identifier, DOI or ADS bibcode of each paper is a link to its target. A summary cites an earlier summary by its file and section.

The rules of the syntheses on **[GK]** marks carry over. A mark covers the rest of its paragraph or list item, so that each paragraph of the assessment carries one, and a mark in a synthesis carries over with the claim it covers. Anything else that the syntheses do not provide is marked as well, such as a derivation that they do not give. A part of a topic that no reference covers, such as the integration of radiative cooling, is named in one line as a gap and not filled. Whether a reference is added or experiments answer the question is decided in the brief that needs it (§2.4). Where the references differ on a method, the summary states the difference.

A summary takes its content from the syntheses, not from the sources. Where a synthesis falls short or proves wrong, the work on the summary stops and the source is read again. The synthesis is completed or corrected first, in a commit of its own with the author's approval, which its section of `design/references/plan.md` records, so that the two layers agree (§4.1). The summary then goes on.

## Steps

The notation page is written in step 0 and topic $n$ in step $n$, one summary per step. Each file is kept in `design/topics/` and named after its topic in lower case, with hyphens and without articles or commas. Sizes are the words of the subsections of the syntheses that a topic draws on, with links stripped, rounded to hundreds. Where a topic takes part of a subsection, a parenthesis names the part, and the size counts only its paragraphs. A subsection or paragraph that serves two topics counts in both.

Each step is put to the author with its review and is committed once the author approves. The review lists what the step found in the syntheses and how it was settled, the gaps it named and the notes it marked **[GK]**. Once a step is committed, the next step begins without a further request, while every commit and every push needs an approval of its own. A review of the whole layer follows the last step. It is done in parts and checks the claims of each summary against the syntheses, its citations and the consistency of the notation between the topics.

| Step | Topic | File | Drawn from | Size | Status |
|---:|---|---|---|---:|---|
| 0 | Notation | `notation.md` | The notations of the five syntheses | — | open |
| 1 | The equations and their variables | `equations-and-their-variables.md` | Zingale 2.1.9, 2.4.1, 2.5.1–2.5.3, 2.5.9; pyro 2.4.1; Ulula 2.1.1, 2.1.3, 2.1.4; ZEUS 2.1.1, 2.3.3, 2.8.1, 2.8.2; Athena 2.1.1, 2.1.4 | 5,400 | open |
| 2 | Equations of state | `equations-of-state.md` | Zingale 2.1.5, 2.5.21, 2.5.22; pyro 2.4.1; Ulula 2.1.2; ZEUS 2.1.1; Athena 2.2 | 6,100 | open |
| 3 | Grids and the finite-volume discretisation | `grids-and-finite-volume-discretisation.md` | Zingale 2.1.3, 2.2.1–2.2.4, 2.2.6, 2.3.5, 2.3.7, 2.3.13; pyro 2.1.1; Ulula 2.2.1, 2.3.1; ZEUS 2.2.1, 2.2.2, 2.4.3; Athena 2.1.3 | 4,300 | open |
| 4 | Boundary conditions and ghost cells | `boundary-conditions-and-ghost-cells.md` | Zingale 2.2.5, 2.5.15; pyro 2.1.3, 2.4.6 (boundaries); Ulula 2.2.2, 2.2.3; ZEUS 2.5.1, 2.8.8 (boundaries); Athena 3.3 | 3,700 | open |
| 5 | Reconstruction and limiting | `reconstruction-and-limiting.md` | Zingale 2.3.9–2.3.11, 2.3.19, 2.3.21, 2.5.11 (reconstruction), 2.5.12, 2.5.13; pyro 2.1.5–2.1.7; Ulula 2.5; ZEUS 2.4.2, 2.7.1 (advection); Athena 2.4 | 8,700 | open |
| 6 | Riemann solvers | `riemann-solvers.md` | Zingale 2.1.5, 2.4.2, 2.5.4–2.5.8, 2.5.14; pyro 2.4.7; Ulula 2.4; Athena 2.5 | 7,100 | open |
| 7 | Time integration | `time-integration.md` | Zingale 2.1.7, 2.3.1–2.3.4, 2.3.8, 2.3.12–2.3.17, 2.3.21, 2.4.3, 2.4.5, 2.5.10, 2.5.11 (tracing), 2.5.16, 2.5.20; pyro 2.1.10, 2.2.1, 2.2.2 (advection_rk), 2.2.4, 2.3.1, 2.4.2, 2.4.3, 2.4.6 (time step), 2.4.8, 2.4.10; Ulula 2.3.1–2.3.3, 2.6; ZEUS 2.1.2 (directional splitting), 2.4.1, 2.5.2, 2.8.8 (time step); Athena 2.6.1, 2.6.3, 2.6.4 (hydrodynamics), 2.6.5 | 13,600 | open |
| 8 | Methods of higher order | `methods-of-higher-order.md` | Zingale 2.1.4, 2.3.18, 2.3.20, 2.4.6, 2.4.7, 2.5.23; pyro 2.1.8, 2.1.9, 2.2.2 (advection_weno), 2.2.3, 2.4.9; Athena 2.7 | 9,000 | open |
| 9 | Artificial viscosity | `artificial-viscosity.md` | Zingale 2.5.13 (artificial viscosity); pyro 2.4.4; ZEUS 2.1.2 (the source step), 2.3.2, 2.3.4 | 2,100 | open |
| 10 | Constrained transport | `constrained-transport.md` | ZEUS 2.8.2–2.8.8, 2.9.1; Athena 2.3, 2.6.2, 2.6.3, 2.6.4 (MHD), 2.16.3 | 14,200 | open |
| 11 | Curvilinear coordinates | `curvilinear-coordinates.md` | Zingale 2.2.6, 2.5.18; pyro 2.1.2; ZEUS 2.2.3, 2.2.4, 2.7.1 (curvilinear advection); Athena 2.8 | 10,800 | open |
| 12 | Source terms | `source-terms.md` | Zingale 2.5.17; pyro 2.4.3 (sources), 2.4.5, 2.4.12 (hse, heating); Ulula 2.3.4, 2.7.1, 2.7.2, 2.7.4, 2.8.5, 2.8.6, 2.8.14, 2.8.15; ZEUS 2.3.1; Athena 2.9.1 | 3,200 | open |
| 13 | Elliptic solvers | `elliptic-solvers.md` | Zingale 2.1.8, 2.6.1–2.6.8, 2.10.8; pyro 2.1.4, 2.6; Ulula 2.7.3; ZEUS 2.6, 2.7.5; Athena 2.10.1 (FFT), 2.10.2, 2.10.3, 2.10.4 (refined meshes), 2.10.5 | 13,900 | open |
| 14 | Self-gravity | `self-gravity.md` | Zingale 2.6.9 (self-gravity); Ulula 2.7.1, 2.7.3, 2.7.4, 2.8.7, 2.8.16; ZEUS 2.6, 2.7.2, 2.7.5; Athena 2.10.1, 2.10.4 (self-gravity), 2.10.6 | 5,500 | open |
| 15 | Diffusion | `diffusion.md` | Zingale 2.4.8, 2.7; pyro 2.3.2, 2.7; Athena 2.1.2, 2.11, 2.12.2 (diffusion) | 4,300 | open |
| 16 | Operator splitting and the coupling of processes | `operator-splitting-and-coupling-of-processes.md` | Zingale 2.8.1–2.8.3, 2.8.6; pyro 2.4.10, 2.4.11; Ulula 2.3.4; ZEUS 2.1.2; Athena 2.11.2, 3.5 (the integrator) | 3,100 | open |
| 17 | Reactions, chemistry and cooling | `reactions-chemistry-and-cooling.md` | Zingale 2.1.7, 2.8.4, 2.8.5, 2.8.7; pyro 2.4.11; Athena 2.15.3 | 2,300 | open |
| 18 | Passive scalars | `passive-scalars.md` | Zingale 2.8.4 (species); pyro 2.4.1 (scalars); Athena 2.12 | 1,800 | open |
| 19 | Particles | `particles.md` | pyro 2.10; Athena 2.13 | 5,400 | open |
| 20 | Radiation transport | `radiation-transport.md` | Zingale 2.6.9 (radiation); ZEUS 2.10–2.12; Athena 2.15.1 | 10,800 | open |
| 21 | The shearing box and orbital advection | `shearing-box-and-orbital-advection.md` | Athena 2.9.1 (rotating frame), 2.9.2–2.9.4 | 6,700 | open |
| 22 | Relativistic MHD | `relativistic-mhd.md` | Athena 2.14 | 12,700 | open |
| 23 | Cosmic rays | `cosmic-rays.md` | Athena 2.15.2 | 500 | open |
| 24 | The driving of turbulence | `driving-of-turbulence.md` | Athena 2.15.4 | 800 | open |
| 25 | Verification and testing | `verification-and-testing.md` | Zingale 2.1.1, 2.1.2, 2.1.6, 2.3.6, 2.9.1, 2.9.2; pyro 2.4.12 (test), 3.4 (convergence, testing); Ulula 2.8.17; ZEUS 2.7.1 (approach), 2.7.6, 2.9.1 (approach), 2.9.8, 2.12.1 (approach), 2.12.4; Athena 3.1 (reproducibility), 3.8 | 3,900 | open |
| 26 | Advection and linear waves | `advection-and-linear-waves.md` | Zingale 2.5.19 (advection); pyro 2.2.5, 2.4.12 (advect, acoustic_pulse); Ulula 2.8.1–2.8.3, 2.8.8; ZEUS 2.9.4, 2.9.7; Athena 2.16.1, 2.16.2 | 5,300 | open |
| 27 | Shock tubes and interacting blast waves | `shock-tubes-and-interacting-blast-waves.md` | Zingale 2.4.4, 2.5.19 (shock tubes); pyro 2.3.3, 2.4.12 (sod); Ulula 2.8.4; ZEUS 2.7.3, 2.7.4 (blast waves), 2.9.2; Athena 2.16.4 | 5,400 | open |
| 28 | Shocks in several dimensions | `shocks-in-several-dimensions.md` | Zingale 2.5.19 (Sedov); pyro 2.4.12 (sedov, quad, ramp, logo); Ulula 2.8.10, 2.8.11; ZEUS 2.7.4 (wind tunnel, double Mach reflection); Athena 2.16.5 (shocks) | 3,900 | open |
| 29 | Instabilities, vortices and convection | `instabilities-vortices-and-convection.md` | pyro 2.4.12 (gresho, kh, rt, rt2, rt_multimode, bubble, convection, plume); Ulula 2.8.9, 2.8.12, 2.8.13; Athena 2.16.5 (instabilities) | 2,600 | open |
| 30 | Multidimensional and astrophysical MHD | `multidimensional-and-astrophysical-mhd.md` | ZEUS 2.9.3, 2.9.5, 2.9.6; Athena 2.16.6 | 4,700 | open |
| 31 | Packaging, configuration and build | `packaging-configuration-and-build.md` | Zingale 3.4, 3.5; pyro 3.1; Ulula 3.1; Athena 3.1 (versions, releases, configuration) | 1,900 | open |
| 32 | Data structures | `data-structures.md` | Zingale 3.1, 3.6; pyro 3.2; Ulula 3.2; ZEUS 3.1; Athena 2.1.4, 3.2 | 5,000 | open |
| 33 | The driver and the control of a time step | `driver-and-control-of-time-step.md` | pyro 3.3 (driver, parameters); Ulula 3.3, 3.5; ZEUS 3.2; Athena 3.1 (main loop, input, units), 3.5 (task lists) | 3,800 | open |
| 34 | Problem setups and user functions | `problem-setups-and-user-functions.md` | pyro 3.3 (problems); Ulula 2.2.3, 2.8.1, 3.6; Athena 3.6 | 1,200 | open |
| 35 | Output, restarts and analysis | `output-restarts-and-analysis.md` | Zingale 3.3; pyro 3.4 (output, plotting); Ulula 3.4; Athena 3.7 | 2,600 | open |
| 36 | Mesh refinement | `mesh-refinement.md` | Zingale 2.2.6, 2.6.5; pyro 2.1.4; Athena 3.4 | 4,500 | open |
| 37 | Parallelisation and performance | `parallelisation-and-performance.md` | Zingale 2.9.1, 3.2; Ulula 3.7; Athena 3.1 (optimisation), 3.5 (parallelisation), 3.9 | 2,500 | open |
