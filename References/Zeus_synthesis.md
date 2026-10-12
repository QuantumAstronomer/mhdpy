# ZEUS (ZEUS-2D) — Synthesis

## Sources and conventions

**Sources used.** Only the three 1992 ZEUS-2D papers in `Zeus/Docs/`. There is no code, and you had no web material for ZEUS.

- **Paper I:** Stone & Norman 1992a, *ZEUS-2D … I. The hydrodynamic algorithms and tests*, ApJS 80, 753.
- **Paper II:** Stone & Norman 1992b, *… II. The magnetohydrodynamic algorithms and tests*, ApJS 80, 791.
- **Paper III:** Stone, Mihalas & Norman 1992, *… III. The radiation hydrodynamic algorithms and tests*, ApJS 80, 819.

The PDFs are scanned ADS copies with OCR text. Equations in particular were partly garbled in the text layer. I relied on the prose descriptions, which were clean. Where an equation-level detail mattered, I describe it in words rather than quote it.

**Markers used in this document**

- **[GK]** marks my general knowledge, not from your material.
- **[Assumption]** marks my interpretation where the papers are not explicit.

Because there is no code, the "architecture" here is the one the papers describe: the flow chart, module boundaries, data centering and code-management approach. I could not check it against an implementation.

**How ZEUS differs from the other three codes.** You asked for this to be explicit. Read §1.1 first: it summarises the differences, and they recur throughout the document.

---

## 1. Purpose

ZEUS-2D is a **research code** for astrophysical **radiation magnetohydrodynamics (RMHD) in two space dimensions**. It was developed in Fortran 77 at NCSA (Illinois) on a Cray X-MP and grew out of M. Norman's earlier ZEUS code (1980s, star formation and jets). The papers describe its goals as follows.

- **Generality and extensibility first.** "Generality has been the driving philosophy." The HD algorithms were chosen as "the most accurate methods to which more complex physical effects can be easily added in a self-consistent fashion". The authors explicitly acknowledge that higher-order Godunov codes (for example PPM) give better results on strong-shock problems. They argue, however, that adding new physics such as MHD or radiation to those schemes self-consistently took "years of algorithm development". Simplicity, robustness, speed, and being able to run at high resolution were valued above per-cell accuracy.
- **Physics scope:**
  - **HD**: Euler equations with an internal-energy equation, plus self-gravity via the Poisson equation, in any orthogonal coordinate system (Cartesian, cylindrical, spherical polar), on a possibly moving grid.
  - **MHD**: ideal, flux-frozen; resistivity and ambipolar diffusion are noted as straightforward future additions.
  - **RHD**: full radiation transport via moment equations closed with variable Eddington factors from a formal solution of the transfer equation. This is explicitly *not* flux-limited diffusion.
- **"2.5-D."** All dependent variables depend on two coordinates, but *all three vector components* are evolved, for example rotation velocity and toroidal field. This is essential for rotating flows and for all MHD wave families. Paper I notes that ZEUS-3D already existed.
- **Size.** Over 30,000 lines including MHD and RHD.
- **Documentation goal.** The papers aim to be detailed enough for others to reimplement the methods, and provide a test suite for comparing codes.

### 1.1 How ZEUS's design differs from Ulula, Pyro and Athena(++)

