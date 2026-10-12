# D12 — Physics module interface

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-12 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how physics enters mhdpy. Hydrodynamics, MHD, passive scalars, radiative cooling, thermal conduction and (self-)gravity are all *modules*. The brief decides:

- what a module is;
- how modules couple to each other;
- which extension points the framework offers;
- in which form module code may be written;
- how physical units reach modules.

The extensibility criterion of architecture.md §1.3 is tested here: a new physics module, such as an alternative cooling function or a new Riemann solver, must plug in without changes to the framework, and every module beyond the hydrodynamic core is a test of that.

The earlier briefs have already decided much of what a module does; this brief gathers it into one contract:

- **D03.** Passive scalars are native, with fluxes tied to the mass flux. Dual energy is optional. Constrained transport keeps the magnetic field on faces.
- **D06.** A module does not own arrays. It registers its variables with metadata and receives index ranges in shared arrays per centring and role; the registry is frozen before allocation. Primitive variables are stored, computed once per stage.
- **D08.** A module declares how its variables behave at boundaries (parity, overrides) and under refinement (operators). User boundary conditions fill boundary blocks.
- **D09.** A step is a sequence of phases, named operations with declared reads and writes, registered by the integrator and the modules. Kernels are called for ranges of blocks; the Python per phase must not grow with the number of blocks.
- **D10.** A module's kernels follow fixed rules. Their component choices are fused types, compiled per combination, never function pointers or Python in inner loops. The equation of state and the Riemann solvers have fixed interfaces.
- **D11.** Sources declare their stiffness: non-stiff sources go inside the stages, stiff ones are Strang-split and integrated per cell by the module. Diffusive modules provide a flux and a parabolic time-step limit, and the framework chooses between super-time-stepping and explicit substeps.

**What the references do** (syntheses in `References/`):

- **Athena++** attaches *physics objects* to every MeshBlock: `Hydro`, `Field`, `PassiveScalars`, `Gravity` and so on, each owning its arrays (conserved and primitive variables, registers, face fluxes) and its own boundary-variable objects. The task list wires them together. Passive-scalar fluxes are computed after the hydrodynamic fluxes, from the stored mass flux. Users extend the code by *enrolling* functions in the problem generator:
  - boundary conditions;
  - source terms;
  - time-step limits;
  - refinement conditions;
  - mesh generators;
  - history outputs;
  - diffusion coefficients.

  Kernels are selected at compile time.
- **ZEUS** grows its physics by operator splitting: every process is a separate, ordered substep, and a new module is inserted at a defined point or replaces a substep. Its synthesis singles out the papers' explicit *integration contract*, which states exactly which substeps a module adds, modifies or replaces, as worth reproducing. ZEUS's consistent transport, with fluxes of other quantities derived from the mass flux, is the same idea as Athena++'s passive scalars.
- **Pyro** has no physics-module abstraction. Each solver is a self-contained package with its own variables, conversions and Riemann solvers, reused through deep inheritance. Its synthesis notes that adding MHD would mean writing another parallel package. Problems are plain modules with a fixed contract (parameters, initial data, finalisation, optional source terms).
- **Ulula** is a single class with branches. It keeps the solver unit-free, with code units attached only for plots and conversions.

## 2. Evidence

### E12.1 — A module's own passes against a fused kernel

**Method.** Passive scalars are the simplest module that couples to the hydrodynamics: the flux of a scalar is the mass flux times the upwind concentration (D03.6). [`experiments/E12.1a-kernels.py`](experiments/E12.1a-kernels.py) adds them to the hydrodynamic kernel of D10 in two ways:

- **fused:** one kernel for all variables. One primitive loop, scalar fluxes computed at each face right after the hydrodynamic flux, one divergence loop.
- **separate passes:** the hydrodynamic kernel's own passes for its five variables, writing the mass flux into the shared flux array. Then the scalar module's own passes: concentrations, fluxes from the stored mass flux, divergence. This is how a module that knows nothing of the hydrodynamic kernel would add them.

