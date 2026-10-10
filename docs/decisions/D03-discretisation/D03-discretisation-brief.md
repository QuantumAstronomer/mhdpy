# D03 — Discretisation family

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-10 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how the equations are turned into discrete form. That covers which family of methods is used, which variable carries the energy, which formal order of accuracy is aimed for, how multidimensional updates are combined, how passive scalars are carried, and how the divergence-free constraint on the magnetic field is kept.

In the bottom-up order of the briefs it is the deliberate exception (see `decisions/README.md`). The discretisation sits high in the architecture, but it determines what the lower layers must be able to hold. Constrained transport, for example, needs magnetic fields on cell faces and electric fields on cell edges, next to the cell-centred hydrodynamic variables. The discretisation also determines which kernel is representative for the performance measurements of the compute-backend brief (D04). MHD comes only after curvilinear coordinates in the roadmap, but the data model is designed in D06, long before then, so the MHD choice has to be made now.

Brief D02 adds a constraint: every scheme must have a known formal order and problems that verify it, and the benchmark problems of the reference codes must be reproducible.

**What the references do** (Athena, Pyro, Ulula and ZEUS syntheses, and the CompHydro book synthesis, in `References/`):

| | Athena / Athena++ | Pyro (compressible) | Ulula | ZEUS-2D |
|---|---|---|---|---|
| Family | finite volume, Godunov (Riemann solvers) | finite volume, Godunov | finite volume, Godunov | finite differences on a staggered mesh; control-volume form only for advection |
| Energy variable | total energy | total energy | total energy | internal energy |
| Shock capturing | upwinding through Riemann solvers | Riemann solvers, plus a little artificial viscosity | Riemann solvers | artificial viscosity (von Neumann–Richtmyer or tensor) |
| Multi-D | unsplit (CTU in Athena; method of lines in Athena++) | unsplit (CTU; method of lines) | dimensionally split (Strang) | operator split, directionally split advection |
| Formal order | 2 (4th-order hydro variant in Athena++, not for MHD) | 2; 4th-order FV and SDC variants | 2 | 2 in smooth flow; measured below 2 for full MHD |
| ∇·B | constrained transport: face-centred B, edge EMFs upwinded by the contact (Gardiner & Stone 2005) | no MHD | no MHD; the paper suggests divergence cleaning (Dedner et al. 2002) for an extension | constrained transport, with EMFs from the method of characteristics |
| Scalars | conserved densities; fluxes derived from the Riemann mass flux | registered variables advected as passive scalars | — | "consistent transport": specific quantities carried by the mass fluxes |

Three arguments recur in the syntheses:

- **Why Athena left the ZEUS family** (S08): operator-split schemes that are not in conservation form "are unsuitable" for mesh refinement, because conservation must be enforced at fine/coarse boundaries. ZEUS's own papers concede that Godunov codes do better on strong shocks.
- **Why MHD needs unsplit integration:** in a dimensionally split sweep, the normal field component cannot evolve, while the divergence constraint requires all components to evolve together.
- **Why Athena upwinds its edge EMFs** (Gardiner & Stone 2005): simply averaging the four face EMFs around an edge is inconsistent. It does not reduce to the 1D scheme for grid-aligned flow, and it fails the field-loop test.

## 2. Evidence

### E03.1 — Finite-volume Godunov against ZEUS-type finite differences

**Question.** How do the two families of the reference codes compare on conservation, shock jumps, and the accuracy of the thermal state when kinetic energy dominates?

**Method.** [`experiments/E03.1-fv-vs-fd.py`](experiments/E03.1-fv-vs-fd.py) (own lockfile; development machine) compares two minimal solvers on identical problems:

