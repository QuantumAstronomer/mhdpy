# Pyro — Synthesis

## Sources and conventions

**Sources used**

- Paper 1: Zingale (2014), *pyro: A teaching code for computational astrophysical hydrodynamics*, Astronomy & Computing 6, 52 (`Docs/1306.6883v3.pdf`). This is the original design paper. It describes an older pyro version that used Fortran kernels and pickle output.
- Paper 2: Harpole, Zingale, Hawke & Chegini (2019), *pyro: a framework for hydrodynamics explorations and prototyping*, JOSS 4, 1265 (`Docs/1902.08702v1.pdf`). This short update covers the move to numba, HDF5, the `Pyro` class and new solvers.
- Code: `Code/pyro/`. The changelog's latest entry is 4.5.1; the online docs report 4.5.0.post18.
- In-repo documentation: `Code/docs/source/*.rst` and notebooks, plus `Code/README.md`.
- Web: python-hydro.github.io/pyro2 (current docs, same content as the in-repo Sphinx sources) and pyro2.readthedocs.io. The README states the readthedocs site is outdated; it shows version 2.2. I used it only to confirm that nothing newer is described there.

**Markers used in this document**

- **[GK]** marks a statement from my general knowledge, not from your material.
- **[Assumption]** marks my interpretation where the sources are not explicit.
- **[Code observation]** marks something read in the code but not verified by running it.

**A link to your own folder.** The pyro docs point to *Introduction to Computational Astrophysical Hydrodynamics* (`CompHydroTutorial.pdf`, Open Astrophysics Bookshelf) as the companion notes for the algorithms. That appears to be the same file as your "Computational Hydrodynamics Book". As you asked, I did not analyse it here.

---

## 1. Purpose

Pyro is an **educational and prototyping framework**, not a high-performance research code.

- **Original goal (2014 paper).** To let students learn the methods used in astrophysical hydro codes by reading and modifying a clean implementation. Where clarity and performance conflict, clarity wins. Each system of equations gets *one* representative method, and "variations and enhancements are left as exercises."
- **Evolved goal (2019 paper and current docs).** It is also a **prototyping bed for algorithms** before they go into production codes. The 4th-order SDC compressible solver was the model for higher-order schemes in the Castro code. The low-Mach atmospheric solver mirrors the Maestro code and is used to prototype new low-Mach algorithms. Both are AMReX-family research codes from the same group **[GK for the AMReX link]**.
- **Breadth over depth.** Pyro is a *collection of solvers for different equation systems*. They share the grid, data, boundary-condition, I/O and driver infrastructure. Currently included:
  - linear advection (several methods)
  - Burgers' equation (inviscid and viscous)
  - compressible Euler (2nd-order CTU, 2nd-order method-of-lines, 4th-order RK, 4th-order SDC, and a reacting stub)
  - shallow-water equations
  - implicit diffusion
  - incompressible flow (inviscid and viscous)
  - low-Mach atmospheric flow
  - multigrid elliptic solvers
  - Lagrangian tracer particles
- **Scope limits.** Everything is **2D**. There is a **single grid** with no domain decomposition, no parallelism and no AMR. Grids are Cartesian, plus an axisymmetric spherical-polar (r–θ) option for some compressible solvers. There is **no MHD**. The 2014 paper lists MHD and flux-limited-diffusion radiation as future directions, but neither exists in the code.
- **Performance.** The code is pure Python plus NumPy. A few hot kernels (interface states, Riemann solvers, artificial viscosity, the shallow-water equivalents) are JIT-compiled with numba. Neither paper benchmarks performance.
- **Software-engineering pedagogy.** This is an explicit goal: open source (BSD-3), git, regression testing against stored benchmarks, pytest unit tests and Sphinx docs are all presented as things students should learn.

---

## 2. Architecture

### 2.1 Layered structure

