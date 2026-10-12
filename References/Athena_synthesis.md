# Athena / Athena++ — Synthesis

## Sources and conventions

As agreed, this is one document. It is centred on **Athena++**, the code in your folder, and covers the original C version of **Athena** as background and lineage.

**Sources used**

- Papers in `Athena/Docs/`:
  - Gardiner & Stone 2005, *Unsplit Godunov method for ideal MHD via CT* (2D). Referred to below as **GS05**.
  - Gardiner & Stone 2008, the same in 3D. Referred to as **GS08**.
  - Stone et al. 2008, *Athena: a new code for astrophysical MHD*. Referred to as **S08**.
  - Skinner & Ostriker 2010, *Athena in cylindrical geometry*.
  - Bai & Stone 2010, *Particle-gas dynamics with Athena*.
  - Stone & Gardiner 2010, *Shearing box in Athena*.
  - Beckwith & Stone 2011, *Second-order Godunov method for relativistic MHD*.
  - Stone, Tomida, White & Felker 2020, *The Athena++ AMR framework: design and MHD solvers*. Referred to as **S20**.
- Code: `Athena/Code/`. This is Athena++ **v24.0 (June 2024)**: about 130,000 lines of C++ in `src/`, plus `configure.py`, `inputs/`, `tst/` (regression tests) and `vis/python/`. The only in-repo `doc/` content is a Doxygen configuration file.
- Web, Athena (C) documentation site (princetonuniversity.github.io/Athena-Cversion) and the linked pages I followed:
  - Equations; Documentation index; Method Papers.
  - Programmer Guide (Mesh, Domains, Grids, Conserved/Primitive variables, Problem Generators, Code Structure).
  - User Guide (Configure, Integrators, Reconstruction, Boundary Conditions, SMR intro, Particle data structures).
  - Galilean invariance; the test-problem index.
- Web, Athena++ site (athena-astro.app): home, download and publications pages. Also the Athena++ GitHub wiki pages I followed: Home and sidebar, Code Structure, Configuring, The Input File, Problem Generators, Boundary Conditions, Coordinate Systems and Meshes, Outputs, Static and Adaptive Mesh Refinement, Using MPI and OpenMP, Super-Time-Stepping, Multigrid, Diffusion Processes, General EOS, Passive Scalars, Non-relativistic Radiation Transport, Regression Testing, High-Order Methods (the last is only a stub, "under construction").

**Markers used in this document**

- **[GK]** marks my general knowledge, not from your material.
- **[Assumption]** marks my interpretation where sources are not explicit.
- **[Code observation]** marks something read in the code but not verified by running.

**Gaps noticed in the material**

- The Athena documentation lists 8 method papers. Your folder has 7. The missing one is **Stone & Gardiner 2009** (New Astronomy 14, 139), which describes the **VL+CT (van Leer / MUSCL-Hancock) integrator**. That integrator is the default in Athena++ and is the one most relevant to a simpler implementation of your own. I describe it below only from what S08, S20, Beckwith & Stone and the docs say about it.
- The wiki's Code Structure page holds only diagrams, and it states they date from July 2017 and are out of date. The architecture below is therefore reconstructed mainly from S20 and the source code.

---

## 1. Purpose

**Athena is a research, production-grade code.** It is built for high-performance astrophysical (M)HD on very large parallel machines, in contrast to Pyro and Ulula, which are teaching codes.

- **Athena (C, 2008–2013, last version 4.2).** Its goal was a *conservative*, high-order Godunov MHD code that would work with static and adaptive mesh refinement. S08 is explicit about the motivation. Operator-split, non-conservative schemes like ZEUS are "unsuitable" for mesh refinement because conservation must be enforced at fine/coarse boundaries. Athena was meant to be accurate, easy to use, adaptable and maintainable, and to serve as a community code. A Fortran95 version also existed. Physics grew over time: isothermal or adiabatic gas, hydro or MHD, passive scalars, self-gravity, viscosity, conduction, resistivity (Ohmic, Hall, ambipolar), cooling, the shearing box and orbital advection, cylindrical coordinates, special relativity, Lagrangian dust particles, and SMR.
- **Athena++ (C++, 2014 onward; v24.0 in your folder).** This is a complete rewrite. S20 gives the reasons:
  - Adding physics to the C code had become "increasingly untenable". Physics was hard-coded in the main loop behind nested preprocessor flags.
  - Its patch-based AMR scaled poorly on modern machines.

  Athena++ is therefore designed as an **AMR framework that is independent of the physics solved on it**. Non-relativistic and relativistic (SR/GR) MHD are its flagship modules. Current extras in the code include general EOS, diffusion with super-time-stepping, the shearing box and orbital advection, FFT and multigrid self-gravity, explicit and implicit radiation transport, cosmic-ray transport, chemistry, and turbulence driving. Its targets are excellent single-core performance (vectorised kernels) and scaling to hundreds of thousands of threads; S20 reports 84% weak-scaling efficiency on about 500k threads.

