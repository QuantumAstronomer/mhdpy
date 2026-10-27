# Synthesis of Zingale's *Introduction to Computational Astrophysical Hydrodynamics*

This synthesis digests the text by Michael Zingale in its version of 26 January 2025, kept as `References/Computational Hydrodynamics Book/CompHydroTutorial.pdf`. Additions found by web search, which fill gaps in the text or check its claims, are marked **[GK]** and cited. A **[GK]** mark covers the rest of its paragraph or list item. Sections, equations, figures and tables of the text are cited by their numbers in this version. A section sign, as in §8.7, always refers to the text.

## 1. Overview

### 1.1 Origin, version and licence

The text grew out of notes for students who begin research projects in computational astrophysics at Stony Brook University (preface). It covers the methods in common use for the hydrodynamics of astrophysical flows, at the level of upper-level undergraduates. Exercises within the text illustrate the central ideas. Source code is available for every method and every figure, since running the methods is held to be the best way to understand them. The text calls itself a work in progress: chapters are added over time, and revisions follow at irregular intervals, usually for a new student or a course.

The title page dates the version summarised here to 26 January 2025. The copyright notice covers the years 2013 to 2017. The text is part of the Open Astrophysics Bookshelf. Its LaTeX source is kept on GitHub in Open-Astrophysics-Bookshelf/numerical_exercises, and a PDF built from it is published at open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf. **[GK]** The published PDF is rebuilt on every push to the main branch, so that it always shows the latest version. As of 27 October 2026 no commit has followed the version summarised here, so the published PDF and the local copy agree. The README of the repository gives the title as *Computational Hydrodynamics for Astrophysics*.

The text is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0). Zingale, of Stony Brook University, is its primary author. Ian Hawke (Southampton) contributed the material on WENO schemes, which the text treats in §5.5, §6.4 and §8.12. The preface traces the treatment of projection methods to an ongoing collaboration with Ann Almgren, John Bell, Andy Nonaka and Weiqun Zhang.

### 1.2 Scope and structure

The text runs to 266 printed pages in six parts, with 15 chapters and three appendices, followed by a bibliography of 88 entries. Its front matter of 22 pages holds the table of contents, lists of the figures and of the 53 exercises, the preface, a table of symbols and a list of contributors. The six parts cover the following.

- **Part I, Basics** (ch. 1 to 3). What a simulation is, and the numerical basics: sources of error, differentiation and integration, root finding, norms, the integration of ODEs and FFTs (ch. 1). The classification of PDEs as hyperbolic, elliptic or parabolic (ch. 2). Finite-volume grids, with differences and their order of accuracy, conservation, boundary conditions through ghost cells, and details of implementation (ch. 3).
- **Part II, Advection and Hydrodynamics** (ch. 4 to 8), nearly half of the text. Linear advection by first-order finite differences, with stability, implicit methods, Eulerian and Lagrangian frames, and convergence (ch. 4). Second- and higher-order finite-volume advection, with limiting, the reconstruct-evolve-average procedure, the method of lines, split and unsplit multi-dimensional schemes, and high-order finite differences with WENO reconstruction (ch. 5). Burgers' equation as a nonlinear model with shocks and rarefactions, also solved with WENO and flux splitting (ch. 6). The theory of the Euler equations: their eigenstructure, the exact solution of the Riemann problem, and alternative forms of the energy equation (ch. 7). The numerical methods for them (ch. 8). Interface states are reconstructed with piecewise constant, linear or parabolic profiles, with flattening and limiting on characteristic variables, and passed to Riemann solvers for the conservative update, with artificial viscosity. Further sections treat boundary conditions, multi-dimensional schemes including unsplit ones in three dimensions, source terms, simple geometries, test problems, method-of-lines integration, temperature and general equations of state, and WENO.
- **Part III, Elliptic and Parabolic Problems** (ch. 9 and 10). Elliptic equations, solved by Fourier methods, relaxation and multigrid (ch. 9). Diffusion, by explicit and implicit differencing and by multigrid in several dimensions, with non-constant conductivity and within hydrodynamics (ch. 10).
- **Part IV, Multiphysics Applications** (ch. 11 to 13). The coupling of physical processes, shown on diffusion-reaction and advection-diffusion problems, with a convergence test that needs no analytic solution (ch. 11). Reactive flow by operator splitting, with species, reaction networks and the burning modes of convective burning, deflagration and detonation (ch. 12). The planning of a simulation, from dimensionality and resolution to boundary conditions, timestep, convergence, computational cost and I/O (ch. 13).
- **Part V, Low Speed Hydrodynamics** (ch. 14 and 15). Incompressible flow by a cell-centred approximate projection method (ch. 14). Low Mach number methods, with their divergence constraints, multigrid for variable-density flows, atmospheric flows and combustion (ch. 15).
- **Part VI, Code Descriptions** (appendices A to C). The three companion codes, described below.