- [`E03.1-godunov1d.py`](experiments/E03.1-godunov1d.py): finite volume, total energy, HLL, MC limiter, SSP-RK2 (the solver of E02.1);
- [`E03.1-zeus1d.py`](experiments/E03.1-zeus1d.py): a sketch of the ZEUS-2D hydro algorithm. It has a staggered mesh, internal energy, von Neumann–Richtmyer artificial viscosity, implicit compressional heating, and consistent transport with van Leer interpolation.

The problems are:

- the Sod shock tube and Toro's test 3 (pressure ratio 10⁵), against their exact solutions, at N = 128 … 1024;
- an isentropic sound wave carried by a bulk flow at Mach 0 … 100. Its exact entropy stays uniform, and by Galilean invariance the physics is the same at every Mach number, so any growth of the entropy error with Mach number is numerical.

Full output: [`experiments/results/E03.1-fv-vs-fd.md`](experiments/results/E03.1-fv-vs-fd.md).

![E03.1](experiments/results/E03.1-fv-vs-fd.png)

**Result 1: conservation and shock jumps.**

| | FV, Sod | FD, Sod | FV, Toro 3 | FD, Toro 3 |
|---|---|---|---|---|
| Total-energy change (N = 1024) | 0 | −0.09 % | 0 | −0.30 % |
| Post-shock pressure error, N = 128 → 1024 | −2.6 × 10⁻⁴ → −3.4 × 10⁻⁵ | −2.4 × 10⁻³ → −1.8 × 10⁻³ | −5.2 × 10⁻³ → −5.5 × 10⁻⁴ | −6.1 × 10⁻³ → −3.8 × 10⁻³ |
| L1 density error (N = 1024) | 6.6 × 10⁻⁴ | 1.3 × 10⁻³ | 1.8 × 10⁻² | 3.1 × 10⁻² |

Both conserve mass. Only the finite-volume scheme conserves total energy, to round-off. The ZEUS-type scheme's post-shock pressure error barely decreases with resolution: an energy error at the shock leads to a **wrong jump**, not a smeared but correct one. In Toro's test 3 it overshoots the density of the shocked shell by about 8 % (figure, middle panel), while finite volume reaches the exact value.

**Result 2: thermal accuracy in supersonic flow.** The usual argument for evolving internal energy is that pressure, obtained as the difference of total and kinetic energy, becomes inaccurate when kinetic energy dominates. The measurement:

| Bulk Mach number | 0 | 1 | 10 | 100 |
|---|---|---|---|---|
| Entropy error, FV (total energy) | 4.6 × 10⁻¹¹ | 3.1 × 10⁻¹⁰ | 2.9 × 10⁻⁹ | 2.9 × 10⁻⁸ |
| Entropy error, FD (internal energy) | 1.1 × 10⁻⁸ | 1.0 × 10⁻⁵ | 1.4 × 10⁻⁵ | 1.4 × 10⁻⁵ |

The total-energy scheme's error does grow with Mach number, but **linearly, not quadratically**, and at Mach 100 it is still 500 times smaller than the internal-energy scheme's. The latter is independent of Mach number but large as soon as the flow moves, because advecting density and internal energy separately does not keep them isentropic.

**What this means.**

- For the regime of the purpose (galactic-fountain clouds, Mach numbers of order 1–10 against the corona), total energy is clearly the more accurate choice.
- **[GK]** The pressure problem of total-energy schemes becomes serious at much higher Mach numbers, of order 10³ and above, as in cosmological accretion flows. It is usually solved by a dual-energy formalism that also evolves an entropy or internal-energy variable.
- The finite-volume scheme's exact conservation is what gives it correct shock jumps. It is also what mesh refinement (S08) and D02's conservation tests require.

### E03.2 — Divergence control on the field-loop test

**Question.** How do the candidate ways of keeping ∇·B = 0 behave on the test that Gardiner & Stone (2005) designed to expose them?