**Lineage** (useful context for your Zeus synthesis): ZEUS (1992; operator-split finite differences) → Athena (2008; unsplit Godunov + CT, C) → Athena++ (2020; framework + task lists, C++). All three are led by J. Stone.

---

## 2. Architecture

### 2.1 Athena (C) in brief — the starting point

These are the C-version concepts that Athena++ reorganised.

- **Grid hierarchy: Mesh → Domains → Grids → cells.**
  - The *Mesh* is the whole calculation.
  - A *Domain* is a contiguous region at one refinement level. There is exactly one root Domain at level 0, and SMR adds nested Domains at higher levels, each refined by a factor of 2.
  - A *Grid* is the piece of a Domain updated by one processor (MPI domain decomposition: slab, pencil or block). Grids at different levels may overlap.
  - Each Grid holds a uniform, logically rectangular array of cells with ghost zones (4 by default).
- **Data layout.** An *array of structs*: each cell is a `ConsS` or `PrimS` struct holding density, momenta or velocities, energy or pressure, cell-centred B, and scalars. Separate face-centred field arrays hold the CT fields. 1D "pencil" structs (`Cons1DS`, `Prim1DS`) are used for reconstruction and Riemann solves, with components permuted by direction. The variable order is fixed and relied on by the eigensystem code and pointer arithmetic. The documentation warns it "cannot be changed".
- **Compile-time configuration.** An autoconf `configure` script selects the problem, gas (hydro or MHD), EOS, flux (Riemann solver), reconstruction order, integrator (CTU or VL), gravity, particles, coordinates, SR, diffusion processes, MPI, SMR, shearing box, FARGO, H-correction and first-order flux correction (FOFC). Runtime parameters are read from a block-structured input file.
- **Runtime dispatch** uses function pointers. `integrate_init()` picks the 1D, 2D or 3D integrator, boundary-condition functions are enrolled per face, and so on. The 1D, 2D and 3D integrators are *separate source files* with different internal structure, while reconstruction, Riemann solvers and eigensystems are shared.
- **Problem generator.** All problem-specific code lives in one file per problem, providing `problem()`, restart read/write, user output expressions, and `Userwork_in_loop` / `Userwork_after_loop`. It can enrol custom BCs, source terms and gravitational potentials.
- **SMR.** Refined regions are fixed in the input file. All levels share one timestep, with no subcycling. The documentation and S20 explain why: in MHD the smallest timestep is often set on the *coarse* level, where densities are low and the Alfvén speed is high.
- **MPI.** Ghost zones are exchanged direction by direction, x then y then z, which avoids separate diagonal messages. S20 later identified this sequential dependency as a scaling bottleneck.
- **Particles.** `GrainS` structs (position, velocity, property index) are stored per Grid, with shared per-species properties, and migrated between processes by MPI.

S08 summarises the design priorities as (1) modularity, with each class of function (Riemann solvers, reconstruction, conversion, BCs, outputs, integrators) behind a common interface; (2) documentation; (3) strict ANSI C; (4) simple control of options. It favours *limited* optimisation (cache-friendly structs, work done on 1D pencils) to keep the code adaptable.

### 2.2 Athena++: the big picture

The central design decision in S20 is **separating the mesh from the physics**. The mesh exists as an abstract framework that stores and communicates cell-, face- and edge-centred variables. AMR, boundary conditions and MPI are implemented for those *discrete variable types*, without reference to any physics. Physics modules are objects attached to each block, and the *order of work* is not hard-coded but assembled into **task lists**.

```
main()
 ├─ ParameterInput            ← input file (+ restart file) + command-line overrides
 ├─ Mesh                      ← whole domain; tree of MeshBlocks; global dt, time, AMR, load balance
 │    └─ MeshBlock[ ]         ← fixed-size logical block (unit of decomposition, refinement, threading)
 │         ├─ Coordinates     ← geometry: positions, widths, areas, volumes, geometric source terms
 │         ├─ BoundaryValues  ← neighbours + physical BCs; owns per-variable BoundaryVariable objects
 │         ├─ Reconstruction  ← DC / PLM / PPM / WENO-Z, optional characteristic projection
 │         ├─ MeshRefinement  ← restriction / prolongation operators, refinement flags
 │         ├─ EquationOfState ← cons↔prim conversion, sound speeds, floors
 │         ├─ Hydro           ← u, w (+ RK registers), fluxes, Riemann solver, source terms, diffusion
 │         ├─ Field           ← face B, cell-centred B, edge EMFs, CT update, field diffusion
 │         ├─ PassiveScalars, Gravity, OrbitalAdvection, NRRadiation, CosmicRay, ChemRadiation …
 │         └─ TaskStates      ← which tasks are done on this block
 ├─ TaskList(s)               ← TimeIntegratorTaskList (main), SuperTimeStepTaskList, gravity/MG/radiation lists
 ├─ Global solvers            ← FFTGravityDriver / MGGravityDriver, MG CR diffusion, implicit radiation, turbulence driver
 └─ Outputs                   ← history, tables, VTK, HDF5, restart
```

### 2.3 Mesh, MeshBlocks and the tree

