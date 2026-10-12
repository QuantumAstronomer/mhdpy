# D11 — Time integration and operator splitting

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-12 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how the solution is advanced in time. It covers:

- the integrator for the hyperbolic part and how its stages are stored;
- how source terms are coupled to it;
- how diffusive terms such as thermal conduction are advanced;
- how the time step is chosen;
- whether levels of mesh refinement share one time step.

The physics of the thesis problem makes these choices consequential. Radiative cooling in dense gas acts much faster than the flow crosses a cell. Thermal conduction in the hot corona has an explicit stability limit that shrinks with the square of the cell size. Both are *stiff* with respect to the hydrodynamic time step, in different ways.

The earlier briefs fix much of the frame:

- **D03 (discretisation).**
  - **Method:** a method-of-lines finite-volume scheme, unsplit, second order first.
  - **Higher order:** the provisions include Runge–Kutta methods of more than second order and a time-step limit supplied by the scheme.
  - **Dual energy:** an optional dual-energy variable.
- **D04 and E04.5.** The combination of integrator stages is a compiled kernel. Low-storage Runge–Kutta schemes, which combine registers with weights, map onto one such kernel per stage.
- **D06.** Stage registers are arrays of the state's layout, declared through the registry.
- **D08.6.** Flux and EMF correction at refinement boundaries assumes that all levels advance with the same time step; subcycling would supersede it.
- **D09.** A step is a sequence of phases registered as data. The integrator contributes its stages as phases. The time step is a minimum over blocks, exact in any order.
- **D10.**
  - **Pairings:** PPM pairs with RK3 and PLM with RK2 or VL2 in Athena++'s recommendations.
  - **FOFC:** first-order flux correction needs a place in each stage, after the update.

**What the references do** (syntheses in `References/`):

- **Athena++** uses the method of lines with explicit integrators in **low-storage 2S/3S\* form** (Ketcheson 2010), so only two or three state registers are needed. The integrator is encoded as task-list stages with weights.
  - **Integrators:** VL2 (the default; a predictor–corrector with a forced first-order predictor, stable to CFL ≈ 0.5 in 2D and 3D), RK1 for testing, SSP RK2 and RK3, RK4 and SSPRK(5,4). S20 recommends VL2 or RK2 with PLM or PPM, and RK3 with PPM. CTU, the C version's integrator, was dropped as too complex for relativistic MHD.
  - **Sources:** explicit source terms (gravity, geometric terms, user sources) are added inside the stages.
  - **Diffusion:** viscosity, conduction and resistivity are added unsplit inside the stages, *or* advanced operator-split by **super-time-stepping** (RKL1 or RKL2) in their own task list. With RKL2 the super step is Strang-split: one before and one after the main step.
  - **Time step:** a global minimum over blocks of the hyperbolic, parabolic and user limits, shared by all refinement levels (S20 argues against subcycling).
- **ZEUS** splits every step into a *source* step (pressure, gravity, curvature, viscosity, compression, Lorentz forces, radiation coupling) and a *transport* step, each a sequence of operator-split substeps.
- **Ulula** applies half of its source terms before and half after the hydrodynamic sweeps (Strang splitting). It can restart a step with a smaller time step when the CFL condition is violated during the step.
- **Pyro** uses CTU or the method of lines with Runge–Kutta, adding source terms in its own way per solver.

## 2. Evidence

All three experiments are small one-dimensional (and, for stability, two-dimensional) NumPy models. They compare integration methods, which do not depend on the compiled kernels. They ran natively.

### E11.1 — Integrators for the hyperbolic part

**Method.** [`experiments/E11.1b-integrators.py`](experiments/E11.1b-integrators.py) advances the minimal 1D solver of D02 ([`E11.1a-hydro1d.py`](experiments/E11.1a-hydro1d.py): PLM with the MC limiter on primitives, HLL) with three integrators:

- **SSP-RK2** (two evaluations per step);
- **SSP-RK3** (three);
- **VL2** (a half step with first-order fluxes, then a full step with PLM fluxes at the half-step state; two evaluations).

It measures:

- **Convergence:** of a linear sound wave.
- **Largest stable CFL number, in 1D:** on the linear wave over four periods and on the Sod shock tube. Stable means finite, positive pressure, no growth of the wave error beyond 50 times its value at CFL 0.1, and Sod's total variation within 5 % of the exact solution's.
- **Largest stable CFL number, in 2D:** on the smooth periodic flow of D04, using D04's NumPy solver ([`E11.1c-hydro2d.py`](experiments/E11.1c-hydro2d.py)), 64² cells, against a reference run.
- **Cost:** the evaluations per unit of simulated time at the 2D limit.