**Method.** [`experiments/E03.2-field-loop.py`](experiments/E03.2-field-loop.py) runs the field-loop advection test exactly as Athena++ sets it up (`inputs/mhd/athinput.field_loop`). The domain is [−1, 1] × [−0.5, 0.5] with 128 × 64 cells, v = (2, 1), and a weak loop of field (plasma β ≈ 10⁶), evolved to t = 2, when the loop is back at its starting point. The solver is a minimal 2D ideal-MHD method of lines, [`E03.2-mhd2d.py`](experiments/E03.2-mhd2d.py): MC-limited PLM, HLL, SSP-RK2. Only the divergence treatment differs between runs:

1. **none:** a cell-centred field without any control;
2. **GLM:** cell-centred, with hyperbolic-parabolic divergence cleaning (Dedner et al. 2002, mixed form of Mignone & Tzeferacos 2010);
3. **CT, averaged EMFs:** face-centred field, edge EMFs averaged from the faces (Balsara & Spicer 1999);
4. **CT, upwinded EMFs:** as Athena++ (`src/field/calculate_corner_e.cpp`), including its upwind weights.

Full output: [`experiments/results/E03.2-field-loop.md`](experiments/results/E03.2-field-loop.md).

![E03.2](experiments/results/E03.2-field-loop.png)

**Result.**

| Divergence treatment | Magnetic energy at t = 2 (exact: 1) | Scaled ∇·B at t = 0 → t = 2 | L1 field error at t = 2 | Run time |
|---|---|---|---|---|
| none | **1.56** | 0.15 → 0.31 | 0.163 | 25 s |
| GLM cleaning | 0.82 | 0.15 → 5.3 × 10⁻³ | 0.026 | 27 s |
| CT, averaged EMFs | 0.88 | 10⁻¹⁶ → 5.6 × 10⁻¹⁵ | 0.032 | 28 s |
| CT, upwinded EMFs | 0.83 | 10⁻¹⁶ → 5.2 × 10⁻¹⁵ | 0.026 | 29 s |

**What this means.**

- **Without control, the solution is wrong, not merely inaccurate.** Magnetic energy grows by 56 %, which ideal MHD forbids, and the loop is shredded.
- **Constrained transport keeps ∇·B at round-off level throughout,** with either EMF construction.
- **Averaging the EMFs gives a visibly distorted loop** (a bright crescent and a trailing arc), exactly the inconsistency Gardiner & Stone describe. Its higher magnetic energy is not better accuracy: its field error is larger.
- **GLM cleaning and CT with upwinded EMFs preserve the loop about equally well** on this test. GLM, however, leaves a divergence of order 10⁻² to 10⁻³ of the field gradients. That is not zero; it is controlled, and its level depends on two tuning parameters (cleaning speed and damping).
- **The cost differences are small:** CT with upwinded EMFs is about 7 % slower than GLM here.
- The cell-centred schemes start from a non-zero divergence because their discrete divergence operator differs from the face-centred one with which the initial field was constructed. With cell-centred fields, "divergence-free" depends on which operator one asks.

## 3. Decisions

### D03.1 — Discretisation family

Which family of methods discretises the equations?

**Options**

- **A. Finite-volume Godunov.** Cell-averaged conserved variables, updated by the difference of face fluxes obtained from Riemann solvers. Used by Athena(++), Pyro and Ulula. Conserves mass, momentum and energy to round-off, which mesh refinement requires (S08). Shocks are captured by the Riemann solvers, without tuned artificial viscosity.
- **B. Staggered finite differences (ZEUS).** Velocities on faces, internal energy, artificial viscosity, operator splitting. Simple, fast per cell (S08 reports ZEUS about 4× faster per cell than Athena with HLLD), and new physics is easy to insert as an extra substep. But it is not conservative in total energy, and E03.1 shows the consequence: wrong shock jumps that do not converge away.
- **C. Conservative high-order finite differences (WENO).** Point values with flux reconstruction (CompHydro book §5.5, §8.12). High order on uniform grids, but more delicate on refined and curvilinear meshes, and not used by any reference code for MHD.
- **D. Discontinuous Galerkin.** **[GK]** High order with a compact stencil; an active research field, but far from the reference codes, whose test suites mhdpy is to reproduce.