- The **`Mesh`** is the logically rectangular domain. It is split into **`MeshBlock`s** that all have the *same number of cells*. Uniform grids also use MeshBlocks: they are the unit of MPI decomposition, and for serial runs you need only one.
- Blocks are organised in a **binary tree, quadtree or oct-tree** (1D, 2D or 3D). For uniform grids, the tree is built to the smallest depth n such that 2ⁿ covers the block count, so some nodes and leaves are empty. With AMR, refinement inserts deeper levels. The tree gives the parent–child relations and fast neighbour finding. Its natural **Z-ordering (Morton order)** of blocks is used to assign blocks to processes with good locality.
- Each `MeshBlock` stores its logical location, its size, index ranges for active and ghost cells, coarse-buffer index ranges for refinement, user data (saved in restarts), and pointers to its physics objects. It also records which arrays are the "primary" representation of each quantity (`RegisterMeshBlockData`). That registration is what load balancing and AMR use to move or refine data without knowing the physics. **[Code observation]**
- **Ghost zones.** NG = 2 suffices for 2nd order. Higher orders need more (3 for PPM-type hydro, 4 for PPM MHD). With AMR, NG must be even.
- **Data containers.** `AthenaArray<T>` is a custom up-to-6D array with contiguous storage, shallow slices and swaps. It is used everywhere, giving a **struct-of-arrays** layout (`u(n,k,j,i)`), which the vectorised kernels require. This is the opposite of the C version's array of structs.

### 2.4 Physics objects per MeshBlock

- **`Hydro`**:
  - Conserved `u` and primitive `w` arrays, plus extra registers (`u1`, `u2`, `u0`, `fl_div`) for low-storage Runge–Kutta and super-time-stepping.
  - Face fluxes `flux[3]`.
  - `CalculateFluxes()`: loops over pencils; for each direction it calls the `Reconstruction` method for the chosen order, then `RiemannSolver()`. For MHD, the Riemann solver also returns the face electric fields and upwinding weights needed for CT.
  - `AddFluxDivergence()`.
  - Source terms (`HydroSourceTerms`: constant acceleration, point mass, self-gravity, shearing box, rotating frame, orbital advection, user sources).
  - Diffusion (`HydroDiffusion`: viscosity, conduction).
  - Its own boundary variable `hbvar`.
- **`Field`**:
  - Face-centred `b` (with RK registers) and cell-centred `bcc`.
  - Edge EMFs `e`, and the face electric fields from the Riemann solver.
  - `ComputeCornerE()`, which builds edge EMFs from face values using the GS05 upwind method.
  - `CT()`, the constrained-transport update of the face fields.
  - Field diffusion (Ohmic, ambipolar).
  - Its own face-centred boundary variable `fbvar`.
- **`EquationOfState`**: conserved ↔ primitive conversion, sound speeds (fast magnetosonic speed for MHD), floors. **Which file implements it is chosen at compile time**: adiabatic or isothermal × hydro or MHD × Newtonian, SR or GR, or the general/tabulated EOS.
- **`Coordinates`**: cell-face and volume-centre positions, widths, face areas, edge lengths, volumes, and `AddCoordTermsDivergence()` for the geometric source terms; metric functions for GR. **This is also one class whose implementation file is selected at compile time** (cartesian, cylindrical, spherical_polar, minkowski, schwarzschild, kerr-schild, gr_user). Nonuniform spacing comes from a geometric ratio or a user mesh-generator function.
- **`Reconstruction`**: methods `DonorCell`, `PiecewiseLinear`, `PiecewiseParabolic`, `WENOZ` and so on, per direction. The order is chosen at runtime (`<time>/xorder` = 1, 2, 2c, 3, 3c, 3f, wenoz, 4, …, where "c" means characteristic projection). **[Code observation]** Incompatible choices are rejected in the constructor, for example 4th order with MHD ("4th-order CT not yet merged"), or general EOS with characteristic projection.
- **Optional modules:** `PassiveScalars`, `Gravity`, `OrbitalAdvection`, `NRRadiation`, `CosmicRay`, `CRDiffusion`, `ChemRadiation`. Each owns its arrays and, where it needs ghost cells, its own boundary-variable object.

### 2.5 Compile-time vs runtime configuration

Configuration is split along a clear line.

- **Compile time** (`configure.py` generates `Makefile` and `defs.hpp`):
  - **Which source file implements a component**: problem generator (`src/pgen/<prob>.cpp`), coordinates, EOS, Riemann solver.
  - **Preprocessor constants** that change data layout or kernels: `MAGNETIC_FIELDS_ENABLED`, `NON_BAROTROPIC_EOS`, `RELATIVISTIC_DYNAMICS`, `GENERAL_RELATIVITY`, `NGHOST`, `NSCALARS`, `NSPECIES`, `STS_ENABLED`, self-gravity type, radiation, CR and chemistry flags.
  - Parallelism and libraries: MPI, OpenMP, FFTW, HDF5; float or double precision.

  The polymorphism here is **link-time**. Each Riemann-solver file defines the same `Hydro::RiemannSolver`, each coordinate file defines the `Coordinates` methods, and so on, and the Makefile compiles exactly one of each. Kernels are therefore free of virtual-call and branch overhead. **[Assumption]** This is the performance motivation; S20 says the class design was benchmarked against raw C until it matched.