[`E12.1b-modularity.py`](experiments/E12.1b-modularity.py) times both natively on one thread, for 2D blocks of 64² and 512² with 0, 1 and 4 scalars. The repetitions are interleaved, as learned in E10. Both forms gave bit-for-bit identical results. Full output: [`results/E12.1b-modularity.md`](experiments/results/E12.1b-modularity.md).

**Results.** Million cells per second for one evaluation of the time derivative:

| Block | Scalars | Fused | Separate passes | Time of separate / fused |
|---|---|---|---|---|
| 64² | 0 | 11.1 | 18.6 | 0.60 |
| 64² | 1 | 9.6 | 14.5 | 0.66 |
| 64² | 4 | 7.1 | 9.8 | 0.72 |
| 512² | 0 | 8.9 | 13.8 | 0.64 |
| 512² | 1 | 7.6 | 10.9 | 0.69 |
| 512² | 4 | 5.0 | 6.8 | 0.73 |

- **The module's separate passes took 27–40 % less time than the fused kernel.** The fused kernel was slower even with no scalars at all: the mere presence of the scalar loop inside the face loop made the compiler generate worse code for the hydrodynamic part. Tight loops that do one kind of work optimise better than loops that mix kinds of work.
- **Re-reading the arrays in separate passes cost less than it saved,** also for 512² blocks, which do not fit in the cache.
- **This does not prove that no fusion can be faster.** A fusion written with as much care as the separate passes might gain something. But it shows that the modular structure has no inherent cost, and that fusing is not automatically an optimisation.
- **Each scalar adds roughly 20–30 % to the time of the hydrodynamic update:** its own conversion, reconstruction, flux and divergence. With one metallicity scalar, as in the thesis problem, that is a moderate cost.

### E12.2 — User source terms in NumPy or compiled

**Method.** Users and module authors without a C compiler would write simple source terms in NumPy. [`experiments/E12.2b-user-sources.py`](experiments/E12.2b-user-sources.py) applies a constant gravitational acceleration (E += dt g m_y, then m_y += dt g ρ) to the state of the thesis grid (1600 blocks of 50²) in three forms:

- **compiled:** [`E12.2a-source-kernel.py`](experiments/E12.2a-source-kernel.py), one call per range of blocks;
- **NumPy, per range:** two NumPy statements over the whole range of blocks;
- **NumPy, per block:** the same statements in a Python loop over the blocks.

Each is run by a thread pool (D09) with 1 and 6 workers, natively, with both interpreters. All forms gave bit-for-bit identical results. Full output: [`results/E12.2b-user-sources.md`](experiments/results/E12.2b-user-sources.md).

**Results.** Million cells per second for the source term alone:

| Interpreter | Workers | Compiled | NumPy, per range | NumPy, per block |
|---|---|---|---|---|
| Free-threaded | 1 | 530 | 114 | 86 |
| Free-threaded | 6 | 622 | 221 | 310 |
| With GIL | 1 | 551 | 118 | 94 |
| With GIL | 6 | 611 | **181** | **54** |

- **A simple source term costs little in any form, compared with the hydrodynamics,** which runs at about 6–7 million cells per second per core. Compiled, it costs about 1 % of a hydrodynamic evaluation; in NumPy over ranges, about 3–5 %. Simple sources are limited by memory bandwidth, which is why even the compiled form gains little from more workers.
- **NumPy over whole ranges of blocks scales under both interpreters,** because NumPy releases the GIL inside its array operations.
- **A Python loop over blocks collapses under the GIL:** with 6 workers it is slower than with one (54 against 94). This is the same lesson as E09.1, now for user code: Python must not run per block.
- **These numbers hold for cheap sources only.** A source that does real work per cell, such as cooling with substeps, would be as slow in NumPy, relative to compiled code, as the hydrodynamic kernels were in E04.1 (4–8×). Such sources must be compiled.