| Aspect | ZEUS-2D | Ulula / Pyro (compressible) / Athena(++) |
|---|---|---|
| Discretisation family | **Finite differences on a staggered mesh.** Only the advection (transport) part uses control-volume, flux-form updates. | **Finite-volume Godunov schemes**: cell-averaged conserved variables updated by interface fluxes from Riemann solvers. |
| Variable placement | **Staggered**: density, internal energy, potential, toroidal velocity and field at zone centres; the in-plane velocity components (and in-plane B) on zone faces. | Hydro variables all **cell-centred** (co-located). Only Athena staggers B (face-centred) for CT. |
| Energy variable | **Internal energy equation**, chosen for accurate temperatures in highly supersonic flow. Total energy is therefore not conserved exactly. | **Total energy** conserved to round-off. |
| Shock capturing | **Explicit artificial viscosity** (von Neumann–Richtmyer, or an optional tensor form). Shocks are spread over about 3 zones. | **Upwinding through Riemann solvers** (HLL, HLLC, HLLD, Roe, …). No artificial viscosity, except a small amount in Pyro. |
| Time integration | **Operator splitting** into a *source step* (pressure, gravity, curvature, viscosity, compression, Lorentz force, radiation coupling) and a *transport step* (advection), each with substeps applied one after another. | Single, mostly unsplit update (Pyro, Athena), or a split but conservative Godunov sweep (Ulula). |
| Multi-D | **Directionally split advection**, *unsymmetrised* (XY, then YX on the next cycle). | Ulula: Strang-split sweeps. Pyro and Athena: **unsplit** (CTU or method of lines). |
| Upwinding | Only in the advection step: upwinded **interpolation** of the advected variable at faces (donor cell, van Leer or PPA), multiplied by the face velocity. | Upwinding through the wave structure of the full system (Riemann problem). |
| Geometry | **Covariant formalism**: one set of difference equations with metric scale factors and volume factors, valid for any orthogonal coordinate system. A moving (orthogonal) grid is allowed. | Ulula: Cartesian only. Pyro: Cartesian or spherical via a geometry object. Athena(++): a coordinate class with areas and volumes; no moving grid. |
| MHD | **CT** (constrained transport: face-centred in-plane B, divergence-free by construction) **+ MOC** (method of characteristics) for EMFs and Lorentz forces, upwinded along Alfvén characteristics. | Athena: CT with EMFs built from Godunov fluxes (GS05). Ulula and Pyro: no MHD. |
| Elliptic solvers | Sparse-matrix iterative solvers (ADI, ICCG, GMRES) on a nonuniform 2D mesh, with multipole boundary values. | Ulula: FFT. Pyro: multigrid. Athena++: FFT or multigrid. |
| Configuration | **CPP preprocessor macros** include or exclude modules at compile time. **Interactive** runtime control: you type commands during the run. | Runtime parameters (Pyro, Ulula); configure script plus input file (Athena). |

Athena's own paper (S08) uses exactly these differences to motivate the move away from ZEUS. Operator-split methods "that do not solve the dynamical equations in conservation form such as ZEUS are unsuitable for use with SMR or AMR". S08 also reports that a 3D ZEUS ran about 4× faster per cell than Athena with HLLD fluxes, even though Athena does about 10× more floating-point work.

---

## 2. Architecture

### 2.1 Top-level structure: one cycle

Paper I (Fig. 7), extended by Paper II (Fig. 4) and Paper III (Fig. 6), gives the program flow:

```
Setup: read parameters, build grid (a-mesh/b-mesh, scale & volume factors), problem initial conditions,
       (RHD: angular quadrature weights)
Main loop (one cycle = one Δt):
  1. Gravity: solve the Poisson equation for Φ (skipped if the stored Φ is still accurate enough)
  2. SOURCE step (operator split, substeps in sequence):
       Substep 1: velocity update from pressure gradient, gravity, curvature ("inertial") terms
                  [+ MHD: Lorentz-force terms; MOC update of the toroidal B and rotation velocity]
       Substep 2: artificial viscous stress + viscous heating
       Substep 3: compressional heating (p dV work) of internal energy
                  [RHD: REPLACED by the implicit solve of the coupled gas + radiation moment equations;
                   then the transfer-equation solver updates the Eddington factors for the next cycle]
  3. TRANSPORT step (directionally split, 1-sweep then 2-sweep, order alternating each cycle):
       advect density, specific internal energy, specific momenta (consistent transport)
       [+ MHD: CT update of the poloidal field using MOC-upwinded EMFs; toroidal flux advection]
       [+ RHD: advect radiation energy density and flux]
  4. Grid motion: recompute grid velocities and positions (if the grid moves)
  5. New Δt from CFL-type limits (Courant number ≈ 0.5)
  6. Output / interrupt handling
until a stopping criterion is met
```

The key architectural idea is that **each physical effect is a separate operator, applied one after another**. MHD and RHD are added as **self-contained modules** called at specific points of this flow, with a few existing substeps modified or replaced. Paper II stresses that the MHD algorithms "are self-contained and independent of the HD algorithms" and could be dropped into almost any explicit Eulerian finite-difference hydrocode.

### 2.2 The mesh and variable centering