- **Runtime** (input file `athinput.*`, with command-line `block/param=value` overrides):
  - mesh size and extent, MeshBlock size, boundary flags;
  - SMR regions or AMR levels;
  - integrator (`vl2`, `rk1`–`rk4`, `ssprk5_4`), reconstruction order, CFL number;
  - physical parameters (γ, isothermal sound speed, diffusion coefficients);
  - outputs (type, variables, cadence);
  - OpenMP threads per rank;
  - problem parameters.

  Mesh refinement needs no compile flag because it is integral to the framework.
- **Default hooks via weak symbols.** `default_pgen.cpp` defines the user hooks (`InitUserMeshData`, `ProblemGenerator`, `UserWorkInLoop`, …) as `__attribute__((weak))`, so a problem file only overrides what it needs. **[Code observation]**

### 2.6 The problem-generator / enrolment interface

This is the user extension point. In `Mesh::InitUserMeshData()` a problem *enrols* function pointers:

- user boundary conditions per face (also for radiation, cosmic rays and multigrid);
- explicit source terms;
- extra timestep constraints;
- AMR refinement conditions;
- user mesh generators;
- history-output quantities;
- GR metrics;
- viscosity, conduction and resistivity coefficient functions;
- orbital velocity profiles.

`MeshBlock::ProblemGenerator()` sets the initial conserved variables and face-centred B; it is the only mandatory function. Other hooks: per-block data allocation (`InitUserMeshBlockData`), work after every cycle (`UserWorkInLoop`), before outputs (`UserWorkBeforeOutput`), and after the run (`UserWorkAfterLoop`). User data registered with the framework is saved in restart files automatically.

### 2.7 Dynamic execution: the TaskList

S20 calls this one of the most important parts of the design.

**Data structures**

- A **`Task`** holds a `task_id`, a `dependency` mask (both bit fields, with one bit per task) and a pointer to the member function that does the work for one MeshBlock and one stage.
- Each MeshBlock keeps **`TaskStates`**: a bit field of finished tasks.

**Execution** (`DoTaskListOneStage` / `DoAllAvailableTasks`)

1. Post non-blocking MPI receives.
2. Loop over MeshBlocks and over each block's remaining tasks.
3. A task runs only if its dependency bits are all set; dependencies within a block are checked with bitwise operations.
4. A task returns `success` (mark done, move on to the *next MeshBlock*), `next` (mark done, continue on the *same* block, for example to send freshly computed data at once), or `fail` (typically "MPI messages not arrived yet"; skip it and try other tasks).
5. Repeat until every task on every block is complete.

Communication with *other* blocks is therefore an external dependency, enforced by a receive task that keeps failing until data arrives. **Communication is overlapped with independent work**, both within a block and across the several blocks a process owns.

**Building the main list.** `TimeIntegratorTaskList` is built *at start-up* from the configured physics:

- Without MHD there are no field tasks. Shearing-box tasks appear only with shear-periodic boundaries. Prolongation tasks appear only with SMR/AMR. Passive scalars, radiation and cosmic rays add their own tasks.
- **[Code observation]** For MHD with refinement the dependency chain is roughly: calculate hydro fluxes → send/receive flux corrections → calculate EMFs → send/receive EMF corrections → integrate hydro and field → add source terms → send/receive/set boundaries for hydro, field and scalars → prolongate → primitives → physical BCs → user work → new block timestep → check refinement → clear boundaries.
- The **time integrator itself is encoded as task-list stages** with weights (`stage_wghts`) for the low-storage RK update. Changing the integrator changes the weights and the stage count, not the code.

**Other task lists** use the same machinery: super-time-stepping (`SuperTimeStepTaskList`), multigrid, FFT gravity, implicit radiation and chemistry-radiation.

**Advantages claimed in S20**

1. Latency hiding improves scaling to millions of cores.
2. Physics combinations are composed at runtime instead of through nested `#ifdef`s. A run can even skip (M)HD entirely, for example chemistry or radiation in post-processing mode.
3. Different MeshBlocks can in principle run *different* task lists: different physics in different regions, or self-gravity on separate ranks. S20 presents this as an enabled capability, with applications to be reported in future.

### 2.8 Main loop (`main.cpp`)