Pyro's architecture is a **shared infrastructure layer** plus **one sub-package per solver**, bound together by a **common driver** and a **common `Simulation` interface**.

```
pyro/
├── pyro_sim.py          Driver: Pyro class + command-line entry point
├── simulation_null.py   NullSimulation base class + grid/BC setup helpers
├── _defaults            Global runtime parameters (driver, io, vis, mesh, particles)
├── mesh/                Grid, data containers, BCs, array indexing, reconstruction, RK integrator
├── multigrid/           Cell-centred multigrid (constant, variable, general coefficient)
├── particles/           Lagrangian tracer particles
├── util/                Runtime parameters, HDF5 reader, compare, profiling, messages, plot helpers
├── analysis/            Post-processing / comparison-to-exact-solution scripts
└── <solver>/            One package per solver:
      simulation.py      Simulation class (subclass of NullSimulation or of another solver)
      _defaults          Solver-specific runtime parameters
      problems/          Problem setups (one module + inputs files per problem)
      tests/             Stored benchmark outputs for regression tests
      [interface.py, riemann.py, fluxes.py, eos.py, derives.py, BC.py …]  numerics
```

The 2014 paper makes a key point that shapes the whole design: **the solution procedure is structurally the same for every PDE system**. The grid, data locations, boundary-condition types and driver flowchart are shared. So one driver can run every solver, and each solver only fills in the numerics.

### 2.2 Infrastructure layer: `mesh/`

This is the part of pyro most directly reusable as a foundation.

**`Grid2d`** (in `patch.py`) holds geometry only:

- cell counts and ghost-cell count;
- index bounds of the valid region (`ilo`, `ihi`, `jlo`, `jhi`);
- 1D and 2D arrays of left-edge, centre and right-edge coordinates.

It deliberately knows nothing about boundary conditions, because those can differ per variable. Two subclasses add a **geometry abstraction**:

- **`Cartesian2d`** provides face areas, cell volumes and the derivatives of log-area (which are zero in Cartesian coordinates).
- **`SphericalPolar`** treats x as r and y as θ, assumes axisymmetry, and provides the true face areas and volumes plus the log-area derivatives used for geometric source terms.

Solvers write their updates as "flux × face area ÷ volume" (at least the CTU compressible solver does), so the same update code works on both geometries.

**`CellCenterData2d`** holds the data that lives on a grid. It is built in stages:

1. Create it on a grid.
2. Call `register_var(name, bc)` for each variable, with that variable's own boundary-condition object.
3. Call `set_aux(key, value)` to attach metadata needed to interpret the data later, such as γ and gravity.
4. Call `add_derived(func)` to register callbacks that compute derived quantities.
5. Call `create()`, which allocates one array shaped `[nx + 2·ghost, ny + 2·ghost, nvar]` and **locks** the object so no more variables can be added.

Other features:

- `get_var(name)` returns a *view* into the main array, so writes go straight into the state. If the name is not a stored variable, the registered derive callbacks are tried in turn. This is how solvers expose velocity, pressure, sound speed and vorticity without storing them.
- `fill_BC(name)` fills the ghost cells of one variable according to its BC object. `fill_BC_all()` does every variable.
- `restrict` and `prolong` (coarsen and refine by a factor of 2) support multigrid.
- `write_data` writes the object to HDF5.

**`FV2d`**, a subclass of `CellCenterData2d`, adds 4th-order-accurate conversion between cell averages and cell-centre point values. The 4th-order solvers need this.

**`FaceCenterData2d`** holds face-centred (staggered) data. It is used for the MAC velocities in the projection solvers.

**`ArrayIndexer`** is a subclass of NumPy's `ndarray` that knows its grid. It offers stencil-style views:

- `v()` for the valid region;
- `ip(k)` and `jp(k)` for the array shifted by k cells in x or y;
- `ip_jp(i, j)` for a diagonal shift;
- `lap()` for a 5-point Laplacian;
- `norm()`, symmetry checks and `fill_ghost()`.