Magnetic fields are absent throughout: MHD occurs only in the title of a cited paper. Radiation transport is not treated, beyond mentions in the descriptions of the companion codes (preface, appendix A), and radiative cooling does not occur. Thermal conduction enters as diffusion in the energy equation (§10.6). Gravity enters as a source term (§8.7), through hydrostatic boundaries (§8.5) and in the atmospheric flows of §15.3. The gravitational potential appears only as an example of the Poisson equation (§2.3, §9.1, §9.2). Adaptive mesh refinement, mapped grids, domain decomposition on parallel computers and moving meshes built from a Voronoi tessellation are named only as directions for further study (§3.5). Smoothed particle hydrodynamics is named only as an alternative to grids (§3.1).

Two draft chapters of the same version complete the reference material, one on self-gravity and one on radiation hydrodynamics, kept as LaTeX files in `References/Computational Hydrodynamics Book/drafts/`. Both are unfinished. The draft on self-gravity holds headings and brief notes only, from the monopole approximation over multipole expansions to full Poisson gravity and conservative formulations. The draft on radiation hydrodynamics leaves its sections on the equations and on the hyperbolic system empty, and works out only a general elliptic solver with multigrid. The drafts are digested with elliptic equations and multigrid, marked as drafts.

**[GK]** In the main LaTeX file of the repository, the two drafts are built only in a debug mode, together with outlines on hydrodynamics test problems and on instabilities and turbulence, and an outline on software engineering practices is commented out. The published PDF omits all five (`CompHydroTutorial.tex`, version of 26 January 2025).

### 1.3 Companion codes

Three codes accompany the text (preface, appendices A to C). hydro_examples is a collection of simple, standalone one-dimensional Python scripts that illustrate the basic solvers, and many of the figures are made with it (github.com/zingale/hydro_examples). pyro is a two-dimensional code built for clarity and easy experimentation, with solvers for advection, diffusion, compressible and incompressible hydrodynamics, and multigrid (github.com/python-hydro/pyro2, arXiv:1306.6883). The preface adds that a grey flux-limited diffusion solver for radiation hydrodynamics is in development. hydro1d is a one-dimensional compressible code that implements the piecewise parabolic method of chapter 8 (github.com/zingale/hydro1d).

**[GK]** hydro_examples has since moved to github.com/python-hydro/hydro_examples, to which the old address redirects. hydro1d is written in modern Fortran and offers piecewise constant, linear and parabolic reconstruction. Its README declares it no longer developed and largely replaced by ppmpy, a Python implementation of the piecewise parabolic method (zingale.github.io/ppmpy). The text cites the pyro paper as accepted for publication. It appeared in Astronomy and Computing 6, 52–62 (2014), doi:10.1016/j.ascom.2014.07.003. That paper names a flux-limited diffusion solver for radiation hydrodynamics as future work (arXiv:1306.6883, §4), and the documentation of pyro 4.5 lists no radiation solver.

### 1.4 Notation