1. Initialise MPI, plus OpenMP (`MPI_THREAD_MULTIPLE` required for hybrid runs). Parse the command line: `-i` input, `-r` restart, `-d` run directory, `-m` dry-run of the mesh decomposition, `-t` wall-time limit, `-c` show configuration.
2. Read `ParameterInput` from the input file and/or restart file, then apply command-line overrides.
3. Construct the `Mesh` (new or from restart). This builds the tree, creates MeshBlocks, and attaches physics objects.
4. Construct the task lists (main; STS if enabled; chemistry-radiation if enabled).
5. `Mesh::Initialize`: call the problem generator, run the initial boundary exchange, compute primitives, compute the first dt. Then create `Outputs` and write the initial-condition outputs.
6. **Loop** while time is below `tlim` and the cycle count is below `nlim`:
   - if STS: an operator-split super-time-step for diffusion (before the main step);
   - turbulence driving, CR diffusion multigrid solve, chemistry and radiation;
   - **for each integrator stage**: `DoTaskListOneStage`. After a main stage, solve self-gravity (FFT or multigrid). Iterate implicit radiation if enabled;
   - if STS with RKL2: a second super-time-step (after the main step);
   - user work in loop; advance `time` and `ncycle`;
   - `LoadBalancingAndAdaptiveMeshRefinement`;
   - `NewTimeStep`: the global minimum over all blocks of the hyperbolic, parabolic and user limits;
   - outputs; check for signals and the wall-time limit.
7. Final outputs, `UserWorkAfterLoop`, timing and performance summary (zone-cycles per second).

### 2.9 Boundary communication and refinement machinery

- **Abstract interfaces** (`bvals_interfaces.hpp`) separate the concerns:
  - `BoundaryCommunication`: set up persistent MPI, start receiving, clear.
  - `BoundaryBuffer`: pack and unpack buffers for same-level, to-coarser and to-finer neighbours; send and receive flux corrections.
  - `BoundaryPhysics`: reflect, outflow, vacuum and so on, per face.
- Concrete classes exist for **cell-centred** variables (hydro, scalars, radiation, cosmic rays) and **face-centred** variables (B, including EMF correction). **Each physics module owns one or more boundary-variable objects**, and `BoundaryValues` on each block keeps the list. The framework therefore communicates any registered variable without knowing what it represents.
- **Every neighbour gets its own buffer and message**: up to 26 in 3D on a uniform grid and up to 56 with AMR. This removes the C version's x-then-y-then-z dependency, at the cost of many small messages. S20 suggests message pooling as possible future work.
- **Fine/coarse boundaries:**
  - The finer block *restricts* its data into a "coarse buffer" and sends it.
  - The coarser block sends its cells, which the finer block *prolongates* into its ghost zones after applying physical BCs on the coarse buffer.
  - **Restriction** is volume-weighted for cell data and area-weighted for face fields.
  - **Prolongation** of cell data is limited-linear (minmod, chosen because sharper limiters gave artefacts) on *primitive* variables at block boundaries, to avoid negative pressure, but on *conserved* variables when new blocks are created, to keep conservation.
  - **Face fields** are prolongated with the divergence-preserving method of Tóth & Roe (2002), extended to nonuniform and curvilinear grids. The v24.0 changelog notes recent divergence-preserving fixes for 3D spherical and cylindrical grids.
- **Flux and EMF correction.** At fine/coarse faces, the coarse flux is replaced by the area-weighted sum of the fine fluxes, and the coarse EMF by the length-weighted sum of the fine EMFs, so that conservation and the divergence of B are exact. Shared edges between blocks are also averaged *even without refinement*. Otherwise round-off (made worse by aggressive compiler optimisation, curvilinear grids and nondeterministic MPI ordering) makes the two copies of a shared face field drift apart, and with CT such errors never decay.
- **Physical BCs:** outflow, reflecting, periodic, shear-periodic, polar (across the pole in spherical coordinates, with EMFs on the axis averaged), polar wedge, and user functions.
- **AMR:**
  - The user refinement condition returns +1 (refine), −1 (derefine) or 0.
  - Neighbouring blocks may differ by at most one level, which also constrains which blocks can refine or derefine.
  - `derefine_count` delays derefinement.
  - **All levels advance with the same global dt** (no subcycling). S20 argues this choice: the fastest signal speeds are often on the coarse levels in MHD, time interpolation adds error especially with self-gravity, and subcycling complicates optimisation and load balancing. The savings are often modest.
- **Load balancing.** Each MeshBlock has a cost, set by the user or measured automatically from timing. Blocks are redistributed along the Z-order so that each process carries a similar total cost. This happens periodically and whenever blocks are created or destroyed. It requires several blocks per process to be effective.
- **Hybrid parallelism.** OpenMP is **coarse-grained**: each thread updates whole MeshBlocks. S20 found loop-level fork/join inefficient. The wiki recommends at least 32³, preferably 64³ cells per block per thread, and 16³ for AMR flexibility at extra ghost-zone overhead.

### 2.10 Outputs, restart, testing