Unstable runs blow up to infinity; stable ones stay within the stated bounds. Full output: [`results/E11.1b-integrators.md`](experiments/results/E11.1b-integrators.md).

**Results.**

| Integrator | Wave error N = 512 (order) | Largest stable CFL, 1D | Largest stable CFL, 2D | Evaluations per unit of CFL time, 2D | Sod L1 error, CFL 0.4 |
|---|---|---|---|---|---|
| SSP-RK2 | 1.3 × 10⁻¹⁰ (1.96) | 1.00 | 0.65 | 3.1 | 2.19 × 10⁻³ |
| SSP-RK3 | 1.0 × 10⁻¹⁰ (1.97) | 1.25 | 0.80 | 3.75 | 2.14 × 10⁻³ |
| VL2 | 1.4 × 10⁻¹¹ (2.32) | 1.00 | 0.65 | 3.1 | 1.87 × 10⁻³ |

- **All three converge at second order,** as the spatial scheme limits them to.
- **In 2D the stable CFL number drops to 0.65 for SSP-RK2 and VL2 and 0.8 for SSP-RK3,** compared with 1–1.25 in 1D. Athena++ quotes about 0.5 for VL2 in 2D and 3D. In 3D the limits drop further **[GK]**. A default CFL number must therefore depend on the dimensionality.
- **Per unit of simulated time, SSP-RK2 and VL2 are equally cheap,** and SSP-RK3 costs 20 % more. Its third evaluation buys only part of its larger stable step.
- **VL2 had the smallest errors** on the linear wave (7× smaller than SSP-RK2 at N = 512) and on Sod. In the 2D smooth flow it differed most from the SSP-RK3 reference (about 10⁻⁴ against 10⁻⁶), so its accuracy depends on the problem.

### E11.3 — Explicit substeps or super-time-stepping for diffusion

**Method.** An explicit diffusion step is limited to dt_par = dx² / 2κ (1D), which in the thesis's hot corona can lie far below the hydrodynamic step. [`experiments/E11.3-super-time-stepping.py`](experiments/E11.3-super-time-stepping.py) advances the diffusion equation (κ = 1, N = 256, two Fourier modes, to t = 0.05) with steps of R × dt_par, for R = 1, 10, 100 and 1000. Each step is covered in one of three ways:

- **explicit substeps** at dt_par;
- **one RKL1 super step** (Runge–Kutta–Legendre, Meyer, Balsara & Aslam 2014, first order);
- **one RKL2 super step** (second order).

In both RKL variants the number of stages s is the smallest that is stable. The experiment counts evaluations of the diffusion operator. Each evaluation is also one exchange of ghost cells between blocks (D08), so the count measures communication as well as computation. Full output: [`results/E11.3-super-time-stepping.md`](experiments/results/E11.3-super-time-stepping.md).

**Results.**

| R = dt_hyp / dt_par | Explicit: evaluations (error) | RKL1: stages, evaluations (error) | RKL2: stages, evaluations (error) |
|---|---|---|---|
| 1 | 6554 (8.8 × 10⁻⁶) | 1, 6554 (8.8 × 10⁻⁶) | 3, 19 662 (4.4 × 10⁻⁶) |
| 10 | 6554 (8.8 × 10⁻⁶) | 4, 2623 (6.8 × 10⁻⁵) | 6, 3934 (4.4 × 10⁻⁶) |
| 100 | 6554 (8.8 × 10⁻⁶) | 14, 920 (6.6 × 10⁻⁴) | 20, 1315 (8.9 × 10⁻⁶) |
| 1000 | 6554 (8.8 × 10⁻⁶) | 45, 303 (6.7 × 10⁻³) | 63, 425 (5.2 × 10⁻⁴) |

- **Super-time-stepping saves work in proportion to √R:** at R = 1000, RKL2 needs 425 evaluations where explicit substeps need 6554, 15 times fewer, and as many fewer ghost exchanges.
- **RKL2 keeps the explicit accuracy up to R ≈ 100** and loses it beyond: at R = 1000 the step is longer than the decay time of the resolved modes. RKL1 is only first order and loses accuracy already at R = 10.
- **For R ≲ 3, explicit substeps are cheaper:** RKL2 needs at least three stages.

