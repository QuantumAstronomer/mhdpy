# Ulula — Synthesis

## Sources and conventions

**Sources used**

- Paper: Diemer (2025), *Ulula: An ultra-lightweight 2D hydrodynamics code for teaching and experimentation*, arXiv:2505.20399 (`Docs/2505.20399v1.pdf`).
- Code: `Code/ulula/` (version 1.0.2, Nov 2025), which contains the `core`, `setups`, `physics`, `utils` and `examples` packages.
- In-repo documentation: `Code/docs/source/*.rst` (Sphinx sources).
- Web: the documentation site at bdiemer.bitbucket.io/ulula, and PyPI (pypi.org/project/ulula). Both match the in-repo docs and add nothing substantive beyond the release history.

**Markers used in this document**

- **[GK]** marks a statement from my general knowledge rather than from your reference material.
- **[Assumption]** marks an interpretation I made that the sources do not state explicitly.
- **[Code observation]** marks something I read in the source code but did not verify by running it.
- Everything without a marker comes from the paper, the docs or the code.

---

## 1. Purpose

Ulula is an **educational and experimentation code**, not a research production code. The paper and docs say so explicitly:

- **Goal.** A finite-volume hydro solver that is short and readable, so a student can identify, swap and modify the classic building blocks: reconstruction, slope limiter, Riemann solver and time integration. These are the parts that production codes bury under parallelisation, adaptive meshes and I/O.
- **Scope.** Compressible Euler equations plus gravity, in 1D and 2D, on a fixed, uniform Cartesian grid. There is no MHD, no 3D, no parallelisation and no mesh refinement. The author deliberately left out MHD and turbulence because most interesting problems there are intrinsically 3D.
- **Size.** The solver framework is under 800 active lines of pure Python plus NumPy. The whole package is about 3000 lines, of which about 1200 are problem setups.
- **Performance target.** "Fast enough for a laptop in class." All array work is vectorised NumPy. The paper measures a fixed cost of about 2×10⁻⁴ s per timestep plus about 4×10⁻⁷ s per cell per step in 2D (half that per cell in 1D). The author concludes that the code is limited by NumPy throughput, not by Python overhead.
- **Positioning.** The paper contrasts Ulula with Pyro: Ulula is *one* framework with interchangeable solver components, whereas Pyro is a collection of separate solvers for different equation sets and is many times larger.

---

## 2. Architecture

### 2.1 The four units

The paper describes Ulula's core as four units. The code confirms this split:

| Unit | Location | Responsibility |
|---|---|---|
| **`HydroScheme`** + **`Simulation`** | `core/simulation.py` | `HydroScheme` is a small configuration object that records the algorithm choices. `Simulation` holds *all* simulation state and *all* numerical routines. |
| **`Setup`** (abstract base) + concrete setups | `core/setup_base.py`, `setups/*.py` | Describes a physical problem: domain, equation of state, gravity, initial conditions, and optional runtime hooks, exact solutions and plot styling. |
| **`run()` driver** | `core/run.py` | Orchestrates a run: creates or restarts a `Simulation`, loops over timesteps, schedules outputs, plots and movies, and monitors conservation. |
| **Plotting/analysis** | `core/plots.py` | Extracts primitive, conserved and derived quantities, converts units, and draws 1D/2D plots. |

Supporting modules:

- `physics/units.py` and `physics/constants.py`: unit tables used only for plotting.
- `utils/utils.py`: version parsing, and a circle–square overlap routine used for radially averaged plots.
- `examples/examples.py`: ready-made run scripts, one per setup.

The structure is essentially **solver object + problem object + driver + post-processing**. The solver is deliberately a single class. Ulula has no separate mesh, equation-of-state, Riemann-solver or boundary-condition classes; these are all methods on `Simulation`.

### 2.2 The `Simulation` class in detail

`Simulation` is internally organised into a few concerns.

**(a) Configuration and the call-order contract**

A set of `set…()` methods configures the run:

