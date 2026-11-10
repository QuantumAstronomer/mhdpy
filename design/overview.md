# Overview of mhdpy

mhdpy is a framework in Python for simulations of astrophysical gases, in hydrodynamics and [MHD](#mhd), from standard tests to runs of the size of published studies ([§1](#1-goals)). This overview sets out what it is for, how its code is cut into five strata and how a step of a run passes through them, what the strata share, and the decision [briefs](#brief) that build each stratum, in the order in which they are taken. It serves newcomers and the author at work alike, and changes as the briefs decide.

**Where the work stands.** B1 and B2, the first two briefs of stratum 1, on the strata in the package and on the route of the kernels, are decided. The next is the third, on execution in parallel ([§6.1](#61-infrastructure)).

## 1. Goals

This part sets out what mhdpy is for. The ranking by which the briefs resolve conflicts between its goals stays in §1 of [CLAUDE.md](../CLAUDE.md), as every brief applies it.

### 1.1 Goals

mhdpy is a framework for astrophysical (magneto)hydrodynamical simulations in Python. It is a hobby project, by an author who used Athena, then a state-of-the-art MHD code, for a bachelor thesis. It serves educational and scientific work, from standard verification problems to production-scale runs of the size used in published studies. These aims can conflict, so §1 of CLAUDE.md ranks them.

The main goal is **learning**. This means learning to write scientifically applicable code, whose physics is demonstrably correct and extensible. It also means learning to build a large, multi-layered software project robustly, in a form that others can pick up easily.

The second goal is **production-scale runs**. The project grew out of earlier work with production-grade MHD software, on simulations of the scale of [Armillotta, Fraternali and Marinacci (2016)](https://ui.adsabs.harvard.edu/abs/2016MNRAS.462.4157A/abstract). Those follow Galactic fountain clouds that lead to coronal condensation, which feeds star formation, on a grid with cells of 2 pc, without [mesh refinement](#mesh-refinement).

### 1.2 Scope

The eventual scope is every physics module that state-of-the-art (magneto)hydrodynamics codes such as Athena++ implement, with a focus on astrophysics. It ranges from compressible hydrodynamics with general [equations of state](#equation-of-state) to Lagrangian particles for dust. This whole scope shapes the architecture from the start, also for parts that are built much later. The lower layers must accommodate those parts without significant redesign.

### 1.3 Success criteria

Success is judged by four criteria, each stated so that it can be checked rather than asserted. Learning is deliberately not among them. It is no property of the finished code, and is served by the way mhdpy is developed instead (§2 of CLAUDE.md).

**Correctness.** No physics module is complete before it is verified against problems with known solutions. For smooth problems, the measured [order of convergence](#order-of-convergence) matches the formal order of the scheme. For problems with discontinuities, results are compared with exact or reference solutions. Conserved quantities are conserved to round-off wherever the boundary conditions permit. The test problems are those of the suites of state-of-the-art reference codes, and a capability counts as implemented once its reference tests are reproduced.

**Production capability.** mhdpy completes a research-scale run like those of Armillotta et al. (2016) on the development machine and on a small multi-core server, within a time still to be set. Such a run is two-dimensional, with hydrodynamics, radiative cooling, thermal conduction and a [passive scalar](#passive-scalar) for the metallicity. The cost of a run is set roughly by its total number of [cell updates](#cell-update). The rate of cell updates per second is therefore the measure tracked during development.

**Extensibility.** New physics modules, such as another [cooling function](#cooling-function) or a new [Riemann solver](#riemann-solver), are added without changes to the framework. Every module beyond the hydrodynamics core tests this criterion, since it plugs in through the same interfaces.

**Usability.** mhdpy installs on macOS and Linux with a single `pip` or `uv` command. A newcomer then runs a standard test problem within minutes by following the documentation.

## 2. Context of a run

A user brings a problem: its initial state, its domain and boundaries, the physics that it switches on, and its parameters, written as a [problem setup](#problem-setup) in Python. A run builds the grid and the state, advances them from the initial time to the final one, and writes [snapshots](#snapshot), a [history](#history) and [restarts](#restart), which the user analyses and plots in Python. mhdpy installs by one command on macOS and Linux, and runs on the machines of [§1.3](#13-success-criteria), a laptop and a small server with several cores. The production runs, of a cloud that crosses a hot corona, need beyond their parameters only the tables of a cooling function.

## 3. Layers

![The five strata of mhdpy, with the components of the first pass in red and the extensions in grey](overview/layers.svg)

mhdpy is cut into five strata by the kind of code that each holds, after the layers pattern of [Buschmann et al.](#buschmann-et-al-1996) (1996). Each stratum rests on those below it and is finished before the next is begun, with its briefs, then its [requirements](#requirement), then its code, as §2.3 of [CLAUDE.md](../CLAUDE.md) asks. In the package, each stratum is one subpackage, from `mhdpy.infrastructure` through `mhdpy.mesh`, `mhdpy.core` and `mhdpy.physics` to `mhdpy.driver`, which imports only the strata below it, reaches code above only through objects handed down to it, and holds no cycle among its modules ([B1D1](briefs/B01-strata-in-package.md#b1d1-the-subpackages-of-the-strata), [B1D2](briefs/B01-strata-in-package.md#b1d2-the-rule-between-the-strata), [B1D3](briefs/B01-strata-in-package.md#b1d3-the-rule-within-a-stratum)). The tests of each stratum lie in its folder of `tests/` under the same rule, which Import Linter checks with every run of the tests ([B1D4](briefs/B01-strata-in-package.md#b1d4-the-place-of-the-tests), [B1D5](briefs/B01-strata-in-package.md#b1d5-the-check-of-the-rule)). A first pass builds the five strata for the production run of [§1.3](#13-success-criteria), hydrodynamics with radiative cooling, thermal conduction and a passive scalar, and provides for the rest of the scope where this costs little. Every other module of the scope of [§1.2](#12-scope) enters later, as an extension of the stratum of its kind of code, MHD first. No problem runs before the driver of stratum 5 exists, so that the lower strata are checked by tests of their own, the numerical core also by a small loop in its tests that steps problems with known solutions.
### 3.1 Infrastructure

The code that every stratum runs on and that knows nothing of grids or physics: the package and its installation ([topic 35](topics/35-packaging-configuration-and-build.md)), runtime parameters and units ([topic 37, §2.5](topics/37-driver-and-control-of-time-step.md#25-runtime-parameters-and-units)), the route of the [kernels](#kernel) ([topic 41](topics/41-vectorised-and-compiled-kernels.md)), execution in parallel and the measure of cell updates ([topic 42](topics/42-parallelisation-and-performance.md)), and the tools of testing ([topic 28](topics/28-verification-and-testing.md)).

To the strata above, it provides the route in which they write their loops over cells, as modules of Python that Cython compiles, each checked in its tests against an independent version [vectorised](#vectorisation) in NumPy, with benchmarks that track the rate of cell updates commit by commit ([B2D1](briefs/B02-kernels.md#b2d1-vectorised-or-compiled) to [B2D4](briefs/B02-kernels.md#b2d4-the-benchmark)), and an execution in parallel, by threads or by processes, which the layout of the data in stratum 2 and the driver of stratum 5 serve. Every module declares its parameters with their defaults, which the driver reads and records, and finds the physical units and constants that cooling and conduction need. The tests of every stratum use its norms, orders of convergence, checks of conservation and [regression tests](#regression-test), and its check lists the requirements that no test cites. For the extensions it leaves room for communication across the whole grid, which the deposition of particles and the Fourier transforms of self-gravity and driven turbulence need.

It is closed by tests of its own, since tools of verification need tests as much as the code that they check ([topic 28, §4](topics/28-verification-and-testing.md#4-assessment)): parameters with defaults, overrides and unknown names, units against their constants, the tools of testing on sequences of known order, and the installation by one command on clean macOS and Linux, the latter in Docker.

### 3.2 Mesh and data

The code that holds the state on the grid: coordinates with a geometry kept general ([topic 3](topics/03-grids-and-finite-volume-discretisation.md)), the arrays of the state with room for the face fields of MHD ([topic 36](topics/36-data-structures.md)), and [ghost cells](#ghost-cell) with the standard boundaries and their exchange between [blocks](#block) ([topic 4](topics/04-boundary-conditions-and-ghost-cells.md)). Extensions: curvilinear coordinates ([topic 12](topics/12-curvilinear-coordinates.md)) and mesh refinement ([topic 40](topics/40-mesh-refinement.md)).

To the numerical core, it provides the [cell averages](#cell-average) of the [conserved and primitive variables](#conserved-and-primitive-variables), each variable named and indexed once for every stratum, any number of passive scalars among them, the fluxes on the faces, and as many ghost cells as the widest [stencil](#stencil) needs, three for parabolic [reconstruction](#reconstruction). Its layout serves the kernels of stratum 1, and its blocks, if the briefs choose them, the execution in parallel. The grid keeps its areas, lengths and volumes general, so that curvilinear coordinates enter later without redesign, and the arrays leave room for the [face-centred fields](#face-centred-field) and the electric fields on the edges that [constrained transport](#constrained-transport) needs. The periodic, outflow and reflecting conditions are its own, while the strata above add conditions of theirs, the [characteristic](#characteristics) conditions of stratum 3 and those of a problem setup. For the extensions it leaves room for blocks of a tree, which refinement needs, and for boundaries across the pole and shifted by the shear.

It is closed by tests of its own: areas and volumes that sum to those of the domain, ghost cells that each standard condition fills as its symmetry demands, and a domain split into blocks that fills them as one block would.

### 3.3 Numerical core

The code that advances the equations of the gas: its variables ([topic 1](topics/01-equations-and-their-variables.md)), equations of state ([topic 2](topics/02-equations-of-state.md)), reconstruction ([topic 6](topics/06-reconstruction-and-limiting.md)), Riemann solvers ([topic 7](topics/07-riemann-solvers.md)), the [integrator](#integrator) ([topic 8](topics/08-time-integration.md)), [source terms](#source-term) ([topic 13](topics/13-source-terms.md)), the coupling of processes within a step ([topic 18](topics/18-operator-splitting-and-coupling-of-processes.md)), the passive scalar, whose flux is the mass flux of the gas ([topic 21](topics/21-passive-scalars.md)), and open boundaries ([topic 5](topics/05-non-reflecting-boundaries.md)). Extensions: MHD with constrained transport ([topic 11](topics/11-constrained-transport.md)) first, then general equations of state ([topic 2, §2.3](topics/02-equations-of-state.md#23-the-general-equation-of-state)), methods of higher order ([topic 9](topics/09-methods-of-higher-order.md)), artificial viscosity ([topic 10](topics/10-artificial-viscosity.md)) and relativistic MHD ([topic 25](topics/25-relativistic-mhd.md)).

In each step of its integrator, taken in one stage or in several, the core turns the conserved variables into primitive ones through the equation of state, reconstructs them on the faces, lets a Riemann solver compute the fluxes, and updates the cell averages with the fluxes and the source terms. To the physics above, it provides a registration by which a new process adds its source terms without changes to the core, the places in the step where diffusive fluxes and [stiff sources](#stiff-source) enter, and the temperature and metallicity that conduction and cooling read. To the driver, it provides the step that the [Courant condition](#courant-condition) allows, and to problem setups the conversion of their initial states. The boundaries through which waves leave the domain, which the production runs need on every side, are its own, since they rest on the waves of the equations. For the extensions, its briefs choose an integrator that serves constrained transport, keep the Riemann solvers behind one interface, which the solvers of MHD join as [§1.3](#13-success-criteria) asks of a new solver, and leave the conversion of variables open to the iterative inversion of relativistic MHD.

It is closed by tests of its own: each Riemann solver against the exact solution, each reconstruction by its order on smooth profiles, and a small loop in its tests that steps Sod's [shock tube](#shock-tube) against its exact solution and a [linear wave](#linear-wave), which must converge at second order and conserve mass, momentum and energy to round-off on a periodic domain.

### 3.4 Physics

The modules that add processes to the flow: diffusion ([topic 16](topics/16-diffusion.md)) and thermal conduction ([topic 17](topics/17-thermal-conduction.md)), and radiative cooling ([topic 20](topics/20-radiative-cooling.md)) with the integration of local, stiff sources ([topic 19](topics/19-reactions-chemistry-and-cooling.md)). Extensions: further diffusion ([topic 16, §2.4](topics/16-diffusion.md#24-physical-diffusion-in-mhd)), gravity of a fixed potential and rotating frames ([topic 13, §2.2](topics/13-source-terms.md#22-gravity)), elliptic solvers and self-gravity ([topic 14](topics/14-elliptic-solvers.md), [topic 15](topics/15-self-gravity.md)), particles ([topic 22](topics/22-particles.md)), driven turbulence ([topic 27](topics/27-driving-of-turbulence.md)), the shearing box ([topic 24](topics/24-shearing-box-and-orbital-advection.md)), radiation ([topic 23](topics/23-radiation-transport.md)), cosmic rays ([topic 26](topics/26-cosmic-rays.md)) and chemical networks.

Thermal conduction carries heat down the gradient of temperature, at a rate that rises steeply with the temperature and [saturates](#saturation) where the gradient grows too steep for the electrons to follow, so that in a hot corona it can outpace the flow by far. It therefore enters the step by [super time-stepping](#super-time-stepping), by semi-implicit sweeps or implicitly, as its brief decides. Radiative cooling removes energy at a rate that a cooling function of temperature and metallicity sets, often faster than the flow changes, and is integrated over each step as a stiff source, exactly or in substeps. To the driver, the stratum provides the limits that both put on the step and the quantities of cooling and mixing that the problems record, and to problem setups the parameters of the table, the conductivity and its saturation. For the extensions it keeps the diffusive fluxes general enough for conduction along the field once MHD enters, and for viscosity and resistivity, and leaves the integration of stiff sources open to chemical networks.

It is closed by tests of its own, each stepped through a small loop in its tests, as the numerical core is: a Gaussian that diffuses against its analytic profile at the order of its integration ([topic 16, §3](topics/16-diffusion.md#3-tests)), a plane conduction front against the self-similar solution of Reale ([topic 17, §3](topics/17-thermal-conduction.md#3-tests)), and a single cell that cools against the exact solution for its cooling function ([topic 20, §3](topics/20-radiative-cooling.md#3-tests)).

### 3.5 Driver and problems

The code that turns the solver into a run: the main loop and the control of its step ([topic 37](topics/37-driver-and-control-of-time-step.md)), problem setups and user functions ([topic 38](topics/38-problem-setups-and-user-functions.md)), outputs, restarts and analysis ([topic 39](topics/39-output-restarts-and-analysis.md)), and the problems that verify the whole scheme ([topic 29](topics/29-advection-and-linear-waves.md) to [topic 34](topics/34-cold-clouds-and-mixing-layers.md)).

The driver reads the parameters, lets a problem setup build the initial state, and takes steps until the run ends, each as long as the Courant condition and the limits of cooling and conduction allow. A problem supplies what the framework cannot know, its initial state, its boundaries and its parameters, and reaches into the run through [hooks](#hook) for boundaries, sources and diagnostics. The run writes snapshots for analysis, a history of totals by which conservation is checked, and restarts from which it continues as if it had never stopped, with every parameter in use recorded. As the top stratum, it provides to no stratum above, but its loop, hooks and outputs must take in every extension without change to the framework: the outputs and restart state of a new module, its limits of the step and its problems.

It closes the first pass. The problems of the whole scheme replace the small loops of strata 3 and 4, and must meet their known solutions and reference results, from the oblique linear waves and Sod's shock tube to the blast waves, the shocked cloud ([topic 34, §2.1](topics/34-cold-clouds-and-mixing-layers.md#21-the-shockcloud-problem)) and the fountain cloud of 2016, the reference of the production runs ([topic 34, §2.6](topics/34-cold-clouds-and-mixing-layers.md#26-fountain-clouds-through-a-corona)). A restart that reproduces an uninterrupted run bit for bit, and the rate of cell updates of the production problem, measured on the development machine, complete it.

## 4. One time step

A step of the production run, a cloud that crosses a hot corona in two dimensions with cooling, conduction and the scalar of its metallicity, passes through the strata as follows. Each choice of method is left to the brief that part 6 names.

1. The driver (stratum 5) chooses the step, the shortest of those that the Courant condition (stratum 3) and the limits of cooling and conduction (stratum 4) allow.
2. The ghost cells (stratum 2) are filled on every side by the open boundaries of stratum 3, which let waves leave the domain, and between blocks, if there are blocks, by exchange.
3. The core (stratum 3) turns the conserved variables into primitive ones through the equation of state, reconstructs them on the faces, computes the fluxes by the Riemann solver, carries the scalar with the mass flux, and updates the cell averages with the fluxes and the registered sources, once or in several stages, as its integrator demands.
4. Conduction (stratum 4) moves heat down the gradient of temperature, saturated where the gradient is steep, by super steps, sweeps or an implicit solve, as its brief chooses.
5. Cooling (stratum 4) removes energy from each cell, integrated over the step as a stiff source at the metallicity that the scalar carries.
6. The driver (stratum 5) advances the time, adds the totals of the step to the history, and writes snapshots and restarts when they are due.

The hooks of the problem act at the points of the step where the driver calls them. Whether steps 4 and 5 act within step 3 or after it, and in which order, is the choice of the brief on the coupling of processes ([§6.3](#63-numerical-core)).

## 5. Crosscutting concepts

Some conventions bind every stratum, although no stratum holds them. Each is settled once, by the brief named, in the stratum whose code first depends on it.

- **Kernels.** Every loop over cells, in strata 2 to 4, is a module of Python that Cython compiles in its pure mode, with the signatures of its functions in a file `.pxd` beside it, while copies of whole arrays stay in NumPy. Its tests compare it with an independent version in NumPy, written first as the prototype of its algorithm, and benchmarks of asv track its rate commit by commit ([topic 41](topics/41-vectorised-and-compiled-kernels.md), [B2](briefs/B02-kernels.md)).
- **Parallel execution.** Threads or processes share the work of a step as the brief on execution in parallel chooses, over the blocks that the brief on the domain decides ([topic 42](topics/42-parallelisation-and-performance.md), [§6.1](#61-infrastructure), [§6.2](#62-mesh-and-data)).
- **Parameters and units.** Every module declares its parameters with their defaults and works in the units and constants that the brief on runtime parameters and units fixes, so that cooling and conduction see physical values ([topic 37, §2.5](topics/37-driver-and-control-of-time-step.md#25-runtime-parameters-and-units), [§6.1](#61-infrastructure)).
- **Testing.** Every test names the requirements that it checks, and measures errors, orders and conservation with the tools that the brief on testing and verification settles ([topic 28](topics/28-verification-and-testing.md), [§6.1](#61-infrastructure)).
- **Names of variables.** Every variable has one name and one index for every stratum, which the brief on the arrays of the state fixes ([topic 36](topics/36-data-structures.md), [§6.2](#62-mesh-and-data)).
- **Unphysical states.** What happens where a density or a pressure would turn negative, a [floor](#floor), an error or a record, is settled once by the brief on equations of state, for the scalar as well ([topic 2, §2.2](topics/02-equations-of-state.md#22-the-internal-energy-and-floors), [§6.3](#63-numerical-core)).
- **Extension.** A new module joins at the points that the strata offer, boundaries in stratum 2, sources in stratum 3 and hooks in stratum 5, each settled by the brief on that point, so that it needs no change to the framework, as [§1.3](#13-success-criteria) asks ([topic 13](topics/13-source-terms.md), [topic 38](topics/38-problem-setups-and-user-functions.md)).
- **Reproducibility.** A run records the version of mhdpy, its parameters and its seeds, and restarts exactly, as the briefs on the package, on parameters and on outputs settle ([topic 39](topics/39-output-restarts-and-analysis.md), [§6.1](#61-infrastructure), [§6.5](#65-driver-and-problems)).

## 6. Briefs

Briefs are opened stratum by stratum, from infrastructure upwards, those of the first pass before the extensions. A brief is opened in the lowest stratum whose code its decision shapes, even where most of its code lies higher: the coupling of processes within a step is decided with the integrator of stratum 3, although the driver of stratum 5 runs it.

Each stratum has a table of the briefs of its first pass in the order in which they are opened and, where it has extensions, a second table of their briefs in a provisional order. A brief not yet opened has no identifier, since it receives one only when it is opened, and its subject names the questions that it settles. The status reads Not begun, Open, or Decided with its date, as in the head of the brief, and names the brief that supersedes it, where a later one does. The last column names what a decided brief changed in the overview, with a link to the sub-decision. A line on the requirements and code of the stratum follows its table, and names each requirement document with its status, Draft or Agreed with its date, as in its head.

### 6.1 Infrastructure

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| [B1](briefs/B01-strata-in-package.md) | The strata in the package: their subpackages, the rule of use between and within them, the place of the tests, and how the rule is checked | [35, §2.1](topics/35-packaging-configuration-and-build.md#21-python-packages) | Decided on 2026-11-09 | §3 names the subpackages of the strata, their rule of use and its check ([B1D1](briefs/B01-strata-in-package.md#b1d1-the-subpackages-of-the-strata) to [B1D5](briefs/B01-strata-in-package.md#b1d5-the-check-of-the-rule)) |
| [B2](briefs/B02-kernels.md) | The route of the kernels: vectorised or compiled, the compiler, a simple version to check a fast one, and the benchmark by which the rate of cell updates is tracked | [41](topics/41-vectorised-and-compiled-kernels.md), [36, §2.5](topics/36-data-structures.md#25-layouts-for-kernels) | Decided on 2026-11-10 | §3.1 and §5 name the kernels compiled by Cython, their references in NumPy and their benchmarks ([B2D1](briefs/B02-kernels.md#b2d1-vectorised-or-compiled) to [B2D4](briefs/B02-kernels.md#b2d4-the-benchmark)) |
| — | Execution in parallel: threads in the [free-threaded build](#free-threaded-build) or processes with [MPI](#mpi), and whether it enters the first pass | [42](topics/42-parallelisation-and-performance.md) | Not begun | |
| — | The package and its installation: the build backend, the versions of Python, the dependencies, the licence and the releases | [35](topics/35-packaging-configuration-and-build.md) | Not begun | |
| — | Runtime parameters and units: their format, declaration and record, and the system of units with its constants | [37, §2.5](topics/37-driver-and-control-of-time-step.md#25-runtime-parameters-and-units) | Not begun | |
| — | Testing and verification: the norms and variables of orders, conservation, the tolerance of regression tests, and the check of requirements | [28](topics/28-verification-and-testing.md) | Not begun | |

Requirements and code: not begun.

### 6.2 Mesh and data

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| — | The arrays of the state: the order of their axes, the naming and indexing of variables, and the storage of face fields beside cell averages | [36](topics/36-data-structures.md) | Not begun | |
| — | The domain in blocks: one block or many, their size, and room for the tree that refinement needs | [36, §2.4](topics/36-data-structures.md#24-blocks-of-a-tree), [40](topics/40-mesh-refinement.md), [42, §2.4](topics/42-parallelisation-and-performance.md#24-parallel-execution) | Not begun | |
| — | The grid and its geometry: uniform or nonuniform spacing, and areas, lengths and volumes kept general | [3](topics/03-grids-and-finite-volume-discretisation.md), [12, §2.2](topics/12-curvilinear-coordinates.md#22-finite-volumes-and-geometric-source-terms) | Not begun | |
| — | Ghost cells and boundaries: their number, the standard conditions, how the strata above add conditions, and the exchange between blocks | [4](topics/04-boundary-conditions-and-ghost-cells.md) | Not begun | |

Extensions, in a provisional order:

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| — | Curvilinear coordinates: cylindrical and spherical grids, with boundaries across the pole | [12](topics/12-curvilinear-coordinates.md), [4, §2.6](topics/04-boundary-conditions-and-ghost-cells.md#26-boundaries-between-blocks-and-across-poles) | Not begun | |
| — | Mesh refinement: restriction, prolongation, the correction of fluxes, and the criteria of refining | [40](topics/40-mesh-refinement.md) | Not begun | |

Requirements and code: not begun.

### 6.3 Numerical core

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| — | The equations and their variables: the energy equation, total, internal or both, and whether the adiabatic and isothermal gas share one path | [1](topics/01-equations-and-their-variables.md) | Not begun | |
| — | Equations of state: the ideal and the isothermal gas, the interface of a general one, and the floors with their record | [2](topics/02-equations-of-state.md) | Not begun | |
| — | The integrator: a single step or the method of lines, one that serves constrained transport, and the Courant number | [8](topics/08-time-integration.md) | Not begun | |
| — | The coupling of processes: the flow, conduction, cooling and the scalar within a step, [split](#operator-splitting) or in the stages | [18](topics/18-operator-splitting-and-coupling-of-processes.md) | Not begun | |
| — | Source terms: their registration and their centring in time | [13, §2.1](topics/13-source-terms.md#21-centring-in-time) | Not begun | |
| — | Reconstruction and limiting: linear or parabolic profiles, the [limiter](#limiter) for contacts and mixing layers, and primitive or characteristic variables | [6](topics/06-reconstruction-and-limiting.md) | Not begun | |
| — | Riemann solvers: HLLE, HLLC or Roe's, their fallback, and corrections for slow flows | [7](topics/07-riemann-solvers.md) | Not begun | |
| — | The passive scalar: its reconstruction, its floor, and the metallicity that cooling reads | [21](topics/21-passive-scalars.md) | Not begun | |
| — | Open boundaries: the condition of each side, the target state and its relaxation, the corners, and whether the frame follows the cloud | [5](topics/05-non-reflecting-boundaries.md) | Not begun | |

Extensions, in a provisional order:

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| — | MHD: constrained transport, the electric fields at the corners, the solvers of MHD, and the tests of topics 30 and 33 | [11](topics/11-constrained-transport.md), [7, §2.5](topics/07-riemann-solvers.md#25-hlld), [33](topics/33-multidimensional-and-astrophysical-mhd.md) | Not begun | |
| — | General equations of state: tables and their interpolation, the inversion of an analytic one, and the estimates of wave speeds that the Riemann solvers need | [2, §2.3](topics/02-equations-of-state.md#23-the-general-equation-of-state), [§2.4](topics/02-equations-of-state.md#24-tables-and-the-inversion-of-an-equation-of-state) | Not begun | |
| — | Methods of higher order: finite volumes of fourth order and their limiting | [9](topics/09-methods-of-higher-order.md) | Not begun | |
| — | Artificial viscosity: whether shocks in MHD need it beside flattening | [10](topics/10-artificial-viscosity.md) | Not begun | |
| — | Relativistic MHD: its equations, the inversion of its variables, and its floors | [25](topics/25-relativistic-mhd.md) | Not begun | |

Requirements and code: not begun.

### 6.4 Physics

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| — | Thermal conduction: its flux and saturation, its integration by super time-stepping, semi-implicit sweeps or implicitly, and diffusive fluxes in a form that viscosity and resistivity can join | [17](topics/17-thermal-conduction.md), [16](topics/16-diffusion.md) | Not begun | |
| — | Radiative cooling: the table and its dependence on metallicity, the floor and heating, the integration of a stiff source, and the limit of the step | [20](topics/20-radiative-cooling.md), [19, §2.2](topics/19-reactions-chemistry-and-cooling.md#22-stiff-integration) | Not begun | |

Extensions, in a provisional order:

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| — | Further diffusion, once MHD enters: conduction along the field, viscosity, resistivity, ambipolar diffusion and the diffusion of scalars | [16, §2.4](topics/16-diffusion.md#24-physical-diffusion-in-mhd), [17, §2.3](topics/17-thermal-conduction.md#23-anisotropic-conduction), [21, §2.4](topics/21-passive-scalars.md#24-scalars-in-the-framework) | Not begun | |
| — | Gravity of a fixed potential and rotating frames: their sources, hydrostatic boundaries, and whether the scheme must keep their balance exactly | [13, §2.2](topics/13-source-terms.md#22-gravity), [4, §2.3](topics/04-boundary-conditions-and-ghost-cells.md#23-prescribed-values-inflow-and-hydrostatic-boundaries) | Not begun | |
| — | Elliptic solvers and self-gravity: multigrid or Fourier transforms, the solve in each stage, and a solver that implicit diffusion and radiation may share | [14](topics/14-elliptic-solvers.md), [15](topics/15-self-gravity.md) | Not begun | |
| — | Particles: tracers of mixing, and dust coupled to the gas by drag | [22](topics/22-particles.md) | Not begun | |
| — | Driven turbulence: forcing in Fourier space and its random state in restarts | [27](topics/27-driving-of-turbulence.md) | Not begun | |
| — | The shearing box and orbital advection | [24](topics/24-shearing-box-and-orbital-advection.md) | Not begun | |
| — | Radiation transport: its closure and its implicit solve | [23](topics/23-radiation-transport.md) | Not begun | |
| — | Cosmic rays: their transport by two moments and their diffusion | [26](topics/26-cosmic-rays.md) | Not begun | |
| — | Chemical networks: their integration and their coupling to the flow | [19](topics/19-reactions-chemistry-and-cooling.md) | Not begun | |

Requirements and code: not begun.

### 6.5 Driver and problems

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| — | The driver: the structure of its loop, the limits of the step that join the Courant condition, and how a step ends at a requested time | [37](topics/37-driver-and-control-of-time-step.md) | Not begun | |
| — | Problem setups and user functions: the form of a problem, the declaration of its parameters, and the hooks that the framework offers | [38](topics/38-problem-setups-and-user-functions.md) | Not begun | |
| — | Outputs, restarts and analysis: the format and contents of snapshots and restarts, the quantities of the history, and whether plotting belongs to the package | [39](topics/39-output-restarts-and-analysis.md) | Not begun | |
| — | The problems that verify the first pass: which problems of topics 29 to 32 and 34 join the suite, their measures and thresholds, and the fountain cloud of 2016 as the production problem | [29](topics/29-advection-and-linear-waves.md), [30](topics/30-shock-tubes-and-interacting-blast-waves.md), [31](topics/31-shocks-in-several-dimensions.md), [32](topics/32-instabilities-vortices-and-convection.md), [34](topics/34-cold-clouds-and-mixing-layers.md) | Not begun | |

The extensions bring their problems with their own briefs, as MHD brings those of topics 30 and 33.

Requirements and code: not begun.

## 7. Glossary

- <a id="block"></a>**Block.** A part of the domain with its own cells, ghost cells and coordinates. A domain cut into blocks can be shared among threads or processes and refined block by block ([topic 36, §2.4](topics/36-data-structures.md#24-blocks-of-a-tree)).
- <a id="brief"></a>**Brief.** A decision brief: the document in which one architectural choice of mhdpy is weighed against the references and experiments, decided, and then frozen ([rules of the briefs](templates/brief-rules.md)).
- <a id="cell-average"></a>**Cell average.** The mean of a quantity over a cell, which a finite-volume scheme stores and changes only by the fluxes through the faces of the cell, so that it conserves what the equations conserve ([topic 3, §2.3](topics/03-grids-and-finite-volume-discretisation.md#23-the-conservative-update)).
- <a id="cell-update"></a>**Cell update.** The advance of one cell by one time step. Their number sets the cost of a run, and their rate per second its speed ([topic 42, §2.1](topics/42-parallelisation-and-performance.md#21-the-cost-of-a-simulation)).
- <a id="characteristics"></a>**Characteristics.** The paths along which the waves of the equations carry information. Characteristic variables each follow one family of waves, so that a reconstruction may limit them and a boundary may let the outgoing waves leave ([topic 1, §2.3](topics/01-equations-and-their-variables.md#23-the-quasi-linear-primitive-and-characteristic-forms)).
- <a id="conserved-and-primitive-variables"></a>**Conserved and primitive variables.** The two sets of variables of the gas: density, momentum and total energy, which the scheme conserves and updates, and density, velocity and pressure, from which it reconstructs ([topic 1](topics/01-equations-and-their-variables.md)).
- <a id="constrained-transport"></a>**Constrained transport.** A method that updates the magnetic field on the faces of the cells from electric fields on their edges, so that the field stays free of divergence to round-off ([topic 11](topics/11-constrained-transport.md)).
- <a id="cooling-function"></a>**Cooling function.** The rate at which optically thin gas radiates, per unit volume and per product of the densities of its electrons and ions, as a function of temperature and metallicity that tables give ([topic 20, §2.1](topics/20-radiative-cooling.md#21-cooling-in-the-equation-of-the-energy)).
- <a id="courant-condition"></a>**Courant condition.** The limit on the step of an explicit scheme: in one step no wave may cross more than a fraction of a cell, the Courant number ([topic 8, §2.1](topics/08-time-integration.md#21-stability-and-the-courant-condition)).
- <a id="equation-of-state"></a>**Equation of state.** The relation that gives the pressure, the sound speed and the temperature of the gas from its density and internal energy ([topic 2](topics/02-equations-of-state.md)).
- <a id="face-centred-field"></a>**Face-centred field.** A field stored on the faces of the cells rather than as cell averages, as constrained transport stores each component of the magnetic field on the faces normal to it ([topic 11, §2.1](topics/11-constrained-transport.md#21-the-staggered-field)).
- <a id="floor"></a>**Floor.** A lower bound set on the density or the pressure where the scheme would make them negative, at some cost in conservation ([topic 2, §2.2](topics/02-equations-of-state.md#22-the-internal-energy-and-floors)).
- <a id="free-threaded-build"></a>**Free-threaded build.** A build of Python without the global interpreter lock, in which threads run Python code at the same time on several cores ([topic 42, §2.5](topics/42-parallelisation-and-performance.md#25-threads-and-processes-in-python)).
- <a id="ghost-cell"></a>**Ghost cell.** A cell outside the domain whose values a boundary condition, or a neighbouring block, sets, so that one stencil serves every cell of the domain ([topic 4, §2.1](topics/04-boundary-conditions-and-ghost-cells.md#21-ghost-cells)).
- <a id="history"></a>**History.** A file of a few numbers per step, such as the totals of mass and energy, by which a run checks its conservation ([topic 39, §2.1](topics/39-output-restarts-and-analysis.md#21-kinds-of-output)).
- <a id="hook"></a>**Hook.** A place in a run where the framework calls a function that a problem setup or a module supplies, such as a boundary condition, a source or a diagnostic ([topic 38](topics/38-problem-setups-and-user-functions.md)).
- <a id="integrator"></a>**Integrator.** The method that advances the state over a time step, in one step or in several stages, each of which computes fluxes and sources ([topic 8](topics/08-time-integration.md)).
- <a id="kernel"></a>**Kernel.** A loop over the cells of a grid that performs one operation of the scheme, such as a reconstruction or a Riemann solver. Kernels take most of the time of a run ([topic 41](topics/41-vectorised-and-compiled-kernels.md)).
- <a id="limiter"></a>**Limiter.** The part of a reconstruction that flattens the profile of a cell near a jump, so that the scheme does not oscillate there ([topic 6, §2.2](topics/06-reconstruction-and-limiting.md#22-slope-limiters)).
- <a id="linear-wave"></a>**Linear wave.** A small eigenmode of the equations that crosses a periodic domain and returns to its initial state, so that the error after one crossing measures the order of convergence ([topic 29, §2.4](topics/29-advection-and-linear-waves.md#24-linear-waves-of-hydrodynamics-and-mhd)).
- <a id="mesh-refinement"></a>**Mesh refinement.** Finer cells where the flow needs them, from a hierarchy of grids whose levels differ by an integer factor and whose cells line up ([topic 40](topics/40-mesh-refinement.md)).
- <a id="mhd"></a>**MHD.** Magnetohydrodynamics, the dynamics of an electrically conducting gas, such as a plasma, together with the magnetic field that it carries ([topic 1, §2.5](topics/01-equations-and-their-variables.md#25-the-equations-of-ideal-mhd)).
- <a id="mpi"></a>**MPI.** The Message Passing Interface, a standard by which separate processes, on one machine or on many, exchange data ([topic 42, §2.4](topics/42-parallelisation-and-performance.md#24-parallel-execution)).
- <a id="operator-splitting"></a>**Operator splitting.** Advancing the processes of a step, such as the flow, conduction and cooling, one after the other, each with its own method, rather than all together ([topic 18](topics/18-operator-splitting-and-coupling-of-processes.md)).
- <a id="order-of-convergence"></a>**Order of convergence.** The power of the cell width with which the error falls as the grid is refined, two for a scheme of second order on a smooth problem ([topic 28, §2.2](topics/28-verification-and-testing.md#22-norms-and-the-order-of-convergence)).
- <a id="passive-scalar"></a>**Passive scalar.** A quantity per unit mass that the flow carries without being acted on by it, such as the metallicity of the gas ([topic 21](topics/21-passive-scalars.md)).
- <a id="problem-setup"></a>**Problem setup.** The code of one problem: its initial state, its domain and boundaries, its parameters, and the functions that act during its run ([topic 38](topics/38-problem-setups-and-user-functions.md)).
- <a id="reconstruction"></a>**Reconstruction.** The building of a profile within each cell from the cell averages, whose values at the faces are the states between which a Riemann solver computes the flux ([topic 6](topics/06-reconstruction-and-limiting.md)).
- <a id="regression-test"></a>**Regression test.** A test that compares the result of a run with one stored earlier, so that an unintended change shows ([topic 28, §2.5](topics/28-verification-and-testing.md#25-regression-tests-and-reproducibility)).
- <a id="requirement"></a>**Requirement.** One statement about a component that a test can decide, written after the briefs of its stratum and before its code ([rules of the requirements](templates/requirements-rules.md)).
- <a id="restart"></a>**Restart.** A file that holds everything needed to continue a run as if it had never stopped, also called a checkpoint ([topic 39, §2.1](topics/39-output-restarts-and-analysis.md#21-kinds-of-output)).
- <a id="riemann-solver"></a>**Riemann solver.** The method that computes the flux through a face from the two states on either side of it, from the waves that the jump between them launches ([topic 7](topics/07-riemann-solvers.md)).
- <a id="saturation"></a>**Saturation.** The limit of the conductive flux where the gradient of temperature is so steep that the electrons cannot carry the classical flux, which caps it near the heat that they hold times their speed ([topic 17, §2.2](topics/17-thermal-conduction.md#22-saturation)).
- <a id="shock-tube"></a>**Shock tube.** A Riemann problem in one dimension: two uniform states that meet at a plane, whose waves have an exact solution in hydrodynamics. Sod's shock tube is the classic one ([topic 30, §2.2](topics/30-shock-tubes-and-interacting-blast-waves.md#22-sods-shock-tube)).
- <a id="snapshot"></a>**Snapshot.** A file of the state at one time, written for analysis and plots ([topic 39, §2.1](topics/39-output-restarts-and-analysis.md#21-kinds-of-output)).
- <a id="source-term"></a>**Source term.** A term of the equations that no flux carries, such as gravity or cooling, which changes the state of a cell directly ([topic 13](topics/13-source-terms.md)).
- <a id="stencil"></a>**Stencil.** The cells from which a scheme computes the update of one cell. Its width sets how many ghost cells the domain needs ([topic 3, §2.1](topics/03-grids-and-finite-volume-discretisation.md#21-differences-and-stencils)).
- <a id="stiff-source"></a>**Stiff source.** A source whose time scale is far shorter than the step of the flow, such as fast cooling, so that an explicit update would need tiny steps and the source is integrated over the step instead ([topic 19, §2.2](topics/19-reactions-chemistry-and-cooling.md#22-stiff-integration)).
- <a id="super-time-stepping"></a>**Super time-stepping.** Explicit steps of diffusion beyond their limit of stability, taken as a sequence of substeps whose sizes keep the whole sequence stable ([topic 16, §2.5](topics/16-diffusion.md#25-super-time-stepping)).
- <a id="vectorisation"></a>**Vectorisation.** Writing a kernel as operations on whole arrays, which NumPy performs in compiled loops, rather than as a loop in Python over the cells ([topic 41, §2.1](topics/41-vectorised-and-compiled-kernels.md#21-vectorisation-in-numpy)).

## Sources

- <a id="buschmann-et-al-1996"></a>Buschmann, F., Meunier, R., Rohnert, H., Sommerlad, P. and Stal, M., Pattern-oriented software architecture, volume 1: a system of patterns, Wiley (1996).