**What the two experiments mean together.**

- **No speed penalty for modularity:** modules can be written as their own compiled passes over the arrays without losing speed. Coupling between modules does not need fused kernels.
- **Cheap module code may be NumPy,** as long as it runs over ranges of blocks; anything per face or per substep must be compiled.

## 3. Decisions

### D12.1 — What a module is

What form does a physics module take?

**Options**

- **A. Physics objects per block,** as Athena++: every block holds a `Hydro`, a `PassiveScalars` and so on, owning their arrays and methods. This conflicts with D06 (the state, not the block, owns storage) and D09 (no Python per block).
- **B. A declaration made once at set-up.** A module is a Python object that, when a simulation is set up, *declares* what it contributes:
  - its variables, with metadata (D06.6);
  - its phases, with the arrays they read and write and their kind (D12.3);
  - its time-step limits;
  - its boundary behaviour and refinement operators (D08);
  - its parameters.

  It does not run anything per block. The work is done by its kernels, called by the framework for ranges of blocks (D09). The set of declarations is the module's *integration contract*, in the sense ZEUS's papers spell out, and it can be printed and checked.
- **C. Self-contained solver packages,** as Pyro: each equation system with its own variables, conversions and Riemann solvers. Easy to start, but adding physics means copying a solver. Pyro's synthesis names that as its main limitation.

**Recommendation.** B. It is the shape the earlier decisions already imply, gathered into one contract: the registry of D06, the phases of D09, the stiffness of D11. It keeps all per-block work in compiled kernels, and it makes the contract explicit, as ZEUS's experience recommends. Extensibility then has a concrete test: a new module is a new declaration and new kernels, with no change to the framework. This serves **extensibility** and **readability**.

**Decision.** *(2026-10-12)* **B, a module is a declaration made once at set-up**, following the recommendation, as the natural continuation of the decisions so far.

### D12.2 — How modules couple

How does one module use another's results, such as passive scalars using the hydrodynamic mass flux, or conduction adding to the energy flux?

**Options**

- **A. Independent phases over all blocks, coupling through stored arrays.** Each module's passes are separate phases over all blocks. Anything one module needs from another, such as the face fluxes, is stored for all blocks between phases. Simple, but the face fluxes of all blocks (two to three times the state, D06.5) must then be kept, where D05 keeps them as per-worker scratch.
- **B. Extension points within a block.** An *equation system* (hydrodynamics, MHD) runs its ranged kernel, and for each block calls the passes of the modules attached to it, back to back, on that block's scratch arrays. For example: hydrodynamic fluxes, then the scalar fluxes from the mass flux still in scratch, then conduction fluxes added to the energy flux, then one divergence. The attached passes are compiled functions with a fixed signature, called through a C function pointer *once per block*, not per face, where E10.1's cost does not arise. Modules that need no fluxes (sources, cooling) are phases of their own, as in A.
- **C. Fused kernels per combination,** compiled for each combination of modules. Fastest only if written with care (E12.1 found a naive fusion slower), and it couples modules at the source level, against the extensibility criterion.

**Recommendation.** B. E12.1 shows that separate passes per module cost nothing: they were faster than the fused form. B keeps those passes per block, so the face fluxes they share stay in each worker's scratch (D05) instead of being stored for the whole grid. One indirect call per block and module is negligible next to the kernel itself. It is also the structure flux and EMF correction (D08.6) and first-order flux correction (D10.6) need, since both work on a block's face fluxes. This serves **performance** and **extensibility**.

**Decision.** *(2026-10-12)* **B, extension points within a block**, as the most logical choice given the evidence of E12.1.

### D12.3 — The extension points

Which kinds of contribution does the framework offer modules?

**Options**