The purpose is readability. The 2014 paper explains that raw NumPy slices hide the index notation used in papers. With `ArrayIndexer`, an expression like `a.ip(1) - 2*a.v() + a.ip(-1)` reads like the formula.

**`BC`** (in `boundary.py`) is a per-variable container naming the boundary type on each of the four edges. Built-in types are outflow, periodic, reflect (even or odd), Dirichlet and Neumann. Inhomogeneous Dirichlet and Neumann conditions can take callback functions. Key details:

- **Odd reflection** is set per direction, so the normal momentum component flips sign at a reflecting wall. The helper `bc_setup()` returns three BC objects for this: generic, odd-in-x and odd-in-y.
- **Extensibility through a registry.** `define_bc(name, function, is_solid)` registers a solver-specific boundary type. The compressible solver uses this for hydrostatic (`hse`), `ambient` and `ramp` boundaries. `fill_BC` dispatches to the registered function after doing the standard fill.
- A table records which boundary types are **solid walls**. The Riemann solvers receive this so they can enforce zero normal flux there.

**Numerical building blocks shared by solvers:**

- `reconstruction.py`: slope limiters (none, 2nd-order MC, 4th-order MC), shock flattening (1D and multi-D), a well-balanced reconstruction helper for gravity, and WENO.
- `integration.py`: a generic explicit Runge–Kutta integrator driven by a Butcher table (RK2, TVD2, TVD3, RK4). It operates on whole `CellCenterData2d` objects: it clones the start state for each stage, accumulates stage increments, and builds the final update.
- `fourth_order.py`: interface states for the 4th-order methods.

### 2.3 The simulation contract: `NullSimulation`

Every solver's `Simulation` class inherits, directly or indirectly, from `NullSimulation`, which defines the **lifecycle interface** the driver relies on:

| Method | Role |
|---|---|
| `__init__` | Stores the runtime parameters, problem callbacks (`init_data`, `finalize`, optional `source_terms`), timers, and the data class to use (`CellCenterData2d` or `FV2d`). |
| `initialize()` | Builds the grid and data. The solver registers its variables and BCs, sets aux data and derives, then calls the problem's `init_data`. |
| `preevolve()` | One-off work before stepping. The projection solvers make the initial velocity divergence-free; the 4th-order solvers convert initial point values to cell averages. |
| `method_compute_timestep()` | Solver-specific stability limit (CFL for hyperbolic solvers, a diffusion limit for diffusion). |
| `compute_timestep()` | Generic wrapper around the above. Applies the driver policies: a fixed dt option, a reduced first step (`init_tstep_factor`), a maximum growth factor per step, and clipping so the run lands exactly on `tmax`. |
| `evolve()` | Advances one step. This is the numerical heart of each solver. |
| `finished()`, `do_output()` | Stopping criterion (time or step count) and output cadence (time interval or step interval). |
| `dovis()` | Live matplotlib visualisation. |
| `write()` / `write_extras()` / `read_extras()` | HDF5 output of the data object, particles, runtime parameters and solver-specific extras. |
| `finalize()` | Calls the problem's finalize hook, which typically prints hints on how to analyse the output. |

Two module-level helpers in `simulation_null.py` standardise the shared setup: `grid_setup(rp, ng)` builds the right grid type from the runtime parameters, and `bc_setup(rp)` builds the three BC objects.

### 2.4 Solvers as an inheritance tree

Solvers reuse each other through **class inheritance**. Only the methods that differ are overridden.