- **Outputs** are subclasses of an abstract `OutputType` with `WriteOutputFile()`: history (`.hst`, global sums plus user-enrolled quantities), formatted tables, VTK, HDF5 (`.athdf` + `.xdmf`, recommended for AMR) and restart (`.rst`, MPI-IO, no extra library). Each `<output[n]>` block sets the cadence (dt or dcycle) and the variables (primitive, conserved, individual fields, user output variables). A restart may use a different number of MPI ranks, as long as it does not exceed the number of blocks.
- **Python tooling** in `vis/python/`: `athena_read.py` and plotting scripts; there is also yt support.
- **Testing.** A regression suite (`tst/regression/run_tests.py`) of 60+ tests, each a Python module with `prepare()`, `run()` and `analyze()`, organised into suites (hydro, mhd, amr, curvilinear, gr, sr, grav, mpi, omp, eos, diffusion, …). Tests compare with analytic solutions where possible (linear-wave convergence, shock tubes) rather than stored bit-for-bit data. There are also style and lint checks (cpplint, flake8), CI (Jenkins, formerly Travis), and coverage measurement (about 65% of C++ lines in S20).

### 2.11 How the extra physics modules plug in

Following your preference, these are described by *how they attach to the framework*, not their internals.

| Module | Activation | How it plugs in |
|---|---|---|
| Passive scalars | `--nscalars=N` | `PassiveScalars` object with conserved `s` and primitive concentration `r`; fluxes derived from the hydro mass flux; own boundary variable; scalar flux, integrate and send/receive tasks in the main list; optional diffusion. |
| General EOS | `--eos=general/…` | Alternative EOS implementation file providing pressure, energy and sound speed as functions of density and pressure or energy; tabulated or hydrogen (Saha) variants. HLLE, HLLC and HLLD were generalised (Coleman 2020). Not allowed with characteristic reconstruction. |
| Diffusion (viscosity, conduction, Ohmic, ambipolar, scalar) | input coefficients or enrolled coefficient functions | Diffusive fluxes from primitives are *added to the hydro/field fluxes* inside the same unsplit update, or advanced operator-split by **super-time-stepping** (RKL1/RKL2) via its own task list, using `-sts`. |
| Shearing box / orbital advection | shear-periodic BCs; `<orbital_advection>` | Extra source terms; shear-periodic boundary tasks (send/receive with remapping); orbital-advection tasks that remap along the orbit. Also usable in global cylindrical and spherical discs. |
| Self-gravity | `--grav=fft` or `mg` | Global solver objects (`FFTGravityDriver`, `MGGravityDriver`) called from `main` after each main stage; gravity source term in `HydroSourceTerms`. Multigrid has its own driver/per-block split and task lists; it requires power-of-two cubic MeshBlocks and uniform Cartesian 3D (Tomida & Stone 2023). |
| Radiation (explicit or implicit discrete ordinates) | `-nr_radiation` / `-implicit_radiation` | `NRRadiation` object with angle- and frequency-dependent intensities; flux, integrate and source-term tasks in the main list; the implicit variant runs an iteration task list each stage. |
| Cosmic rays | CR flags | `CosmicRay` object with two-moment transport tasks in the main list; CR diffusion with multigrid. |
| Chemistry | `--chemistry=…` | Species carried as passive scalars; ODE integration (forward Euler or CVODE) as an `IntegrateChemistry` task. Optional chemistry-radiation task list run once per cycle. |
| SR/GR | `-s`, `-g` | Different EOS (conversion and inversion), Riemann-solver and coordinate implementation files; same framework, CT and AMR. |
| Turbulence driving | `<turbulence>` | FFT-based driver called from `main` each cycle. |

The Athena C version had **Lagrangian dust particles** (Bai & Stone 2010). S20 lists a particle module as "under development". **[Code observation]** In your v24.0 copy, `Particles` is only forward-declared in `mesh.hpp`; no particle module exists.

---

## 3. Numerics overview

### 3.1 Discretisation (shared by Athena and Athena++)

- **Finite volume** for mass, momentum, energy (and scalars): cell-averaged conserved variables, updated by differences of time- and area-averaged face fluxes.
- **Finite area / constrained transport (CT)** for the magnetic field. The **face-centred area averages** of B are the primary variables, updated with **edge-centred, line-averaged EMFs**. This keeps the discrete divergence of B, summed over each cell's faces, at zero to round-off; equivalently, magnetic flux through every cell is conserved. Cell-centred B is the average of the two face values and is used only to build fluxes. S08 and GS05 argue this is the natural discretisation, consistent with the integral form of the induction equation.
- **Why unsplit integration is essential for MHD.** In a dimensionally split sweep, the normal field component cannot evolve, but the divergence constraint requires all components to evolve together. Splitting therefore forces non-conservative divergence-source-term formulations. All Athena integrators are unsplit for this reason.
- **The EMF construction (GS05) is a key ingredient.** Simply averaging the four face electric fields around an edge is *inconsistent*: it does not reduce to the 1D scheme for grid-aligned flow and fails the field-loop advection test. Athena instead integrates from face to edge using gradients of the electric field, upwinded according to the direction of the contact (mass-flux) wave. The resulting scheme reduces exactly to the 1D algorithm for plane-parallel, grid-aligned flow.
- **The field-loop test** (GS08) is a sensitive check that the divergence-free constraint is preserved on the correct stencil. A planar field loop advected with a velocity component out of its plane must keep a zero out-of-plane field.

### 3.2 Athena (C) integrators