- **A. A fixed set of named extension points, each with its place in the step (D11) and its contract:**
  - **equation systems:** variables, conversions, Riemann solvers, the CFL limit;
  - **flux contributions** attached to an equation system: advected quantities such as passive scalars and dual energy, explicit diffusive fluxes;
  - **diffusion** for super-time-stepping (flux and parabolic limit, D11.4);
  - **non-stiff sources** inside the stages;
  - **stiff sources** with their per-cell integrator (D11.3);
  - **global solvers,** such as self-gravity, which need communication across all blocks (a Poisson solve) and run as phases of their own between stages, as in Athena++;
  - **boundary conditions** (D08.4);
  - **refinement criteria;**
  - **diagnostics and history quantities.**

  This is in effect Athena++'s enrolment list, made uniform for internal and user modules.
- **B. Generic phases only:** modules insert arbitrary phases at arbitrary places. Maximally flexible, but the framework can no longer check a module's contract or place it correctly in the step.
- **C. A, with generic phases as an escape hatch** for modules that fit no named point, at a declared place in the step.

**Recommendation.** C. The named extension points cover every module on mhdpy's roadmap and let the framework place, order and check them (D09.1). The escape hatch keeps research modules possible without changing the framework, which is what extensibility means. User contributions, such as a problem's own source term or boundary condition, use the same extension points as built-in modules: a user module is a module. This serves **extensibility** and **correctness** (contracts that can be checked).

**Decision.** *(2026-10-12)* **C, named extension points with generic phases as an escape hatch**, following the recommendation and its reasoning.

### D12.4 — In which form module code is written

Must a module's kernels be compiled, or may they be NumPy?

**Options**

- **A. Compiled only:** every module's kernels are Cython in pure Python mode (D04). Modules outside mhdpy are packages of their own, built with meson-python against mhdpy's published declarations (`.pxd` files).
- **B. Compiled where it matters, NumPy where it does not.** Kernels that work per face or per substep (fluxes, Riemann solvers, reconstruction, stiff sources, diffusion) are compiled. Extension points that work per cell without much arithmetic (simple sources, boundary conditions, initial conditions, diagnostics, refinement criteria) also accept NumPy functions. Those functions receive a range of blocks, never a single block (E12.2), and run on any interpreter.
- **C. Compilation at run time** of user Cython code on first use. Convenient for authors, but it requires a C compiler on every user's machine, against the installation exception.

**Recommendation.** B. E12.2 shows that a simple source in NumPy over ranges of blocks costs a few per cent of a step and scales on both interpreters, so requiring a compiler for it would only make mhdpy harder to extend. Per face or per substep, NumPy would be several times slower (E04.1). The rule "functions receive ranges, never single blocks" keeps Python out of the per-block loop. External compiled modules (A) remain possible for authors who need speed. This serves **ease of use** and **extensibility**, without giving up **performance** where it counts.

**Decision.** *(2026-10-12)* **B, compiled where it matters, NumPy over ranges of blocks where it does not.** Ease of use and extensibility weigh more here than the small gain that compiling cheap module code would bring (E12.2). Kernels that work per face or per substep are compiled in any case. Should NumPy module code become a bottleneck in practice, compilation at run time (C) can be reconsidered then.

### D12.5 — Physical units

How do modules that depend on physical constants, such as cooling functions in erg cm³ s⁻¹ or Spitzer conductivity, get them?

**Options**

- **A. Code units only,** as Athena++ and Ulula do: the solver is unit-free, and every module and user converts constants by hand.
- **B. A unit system set up with the simulation:** the code units of length, mass and time (and temperature through the mean molecular weight) are defined once in cgs. Modules that use physical constants ask it for conversions; the equations stay dimensionless in code units. Outputs record the unit system (D14).
- **C. Physical units throughout,** all variables in cgs. Simple to read, but astrophysical magnitudes span many orders, and every test problem in the literature is posed in code units.