- `setHydroScheme`
- `setEquationOfState`
- `setCodeUnits`
- `setGravityMode`
- `setUserUpdateFunction`
- `setUserBoundaryConditions`

All of these must be called *before* `setDomain()`. This is enforced with a `domain_set` flag: once the domain exists, the "fundamental" choices are frozen, because they decide which arrays are allocated.

`setDomain()` also checks that the combination of choices makes sense. HLLC requires the ideal-gas EOS, and the Poisson gravity solver requires periodic boundaries.

**(b) Component selection by function pointers (strategy pattern)**

`setHydroScheme()` translates the string choices into bound methods:

- `self.reconstruction` is set to `reconstructionConst` or `reconstructionLinear`.
- `self.limiter` is set to `limiterNone`, `limiterMinMod`, `limiterVanLeer` or `limiterMC`.
- `self.riemannSolver` is set to `riemannSolverHLL` or `riemannSolverHLLC`.

The time-integration choice (`euler`, `hancock` or `hancock_cons`) is checked here but branched on inside `reconstructionLinear`.

The reconstruction choice also fixes the **number of ghost cells**: one for constant reconstruction, two for linear. Adding a new limiter or Riemann solver therefore means adding a method and a branch in `setHydroScheme`.

The docs stress that Ulula deliberately allows "crazy" combinations, such as no limiter or constant states with a Hancock step, so that students can watch schemes fail.

**(c) Data layout**

- **`V`** holds the primitive variables (density, x-velocity, y-velocity, pressure). When gravity is on, it also holds the gravitational potential and its gradients. **`U`** holds the conserved variables (mass, x-momentum, y-momentum, total energy).
- Both are NumPy arrays shaped `[variable, nx + 2·ghost, ny + 2·ghost]`. In 1D, the y-dimension has length 1 and no ghost cells.
- **Variable indices are not hard-coded.** `setDomain()` builds two dictionaries, `q_prim` and `q_cons`, that map short names (`DN`, `VX`, `VY`, `PR`, `MS`, `MX`, `MY`, `ET`, `GP`, `GX`, `GY`, `GU`) to array rows. Pressure and energy rows exist only for the ideal-gas EOS; for an isothermal gas they are omitted entirely. Gravity rows exist only when gravity is on. Plotting, I/O and setups all use these dictionaries.
- There are three counts of variables:
  - *hydro* variables: those whose fluxes are evolved.
  - *state* variables: hydro variables plus the potential, which is needed in edge states because energy includes potential energy.
  - *all* variables: state variables plus the gradients and the user-added potential.
- Separate arrays `V_im12` and `V_ip12` hold the reconstructed left-edge and right-edge states of each cell.
- **Backup copies** `V_cpy` and `U_cpy` hold the state at the start of a step, so the step can be undone (see the CFL handling below).
- Many index slices are pre-computed once in `setDomain()`: interior, left and right neighbours, and the physical domain without ghosts. This avoids rebuilding them every step.

**(d) Numerical building blocks (each a method)**

- **Conversions and flux:** `primitiveToConserved`, `conservedToPrimitive`, `fluxVector`, `soundSpeed`, and `checkPressure` (which raises an error or applies an optional pressure floor).
- **Reconstruction:** `reconstructionLinear` computes left and right undivided differences, calls the limiter, and builds the edge states. It then optionally applies the Hancock half-step, either in primitive form via `primitiveEvolution` (the linearised Euler equations) or in conservative form.
- **Riemann solvers:** `riemannSolverHLL` and `riemannSolverHLLC`.
- **Timestep size:** `cflCondition` and `maxSpeedInDomain`.
- **Gravity:** `solveGravity` (fixed acceleration, fixed potential or FFT Poisson solve) and `addSourceTerms`.
- **Boundaries:** `enforceBoundaryConditions` (periodic, outflow or wall, corners included). It is applied to both `V` and `U`.
- **I/O:** `save()` and the module-level function `load()`.

**(e) The timestep method — how the pieces connect**

`timestep(dt)` is the heart of the code. One call does the following:

1. Back up `V` and `U`.
2. If no `dt` was given, compute it from the CFL condition.
3. Choose the sweep order. In 2D, Ulula uses two directional sweeps whose order alternates every step (xy, then yx, then xy, …). This is Strang-type dimensional splitting. In 1D there is a single sweep.
4. If source terms (gravity) are active, apply **half** of the source term, convert to primitives, and fill the ghost cells.
5. For each sweep direction:
   - Before the *second* sweep, recompute the maximum signal speed. If the effective CFL number now exceeds `cfl_max` (because the first sweep changed the flow), restore the backup, shrink `dt` by a factor, and restart. After `cfl_max_attempts` failures the run aborts.
   - **Reconstruct** the edge states, including the Hancock half-step if chosen.
   - **Riemann-solve** each interface, using the right-edge state of the left cell and the left-edge state of the right cell.
   - **Update** `U` by differencing the interface fluxes.
   - After the last sweep, apply the **second half** of the source term.
   - Convert `U` to `V`, then **fill the ghost cells**. This happens after *every* sweep, so the second sweep sees up-to-date boundaries.
6. Advance the time and step counter, and record the last sweep direction.

**(f) Runtime hooks**

Two optional callbacks are called inside `enforceBoundaryConditions`:

- A **user update function**, called *before* the standard boundary conditions. It can modify the domain, for example to inject a sound wave.
- A **user boundary-condition function**, called *after* the standard boundary conditions. It can overwrite ghost cells, for example to drive an inflow.

The code trusts these callbacks to keep `V` and `U` consistent.

### 2.3 The `Setup` abstraction

A problem is a subclass of the abstract `Setup`.

**Required overrides**

- `shortName()`: a name used in file names.
- `setInitialConditions(sim, nx)`: the setup calls `sim.setDomain(...)` (and, if needed, `setEquationOfState` and `setGravityMode`), then fills `sim.V` in primitive variables. So **the setup owns the physics configuration (EOS, gravity, boundaries, domain shape)**, while **the driver owns the algorithm configuration (`HydroScheme`)**.

**Optional overrides**

- `trueSolution()`: an analytic solution, overlaid in 1D plots.
- `plotLimits()` and `plotColorMaps()`: plot styling.
- `updateFunction()` and `setBoundaryConditions()`: the runtime hooks above.

**The wrapper `initialConditions()`** standardises everything around the user code:

1. Set the code units.
2. Call the user's `setInitialConditions`.
3. Validate that density and pressure are positive.
4. Register the hooks.
5. Initialise the gravitational potential.
6. Convert primitives to conserved variables.
7. Fill the ghost cells.

**[Code observation]** The base class detects whether a hook was overridden by calling it with `None`. The base implementation returns `False`, and overrides must not.

There are 15 pre-built setups:

- 1D: advection, sound wave, Sod shock tube, free fall, atmosphere, Jeans instability.
- 2D: advection, Kelvin–Helmholtz, Rayleigh–Taylor, cloud crushing, Sedov–Taylor, Gresho vortex, tidal disruption, Keplerian disk, merger.

These double as the test suite. Several provide exact solutions, and the paper uses them for convergence tests.

### 2.4 The `run()` driver

`run(setup, hydro_scheme, nx, tmax, …)` does the following:

- **Creation or restart.** It either builds a new `Simulation` (setting the hydro scheme, then calling `setup.initialConditions`) or loads one from an HDF5 restart file.
- **Main loop.** Each iteration computes `dt` from the CFL condition. It aborts if `dt` collapses below 10⁻¹⁰.
- **Output scheduling.** Outputs, plots and movie frames can each be triggered by step count or by simulation time. Exact output times are hit **without perturbing the main run**: if an output time falls inside the next step, the driver copies the `Simulation` object, advances the copy exactly to the output time, writes or plots it, and discards it. The main simulation keeps its natural CFL step sequence.
- **Conservation monitoring.** It tracks total mass, energy and momentum, but only those the boundary conditions should conserve. Periodic boundaries conserve everything, wall boundaries conserve mass and energy, and outflow boundaries conserve nothing. Gravity also breaks strict conservation.
- **Movies.** Frames are assembled with ffmpeg (mp4) or Pillow (gif).
- **Plot keyword routing.** Plotting keywords are passed through to `plot1d` or `plot2d` by inspecting their function signatures.