### E11.2 — Coupling a stiff source term

**Method.** In dense gas, the cooling time can be orders of magnitude below the hydrodynamic step. [`experiments/E11.2-stiff-sources.py`](experiments/E11.2-stiff-sources.py) uses a model with the same structure and a computable exact solution: advection with relaxation towards an equilibrium, where both the rate and the equilibrium vary in space.

    q_t + q_x = −k(x) (q − q_eq(x)),   k = k0 (1 + 0.9 sin 2πx),   q_eq = 1 + 0.5 cos 2πx

The flow keeps carrying gas from one equilibrium to another. The variation in space makes advection and source non-commuting, so splitting errors are real. The exact solution is integrated along the characteristics; doubling its step changes it by at most 6 × 10⁻⁸. Advection uses PLM (MC) with SSP-RK2 at CFL 0.4. The stiffness k0 ranges over 1, 10² and 10⁴. The couplings compared:

- **unsplit:** the source added inside the Runge–Kutta stages, at the hydrodynamic step, or with the step also limited to k·dt ≤ 1;
- **Lie splitting:** advection, then the source over the whole step, integrated exactly per cell;
- **Strang splitting:** half a source step, advection, half a source step, with the source integrated exactly, or by subcycled explicit substeps as a cooling function without an exact integral would need;
- **IMEX:** the implicit-explicit Runge–Kutta scheme IMEX-SSP2(2,2,2) (Pareschi & Russo 2005), with advection explicit and the source implicit per cell inside the stages, at the hydrodynamic step.

Full output: [`results/E11.2-stiff-sources.md`](experiments/results/E11.2-stiff-sources.md).

**Results.** L1 error at N = 1024 (order between N = 512 and 1024), and evaluations of advection per cell:

| Coupling | k0 = 1 | k0 = 10² | k0 = 10⁴ | Advection evaluations (k0 = 10⁴) |
|---|---|---|---|---|
| Unsplit, hydrodynamic step | 1.7 × 10⁻⁵ (2.0) | 5.8 × 10⁻⁷ (2.0) | blows up | — |
| Unsplit, step limited to k·dt ≤ 1 | 1.7 × 10⁻⁵ (2.0) | 5.8 × 10⁻⁷ (2.0) | **5.0 × 10⁻⁷ (2.0)** | 19 000 |
| Lie splitting, exact source | 1.2 × 10⁻⁴ (1.1) | 3.9 × 10⁻⁴ (1.0) | 2.2 × 10⁻⁴ (0.6) | 2 562 |
| Strang splitting, exact source | 1.7 × 10⁻⁵ (2.0) | 1.5 × 10⁻⁶ (2.0) | 6.1 × 10⁻⁵ (0.9) | 2 562 |
| Strang splitting, subcycled source | 1.7 × 10⁻⁵ (2.0) | 4.9 × 10⁻⁷ (2.1) | 5.9 × 10⁻⁵ (0.9) | 2 562 (plus 40 964 cheap source evaluations) |
| IMEX-SSP2(2,2,2) | 1.7 × 10⁻⁵ (2.0) | 1.9 × 10⁻⁶ (2.0) | 1.2 × 10⁻⁴ (1.6) | 2 562 |

- **Adding a stiff source inside the stages at the hydrodynamic step is unstable,** and limiting the step to the source's time scale is accurate but costs 7.4 times as many hydrodynamic evaluations here. In the thesis problem, with cooling times far below the flow's, that factor would be far larger.
- **Lie splitting is first order** and the least accurate in every case.
- **Strang splitting keeps second order while the source is moderately stiff (k0 = 10²) and loses it when the source is very stiff (k0 = 10⁴), falling to order 0.9.** This is the known *order reduction* of splitting with stiff sources **[GK]**. The error remains small, 6 × 10⁻⁵ against an equilibrium that varies by 0.5. The solution sits close to its local equilibrium, and the error is in how closely it tracks that equilibrium.
- **Subcycling the source instead of integrating it exactly gives the same accuracy.** It costs many more source evaluations, but those are cheap pointwise operations, and their uneven cost per block is what D09.3's dynamic assignment absorbs.
- **IMEX was not better here:** less accurate than Strang at k0 = 10⁴ on these grids, though of higher order (1.6). It would also need a local implicit solve per cell for a nonlinear cooling function.