```
NullSimulation
├── advection.Simulation              (2nd-order unsplit CTU)
│   ├── advection_rk.Simulation       (method of lines + RKIntegrator: overrides evolve/substep)
│   │   └── advection_fv4.Simulation  (4th-order FV, uses FV2d data class)
│   └── advection_weno.Simulation
├── advection_nonuniform.Simulation
├── burgers.Simulation
│   ├── burgers_viscous.Simulation
│   └── incompressible.Simulation     (reuses Burgers advection + MAC/approximate projection via multigrid)
│       └── incompressible_viscous.Simulation
├── compressible.Simulation           (2nd-order unsplit CTU, Colella 1990)
│   ├── compressible_rk.Simulation    (method of lines + RK; overrides evolve, adds substep)
│   │   └── compressible_fv4.Simulation   (4th-order FV + RK4; FV2d; overrides substep, preevolve)
│   │       └── compressible_sdc.Simulation (same spatial operator; SDC time integration replaces evolve)
│   └── compressible_react.Simulation (Strang-splits burn/diffuse around the parent evolve — stubs only)
├── diffusion.Simulation              (Crank–Nicolson via multigrid)
├── swe.Simulation                    (shallow water, CTU, structurally parallels compressible)
└── lm_atm.Simulation                 (low-Mach atmosphere; variable-coefficient multigrid; 1D base state)
```

Problem setups are shared across a family by **symlinking** the `problems/` directory. For example, all compressible variants use `compressible/problems/`.

The compressible family shows a nice **separation of spatial and temporal discretisation**. The method-of-lines solvers define `substep(state)`, which returns the time derivative (minus the flux divergence plus sources) for a given state. The time integrator decides how to combine substeps:

- `compressible_rk` uses the generic `RKIntegrator`.
- `compressible_fv4` inherits that `evolve` but overrides `substep` with a 4th-order spatial operator.
- `compressible_sdc` keeps the `fv4` `substep` and overrides only `evolve`, with three Gauss–Lobatto nodes and four correction iterations.

### 2.5 Inside a solver: the `compressible` CTU solver as the reference example

**Module layout**

- `simulation.py`:
  - A `Variables` class that maps variable names to indices for the conserved and primitive vectors. Any extra registered variables are treated as passively advected scalars.
  - `cons_to_prim` and `prim_to_cons`.
  - `get_external_sources` (constant gravity, the geometric terms for spherical coordinates, and an optional problem-supplied heating term).
  - `get_sponge_factor`.
  - The `Simulation` class itself.
- `unsplit_fluxes.py`: the high-level steps of the CTU algorithm (interface states, source terms on interface states, transverse corrections, artificial viscosity).
- `interface.py` (numba): the 1D characteristic-tracing prediction of interface states using explicit eigenvectors, plus the artificial-viscosity kernel.
- `riemann.py` (numba): the CGF two-shock solver, HLLC, a low-speed HLLC variant, the conserved-flux function, and the `riemann_flux` dispatcher, which picks the solver from a dictionary keyed by the runtime parameter.
- `eos.py`: gamma-law pressure and energy functions.
- `derives.py`: velocity, pressure, sound speed, vorticity, Mach number and so on, computed on demand.
- `BC.py`: hydrostatic, ambient and ramp boundaries, plus inflow helpers.

**Setup.** `initialize()` registers density, energy and the two momenta. The momenta get odd-reflecting BCs. It registers the solver-specific BCs, sets γ and gravity as aux data, creates a parallel `aux_data` object for source-term arrays (so their ghost cells can be filled too), creates particles if requested, and then calls the problem's `init_data`. By default there are 4 ghost cells.

**Data flow for one step of `evolve()`:**

1. Clean the state (density floor).
2. Convert to primitive variables. Compute the shock-flattening coefficient and the limited slopes in x and y.
3. **Predict the normal interface states** at the half time in each direction by characteristic tracing (numba kernel). Convert them to conserved form.
4. Add the half-step source terms to the interface states.
5. **Transverse correction.** Solve Riemann problems on the provisional states of the *other* direction and add the transverse flux differences (corner coupling). This is what makes the scheme unsplit.
6. **Riemann solve** at every x-face and y-face to get the fluxes.
7. Add artificial viscosity to the fluxes.
8. **Conservative update** using flux × area ÷ volume. In spherical geometry, the pressure gradient is applied separately as a source.
9. **Sources by predictor–corrector.** Add the full-step old source, recompute the source with the new state, then correct by half the difference. For gravity, the energy source uses the updated momentum.
10. Optionally apply the sponge damping, implicitly in velocity.
11. Advance the tracer particles. Increment time and step count.