**[Code observation]** In the time-based plotting branch, `doPlotting` is passed the main `sim` rather than the advanced copy `sim_copy`. The file name uses the copy's time, but the plotted state may be the one at the start of that step. This looks like a minor bug.

### 2.5 Units, I/O and plotting

- **Units.** The solver is unit-free ("code units"). Length, time and mass scales can be attached, but the solver never uses them; they only affect plot labels and conversions. Gravity constants (g, G) are given in code units.
- **I/O.** HDF5 files with groups for code version, hydro scheme, EOS, units, gravity, domain, run state and grid. The grid group stores primitives only, without ghosts. Every snapshot is also a restart file. User callback functions cannot be serialised, so they must be passed in again when loading.
- **Plotting.** A central `fields` dictionary defines everything plottable, including derived quantities: total, radial and azimuthal velocity, internal energy, and temperature in kelvin. `getQuantities()` does extraction plus unit conversion and is usable on its own for analysis. `plot1d` supports a line cut or a radial average; the radial average uses exact circle–square overlap weights. `plot2d` draws colour maps.

### 2.6 Dependencies

The declared dependencies are NumPy, SciPy, matplotlib and h5py. ffmpeg and Pillow are optional, for movies.

**[Code observation]** `setup_base.py` imports `six`, which is not declared in `pyproject.toml`.

---

## 3. Numerics overview

| Component | Options in Ulula | Notes from the paper/docs |
|---|---|---|
| Discretisation | Finite-volume Godunov scheme on a uniform Cartesian grid with square cells | Conserved quantities change only through interface fluxes plus source terms. |
| Multi-D strategy | **Dimensionally split** (x and y sweeps, order alternated each step) | Chosen for simplicity: each sweep is a 1D problem, and the same code runs in both directions by swapping velocity components. The paper notes that unsplit schemes treat directions symmetrically but are more complex. |
| Reconstruction | Piecewise-constant (1st order) or piecewise-linear (2nd order) in **primitive** variables | Reconstructing primitives makes it easy to avoid negative density or pressure at edges. |
| Slope limiters | None, MinMod (most diffusive), van Leer (intermediate), MC (sharpest, least stable) | Limiters set the slope to zero at extrema. The best choice depends on the problem: MC is sharpest on advection but can cause artefacts in shock tubes. |
| Time integration | "Euler" (1st order), Hancock in primitive form (default), Hancock in conservative form | Hancock advances the edge states by half a step before the Riemann solve. Combined with linear reconstruction this is the **MUSCL-Hancock** scheme. The primitive variant applies the linearised Euler equations to the limited slope; the paper reports the same results as the conservative variant but faster. Runge-Kutta is mentioned as an alternative that was not chosen because it needs more Riemann solves. |
| Riemann solvers | HLL; HLLC (ideal gas only) | Wave-speed estimates are simply left velocity minus left sound speed and right velocity plus right sound speed. The contact speed in HLLC follows Toro (2009). HLLC handles contact discontinuities much better, as shown in the paper's advection test. |
| Timestep | CFL condition with the maximum over the grid of \|velocity component\| + sound speed; default CFL 0.8 | A second sweep may tolerate up to `cfl_max` (default 0.95); beyond that the step is redone with a smaller `dt`. |
| Source terms | Gravity, applied as two half-steps around the hydro sweeps | This keeps 2nd-order accuracy. Total energy *includes* potential energy, so the potential is part of the flux of energy. With Poisson gravity, the energy is corrected for the change in potential each step. |
| Gravity | Fixed acceleration; fixed user potential (gradients taken once); FFT Poisson solve (periodic only); FFT Poisson + fixed potential | The FFT Green's function matches the standard 5-point discrete Laplacian. The zero-frequency (mean-density) mode is handled specially. |
| EOS | Ideal gas (adjustable γ); isothermal (pressure and energy not evolved) | Implemented as branches on a `track_pressure` flag, not as a separate EOS object. |
| Boundaries | Periodic, outflow (zero-gradient), wall (reflecting, normal velocity flipped), plus user callbacks | Applied after every sweep. |
| Robustness | Optional pressure floor; otherwise an exception on non-positive pressure; exception if the sound speed becomes NaN | — |