**What the three experiments mean together.**

- **Hyperbolic integrators:** the three candidates cost about the same per unit of simulated time. The stable CFL number is set by the dimensionality more than by the integrator.
- **Stiff sources:** they belong outside the Runge–Kutta stages, Strang-split around them and integrated per cell. That is accurate where the source is moderately stiff and acceptably accurate, with reduced order, where it is very stiff. Full second order in the very stiff limit is available only by resolving the source in time, at a cost that grows with the stiffness.
- **Diffusion:** super-time-stepping with RKL2 reduces the work and the ghost exchanges of conduction by a factor that grows as √R, at explicit accuracy up to R ≈ 100.

## 3. Decisions

### D11.1 — The integrator for the hyperbolic part

Which explicit integrators advance the method of lines, and which is the default?

**Options**

- **A. SSP-RK2 only.** Second order, two evaluations per step, stable to CFL 0.65 in 2D (E11.1). The simplest set.
- **B. The Athena++ set from the start:** VL2, SSP-RK2 and SSP-RK3, with RK1 for tests and RK4 and SSPRK(5,4) later. The default follows the reconstruction (D10.5): VL2 with PLM, SSP-RK3 with PPM, as S20 recommends.
- **C. Integrators with error control** (embedded Runge–Kutta pairs). Not the practice in finite-volume astrophysics codes, where the CFL condition, not the time error, sets the step.

**Recommendation.** B. The three cost about the same per unit of simulated time (E11.1), and the pairing with the reconstruction is what the reference codes recommend. VL2 was the most accurate on waves and shocks with PLM, and SSP-RK3 is the natural partner of PPM, which D10.5 brings in from the start. They share one implementation as data (D11.2), so the set costs little more than one integrator. This serves **correctness** and **performance**.

**Decision.** *(2026-10-12)* **B, the Athena++ set from the start:** VL2, SSP-RK2 and SSP-RK3, with RK1 for tests. Higher-order methods are of explicit interest, beyond the second-order core. That means RK4 and SSPRK(5,4) as in Athena++, and further integrators such as Ketcheson's ten-stage fourth-order SSP method **[GK]**. Together with D03's provisions for higher-order spatial schemes, they make tests of higher-order accuracy possible. Because integrators are data (D11.2), each is a table to add rather than a code path to write.

### D11.2 — Integrators as data

How are integrators implemented?

**Options**

- **A. As data:** each integrator is a table of stages. Each stage carries:
  - its weights for combining the registers, in the low-storage 2S/3S\* form of Ketcheson (2010) that Athena++ uses;
  - its time fraction;
  - its properties, for example "first-order reconstruction" for VL2's predictor.

  One compiled, ranged kernel combines registers with weights (E04.5, D09.2). The integrator contributes its stages as phases (D09.1). Adding an integrator means adding a table.
- **B. One code path per integrator.** Clear for one or two integrators, but every integrator repeats the stage structure, and every phase that depends on the stage must be written for each.

**Recommendation.** A. It is how Athena++ encodes its integrators, it uses two or three registers, and it fits D09's phases-as-data directly. FOFC (D10.6) and the stiff-source splitting (D11.3) become steps placed around the stages, not edits to each integrator. This serves **extensibility** and **readability**.

**Decision.** *(2026-10-12)* **A, integrators as data**, following the recommendation. This is the same pattern used elsewhere in mhdpy:
- **D09.1:** a step is a sequence of phases described as data and registered, not assembled by hand-written conditionals.
- **D08.1:** an exchange plan is a table of regions that one compiled kernel executes.

Here an integrator is a table of stages and weights that one compiled stage kernel executes.

### D11.3 — Coupling source terms

How are source terms coupled to the hyperbolic update?

**Options**