- **Two meshes along each axis.** The *a-mesh* holds zone edges (`x1a`, `x2a`) and the *b-mesh* holds zone centres (`x1b`, `x2b`). The spacings `dx1a` and `dx1b` are stored independently, so grids can be **nonuniform**. Because the grid is orthogonal, the spacing in one direction applies along the whole of the other direction.
- **Ghost zones.** There are two on each side, needed for derivatives and for the PPA stencil. Indexing runs from inner (`ii`, `ji`) to outer (`io`, `jo`) active zones.
- **Staggered centering.**
  - Zone-centred: scalars (density, internal energy, potential, artificial viscous pressure) and the 3-component of vectors (rotation velocity, toroidal field).
  - Face-centred: the 1-component of vectors on 1-faces, the 2-component on 2-faces. This applies to both velocity and the poloidal magnetic field.
  - Zone corners: off-diagonal tensor components (radiation stress) and the 3-component of the EMF and current.
  - Paper I lists the advantages: most differences are naturally centred and second order, and face velocities directly give fluxes through control-volume faces. The disadvantage is extra averaging, for example to form momentum from density and velocity, which "can ultimately limit the overall accuracy".
- **Shared indices.** A scalar and the vector component at its *lower* face share the same index (i or j); no half-index notation is used.
- **Non-rectangular domains.** The inner and outer index limits can vary along the other axis, for example to cut out a central object.
- **Moving grid.** Grid velocities sit at the same positions as fluid velocities. After each step, edge and centre coordinates are recomputed. The grid can be made semi-Lagrangian along a strip, or follow a prescribed collapse. Orthogonality must be preserved, so grid motion along one axis is uniform across the other.

### 2.3 Geometry: the covariant formalism

This is a central architectural choice. **All differential operators are written once, using metric scale factors**, so the same difference equations serve every supported orthogonal coordinate system.

- The scale factors are restricted to a product form. In the code they are stored as three arrays (`g2`, `g31`, `g32`), plus their derivatives, each defined on both meshes. This saves memory and operations but rules out, for example, oblate spheroidal coordinates.
- **Volume factors** (`dvl1`, `dvl2`, for instance Δ(r³/3) and Δ(−cos θ) in spherical coordinates) are used wherever a divergence-like radial or angular difference appears. This keeps the differencing correct near coordinate singularities, a simple form of "coordinate regularisation".
- The only coordinate-dependent step is computing these factors once at start-up, or each step if the grid moves.
- Writing the transport equations with the scalar divergence theorem drops curvature terms. These **inertial forces** are therefore added in the source step.

### 2.4 The source step

The source step solves the non-advective parts as three substeps, each using the result of the previous one.

1. **Forces.** Pressure gradients (pressure from the EOS at the start of the step; usually ideal gas), gravity (from the potential solved at the start of the step) and curvature terms update the face velocities. Averaging to faces is needed because of the staggering. MHD adds the Lorentz force here.
2. **Artificial viscosity.**
   - The default is the von Neumann–Richtmyer form: a zone-centred viscous pressure that is non-zero only in compression and proportional to the square of the velocity jump, applied separately per direction. The dimensionless coefficient is about 3, the number of zones over which a shock is spread.
   - It adds a stress to the momentum and a dissipative heating term to the internal energy.
   - The papers call the per-direction extension "ad hoc" and potentially problematic in curvilinear coordinates. Appendix B therefore gives a **tensor artificial viscosity**: traceless, based on the velocity divergence, with shear components dropped, and with the heating written as a sum of squares for stability.
3. **Compressional heating.** For a gamma-law gas, an implicit time-centred update gives an explicit closed form and improves energy conservation. For a general EOS a predictor–corrector is used. **RHD replaces this substep** with the implicit gas-radiation solve (§2.7).

### 2.5 The transport step

The transport step solves the advection equations in **integral (control-volume) form**. This is the only conservative part: each face flux is used for both neighbouring zones, so the global integral of each advected quantity is conserved apart from boundary fluxes.