- **CTU+CT** (default in C): Colella's corner transport upwind, extended to MHD.
  - In 2D: reconstruct interface states with characteristic tracing (adding multidimensional "MHD source terms" proportional to the field divergence across the cell); first-order Riemann solves; corner EMFs; half-step CT update of face fields; transverse-flux corrections of interface states (with more divergence source terms); second Riemann solve; final CT and finite-volume update.
  - In 3D, a **6-solve** variant (stable for CFL ≤ 0.5) is used instead of the 12-solve version. GS08 found it as accurate, at the same cost, and much simpler.
  - CTU is less diffusive and recommended where possible.
- **VL+CT**: a simpler two-step predictor–corrector (first-order predictor, then a second-order corrector), similar to MUSCL-Hancock. It is more robust for extreme flows (very supersonic or strongly magnetised turbulence), needs no characteristic tracing, and is required for SR. It can be combined with **FOFC** (first-order flux correction): cells that would become negative in density or pressure are recomputed with first-order fluxes.
- **Reconstruction:** 1st (donor cell), 2nd (PLM) and 3rd (PPM) order, limited in characteristic variables by default, optionally in primitives. The docs recommend 3rd order for all applications. Overall accuracy stays at 2nd order, but errors are noticeably smaller.
- **Riemann solvers:** Roe (default), HLLE, HLLC, HLLD, exact, two-shock, FORCE. The **H-correction** suppresses the carbuncle instability.
- **Timestep:** CFL estimate from cell-centred fast-magnetosonic speeds.
- **Curvilinear (cylindrical; Skinner & Ostriker).** The equations are written so that the existing Riemann solvers and eigensystems are reused unchanged. The momentum update is formulated to conserve angular momentum, and reconstruction and characteristic tracing are adapted for the geometry. The guiding principle was to change the Cartesian code "as minimally and transparently as possible".
- **Shearing box (Stone & Gardiner 2010).**
  - Coriolis and tidal source terms use Crank–Nicolson differencing, which conserves epicyclic energy to round-off.
  - The tidal term in the energy equation is written as the gradient of an effective potential, so that total energy is conserved.
  - **Orbital advection** (FARGO-style, with CT) removes the background shear flow from the timestep limit.
  - Shear-periodic boundaries are corrected to conserve net vertical flux.
- **Relativistic MHD (Beckwith & Stone 2011).**
  - VL+CT, because characteristic tracing is too complex in relativity.
  - Several relativistic Riemann solvers.
  - Primitive recovery by the 1D method of Noble et al.
  - A **hierarchy of correction steps** for unphysical states: first-order fluxes, then floors. These are rarely triggered but crucial for robustness.
- **Particles (Bai & Stone 2010).**
  - Super-particles coupled to the gas by drag.
  - A second-order predictor–corrector couples particles and gas. Momentum feedback to the gas is a source term, with exact momentum conservation.
  - Triangular-shaped-cloud (TSC) interpolation and deposition.
  - Semi-implicit (leap-frog generalisation) and fully implicit particle integrators handle stiff, strongly coupled regimes.
  - It is combined with the CTU integrator.

### 3.3 Athena++ numerics

- **Method of lines.** CTU is *not* implemented in Athena++ because its characteristic projections are too complex for relativistic MHD (S20). The flux divergence is computed at one time level, then advanced by an explicit ODE integrator written in **low-storage 2S/3S\* form** (Ketcheson 2010), so only two or three state registers are needed. The options are:
  - **VL2** (default): predictor–corrector midpoint method with a forced first-order predictor. Stable to CFL ≈ 0.5 in 2D and 3D.
  - **RK1**, for testing.
  - **RK2** and **RK3**: SSP Runge–Kutta.
  - **RK4**, and **SSPRK(5,4)** (the latter needs one extra hard-coded register operation).

  S20 recommends VL2 or RK2 with PLM or PPM, and RK3 with PPM.
- **Reconstruction:** DC, PLM, PPM, WENO-Z variants, on primitive variables (or characteristic variables for non-relativistic ideal-EOS runs).
  - **Limiters adapted to nonuniform and curvilinear grids.** Original van Leer on uniform grids; the Mignone (2014) modification on nonuniform or curvilinear grids, where slopes are divided by distances to *volume* centroids.
  - The PPM limiter is extremum-preserving (McCorquodale et al. 2015) on Cartesian grids.
  - CT stays formally 2nd order, so the overall MHD scheme is 2nd order even with PPM, though more accurate. A fully 4th-order variant exists (Felker & Stone 2018), but in this code copy it is only allowed for hydro. **[Code observation]**