A table of symbols precedes the text and gives the meaning and units of each symbol (table 1). Vectors and matrices are set in bold. The conserved variables form the vector $\boldsymbol{\mathcal{U}}$, the primitive variables $\mathbf{q}$ and the characteristic variables $\mathbf{w}$, and $\mathbf{F}$ is the flux vector. The Jacobian matrix $\mathbf{A}$ has eigenvalues $\lambda$, collected in the diagonal matrix $\boldsymbol{\Lambda}$, and left and right eigenvectors $\mathbf{l}$ and $\mathbf{r}$, collected in the matrices $\mathbf{L}$ and $\mathbf{R}$. $\mathcal{R}(\mathbf{q}_L, \mathbf{q}_R)$ denotes the Riemann problem between a left and a right state. The velocity is $\mathbf{U}$, with components $u$ and $v$ in two dimensions, set upright as against the calligraphic $\boldsymbol{\mathcal{U}}$ of the conserved variables.

Thermodynamic quantities are specific, that is per unit mass: $e$ is the internal energy, $E$ the total energy, $h$ the enthalpy and $s$ the entropy, and $\tau = 1/\rho$ is the specific volume. Two adiabatic indices are kept apart. The first adiabatic exponent is $\Gamma_1 = (\partial \log p / \partial \log \rho)_s$, and the ratio of specific heats is $\gamma = c_p / c_v$, with $c_p = (\partial h / \partial T)_{p, X_k}$ and $c_v = (\partial e / \partial T)_{\rho, X_k}$. The quantity $\gamma_e = p/(\rho e) + 1$ links pressure and internal energy. The sound speed is $c = \sqrt{\Gamma_1 p / \rho}$, and the Lagrangian sound speed is $C = \sqrt{\Gamma_1 p \rho}$. $\mathcal{C}$ is the CFL number, and $M = |\mathbf{U}| / c$ the Mach number. Species enter through their mass fractions $X_k$, which sum to one, and their creation rates $\dot{\omega}_k$. The remaining symbols are the gravitational acceleration $\mathbf{g}$, the heat sources $H$ and the nuclear energy source $H_\mathrm{nuc}$, the thermal conductivity $k_\mathrm{th}$, the source term $S$ of the divergence constraint, and $\mathcal{I}$, the integral under a piecewise parabolic reconstruction. All units are those of the cgs system, except two that the table gives in metres: m s$^{-1}$ for the sound speed and g m$^{-2}$ s$^{-1}$ for the Lagrangian sound speed. **[GK]** The dimensions of $\sqrt{\Gamma_1 p / \rho}$ and $\sqrt{\Gamma_1 p \rho}$ show that centimetres are meant in both.

## 2. Numerical methods

To be written in ten subjects, each fed by one or two consecutive chapters, in the steps of `plan.md`.

## 3. Software architecture

To be written from §3.4, §13.6, §13.7 and appendices A to C, in the steps of `plan.md` that cover them.

## 4. Sources

The text: Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025. LaTeX source at github.com/Open-Astrophysics-Bookshelf/numerical_exercises, PDF at open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf, licence CC BY-NC-SA 4.0. The local copy is `References/Computational Hydrodynamics Book/CompHydroTutorial.pdf`. The drafts are `gravity/gravity.tex` and `radiation/radiation.tex` of the repository in the same version, with local copies in `References/Computational Hydrodynamics Book/drafts/`.

Works cited by the text:

- Zingale, M., pyro: a teaching code for computational astrophysical hydrodynamics, arXiv:1306.6883, cited as [86]. **[GK]** Astronomy and Computing 6, 52–62 (2014), doi:10.1016/j.ascom.2014.07.003.

Web sources **[GK]**, consulted on 27 October 2026:

- github.com/Open-Astrophysics-Bookshelf/numerical_exercises: README.md, CompHydroTutorial.tex, the three other draft chapters and the commit history, in the version of 26 January 2025.
- github.com/python-hydro/hydro_examples, the present location of hydro_examples.
- python-hydro.github.io/pyro2, the documentation of pyro 4.5.
- github.com/zingale/hydro1d: README.md at commit 0187eb7 of 13 August 2024.