- **Directional splitting**: a full 1-sweep, then a 2-sweep using the partly updated values. ZEUS deliberately uses the *unsymmetrical* XY ordering (alternating to YX on the next cycle) instead of symmetric Strang splitting (half-X, Y, half-X). Numerical experiments cited in Paper I showed that, for a given CPU time, more resolution beat the 50% extra cost of symmetric splitting at the problem sizes of the day.
- **Interface values** come from upwinded interpolation of the advected quantity, with the fraction of a zone swept in one step taken into account. Three schemes are available:
  - **donor cell**: first order, too diffusive, used only for tests;
  - **van Leer**: piecewise linear with a harmonic-mean monotonised slope that accounts for nonuniform spacing; second order and the usual default;
  - **PPA** (piecewise parabolic *advection*): third-order interpolation following Colella & Woodward, with contact steepening. It is roughly twice as costly as van Leer and keeps contacts about two zones wide. The paper stresses that PPA here is *not* PPM: no Riemann solver is involved.
- **Consistent transport** (Norman et al. 1980). Mass is advected first. The other quantities are advected as **specific** quantities: specific internal energy, and specific momenta, including the angular-momentum-like ones (the geometric factors are built into the momentum definitions). Their fluxes are the face **mass fluxes** multiplied by the interpolated specific quantity. This keeps the transport of energy and (angular) momentum consistent with mass transport and greatly improves local conservation of specific angular momentum.
- **Staggering gives different control volumes.** Zone-centred quantities and the two face-centred momenta each have their own control volume. Their fluxes therefore sit at different positions, and velocities and densities must be averaged accordingly.
- **Variable conversions.** The source step works with velocities and the transport step with momenta. Momenta are formed from velocities at the start of the transport step, velocities are held fixed throughout it, and new velocities are recovered at the end.

### 2.6 MHD module (Paper II)