- **Riemann solvers** (compile-time `--flux`): HLLE, HLLC, LHLLC, HLLD, LHLLD, Roe, LLF, plus relativistic HLLE, HLLC and HLLD, and frame-transformation variants for GR. No exact solver ("no significant gain").
- **Geometric source terms** in cylindrical and spherical-polar coordinates are discretised so that the momentum update is algebraically identical to a conservative angular-momentum update. Angular momentum is therefore conserved to machine precision.
- **Diffusion** (viscosity, conduction, Ohmic, ambipolar): second-order fluxes added unsplit within each integrator stage, *or* operator-split with RKL1/RKL2 super-time-stepping, where each super-step takes many stages (about s² times the explicit diffusive step).
- **Timestep:** a global minimum over blocks of the CFL limit, an optional parabolic limit (with STS) and user limits. The same dt is used on all AMR levels.
- **Relativity:** reconstruct only on primitives, using spatial 4-velocity so that any reconstructed state is sub-luminal. Primitive inversion follows Newman & Hamlin (2014), which guarantees a root if one exists. Floors on density and pressure; ceilings on Lorentz factor, inverse plasma beta and magnetisation.
- **Self-gravity:** FFT (periodic or uniform grids) or full multigrid (O(N), designed to extend to AMR). A total-energy-conserving formulation is listed among module papers (Mullen et al. 2021).

---

## 4. Notable design choices

**Worth borrowing (adapted to Python)**

1. **Mesh/physics separation.** Build the grid, refinement, boundary exchange and I/O around *generic variable types* (cell-, face- and edge-centred arrays registered with the block), with no knowledge of the equations. Physics modules register their arrays and receive communication, restriction, prolongation and restart support for free. This is the single most important lesson from the Athena → Athena++ rewrite, which happened precisely because the C code mixed the two.
2. **Blocks of fixed size as the universal unit.** Fixed-size MeshBlocks serve decomposition, refinement, threading and load balancing alike. Every kernel then works on the same logical shape, which **[Assumption]** maps naturally onto vectorised NumPy or Numba/JAX operations over a "batch of blocks". A tree with Z-ordering gives neighbour lookup and locality.
3. **Describe the algorithm as data: a task list with dependencies.** Even without MPI, expressing a timestep as named tasks with explicit dependencies, generated from the active physics, makes it easy to add or remove physics and integrators without editing a monolithic step function. **[Assumption]** In Python this could be a small DAG scheduler. It would also make the communication points explicit for any later parallel version.
4. **Separate the time integrator from the spatial operator.** The method-of-lines formulation with the integrator encoded as stage weights (low-storage RK) lets one flux-divergence routine serve every integrator. It also avoids characteristic tracing, which is the most intricate and least general part of CTU. That was the reason Athena++ dropped CTU.
5. **Unsplit integration plus staggered CT for MHD, with upwinded EMF construction (GS05).** If MHD is a goal, this decision shapes your data model from the start. You need face-centred B and edge-centred EMF arrays alongside cell-centred variables, and the face-to-edge upwinding must be done carefully. Plan for it even if you start with pure hydro.
6. **Geometry encapsulated in a Coordinates object** (face areas, volumes, volume centroids, geometric source terms), with limiter and stencil weights aware of nonuniform and curvilinear spacing. Angular-momentum-conserving source terms are a subtle but valuable detail.
7. **Conservation at block boundaries by flux and EMF correction**, and averaging of shared face and edge values even without refinement.
8. **A clear split between compile-time and runtime choices.** Choices that change data layout (MHD on or off, number of scalars, relativity) are fixed early; algorithmic knobs (integrator, reconstruction order, CFL, refinement, outputs) are runtime parameters. **[Assumption]** In Python, the "compile-time" tier could become choices made once at construction (selecting kernels or JIT-specialising), while the runtime tier stays in the input file.
9. **Hooks plus enrolment for user code** (problem generator, BCs, sources, refinement criteria, timestep limits, history outputs), with sensible defaults (weak symbols in C++, default methods in Python).
10. **Verification culture.** A regression suite organised by physics, built around convergence tests against analytic solutions (linear waves in every MHD family, field-loop advection, shock tubes) rather than bit-for-bit comparisons. CI runs it on every change.

**Trade-offs and limitations to be aware of**

1. **Complexity.** The C++ code is about 130,000 lines. Inter-block communication with AMR (up to 56 neighbours, coarse buffers, separate rules for shared faces, EMF averaging) is where most of that complexity sits.
2. **Link-time component selection** gives speed, but you must recompile to change the Riemann solver or EOS, and you cannot mix them in one run. In Python, runtime strategy objects would be more natural; the performance cost would need care **[Assumption]**.
3. **The time-integrator task list is a long chain of nested conditionals.** The source itself has a TODO comment calling them "horrible". This shows the limit of generating the list by hand as the number of physics combinations grows.
4. **A single global timestep across AMR levels.** This is simple and robust but inefficient for very deep hierarchies covering a small fraction of the volume. S20 acknowledges this.
5. **Block-based AMR refines whole blocks.** It adapts less tightly to flow features than patch- or cell-based AMR, and there is a block-size trade-off: flexibility versus ghost-zone overhead.
6. **The C version's array-of-structs layout and fixed variable order** are explicitly called fragile in its own documentation. Athena++ moved to struct-of-arrays.
7. **Galilean invariance.** The C docs note that apparent non-invariance in tests (for example Kelvin–Helmholtz in a moving frame) comes from *under-resolved* interfaces dominated by truncation error, not from the Riemann solver. This matters when you design your test suite.