**Timestep.** CFL is the minimum over the grid of cell width ÷ (|velocity| + sound speed), with default CFL 0.8.

### 2.6 Problems, parameters, driver and I/O

**Problem module contract.** Each problem file in `<solver>/problems/` provides:

- `PROBLEM_PARAMS`: a dictionary of problem parameters and their defaults, with namespaced keys such as `sod.dens_left`;
- `DEFAULT_INPUTS`: the default inputs file name;
- `init_data(data, rp)`: fills the state in conserved variables, by writing into the views returned by `get_var`;
- `finalize()`;
- optionally `source_terms(grid, U, ivars, rp)` for problem-specific heating and similar.

Problems are found by module import (`pyro.<solver>.problems.<name>`). Custom problems can also be registered at runtime with `Pyro.add_problem(name, func, problem_params)`.

**Runtime parameters (`RuntimeParameters`).** Parameters live in INI-like files with `[section]` headers and `key = value ; comment` lines. They are layered in this order:

1. global `_defaults`;
2. solver `_defaults`;
3. the problem's `PROBLEM_PARAMS`;
4. the inputs file, which may only override existing keys;
5. command-line `section.key=value` pairs, or `inputs_dict` when used from Python.

Types are inferred from the text. The full resolved set is written to `inputs.auto` at start-up, and parameters never read are reported at the end. Parameters are also stored in every output file.

**Driver (`pyro_sim.py`).**

- The **`Pyro`** class imports the solver package dynamically by name, loads the parameter layers, instantiates the solver's `Simulation`, and calls `initialize()` and `preevolve()`.
- `run_sim()` loops `single_step()` until `finished()`. Each `single_step()` fills all boundary conditions, computes the timestep, calls `evolve`, then does output and visualisation as scheduled.
- Accessors `get_var`, `get_grid` and `get_sim` support notebook use. When not run from the command line, visualisation, verbosity and I/O are switched off.
- **`PyroBenchmark`** is a subclass that adds storing of, and comparison to, benchmark output.
- The command-line wrapper is the console script `pyro_sim.py solver problem inputs [overrides]`.

**I/O.**

