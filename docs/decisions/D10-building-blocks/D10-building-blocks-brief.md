# D10 — Numerical building blocks

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-12 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how the numerical building blocks of the finite-volume scheme are organised:

- reconstruction and slope limiters;
- Riemann solvers;
- the equation of state;
- the safeguards that keep density and pressure positive.

It decides how a simulation selects among them when it is set up, and how kernels are written so that they are fast in every direction and symmetric enough for the bit-for-bit tests of D02. The time integrator is D11's and the interface through which physics modules contribute their kernels is D12's. This brief decides what goes *into* the kernels.

The earlier briefs fix much of the frame:

- **D03 (discretisation).** Finite-volume Godunov with constrained transport and upwinded EMFs, second order first. There are provisions for higher order: interchangeable reconstruction, a ghost width that follows the stencil, and WENO and DG as experimental options. Passive scalars are advected with the mass flux, and dual energy is optional.
- **D04 (backend).** Kernels are Cython in pure Python mode, compiled for speed and run uncompiled for coverage, with bit-for-bit identical results (D04.3).
- **D06 (data model).** Kernels are always three-dimensional and execute direction-specific code, which "D10 decides how to produce" (D06.3). Velocity and field components must be handled symmetrically for the direction tests, including the order of additions (E06.1). Primitive variables are stored and computed once per stage, with floors in one place (D06.7).
- **D07 (geometry).** Geometry reaches the kernels as separable 1D arrays. Reconstruction on nonuniform grids and the source terms of curvilinear coordinates are designed here, together with whether kernels get a uniform-Cartesian specialisation, worth 4–8 % (E07.2).
- **D08 and D09.** Kernels write the fluxes of a block's boundary faces into flux registers when refinement is active (D08.6). They are called for a range of blocks and loop over them in compiled code (D09.2).

One constraint is new. A simulation chooses its Riemann solver, limiter and equation of state when it is set up, by parameter. Athena++ makes that choice when the code is compiled, and links exactly one implementation of each, so its kernels pay nothing for the choice. Python users expect to choose at run time. Whether that choice costs speed, and how to avoid it, is the first question of this brief.

**What the references do** (syntheses in `References/`):