**Recommendation.** B. The thesis physics depends on physical constants: a cooling function of temperature and metallicity, Spitzer conduction with saturation. Letting each module and user convert by hand invites exactly the unit errors that are hard to find. A single unit system, defined at set-up and recorded in the outputs, keeps the kernels dimensionless, as the test suites need, and the physics correct. This serves **correctness** and **ease of use**.

**Decision.** *(2026-10-12)* **B, a unit system set up with the simulation**, following the recommendation. The code itself stays dimensionless, in code units; the unit system provides the conversions, for ease of use.

## 4. Consequences for higher layers

**For every layer**

- **What a module is:** an object that, at set-up, declares what it contributes. Its integration contract consists of:
  - variables with metadata (D06.6);
  - phases or attached passes, with the arrays they read and write and their extension point;
  - time-step limits;
  - boundary behaviour and refinement operators (D08);
  - parameters.

  The framework places, orders and checks the contributions. Nothing in a module runs per block in Python (D12.1).
- **Equation systems:** hydrodynamics and MHD are equation systems. Their ranged kernel calls, for each block, the passes of the modules attached to it, on that block's scratch arrays, through C function pointers once per block. Passive scalars, dual energy and explicit diffusive fluxes attach this way. Flux registers for refinement (D08.6) and first-order flux correction (D10.6) work on the same per-block face fluxes (D12.2).
- **Extension points:**
  - equation system;
  - flux contribution;
  - diffusion for super-time-stepping;
  - non-stiff source;
  - stiff source with its per-cell integrator;
  - global solver;
  - boundary condition;
  - refinement criterion;
  - diagnostic.

  Generic phases at a declared place are the escape hatch. User contributions use the same points: a user module is a module (D12.3).
- **Compiled or NumPy:** kernels that work per face or per substep are compiled (Cython, pure Python mode, D04). Simple sources, boundary conditions, initial conditions, diagnostics and refinement criteria may be NumPy functions. Every NumPy function receives a range of blocks, never a single block (D12.4, E12.2).
- **Units:** the equations are solved in dimensionless code units. A unit system, defined once at set-up by the code units of length, mass and time in cgs (and the mean molecular weight for temperature), provides the conversions that modules with physical constants need (D12.5).

**For the documentation**

- The guide for writing modules describes the integration contract and every extension point, with its place in the step (D11) and its rules. Those rules are:
  - kernels follow D10.7;
  - component choices are fused types (D10.1);
  - NumPy functions take ranges;
  - variables are registered, not allocated (D06.4).

  It includes a worked example (passive scalars) and a user source term in NumPy. D06 §4 already asked for this guide.
- External compiled modules are packages built with meson-python against mhdpy's published `.pxd` declarations, a stable interface to document and version.

**For the verification of D02**

- Every module is tested against its contract: its declarations are complete and consistent (no phase reads an array no one writes), and its kernels follow D10.7 (equivalence uncompiled, symmetry).
- The extensibility criterion of architecture.md §1.3 becomes a test: modules beyond the hydrodynamic core (passive scalars, cooling, conduction, gravity) are added without any change to the framework. A change to the framework that a module needs is recorded as a finding.
- Unit conversions are tested against known physical values. The kernels' independence of the unit system is a test too: the same problem in two unit systems gives the same results in code units.

**For brief D13 (driver)**

- At set-up, the driver collects the modules' declarations, freezes the registry, assembles the phases (D09.1) and the per-block extension points (D12.2), and reports the resulting integration contract of the whole simulation.

**For brief D14 (I/O)**

- Outputs record the unit system and each module's declarations and parameters, so that a file is self-describing and a restart reconstructs the same simulation.

**For brief D15 (configuration)**

- Modules declare their parameters (types, defaults, validation); D15 decides how values are supplied (Python API, input files) and recorded. The problem set-up (initial conditions, its own sources and boundary conditions) is a user module under the same contract.

**Noted for later**

- Compilation of user code at run time (D12.4 C), should NumPy module code turn out to be a bottleneck.