- HDF5 files contain: solver and problem names, time and step attributes, the grid, each variable with its BC types, aux data, particles, runtime parameters, and solver extras such as the low-Mach base state and custom BC names.
- `util/io_pyro.read()` rebuilds the grid and data object and then a `Simulation` object of the right solver class, re-attaching the derive functions by walking the class hierarchy. The result is useful for plotting (`plot.py` reuses the solver's `dovis`) and analysis.
- **[Code observation]** I found no driver option to *restart* a run from a file. The reader reconstructs the object, but `Pyro` has no restart path.

**Testing.**

- Regression: `test.py` runs a list of solver/problem combinations, optionally in parallel, and compares the final output zone by zone with the HDF5 benchmarks in each solver's `tests/` directory (`util/compare.py`). It is exact by default, with a relative tolerance option. The 2014 paper argues for bit-for-bit comparison because it catches round-off-level changes that tolerance checks miss.
- Unit tests: pytest, including notebook validation with `nbval`.

**Analysis.** Scripts in `analysis/` compare runs with exact solutions (Sod, Sedov, Gaussian diffusion, incompressible convergence, dam break) and plot variables.

**Particles.** `Particles` holds a dictionary of `Particle` objects created randomly, on a grid, or from an array. Each step moves them with a midpoint method using bilinearly interpolated cell-centred velocity (described as based on AMReX's `AdvectWithUcc`), then enforces boundaries. Solvers opt in by creating them in `initialize` and calling `update_particles(dt)` in `evolve`.

---

## 3. Numerics overview

These are the methods pyro implements, with emphasis on the compressible solvers that matter for your project.

| Area | What pyro does |
|---|---|
| Discretisation | Cell-centred finite volume on a uniform logically Cartesian 2D grid. The 4th-order solvers distinguish cell averages from point values and convert between them with Laplacian corrections. |
| Multi-D strategy | **Unsplit** throughout. The `advection`, `compressible` and `swe` solvers use **corner transport upwind (CTU, Colella 1990)**: interface states are predicted to the half time with a Taylor expansion, then corrected with transverse flux differences from extra Riemann solves. The `_rk`, `_fv4` and `_sdc` solvers use a **method-of-lines** approach: build the spatial operator, then integrate with RK or SDC. Dimensional splitting is described only as an exercise. |
| Reconstruction | Piecewise linear (PLM) in primitive variables with an MC limiter (2nd- or 4th-order variants, or none). Optional multidimensional shock **flattening** (Colella 1990). WENO for `advection_weno`. 4th-order reconstruction for the fv4 and SDC solvers. |
| Characteristic tracing | In CTU compressible, the normal prediction projects the jumps onto the eigenvectors of the primitive-variable system and keeps only the waves moving toward the interface. The eigenvectors are built explicitly in the code for teaching clarity, whereas most papers present only the multiplied-out result. |
| Riemann solvers | Compressible: **CGF** (Colella–Glaz–Ferguson, an approximate two-shock solver, as in Castro), **HLLC** (Toro), and a low-speed HLLC variant. HLLC is not allowed with spherical-polar geometry. Advection: upwinding. Burgers/incompressible: the Burgers Riemann problem. |
| Dissipation | Artificial viscosity added to the fluxes (coefficient 0.1 by default), as in Colella 1990. |
| Time integration | CTU: single-step, 2nd order. Method of lines: RK2, TVD2, TVD3 or RK4 via a Butcher-table integrator. SDC: 3 Gauss–Lobatto nodes, 4 iterations, giving 4th order. |
| Sources | CTU: predictor–corrector, time-centred, 2nd order. Gravity is a constant vertical acceleration (radial in spherical coordinates). Spherical geometry adds geometric terms. There is a sponge and a problem-defined heating term. Method of lines: sources are part of the right-hand side at each stage. |
| EOS | Gamma-law only (γ = 1.4 by default). |
| Elliptic solvers | Cell-centred geometric multigrid using V-cycles, red-black Gauss–Seidel smoothing, restriction by averaging 4 cells, and bilinear prolongation. Grids have power-of-two size and are coarsened down to 2×2. Constant-coefficient Helmholtz (Poisson as a special case), variable-coefficient and general linear elliptic variants exist. Boundaries are Dirichlet, Neumann or periodic. |
| Parabolic | Crank–Nicolson diffusion, solved as a Helmholtz problem with multigrid, so it is unconditionally stable. |
| Incompressible | Cell-centred **approximate projection** (Bell–Colella–Glaz style, final projection after Martin & Colella 2000). There is also a MAC projection of the half-time advective velocities, needed for stability at CFL near 1. Multigrid does both projections. |
| Low Mach | Atmospheric low-Mach equations with a 1D hydrostatic base state (`Basestate` objects for density, pressure and related quantities) and a variable-coefficient multigrid projection. |
| Gravity (self-gravity) | **None.** Only constant gravity. Multigrid could solve Poisson, but it is not coupled to the compressible solvers. |
| Verification | The papers show near-2nd-order convergence for smooth advection (the shortfall is attributed to limiters), exact 2nd order for multigrid, near-2nd order for incompressible, and good agreement with exact Sod, Sedov and Gaussian-diffusion solutions. |

---

## 4. Notable design choices

**Worth borrowing for your own framework**

1. **Separate geometry, data and boundary conditions.** `Grid2d` (geometry), `CellCenterData2d` (named, registered fields with per-field BCs), and BC objects with a registry for custom types. This lets every solver share one infrastructure. Per-variable BCs elegantly handle parity at reflecting walls.
2. **A geometry object that supplies face areas, volumes and log-area derivatives.** Writing the update as flux × area ÷ volume lets one solver run in Cartesian and axisymmetric spherical-polar coordinates.
3. **The "register then create then lock" pattern for data**, together with derived-variable callbacks. Physics packages declare what they need, and diagnostics such as pressure, sound speed and vorticity are computed on demand rather than stored.
4. **A stencil-aware array subclass (`ArrayIndexer`).** Index-shift helpers make vectorised NumPy read like the equations. For a Python framework this is a cheap but strong readability win.
5. **A minimal, stable lifecycle contract** (`initialize`, `preevolve`, `compute_timestep`, `evolve`, `write`, `finalize`, `dovis`) driven by one driver. New solvers plug in without touching the driver.
6. **Separate the spatial operator from the time integrator.** A `substep` method returns the time derivative, and pluggable integrators (RK via a Butcher table, SDC) combine substeps. Pyro uses this to go from 2nd to 4th order by overriding one method at a time. **[Assumption]** This pattern maps well onto a framework where you want to swap time integrators independently of reconstruction and Riemann solvers.
7. **Layered runtime parameters with namespaced keys.** Global, solver and problem defaults, then inputs file, then command line or dictionary, with type inference, a dump of all resolved parameters, unused-parameter warnings, and parameters stored in outputs. This is very good for reproducibility.
8. **Problems as plain modules with a fixed contract** (`PROBLEM_PARAMS`, `init_data`, `finalize`, optional `source_terms`), plus runtime registration for notebook-defined problems.
9. **Regression testing against stored benchmarks**, bit-for-bit by default, and runnable in parallel. This is pyro's safety net when refactoring numerics.
10. **Targeted JIT (numba) only on hot loops** (characteristic tracing, Riemann solvers, artificial viscosity), keeping the orchestration in readable Python.
11. **Script and object APIs side by side.** The command line suits batch runs and tests; the `Pyro` class suits notebooks and step-by-step use.

**Limitations and trade-offs to be aware of**

1. **Reuse through deep inheritance.** For example, `incompressible` inherits from `burgers`, and `compressible_sdc` from `fv4`, from `rk`, from `compressible`. This makes reuse cheap, but behaviour is spread across levels and some overrides are only partial. **[Assumption]** For a framework meant to combine physics modules (hydro + MHD + gravity + cooling), composition (separate equation-set, reconstruction, Riemann and integrator objects) would probably scale better.
2. **No physics-module abstraction.** Each solver is a self-contained package with its own `Variables` class, conversions and Riemann solvers. The shallow-water solver largely mirrors the compressible one instead of sharing code. Adding MHD would mean writing another parallel solver package, not plugging a module into a shared hydro core.
3. **String- and dictionary-based configuration everywhere**, with runtime parameter lookups (`rp.get_param`) deep inside numerical routines. This is flexible, but the dependencies between modules and parameters are implicit.
4. **2D only, single grid, no restart, no parallelism.** Pyro does not try to address scaling.
5. **Limited physics coupling.** Gravity is constant only; there is no self-gravity in the compressible solvers. The reacting solver is a stub.
6. **Documentation drift.** The 2014 paper describes Fortran plus f2py and pickle I/O, both since replaced. The `particles` docs show a constructor signature that differs from current usage in `compressible/simulation.py` [Code observation]. The in-repo `intro.rst` lists a "special relativistic compressible" solver, and there is a `compressible_sr_defaults.inc` docs fragment, but no such solver package exists in your code copy, and the current online docs do not list it either.