| | Athena++ | Pyro | Ulula |
|---|---|---|---|
| Selection | Riemann solver, EOS and coordinates linked at compile time, one file each; reconstruction order at run time (`xorder`) | Riemann solver from a dictionary keyed by a run-time parameter, inside Numba kernels | methods selected by string comparison and `if` branches, in NumPy |
| Reconstruction | donor cell, PLM, PPM, WENO-Z; on primitive variables, or characteristic variables (the C version's default); limiters adapted to nonuniform and curvilinear grids (Mignone 2014) | PLM with MC limiter (2nd or 4th order), optional multidimensional flattening; WENO | none, minmod, van Leer, MC; PLM, with a MUSCL-Hancock half step |
| Riemann solvers | HLLE, HLLC, HLLD, Roe, LLF, plus low-dissipation and relativistic variants; Athena (C) also had an exact solver and an H-correction against the carbuncle instability | CGF (two-shock), HLLC, low-speed HLLC | HLL, HLLC |
| EOS | adiabatic or isothermal, hydro or MHD; general and tabulated EOS, for which HLLE, HLLC and HLLD were generalised | gamma law | ideal gas or isothermal, as branches |
| Robustness | floors on density and pressure in the EOS; Athena (C) had a first-order flux correction (FOFC) as a configure option | — | optional pressure floor, otherwise an error |

Two remarks from the syntheses bear on the choices here. Ulula's are made by branches in one class, which its synthesis judges would not scale beyond its size. Pyro keeps each solver in its own package, which keeps components apart but duplicates them.

## 2. Evidence

Both experiments time one evaluation of the time derivative (the D09 kernel: five variables, PLM with the MC limiter, HLL) on one block and one thread. They ran natively with Apple's Clang (the compiler of the macOS wheels) and in a Linux container with GCC (the compiler of the Linux wheels, [`E10.1d-Dockerfile`](experiments/E10.1d-Dockerfile)), for 2D blocks of 64² and 512² and 3D blocks of 32³. A first run gave inconsistent container timings (the same kernel at 5.1 and 7.6 million cells per second), because each form was timed in one stretch while the machine's speed drifted. The scripts now interleave: every one of nine repetitions times every form once, and the best is kept. All results below are from the interleaved runs, and every form gave a result bit-for-bit identical to the reference form.

### E10.1 — Selecting components at run time

**Method.** [`experiments/E10.1c-dispatch.py`](experiments/E10.1c-dispatch.py) generates variants of the kernel from its source ([`E10.1a-kernels.py`](experiments/E10.1a-kernels.py)), which select between two Riemann solvers and two limiters. The alternatives (`hll_alt`, `mc_alt`) are exact copies, so all forms compute the same result. The forms:

- **direct:** the kernel calls the solver and limiter by name (a fixed choice; the reference);
- **switch:** every call branches on an integer chosen at run time;
- **function pointer:** the kernel picks both functions once and calls them through C function pointers (types from [`E10.1b-kernels.pxd`](experiments/E10.1b-kernels.pxd));
- **switch, fixed per wrapper:** the switch form declared inline and called from a wrapper with constant selections;
- **fused types:** Cython's compile-time specialisation. The selection is an argument whose *type* is a fused type, one member per choice, and Cython compiles one copy of the kernel per combination with every `if T is <member>` resolved at compile time. The tests are written `(T is cython.char) if cython.compiled else (tag == 0)`, with distinct tag values, so that the uncompiled module takes the same branch. A separate check runs the uncompiled module with the alternatives replaced by recording stubs.

Full output: [`results/E10.1c-dispatch.md`](experiments/results/E10.1c-dispatch.md).

**Results.** Speed relative to the direct form:

| Compiler | Block | Switch | Function pointer | Switch, fixed per wrapper | Fused types |
|---|---|---|---|---|---|
| Clang (macOS) | 2D, 64² | 0.65 | 0.46 | 0.62 | **1.08** |
| Clang (macOS) | 2D, 512² | 0.65 | 0.49 | 0.65 | **1.00** |
| Clang (macOS) | 3D, 32³ | 0.65 | 0.47 | 0.66 | **1.02** |
| GCC (Linux) | 2D, 64² | 1.00 | 0.75 | 0.93 | **0.98** |
| GCC (Linux) | 2D, 512² | 1.02 | 0.84 | 1.02 | **0.99** |
| GCC (Linux) | 3D, 32³ | 0.93 | 0.71 | 0.83 | **0.83** |

The uncompiled fused module took the selected branch: no call of the alternatives with the first selection, and 144 and 1440 calls with the second.

- **Function pointers are costly with both compilers** (0.46–0.49 with Clang, 0.71–0.84 with GCC). A call through a pointer cannot be inlined, and the Riemann solver and limiter are called for every face and variable.
- **A branch per call costs a third of the speed with Clang,** yet nothing with GCC. Run-time selection inside a kernel would make speed depend on the platform the wheel was built for.
- **A wrapper with constants does not help:** a kernel this large is not inlined, so the constants never reach the branches.
- **Fused types matched the direct form with Clang (1.00–1.08) and in 2D with GCC (0.98–0.99).** In 3D with GCC they reached 0.83, as did the wrapper, while the plain switch reached 0.93. The specialised copy is exactly the direct code, so this points to how GCC lays out a larger module rather than to the mechanism. It should be watched in D04's benchmarks.
- **The uncompiled run takes the right branch,** so compile-time specialisation keeps D04.3's one-source-both-ways verification.

### E10.2 — One flux routine for all directions

**Method.** [`experiments/E10.2b-directions.py`](experiments/E10.2b-directions.py) times four versions of the same kernel:

- **direction-specific:** every direction written out by hand (`rhs` of E10.1a);
- **one routine, inline:** [`E10.2a-face-routine.py`](experiments/E10.2a-face-routine.py), with one face-flux routine called three times with the direction as constant arguments (offsets dk, dj, di and velocity components n, a, b), its five variables written out, and marked inline;
- **one routine, no inline hint:** the same without `@cython.inline`;
- **generic:** D06's kernel, whose routine also loops over the variables with small arrays.

Full output: [`results/E10.2b-directions.md`](experiments/results/E10.2b-directions.md).

**Results.** Speed relative to the direction-specific kernel:

| Compiler | Block | One routine, inline | One routine, no inline hint | Generic |
|---|---|---|---|---|
| Clang (macOS) | 2D, 64² | 0.97 | 0.97 | 0.62 |
| Clang (macOS) | 2D, 512² | 0.98 | 0.99 | 0.67 |
| Clang (macOS) | 3D, 32³ | 1.03 | 0.95 | 0.71 |
| GCC (Linux) | 2D, 64² | 1.01 | 1.00 | 1.00 |
| GCC (Linux) | 2D, 512² | 1.01 | 0.98 | 1.00 |
| GCC (Linux) | 3D, 32³ | 0.96 | 1.02 | 0.92 |

- **One routine per operation, called with the direction as constants, is as fast as code written out per direction,** with both compilers (0.95–1.03). The compilers inline it and fold the constants, with or without the hint.
- **D06's slowdown came from looping over the variables, not from passing the direction:** the generic kernel lost 29–38 % with Clang, while the routine that writes the variables out lost nothing. With GCC even the generic kernel lost little, another sign that compiler behaviour differs and that the code must be written for the less forgiving one.

**What the two experiments mean together.** Kernels can be written once per operation, with the direction as arguments to an inline routine, and once for all components, with the choice as a fused type. In both cases the compiler produces the specialised code, without a code generator and without losing the uncompiled verification of D04.3. What must stay out of the inner loops is any selection made at run time: branches, and above all function pointers.

## 3. Decisions

### D10.1 — Selecting components

How does a run-time choice of Riemann solver, limiter, reconstruction or equation of state reach the compiled kernels?

**Options**

- **A. Branches inside the kernels** on an integer chosen at set-up (Ulula's approach, compiled).
- **B. Function pointers,** chosen once per kernel call (Athena's C version used them for its integrators and boundary conditions).
- **C. Compile-time specialisation with fused types:** the choice is passed as an argument whose *type* is a fused type with one member per option. Cython compiles one copy of the kernel per combination, in which every `if T is <member>` is resolved at compile time. A simulation selects the specialisation once, at set-up, through the phase it registers (D09.1). For the uncompiled runs of D04.3, the tests are written `(T is cython.char) if cython.compiled else (tag == 0)`, with distinct tag values, so both forms take the same branch.
- **D. Code generation at build time:** a generator writes one kernel source per combination, which Cython then compiles. Equivalent to C in the result, but it adds a generator, generated files and a build step to maintain, where Cython already offers the mechanism.

**Recommendation.** C, compile-time specialisation with fused types. It was the only option as fast as a fixed choice with both compilers (E10.1, apart from one GCC case to be watched). It keeps a single source per kernel, and the guarded tests keep the uncompiled runs equivalent (D04.3). Run-time selection inside kernels (A, B) costs up to half the speed, and D adds machinery that Cython already provides.

The price is the number of compiled copies. Every fused dimension multiplies them: Riemann solver × limiter × equation of state × geometry. The fused dimensions are therefore reserved for choices inside the inner loops. The set of combinations a release compiles is an explicit, documented list, not the full product. Build time and wheel size are to be watched as components are added. This serves **performance**, with the flexibility of run-time choice at set-up for **ease of use**.

**Decision.** *(2026-10-12)* **C, compile-time specialisation with fused types**, following the recommendation, mainly for performance.

### D10.2 — Producing direction-specific code

How do kernels execute code specific to each direction (D06.3) without triplicating their source?

**Options**

- **A. Every direction written out by hand,** as the D06–D09 kernels. Fast, but three copies of every routine to keep identical.
- **B. Generated per direction at build time** from one template.
- **C. One routine per operation, written once,** taking the direction as arguments (offsets dk, dj, di and the components n, a, b), and called once per direction with constants. The compiler inlines it and folds the constants, producing direction-specific machine code from a single source. Variables are written out inside the routine; looping over them with small arrays is what made D06's generic kernel slow (E06.1, E10.2).

**Recommendation.** C, one routine per operation with the direction as constant arguments. It was as fast as hand-written direction-specific code with both compilers (E10.2), it keeps one source per operation, and it needs no generator. It realises D06.3 ("kernels execute direction-specific code") without its cost in code. The variables inside such a routine are written out (D10.7). This serves **readability** at no cost in **performance**.

**Decision.** *(2026-10-12)* **C, one routine per operation with the direction as constant arguments.**

### D10.3 — The equation of state

How is the equation of state represented?

**Options**

- **A. The ideal-gas law built into the kernels,** as Pyro. Simplest; adequate for the thesis problem (γ = 5/3).
- **B. A component with a fixed interface, selected as in D10.1:**
  - pressure from density and internal energy;
  - internal energy from density and pressure;
  - sound speed;
  - the conversions between conserved and primitive variables, where floors are applied (D06.7, D10.6).

  Ideal gas and isothermal come first, as in every reference code; the isothermal one also removes the energy variable from the registry (D06.6). A general or tabulated equation of state, as Athena++ offers, can follow without touching the Riemann solvers, provided they are written against the interface (Athena++ had to generalise its HLLE, HLLC and HLLD for that).
- **C. An equation-of-state object called from Python per block.** Flexible, but its calls would sit in the inner loops, which E10.1 shows is costly in any form other than compile-time specialisation.

**Recommendation.** B. The interface costs nothing with compile-time specialisation (D10.1), and it keeps the Riemann solvers and reconstruction free of hard-wired ideal-gas expressions, which is what made Ulula's equations "hard-wired" according to its synthesis. Isothermal flows are part of the standard test suites (D02). This serves **extensibility** at no cost in **performance**.

**Decision.** *(2026-10-12)* **B, a component with a fixed interface.** The equation of state must be general: tabulated and other non-ideal equations of state are meant to follow. Building it as a component with a fixed interface serves that extensibility, and since it comes at no cost in performance (D10.1), it is the way forward.

### D10.4 — Riemann solvers

Which Riemann solvers are provided, in which order, and with which interface?

**Options**

- **A. A minimal set: HLL for hydrodynamics and MHD.** Robust and simple, but diffusive at contact discontinuities. The thesis problem is about the mixing of a cold cloud into a hot corona across a contact.
- **B. The production set of Athena++, in stages:**
  - hydrodynamics: HLL, then HLLC (resolves contacts, the default), then LLF as the robust fallback for D10.6;
  - MHD: HLL, then HLLD (the default), then LLF;
  - Roe and the low-dissipation variants only if a test or application asks for them;
  - an exact solver for tests, not for production, as Athena++ judges ("no significant gain").
- **C. As B, plus Roe from the start,** the default of Athena (C). Accurate, but it needs entropy fixes and an eigensystem per equation of state.

All options share the interface:
- **Inputs:** left and right primitive states at a face, in the direction-relative order (density, normal velocity, tangential velocities, pressure, then fields), plus the face-normal field for constrained transport.
- **Outputs:** the fluxes, plus, for MHD, the face electric fields and the upwind weight of the mass flux used by the EMF construction (D03.5, E08.2).
- **Passive scalars:** their fluxes are formed once, after the solver, from the mass flux and the upwind concentration (D03.6), for every solver alike.

**Recommendation.** B. HLLC and HLLD are the defaults for good reason: they resolve contact and Alfvén waves that HLL smears, and the thesis problem is dominated by a contact. LLF is needed anyway as the fallback of D10.6. Every solver is a component selected as in D10.1, written against the equation-of-state interface (D10.3) and the shared Riemann-solver interface. This serves **correctness**, the physics the thesis problem depends on.

**Decision.** *(2026-10-12)* **B's staging, with Roe brought into the first set, which makes it C.** There is value in having the Roe solver from the start. It is the classic linearised solver and the default of Athena (C), and its eigensystems are the same ones the characteristic projection of D10.5 needs, so the work serves both. It comes with an entropy fix and Athena's H-correction against the carbuncle instability. The defaults remain HLLC (hydrodynamics) and HLLD (MHD); LLF is the fallback of D10.6.

### D10.5 — Reconstruction

Which reconstruction methods and limiters are provided, on which variables, and how do they handle nonuniform and curvilinear grids?

**Options**

- **A. PLM on primitive variables with selectable limiters** (MC as default, plus minmod and van Leer, as Ulula and Pyro offer), in the uniform form only.
- **B. As A, with the nonuniform and curvilinear form from the start:** slopes divided by distances to volume centroids (Mignone 2014, as Athena++), using the geometry arrays of D07.6. The uniform Cartesian case is a compile-time specialisation (D10.1) in which those weights reduce to constants, which also takes the 4–8 % of E07.2.
- **C. As B, plus characteristic projection and PPM** from the start.

The order after that: PPM (Athena++'s recommendation for production), characteristic projection as an option, then WENO-Z as one of D03's provisions. All of them sit behind one interface: reconstruct the left and right face states of a range of faces in one direction, with the ghost width the method requires (D07.5).

**Recommendation.** B. PLM on primitives is the second-order method of D03 and the reference codes' common ground. Building the nonuniform form in from the start costs little, because the geometry arrays are already there (D07.6) and the Cartesian specialisation removes their cost where they are not needed. Adding it later would mean revisiting every reconstruction routine. PPM and characteristic projection follow as separate components once the second-order verification suite passes. This serves **correctness** and **extensibility**.

**Decision.** *(2026-10-12)* **C: PLM with the nonuniform form, characteristic projection and PPM from the start.** PPM matters here, so that its difference from PLM can be tested on the same problems. WENO-Z follows as before.

Other reconstruction methods are noted for later, without a decision to implement them. These are research methods from the literature **[GK]**; none appears in the reference material:

- **WENO family:** WENO-JS (Jiang & Shu 1996), WENO-Z (Borges et al. 2008, already planned), WENO-AO with adaptive order (Balsara et al. 2016), TENO (targeted ENO, Fu et al. 2016) and the central-upwind WENO-CU6.
- **MP5:** fifth-order monotonicity-preserving reconstruction (Suresh & Huynh 1997).
- **PPM variants:** extremum-preserving PPM (Colella & Sekora 2008; McCorquodale & Colella 2011, the limiter Athena++ uses on Cartesian grids) and Colella's shock flattening (1990, as in Pyro).
- **Interface-sharpening hybrids:** THINC (Xiao et al. 2005) and the BVD principle (boundary variation diminishing, Sun et al. 2016), which combines a high-order scheme with THINC to keep contacts sharp. These are of interest for cloud–corona interfaces.
- **A posteriori limiting:** MOOD (Clain, Diot & Loubère 2011), which computes an unlimited high-order update first and falls back cell by cell where it fails, a relative of D10.6's FOFC.
- **Fourth-order finite volume:** with conversion between cell averages and point values (Felker & Stone 2018, Athena++ hydro), D03's higher-order path.
- **Gaussian-process reconstruction:** GP-WENO (Reyes et al. 2018).
- **Discontinuous Galerkin and ADER schemes:** D03's experimental provision.

### D10.6 — Positivity safeguards

What keeps density and pressure positive in extreme flows?

**Options**

- **A. Floors only:** density and pressure (or internal energy) are raised to floor values in the conversion to primitive variables, in one place (D06.7). The number of cells floored is counted and reported. Simple, but floors add mass and energy, so conservation suffers wherever they act.
- **B. Floors plus first-order flux correction (FOFC),** as Athena (C) offered. After the update, cells that would have negative density or pressure are recomputed with first-order LLF fluxes on their faces, which keeps positivity for a CFL number of at most about 0.5 **[GK]** while staying conservative. Floors remain as the last resort.
- **C. A positivity-preserving limiter** **[GK]** (Zhang & Shu) that limits reconstructed states towards the cell averages. Principled, but it constrains the time step and has to be designed together with each reconstruction method.

**Recommendation.** B. The thesis problem combines strong radiative cooling with high-contrast cloud–corona interfaces, exactly where pressure can turn negative. FOFC repairs those few cells conservatively, where floors alone would silently add energy. Counting floor activations makes visible how often the safety net catches anything. A dual-energy variable (D03.2) remains the complementary option for flows dominated by kinetic energy. This serves **correctness**.

**Decision.** *(2026-10-12)* **B, floors plus first-order flux correction**, as in Athena's implementation.

### D10.7 — Rules for writing kernels

Which rules do kernels follow so that results are symmetric and reproducible?

**Options**

- **A. A fixed set of rules, checked by tests:**
  - quantities are formed in direction-relative order (normal component first, then the tangential ones cyclically: x: y, z; y: z, x; z: x, y), so that the same one-dimensional problem along x, y or z gives bit-for-bit identical results (D02);
  - no branches that treat the two signs asymmetrically, such as `u > 0` against `u <= 0` (D02);
  - no arithmetic that depends on block boundaries or on the order in which blocks are processed (D05.5, D08.3);
  - every kernel has a per-block form for tests and runs uncompiled for coverage (D04.3);
  - variables are written out, not looped over with small arrays (E06.1, E10.2).
- **B. Symmetry tested with tolerances only,** which allows freer code but catches asymmetries only above the tolerance.

**Recommendation.** A. Every rule follows from an earlier decision or an experiment, and together they make the bit-for-bit invariants of D02 possible, the sharpest tests available. This serves **correctness**.

**Decision.** *(2026-10-12)* **A, a fixed set of rules, checked by tests**, following the recommendation and its explanation.

## 4. Consequences for higher layers

**For every layer**

- **Component choices:** choices inside the inner loops (Riemann solver, limiter and reconstruction, equation of state, geometry Cartesian or general) are fused-type arguments of the kernels. Cython compiles one copy per combination. The test of a choice is written `(T is <member>) if cython.compiled else (tag == <value>)`, so the uncompiled kernels take the same branch (D10.1, D04.3).
- **Compiled combinations:** the combinations a release compiles are an explicit, documented list. Build time and wheel size are watched as components are added (D10.1).
- **Selection:** a simulation selects its components at set-up. The phases it registers (D09.1) call the matching specialisations. No selection is made inside a kernel at run time (E10.1).
- **Direction:** each operation is one routine with the direction as constant arguments, called once per active direction. Variables inside it are written out (D10.2, D10.7).
- **Kernel rules (D10.7):** these hold for every kernel and are checked by tests:
  - direction-relative order of components;
  - no sign-asymmetric branches;
  - no dependence on block boundaries or processing order;
  - a per-block form;
  - uncompiled equivalence.

**For the physics and numerics to implement**

- **Equation of state:** an interface providing pressure, internal energy, sound speed and the conversions between conserved and primitive variables, where floors are applied. Ideal gas and isothermal come first; general and tabulated equations of state follow. Riemann solvers and reconstruction use only this interface (D10.3).
- **Riemann solvers:**
  - **First set:** HLL, HLLC, Roe and LLF for hydrodynamics; HLL, HLLD, Roe and LLF for MHD; an exact solver for tests.
  - **Defaults:** HLLC and HLLD.
  - **Roe:** an entropy fix and the H-correction against the carbuncle instability.
  - **Shared interface:** for MHD, every solver returns the face electric fields and the upwind weight of the mass flux.
  - **Passive scalars:** their fluxes are formed once from the mass flux (D10.4).
- **Eigensystems:** one eigensystem per equation of state and per system (hydrodynamics, MHD) serves both the Roe solver and the characteristic projection (D10.4, D10.5).
- **Reconstruction:**
  - **First set:** PLM with MC (default), minmod and van Leer limiters, in the nonuniform and curvilinear form (Mignone 2014); characteristic projection; PPM.
  - **Uniform Cartesian:** a specialisation in which the geometric weights are constants.
  - **Later:** WENO-Z.
  - **Noted, not decided:** the other methods listed under D10.5.
  - **Interface:** all methods share one interface (left and right face states for a range of faces in one direction) and declare the ghost width they need (D07.5).
- **Positivity:**
  - floors in the conversion to primitive variables, counted and reported;
  - first-order flux correction with LLF fluxes for cells that would turn negative;
  - dual energy (D03.2) as the complementary option (D10.6).

**On performance**

- **An unselected component costs nothing at run time.** Each combination is its own compiled specialisation (D10.1), so adding Roe, characteristic projection or further equations of state does not slow down a run that does not use them. The cost appears at build time and in wheel size, through the number of combinations in the release list.
- **When selected, some components cost more per face than the defaults** **[GK]**:
  - **Roe** needs the eigensystem at every face, which is heavier than HLLC in hydrodynamics and than HLLD in MHD.
  - **Characteristic projection** adds two projections per cell and direction.
  - **A tabulated equation of state** replaces closed-form expressions by table look-ups and interpolation in every call for pressure and sound speed.

  These are choices made per simulation, with their cost measured in the benchmarks of D02.
- **Roe depends on the equation of state more than the other solvers** **[GK]**. Its averages and eigensystems are derived for the ideal-gas and isothermal laws. For general and tabulated equations of state, the HLL family (HLLE, HLLC, HLLD) applies, which is how Athena++ supports its general EOS. The list of compiled combinations therefore pairs Roe and characteristic projection only with equations of state that provide an eigensystem.

**For the verification of D02**

- Every Riemann solver and reconstruction method gets unit tests and Hypothesis properties:
  - consistency (equal states give the physical flux);
  - mirror symmetry;
  - positivity of reconstructed states where the method guarantees it.
- Every fused specialisation in the release list is covered by the equivalence test of compiled against uncompiled kernels (D04.3).
- The same one-dimensional problem along x, y and z must give bit-for-bit identical results, for every solver and reconstruction (D10.7).
- PLM against PPM on the same problems is part of the verification matrix, as the comparison behind D10.5.

**For brief D11 (time integration)**

- PPM is recommended by Athena++ with RK3, PLM with RK2 or VL2. The integrator choice should allow those pairings.
- FOFC acts after a stage's update, so the integrator must give it a place: recompute the flagged cells' fluxes, then redo their update (D10.6).

**For brief D12 (physics module interface)**

- A physics module provides its kernels as routines over a range of blocks, with its component choices as fused types. It never calls through function pointers or Python in its inner loops.

**For D04 (build) and the project setup**

- The number of compiled specialisations grows with every fused dimension. CI tracks build time and wheel size, and the release list of combinations is kept in one place.
- E10.1 found one GCC case (3D, fused types at 0.83 of the direct form) to watch in the benchmarks.