**Recommendation.** A, finite-volume Godunov. It is the only family that delivers what the correctness criterion demands: conservation to round-off, and correct shock jumps (E03.1: exact energy conservation and a converging post-shock pressure, against a 0.1–0.3 % energy loss and a non-converging jump for B). It is the family of the reference codes, including Athena(++), which the purpose names as the model, so their verification problems apply directly. And it is the precondition for conservative mesh refinement, second on the roadmap. ZEUS's speed advantage per cell does not outweigh correctness, the first priority. This serves **correctness**.

**Decision.** *(2026-10-10, revised before commit on the same day)* **A, finite-volume Godunov**, as a proven method, for production use. In addition, the door is kept open for experimental work with higher-order families, WENO and discontinuous Galerkin. This is done through provisions in the interfaces, not by implementing them:

- **An interchangeable spatial operator.** The spatial discretisation turns the state into its time derivative (method-of-lines form), rather than being a reconstruct-then-Riemann-solve sequence built into the framework.
- **Every data placement is supported.** The state on the grid can hold cell-centred, face-centred, line-centred (edge) and node-centred (vertex) data. This is the most general choice: it accommodates constrained transport (faces and edges), a cell-centred magnetic field (see below), vector potentials (nodes in 2D, edges in 3D), and node-based discretisations, so later layers are not constrained by the data model.
- **Multi-valued cells.** A variable can hold more than one value per cell: the degrees of freedom of a DG scheme, and later the angles of radiation transport.
- **The magnetic field can be registered either face-centred or cell-centred.** Constrained transport is tied to the finite-volume picture (face averages updated through Stokes' theorem). **[GK]** For WENO and DG, the established divergence control is GLM cleaning (Dedner et al. 2002), the standard in DG-MHD codes such as FLEXI and Trixi.jl and common in WENO codes, which needs a cell-centred field. Exactly divergence-free alternatives (vector-potential schemes, upwind CT for finite differences, divergence-free DG bases) exist but are tied deeply into each scheme. GLM therefore remains possible for non-finite-volume schemes (D03.5). Its other ingredients fit the framework as they are: the cleaning scalar psi is one more cell-centred variable, its damping is a source term, and its treatment of the normal field at faces is a wrapper around the Riemann solver (D10).

### D03.2 — Energy variable

Which energy equation is evolved?

**Options**

- **A. Total energy (conservative).** As Athena(++), Pyro and Ulula. Pressure is derived as total minus kinetic (and magnetic) energy. Energy is conserved to round-off, and shock jumps are correct.
- **B. Internal energy (ZEUS).** Pressure is evolved directly. Total energy is not conserved, so shock jumps are wrong (E03.1).
- **C. Total energy plus an auxiliary entropy or internal-energy variable ("dual energy").** **[GK]** The auxiliary variable is used for the pressure only where kinetic energy dominates extremely, as in cosmological codes. It needs a switching criterion and one extra evolved variable.

**Recommendation.** A, total energy, with the explicit provision that an auxiliary entropy variable (C) can be added later as an extra evolved scalar, without changing the framework, should a target problem need it. E03.1 shows that in mhdpy's regime total energy is both conservative and the *more* accurate choice for the thermal state: its entropy error is 500 times smaller than the internal-energy scheme's even at Mach 100, and it grows only linearly with Mach number. Dual energy solves a problem of Mach numbers of order 10³ and more, which the purpose does not require now, and the provision keeps the door open at no cost. This serves **correctness**.

**Decision.** *(2026-10-10)* **A, total energy**, following the recommendation, with the provision that a dual-energy variable can be added later as an additional evolved scalar.

### D03.3 — Formal order of accuracy

What formal order of accuracy does the scheme aim for?

**Options**

- **A. Second order, with a choice of reconstructions.** Piecewise linear (PLM), piecewise parabolic (PPM) or WENO-type reconstruction within a second-order finite-volume framework, as Athena++ does by default. Higher-order reconstructions lower the error without raising the formal order. Constrained transport, mesh refinement and geometric source terms are all naturally second order.
- **B. Fourth-order finite volume.** As Athena++'s fourth-order hydro (Felker & Stone 2018) and Pyro's fv4 solver. Distinguishes cell averages from point values, needs wider stencils (more ghost cells) and fourth-order versions of every component. Athena++ has not merged a fourth-order CT, so it is hydro only.
- **C. A higher order still** (high-order FD-WENO, DG): see D03.1.

**Recommendation.** A, second order, with the ghost-zone width left as a parameter set by the chosen reconstruction (2 for PLM; up to 4 for PPM with MHD, as in Athena++). Second order is what every reference code uses for MHD and what CT and mesh refinement support. Fourth order would multiply the work on every later layer for a gain only in smooth flows. Choosing A does not close the door: a later brief could supersede it for hydro, as Athena++ did, provided the data model allows wider stencils. This serves **correctness**, through a scheme whose order every component can actually deliver, and **performance**, since the code is not paying for a fourth order it cannot use.

**Decision.** *(2026-10-10, revised before commit on the same day)* **A, second order first**, with **provisions for higher-order spatial schemes**, which are explicitly in scope for later. A scheme's overall order is the lowest of its spatial and temporal orders, and constrained transport is second order, so higher-order Runge–Kutta integrators (D11) raise the overall order only together with a higher-order spatial scheme. **[GK]** For finite-volume MHD, fourth-order CT schemes exist in the literature, and Athena++ had one in development, so higher order does not rule out CT. The provisions:

1. The ghost-zone width is a parameter (WENO5 needs 3 zones; fourth-order finite volume or WENO7 needs 4 or more).
2. The meaning of stored values is explicit: cell average, point value or DG coefficient, with conversion operators between them where a scheme needs them. Second order does not distinguish cell averages from point values; fourth order does.
3. Initial conditions are supplied as functions, not as values at cell centres, so that the framework can produce cell averages (by quadrature) to the order the scheme requires.
4. The time-step limit is provided by the spatial scheme (DG, for instance, needs a CFL number smaller by a factor of about 2p + 1).
5. Boundary filling, prolongation and restriction have a selectable order (D08), so that mesh refinement does not limit a higher-order scheme.
6. Time integrators of higher order than two are supported (D11).

Moving beyond second order in practice would supersede this sub-decision.

### D03.4 — Multidimensional strategy

Are the directions updated together (unsplit) or one after another (dimensionally split)? *Which* unsplit time integrator to use (method of lines, VL2, CTU) is the subject of brief D11.

**Options**

- **A. Unsplit.** Fluxes in all directions are computed from the same state and applied together, as in Athena(++) and Pyro. Directions are treated symmetrically, and constrained transport is possible.
- **B. Dimensionally split** (Strang or alternating order), as Ulula and ZEUS. Each sweep is a 1D problem, which is simple and cheap. But in a split sweep the normal field component cannot evolve, so constrained transport is impossible. Splitting also introduces a splitting error and treats the directions asymmetrically within a step.

**Recommendation.** A, unsplit. It is required by constrained transport (D03.5), and it matches the symmetry invariants of D02. Same problem along x, y and z, mirrored problems: an unsplit update gives identical results by construction, while a split one depends on the sweep order. This serves **correctness**.

**Decision.** *(2026-10-10)* **A, unsplit**, following the recommendation; this is the norm in modern hydrodynamics and MHD codes.

### D03.5 — Divergence of the magnetic field

How is ∇·B = 0 maintained?

**Options**

- **A. No control.** Rejected by E03.2: the solution becomes physically wrong (magnetic energy grows by 56 %).
- **B. Powell's eight-wave source terms.** **[GK]** Source terms proportional to ∇·B make the equations Galilean invariant again, but they are non-conservative and let divergence errors accumulate.
- **C. Hyperbolic-parabolic cleaning (GLM, Dedner et al. 2002).** An extra scalar carries divergence errors away and damps them. Everything stays cell-centred, which keeps the data model, mesh refinement and curvilinear coordinates simple. In E03.2 it preserves the loop as well as CT, but ∇·B is only controlled (10⁻²–10⁻³ of the field gradients), not zero, and the result depends on a cleaning speed and a damping parameter.
- **D. Projection.** **[GK]** After every step, an elliptic equation is solved to remove the divergence: a global solve per step, and it changes the field non-locally.
- **E. Constrained transport with averaged edge EMFs.** ∇·B = 0 to round-off (E03.2), but the EMF construction is inconsistent and distorts the loop (E03.2; Gardiner & Stone 2005).
- **F. Constrained transport with upwinded edge EMFs (Gardiner & Stone 2005), as Athena(++).** Face-centred normal field components, updated by Stokes' theorem with edge EMFs that are upwinded according to the mass flux. ∇·B = 0 to round-off in every cell, and the best loop preservation in E03.2. It requires face-centred and edge-centred quantities in the data model, divergence-preserving restriction and prolongation for mesh refinement, and EMF corrections at fine/coarse boundaries. All of these exist in Athena++ as a worked reference.

**Recommendation.** F, constrained transport with upwinded EMFs. It is the only option that keeps the divergence constraint exactly, as the integral form of the induction equation demands, and it preserved the field loop best in E03.2. GLM matched it on loop shape. But "controlled" is weaker than "exact" for the first priority, and GLM's parameters would themselves need verifying. CT is also what Athena(++) uses, so its MHD test suite (field loops including the 3D variant with out-of-plane velocity, linear waves, Orszag–Tang) can be reproduced as the success criterion requires. The price is paid in the data model and in mesh refinement, which must handle face- and edge-centred quantities. Choosing CT now, before D06 designs the data model, is what keeps that price manageable. The run-time cost in E03.2 was about 7 %. This serves **correctness** directly, at a small cost in **performance** and in the complexity of the lower layers.

**Decision.** *(2026-10-10, revised before commit on the same day)* **F, constrained transport with upwinded edge EMFs, as implemented in Athena++**, following the recommendation. E03.2 shows it to be the best of the methods tested, and it is *the* divergence treatment of the finite-volume scheme. GLM cleaning (C) is not implemented now, but remains possible as the divergence treatment for non-finite-volume schemes (WENO, DG), through the provisions of D03.1. No provisions are made for the other methods.

### D03.6 — Passive scalars

How are passive scalars, such as metallicity, carried with the flow?

**Options**

- **A. Conserved scalar densities (ρX) with fluxes derived from the Riemann-solver mass flux.** The concentration X is reconstructed, and the scalar flux is the mass flux times the upwind concentration. This is Athena++'s approach, and ZEUS's "consistent transport" in finite-volume form. **[GK]** A uniform concentration stays exactly uniform, and the concentration stays within the bounds of its neighbours. Every scalar travels exactly with the mass that carries it.
- **B. Scalars as independent conserved variables with their own Riemann-solver flux.** Simpler to bolt on, but the scalar flux is computed independently of the mass flux, so scalar and mass transport can disagree. Uniform concentrations are then not preserved exactly.

**Recommendation.** A. The scientific use of scalars in mhdpy, such as metallicity tracing how much coronal gas a fountain cloud mixes in, depends on scalars moving *exactly* with the mass. A guarantees that by construction, and it gives D02 an exact invariant to test (uniform concentration preserved bit for bit). This serves **correctness**.

**Decision.** *(2026-10-10)* **A, conserved scalar densities with fluxes derived from the mass flux**, following the recommendation. Passive scalars are a native part of the framework, and every scalar is tied to the mass flux.

## 4. Consequences for higher layers

**For brief D04 (compute backend)**

- The representative kernels for performance measurements are those of second-order finite-volume MHD with constrained transport: primitive reconstruction (PLM, PPM), the Riemann solver (HLL-type, later HLLD), and the edge-EMF construction with its upwind weights. The production target of architecture.md §1.3 is a hydrodynamics run, so a hydrodynamic kernel sets the throughput requirement. The MHD kernels must not be disproportionately slower.

**For brief D05 (parallelism) and D08 (boundaries and communication)**

- Besides cell-centred data, face-centred magnetic fields and edge-centred EMFs cross block boundaries. Faces and edges shared by two blocks must stay identical. Athena++ averages shared face and edge values even without refinement, because round-off would otherwise make the two copies drift apart, and with CT such errors never decay.
- Mesh refinement needs flux corrections and EMF corrections at fine/coarse boundaries, area-weighted restriction, and divergence-preserving prolongation (Tóth & Roe 2002) for the face fields.

**For brief D06 (data model)**

- The state on the grid supports all four placements: **cell-centred** (volume averages), **face-centred** (area averages, one array per direction, one larger along its own direction), **line-centred** (edge, line averages) and **node-centred** (vertex) data. In particular:
  - conserved hydrodynamic variables, passive-scalar densities and an optional dual-energy entropy are cell-centred;
  - with constrained transport, the magnetic field is face-centred and its EMFs are line-centred;
  - for non-finite-volume schemes, the magnetic field (and the GLM scalar psi) can be registered cell-centred instead.
- Variables can carry more than one value per cell (degrees of freedom of a DG scheme; later, angles of radiation transport).
- Every variable records what its values mean (cell average, point value, DG coefficient), so that conversions can be applied where a scheme needs them.
- The ghost-zone width is a parameter: at least 2, up to 4 for PPM with MHD, and wider for higher-order schemes.

**For brief D07 (mesh and geometry)**

- Geometry must provide not only cell volumes and face areas but also edge lengths, which constrained transport needs in curvilinear coordinates.

**For brief D10 (numerical building blocks)**

- Riemann solvers must return the mass flux separately: passive-scalar fluxes are derived from it (D03.6), and so are the upwind weights of the edge EMFs (D03.5). They must also return the face EMFs for constrained transport.
- The Riemann-solver interface must allow wrappers that modify the interface states before the flux is computed, as GLM cleaning does with the normal field and psi.
- Reconstruction acts on primitive variables, including the concentrations of passive scalars.

**For brief D11 (time integration)**

- The integrator is unsplit and works on a spatial operator in method-of-lines form, so that the spatial scheme is interchangeable (D03.1). Every stage updates the face-centred fields with the edge EMFs.
- Integrators of higher order than two must be supported (D03.3), and the time-step limit is obtained from the spatial operator rather than computed by the integrator itself.

**For brief D08 (boundaries and refinement) and D15 (configuration and user interface)**

- Boundary filling, prolongation and restriction have a selectable order (D03.3).
- Problem setups supply initial conditions as functions, from which the framework produces the values the scheme needs (cell averages by quadrature, point values, or DG coefficients).

**For brief D12 (physics modules)**

- An auxiliary entropy variable (dual energy) can be added as an optional module that registers one more evolved scalar (D03.2). Source terms such as radiative cooling act on the total energy.

**For the verification of D02**

- Exact invariants come with these choices and are tested as such:
  - ∇·B equal to zero at round-off level in every cell, at every step;
  - total mass, momentum and energy conserved to round-off with periodic boundaries;
  - a uniform passive-scalar concentration preserved bit for bit.
- The MHD test suite includes the field-loop test in 2D and in its 3D variant with out-of-plane velocity (Gardiner & Stone 2008).