The paper measures convergence slightly shallower than 2nd order on 1D advection, free fall and the Gresho vortex. It reports that conservation holds to machine precision without gravity and with periodic boundaries.

---

## 4. Notable design choices

**Worth borrowing for your own framework**

1. **A clean split of responsibility between problem, algorithm and driver.** The `Setup` decides the physics and initial conditions, `HydroScheme` decides the numerics, `Simulation` executes, and `run()` orchestrates. The same problem can be run with any scheme, and the same scheme on any problem. This is the most transferable idea in Ulula.
2. **Configuration first, then allocation.** Options are frozen by `setDomain()`, which then allocates exactly the arrays the configuration needs and validates incompatible combinations up front.
3. **Name-indexed state vectors.** Variables are indexed by name (dictionaries mapping names to rows) rather than by global constants. The variable set can then change with the physics (isothermal vs adiabatic, gravity on or off) without touching the solver, plotting or I/O code.
4. **Keeping both primitive and conserved arrays live**, with conversions at well-defined points. This makes analysis and plotting trivial and keeps reconstruction in primitive variables.
5. **A transactional timestep.** The state is backed up at the start of a step, so a step can be rolled back and retried with a smaller `dt`. This is a simple, general robustness mechanism.
6. **Exact-time output without disturbing the run.** The driver advances a *copy* of the simulation to the output time. The main simulation's step sequence is unchanged, so results don't depend on how often you output.
7. **Snapshots that are also restart files**, carrying the full configuration plus a version check.
8. **Built-in diagnostics.** Conservation is checked automatically, aware of which quantities the boundary conditions should conserve. Every test setup can supply an exact solution for plots.
9. **Vectorised NumPy with pre-computed slices**, which is enough for 2D teaching-scale problems. The overhead per step is negligible relative to the per-cell cost.

**Limitations and trade-offs to be aware of**

1. **A monolithic `Simulation` class.** The solver, EOS, gravity, boundaries and I/O are all methods on one class, and components are selected by string comparisons plus `if` branches. This is fine at about 800 lines. **[Assumption]** It would not scale to MHD, extra physics or multiple reconstruction families without becoming hard to maintain. The author's own list of extensions (more Riemann solvers, PPM, curvilinear geometry, viscosity, cooling) would each add more branches.
2. **Hard-wired equations.** The Euler equations are spread across `fluxVector`, `primitiveEvolution`, the conversion routines and the HLLC solver. No single "equation system" object could be swapped for MHD.
3. **The dimensionally split update is baked into `timestep()`.** **[GK]** The constrained-transport MHD schemes used by codes such as Athena need an unsplit integrator with face-centred magnetic fields, which this design does not support. The paper itself suggests that an MHD extension would use cell-centred divergence cleaning (Dedner et al. 2002) instead.
4. **A uniform Cartesian grid only.** There is no mesh abstraction (geometry, cell volumes, face areas), so curvilinear coordinates or refinement would mean restructuring.
5. **No parallelism.** The author suggests jax or numba for threading and considers MPI too complex for the code's goals.
6. **Mixed responsibilities in `run()`.** The driver handles stepping, plotting, movies, I/O and conservation checks in one long function. For a bigger framework you would likely split these into an event or output scheduler. **[Assumption]**

---

## 5. Gaps in the reference material

- The paper and docs say little about *why* particular defaults were chosen (CFL 0.8, MC limiter, HLLC). These choices appear only in the code.
- There is no automated test suite in the repository. Validation relies on the example setups and the paper's convergence plots.