- **A. All sources inside the stages.** Simplest and second order. But stiff sources make it unstable at the hydrodynamic step or force the step down to the source's time scale, which in E11.2 cost 7.4× and in cooling-dominated runs would cost far more.
- **B. By stiffness, declared per source:**
  - **Non-stiff sources** (gravity, geometric terms of curvilinear coordinates, user sources) are added inside the stages, as Athena++ does.
  - **Stiff sources** (radiative cooling and heating, later chemistry) are Strang-split around the hyperbolic step: half before, half after. They are integrated per cell, exactly where an exact integral exists **[GK]** (for example Townsend's 2009 exact integration of piecewise power-law cooling), otherwise by an adaptive local ODE integration.

  A user who needs full second order where the source is very stiff can additionally limit the step to a fraction of the source's time scale (D11.5).
- **C. IMEX Runge–Kutta for stiff sources,** implicit per cell inside the stages. Not more accurate than Strang splitting in E11.2 at the stiffness of interest, and it needs a local implicit (Newton) solve for nonlinear cooling.

**Recommendation.** B. Strang splitting with per-cell integration keeps the hydrodynamic step whatever the cooling time, is second order where the source is moderately stiff, and keeps the error small where it is very stiff (E11.2). The per-cell integration's uneven cost is absorbed by dynamic assignment (D09.3). The stiffness of a source is declared by the module that provides it (D12), so the framework places it correctly. IMEX remains an option for later sources that are both stiff and strongly coupled to the flow. This serves **correctness** within the **performance** targets.

**Decision.** *(2026-10-12)* **B, sources coupled by declared stiffness**, following the recommendation. Athena++'s approach (non-stiff sources inside the stages) is the model, from a code known to be robust and performant. Stiff sources such as cooling are Strang-split and integrated per cell.

### D11.4 — Diffusion terms

How are diffusive terms, such as thermal conduction, advanced?

**Options**

- **A. Explicitly inside the stages,** with the step limited to the diffusive limit (∝ dx²). Exact enough, but where conduction is fast (the hot corona) the step collapses: R explicit evaluations and ghost exchanges for every hydrodynamic step.
- **B. Super-time-stepping with RKL2, operator-split,** as Athena++: one super step of s ≈ 2√R stages per hydrodynamic step, Strang-split around it (half before, half after) **[GK]** as Athena++ does with RKL2. When R ≲ 3, explicit substeps inside the stages are cheaper and are used instead. RKL1 is available but first order.
- **C. Implicit diffusion** with a global linear solve (for example multigrid). Unconditionally stable, but every solve couples all blocks, which is the most expensive form of communication, and it is a large component of its own.

**Recommendation.** B. RKL2 cut the work and the ghost exchanges by 1.7× at R = 10, 5× at R = 100 and 15× at R = 1000, at explicit accuracy up to R ≈ 100 (E11.3). It is explicit and local, so it fits blocks, exchange plans and threads (D05–D09) without a global solver. C becomes worth it only for ratios beyond what RKL2 handles accurately, and can be added later as another component. The physics of conduction, Spitzer, saturated, and later anisotropic along the field, belongs to the module (D12). This serves **performance**.

**Decision.** *(2026-10-12)* **B, super-time-stepping with RKL2, operator-split,** as Athena++ does, with explicit substeps when R ≲ 3.

### D11.5 — Controlling the time step

How is the time step chosen?

**Options**

- **A. A CFL step,** the global minimum over blocks (D09) of CFL · dx / (|u| + c_f) per direction, computed at the end of each step for the next, as Athena++.
- **B. A, plus limits from other physics and from the user, plus safeguards:**
  - **Diffusion:** a parabolic limit when diffusion is explicit (D11.4).
  - **Stiff sources:** an optional limit to a fraction of their time scale (D11.3).
  - **User limits.**
  - **Growth:** a bounded growth of the step from one step to the next **[GK]**.
  - **Output times:** the step is shortened to hit output times exactly (D13).
  - **CFL default:** the default CFL number depends on the dimensionality and integrator, with a margin below the measured limits: 0.65 for SSP-RK2 and VL2 and 0.8 for SSP-RK3 in 2D (E11.1), lower in 3D.
- **C. B, plus step rejection:** a step that produces invalid states is undone and repeated with a smaller step, as Ulula does. That needs a backup of the state every step (one more register and a copy).

**Recommendation.** B. The limits are what the physics of the thesis problem requires. Rejection (C) is left out by default, because floors and first-order flux correction (D10.6) already repair invalid cells conservatively without repeating a step. It can be added as an option if a problem needs it. This serves **correctness** and **ease of use** (safe defaults).

**Decision.** *(2026-10-12)* **B, the CFL step with limits and safeguards.** Step rejection (C) was the first preference. With floors and first-order flux correction already repairing invalid cells (D10.6), it would be largely redundant for now. It remains a possible later addition, for problems where repeating a step is more useful than repairing cells.

### D11.6 — Time steps across refinement levels

Do all refinement levels advance with the same time step?

**Options**

- **A. One time step for all levels,** as Athena++. S20 argues the case:
  - in MHD the smallest step is often set on the coarse levels, where the Alfvén speed is high;
  - interpolating in time adds error, especially with self-gravity;
  - subcycling complicates optimisation and load balancing;
  - the savings are often modest.

  Consistent with the correction of fluxes and EMFs within the step (D08.6).
- **B. Subcycling:** finer levels take more, smaller steps. Saves work when the finest levels cover a small volume and set the step, but needs time interpolation of ghost zones, refluxing after the fact (which would supersede D08.6), and more complex scheduling.

**Recommendation.** A. It is consistent with D08.6, and S20's arguments apply to mhdpy's targets, including MHD. The thesis problem in its reference form is a uniform grid, where the question does not arise. Subcycling can be revisited with measurements once refinement exists; it would supersede D08.6 and this sub-decision together. This serves **correctness** and **readability**.

**Decision.** *(2026-10-12)* **A, one time step for all levels.** Subcycling looked more efficient at first, but the additional complexity it brings is not worth it, in line with S20's arguments.

## 4. Consequences for higher layers

**For every layer**

- **Integrators as data:** an integrator is a table of stages with weights in low-storage form, plus per-stage properties (time fraction, reconstruction order for VL2's predictor). One compiled, ranged kernel combines the registers. The integrator registers its stages as phases (D09.1), and the number of registers it needs (two or three) is declared through the registry (D06.6) (D11.2).
- **First set and defaults:** VL2, SSP-RK2 and SSP-RK3, with RK1 for tests. VL2 is the default with PLM, SSP-RK3 with PPM. RK4, SSPRK(5,4) and further higher-order integrators follow as tables (D11.1).
- **A step, in order:**
  1. half a step of the stiff sources (Strang);
  2. half a super step of diffusion (RKL2) when it is operator-split;
  3. the integrator's stages, each with exchange, boundary conditions, primitives, fluxes with the non-stiff sources, update and first-order flux correction;
  4. the second half super step of diffusion;
  5. the second half step of the stiff sources;
  6. the new time step.

  The exact placement of the diffusion halves follows Athena++. All of these are phases (D09.1).
- **Time step:** the minimum over blocks of the CFL limit, the parabolic limit when diffusion is explicit, the optional stiff-source limit and user limits. Its growth between steps is bounded, and it is shortened to hit output times. The default CFL number depends on the dimensionality and the integrator, below the limits measured in E11.1 (D11.5).
- **Refinement levels:** all of them advance with the same time step (D11.6), so D08.6's correction of fluxes and EMFs within the step stands.

**For brief D12 (physics module interface)**

- **Sources:** a module declares each of its source terms as non-stiff (added inside the stages) or stiff (Strang-split, integrated per cell). For stiff sources it provides the per-cell integrator: exact where an exact integral exists, adaptive otherwise. The uneven cost per block is absorbed by dynamic assignment (D09.3) (D11.3).
- **Diffusion:** a module providing a diffusive term (conduction, viscosity, resistivity) provides its flux and its parabolic time-step limit. The framework decides between super-time-stepping and explicit substeps (D11.4).
- **Conduction:** the physics of thermal conduction is the module's. That covers Spitzer conductivity, saturation, and later anisotropic conduction along the field, which needs limiters that keep temperatures monotonic **[GK]**.

**For brief D13 (driver)**

- The driver runs the step in the order above, chooses the step by D11.5, shortens it for outputs, and records the limiting constraint, for diagnostics.

**For the verification of D02**

- **Convergence:** every integrator's order is verified on smooth problems, with limiters off. Its stable CFL number is checked against the defaults.
- **Stiff sources:** they are tested on problems with exact solutions in both regimes, as in E11.2. The reduced order of Strang splitting in the very stiff limit is a documented property, not a test failure.
- **Super-time-stepping:** it is verified against explicit substeps and analytic diffusion solutions, as in E11.3.

**Noted for later**

- **Step rejection** (D11.5 C), for problems where repeating a step is more useful than repairing cells.
- **IMEX Runge–Kutta** (D11.3 C), for sources that are both stiff and strongly coupled to the flow.
- **Implicit diffusion with a global solver** (D11.4 C), for ratios beyond RKL2's accurate range.
- **Subcycling of refinement levels** (D11.6 B), only with measurements and together with superseding D08.6.