- **Centering.** The poloidal (in-plane) B components are face-centred like the velocities, chosen so that the coupled velocity and field components of Alfvén waves sit at the same place. This differs from the original Evans & Hawley CT layout. The toroidal component is zone-centred. Current density components and the 3-EMF lie at faces and corners respectively.
- **Poloidal field: constrained transport.** The field is updated by the circulation of the edge-centred EMF around each face (Stokes' theorem), so the discrete divergence of B stays zero to round-off. ZEUS rejects the older vector-potential approach: accurate Lorentz forces need second derivatives of the vector potential, which caused anomalous current reversals at sharp features.
- **The EMF: method of characteristics.** CT alone guarantees zero divergence but not accuracy. Using the hydro upwind schemes for the field gave large *dispersion* errors for Alfvén waves. ZEUS therefore computes time-advanced velocities and fields at each edge by **solving the Alfvén-wave characteristic equations** (forward and backward along the field), and builds the EMF from those values. This is the hybrid **MOC-CT** scheme. The Lorentz-force terms in the momentum equation are differenced consistently with it.
- **Toroidal field.** Divergence-free by symmetry, so no CT is needed, but torsional Alfvén waves need a dedicated MOC-type update coupled to the rotation velocity. The toroidal flux is advected in the transport step.
- **Integration with HD.** The MOC-CT routines are modules. Substep 1 of the source step gains the Lorentz forces and the toroidal update; the transport step gains the poloidal CT update. The CFL limit uses the fast magnetosonic speed instead of the sound speed.
- **Boundary conditions** are specified for EMFs in the ghost zones (reflecting, inflow, outflow, periodic) rather than directly for B.
- **Verification.** Convergence testing on the Weber–Davis magnetised wind showed the full code converging *below* second order. The authors flag this as needing further work.

### 2.7 RHD module (Paper III)

- **Equations.** Radiation energy and flux moment equations, derived from the comoving-frame transfer equation to first order in v/c, are coupled to the gas energy and momentum equations.
- **Closure.** A **tensor variable Eddington factor**. It comes from a formal solution of the static, frequency-integrated transfer equation on a separate angular/spatial "radiation grid", using the **method of short characteristics**, followed by angular quadrature. No diffusion approximation or flux limiter is needed, so the method works in optically thin and thick regions alike.
- **Source/transport split again.** In the source step, the radiation momentum equation is integrated in time analytically ("automatic flux limiting"), which removes the flux as an unknown. The remaining coupled, nonlinear, **implicit** equations for gas and radiation energy are solved by **Newton–Raphson**. Each iteration solves a sparse banded linear system (9-point stencil) with the same iterative sparse solvers used for gravity; it typically converges in 4–8 iterations. Time-centring is controlled by a parameter that must be at least 0.5: 0.5 gives Crank–Nicolson and 1 gives fully implicit; tests favour fully implicit as more diffusive but robust. In the transport step the radiation variables are advected explicitly, like the gas.
- **Integration with HD.** The implicit moment solve *replaces* Substep 3. The transfer solver runs right after it to update the Eddington factors for the next cycle. The transport step gains radiation advection, and setup gains quadrature weights.
- **Side benefit.** The transfer solver can be run as a post-processor to make emergent-intensity images of any simulation.
- **Mixed explicit/implicit.** Hydro and MHD remain explicit and CFL-limited; only the radiation is implicit, to avoid the light-speed timestep limit.

### 2.8 Gravity

- **Poisson equation** discretised with the covariant Laplacian (5-point stencil, volume differencing near the origin). This gives a symmetric, positive-definite sparse banded matrix.
- **Solvers:** ADI iteration (pseudo-time relaxation), ICCG and GMRES. In practice the library-based Krylov solvers are used, sharing storage with the RHD solver and making it easy to swap in new solvers.
- **Boundaries:** Neumann at symmetry boundaries; Dirichlet at outer boundaries, with values from a **multipole expansion** of the mass distribution (Legendre series, up to 100 terms, to 1 part in 1000). This works only in curvilinear geometries with an axis of symmetry.
- **Avoiding unnecessary solves.** The residual of the stored potential against the current density is checked each cycle, and a new solve is done only if it exceeds about 10⁻⁵. This often cuts solves to about one every ten cycles.

### 2.9 Boundary conditions

There are five types:

- **reflecting**: normal velocity zero on the boundary;
- **axis of symmetry**: as reflecting, but also flips the rotation velocity;
- **inflow**: ghost values prescribed, possibly time-dependent;
- **outflow**: copy from the active zones; exact only for supersonic flow and reflects waves when subsonic;
- **periodic**.

They are applied after every update, can be set **independently for every zone along every boundary** (for example a jet nozzle inlet on part of a boundary), and are **implemented per variable in separate subroutines** for modularity. MHD uses EMF-based boundary conditions, and RHD has its own.

### 2.10 Timestep

Δt is the Courant number (about 0.5) times the inverse of the root-sum-square of four limiting rates:

- sound crossing of the smallest zone dimension;
- flow speed relative to the grid in direction 1;
- flow speed relative to the grid in direction 2;
- the explicit-diffusion limit from the artificial viscosity.

MHD uses the fast speed in place of the sound speed. **Δt may grow by at most 30% per cycle** but may shrink by any amount.

### 2.11 Code management and control

- **Fortran 77**, following an established coding paradigm (Winkler & Norman 1986) for portability. Graphics through NCAR graphics and raster images; data dumps in **HDF**, an NCSA format.
- **The C preprocessor (CPP)** manages physics, geometry and output options. Building without the MHD or RHD macros removes all their arrays and routines, giving optimised HD-only or MHD-only executables. The authors describe CPP as essential at the 30,000-line scale.
- **An interactive interrupt handler** in the main loop: during a run you can type commands to dump data, change control flags or variables, pause, stop or restart.

### 2.12 Testing philosophy

Paper I describes a "test suite" philosophy: build up from tests of individual components to tests of the whole code. The progression is:

- 1D Cartesian advection (square pulses and other profiles, each method, each direction);
- curvilinear advection;
- shock tubes;
- strong-shock 2D problems (Woodward & Colella);
- self-gravity against analytic potentials (homogeneous sphere, centrally condensed sphere, ellipsoid).

Paper II adds MHD advection, an MHD Riemann problem, the Weber–Davis wind (also used for convergence testing), B. C. Low's coronal transients, magnetic braking of an aligned rotator, and shear Alfvén waves. Paper III adds streaming-limit, static- and dynamic-diffusion, searchlight-beam and Eddington-factor tests. It notes the lack of a dynamical RHD Riemann-problem test. Paper II recommends three kinds of convergence testing:

- single-step convergence;
- extended-evolution convergence against an analytic solution;
- self-convergence between resolutions.

---

## 3. Numerics overview

| Component | ZEUS-2D choice |
|---|---|
| Equations | Mass, momentum (velocity form in the source step, specific momenta in the transport step), **internal** energy, Poisson; ideal MHD; RHD moment equations. |
| Spatial discretisation | Finite differences on a staggered, nonuniform, orthogonal, optionally moving mesh; covariant metric/volume-factor formulation; control-volume flux form for advection only. |
| Time integration | Explicit, first-order-in-time operator splitting (source substeps, then transport). The components are time-centred where cheap (for example the implicit compression heating, and fluxes built from time-centred quantities). |
| Advection | Directionally split, unsymmetrised and alternating; upwinded interpolation (donor / van Leer / PPA); consistent transport with mass fluxes. |
| Shocks | Artificial viscosity, von Neumann–Richtmyer (default) or tensor. |
| MHD | CT for poloidal B, with EMFs from MOC along Alfvén characteristics; MOC for toroidal B and rotation. |
| Radiation | Variable-Eddington-tensor moment method; implicit Newton–Raphson gas-radiation energy coupling; short-characteristics formal solution. |
| Gravity | Sparse iterative solve (ADI / ICCG / GMRES), multipole Dirichlet boundary conditions, solve only when the residual is large. |
| CFL | Courant number ≈ 0.5; sound, flow and viscous limits; fast speed for MHD; Δt growth capped at 30%. |
| Accuracy | Formally second order in smooth flow (van Leer). Measured convergence below second order for the full MHD code; error sources include the staggered-mesh averaging and the splitting. |

---

## 4. Notable design choices

**Worth borrowing for your own framework, even though you are building a finite-volume Godunov code**

1. **Operator splitting as a module-integration strategy.** Each physical process is a separate, ordered update, and new physics enters as a module inserted at a defined point, or replacing a substep. This is the simplest way to grow a code's physics, and ZEUS's success with "hundreds of applications" (as S08 puts it) came largely from that ease of extension. **[Assumption]** In a finite-volume framework, the same idea appears as operator-split source terms (cooling, chemistry, radiation coupling) around a conservative hyperbolic core. Athena++ makes it more flexible with task lists and super-time-stepping.
2. **A coordinate-independent ("covariant") formulation** with precomputed scale and volume factors. The same equations serve Cartesian, cylindrical and spherical grids, and volume differences give correct behaviour near the origin and axis. This parallels Pyro's and Athena++'s geometry objects, which supply areas and volumes; ZEUS shows the idea predates Godunov codes.
3. **Consistent transport.** Fluxes of momentum and energy are derived from the mass flux, so specific quantities (especially angular momentum) are transported consistently. The same idea lives on in Athena++ as passive-scalar fluxes derived from the Riemann-solver mass flux.
4. **Separate a module's internals from its integration points.** The MHD and RHD papers each spell out exactly which substeps are added, modified or replaced, and give an updated flow chart. That level of explicit "integration contract" is worth reproducing in your architecture documentation.
5. **Avoid unnecessary elliptic solves** by checking the residual of the stored potential first. **[Assumption]** This is a cheap, general trick for any slowly varying field solved implicitly.
6. **Per-variable, per-zone boundary specification**, with boundary routines kept separate per variable.
7. **A methodical, incremental test suite**: component tests first, then integrated tests, with three styles of convergence testing.

**Why the later codes (Athena in particular) moved away from it**

1. **Not conservative in total energy**, because it evolves internal energy, and **not in fully conservative form** overall because of the operator splitting and staggered averaging. S08 states this makes ZEUS-type schemes unsuitable for mesh refinement, which requires conservation at fine/coarse boundaries.
2. **Shocks are captured by tuned artificial viscosity** and spread over several zones. The papers themselves concede that Godunov/PPM codes do better on strong-shock problems.
3. **Splitting errors and averaging** limit measured convergence to below second order for the full MHD code (Paper II).
4. **Directionally split advection** does not preserve symmetry as well as unsplit methods. **[GK]** Splitting is also why multidimensional MHD needed the special MOC-CT treatment rather than a straightforward extension.
5. **CPP-driven configuration and Fortran 77 common-block style.** These are effective, but they are the same "nested preprocessor flags" that Athena++ later identified as unmaintainable as physics grew.

**[GK] Context.** ZEUS-3D and later ZEUS-MP (a parallel 3D successor) continued this lineage. The same operator-split, staggered-mesh approach also underlies codes such as ZEUS-MP and parts of the FARGO family. These codes remain popular for problems where robustness and the ease of adding physics outweigh shock fidelity. None of this is in your reference material.
