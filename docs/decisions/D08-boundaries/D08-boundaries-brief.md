# D08 — Boundaries and inter-block communication

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-12 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how blocks get the data they need from outside themselves. It covers:

- how ghost zones are filled from neighbouring blocks, and how that is executed;
- how physical boundary conditions are specified and applied;
- how values on faces and edges shared by two blocks are kept consistent;
- how data moves between refinement levels: restriction, prolongation, and the correction of fluxes and EMFs at fine/coarse boundaries. This is designed now and implemented with mesh refinement (D07.7).

All of these are the "communication layer" that D05.1 requires every movement of data between blocks to go through, so that it can later be carried by MPI messages.

The earlier briefs fix the frame:

- **D05 (parallelism).**
  - **One layer:** all data movement between blocks goes through one communication layer, in-memory copies now and MPI later.
  - **Determinism:** the state must not depend on the decomposition, so values on faces shared by two blocks must be computed identically by both (D05.5).
  - **GIL share:** the Python that holds the GIL per block must be small, for the standard interpreter to scale. Ghost filling is the first candidate for compiled code (D05.4); how much that matters was left to be measured here.
- **D06 (data model).** Data lives in one array per process for each centring and role (`[block, var, k, j, i]`), and staggered data is padded so that a block stores *both* faces of each of its cells. The registry carries, per variable:
  - whether it is exchanged;
  - its behaviour under reflection (even or odd);
  - its restriction and prolongation operators.

  Ghost filling in NumPy cost about 10 % of a kernel evaluation (E06.2).
- **D07 (mesh).**
  - **Neighbours:** they follow from logical locations, and a physical boundary is where a neighbour falls outside the root grid.
  - **Ghost width:** set once, as the largest requirement of all operators including boundary conditions.
  - **Refinement:** neighbouring blocks differ by at most one level.
- **D03 (discretisation).** Constrained transport keeps the magnetic field on faces and updates it from edge EMFs. Boundary conditions and prolongation of selectable order are among the provisions for higher-order schemes.
- **D02 (verification).** Conservation to round-off wherever the boundary conditions permit. Mirror-symmetric problems must give mirror-symmetric results bit for bit, which reflecting boundaries must respect.

**What the references do** (syntheses in `References/`):

- **Athena** (C) exchanged ghost zones direction by direction (x, then y, then z), which fills corners without diagonal messages but makes each direction wait for the previous one; S20 names that dependency as a scaling bottleneck.
- **Athena++** separates the concerns into abstract interfaces:
  - communication (persistent MPI, start receiving, clear);
  - buffers (pack and unpack, for same-level, coarser and finer neighbours, plus flux corrections);
  - physical boundary conditions per face of the domain.

  Concrete classes exist per centring (cell-centred, face-centred with EMF correction). Each physics module owns boundary-variable objects for its arrays, so the framework communicates any registered variable without knowing what it means. Every neighbour has its own buffer and message (up to 26 in 3D, 56 with refinement), which removes the direction-by-direction dependency at the cost of many small messages. At fine/coarse boundaries:
  - **Restriction:** the finer block restricts into a coarse buffer, volume-weighted for cells and area-weighted for faces.
  - **Prolongation:** the coarser block's data is prolongated with a minmod-limited linear reconstruction. This works on primitives at block boundaries, to avoid negative pressure, and on conserved variables when blocks are created, to keep conservation.
  - **Face fields** are prolongated divergence-free (Tóth & Roe 2002).
  - **Fluxes and EMFs:** coarse fluxes are replaced by the area-weighted sum of fine fluxes, and coarse EMFs by the length-weighted sum of fine EMFs. That keeps conservation and the divergence of B exact.
  - **Shared edges:** EMFs on edges shared by blocks are averaged even without refinement, because round-off would otherwise let the two copies of a shared face field drift apart.

  Physical boundary conditions: outflow, reflecting, periodic, shear-periodic, polar (across the pole in spherical coordinates), polar wedge, and user functions, chosen per face of the domain.
- **Pyro** attaches a boundary-condition object to every registered variable (`register_var(name, bc)`), so that, for example, momenta reflect with odd parity, and fills ghost cells per variable (`fill_BC`).
- **Ulula** applies one choice to the whole domain (periodic, outflow, or wall with the normal velocity flipped, corners included), after every sweep. A user function can overwrite ghost cells afterwards (for example to drive an inflow), and the conservation monitor knows which quantities each boundary type conserves.
- **ZEUS** sets boundary conditions independently for every zone along every boundary (a jet nozzle on part of a boundary), in separate routines per variable. For MHD it sets them on the EMFs rather than on the field.

## 2. Evidence

### E08.1 — Ghost cells: NumPy copies or a compiled copy kernel

**Method.** [`experiments/E08.1b-ghost-copies.py`](experiments/E08.1b-ghost-copies.py) runs full SSP-RK2 steps on the thesis grid (4000 × 1000, periodic, blocks of 50² and 25²), with the kernels, data layout and thread model of E07.1. The ghost cells are filled in three ways:

- **NumPy slice copies**, eight per block and stage (edges and corners);
- **a compiled copy kernel, one call per block:** `copy_regions` in [`E08.1a-kernels.py`](experiments/E08.1a-kernels.py) executes the block's rows of an exchange plan. The plan is a table of integers built once from the blocks: destination block and offsets, source block and offsets, extent. The kernel runs without the GIL;
- **the same kernel, one call per worker and stage,** for all regions of the worker's blocks at once.

[`E08.1d-run.py`](experiments/E08.1d-run.py) runs it natively (6 cores, 12 hardware threads) and in a Linux container ([`E08.1c-Dockerfile`](experiments/E08.1c-Dockerfile), 8 virtual CPUs), each with the free-threaded and the standard interpreter. All 72 configurations were bit-for-bit identical to a single-block serial reference.

A first native run with the standard interpreter unintentionally ran on the free-threaded one, because uv reused a cached environment. The driver now requests `3.14+gil`, and the run was repeated; the same error affected E07.1 and has been corrected there. Full output: [`results/E08.1d-ghost-copies.md`](experiments/results/E08.1d-ghost-copies.md).

**Results.** Million cell updates per second:

| Interpreter, platform | Block | Workers | NumPy copies | Compiled, per block | Compiled, per worker |
|---|---|---|---|---|---|
| Free-threaded, macOS | 50² | 1 / 6 / 12 | 6.4 / 29.8 / 33.3 | 6.9 / 28.7 / 31.4 | 6.9 / 29.1 / 32.0 |
| Free-threaded, macOS | 25² | 1 / 6 / 12 | 4.2 / 19.9 / 24.2 | 4.6 / 20.7 / 24.1 | 5.1 / 20.8 / 23.5 |
| With GIL, macOS | 50² | 1 / 6 / 12 | 6.7 / 22.6 / 23.8 | 7.0 / 30.0 / 35.6 | 7.7 / **31.7** / 33.2 |
| With GIL, macOS | 25² | 1 / 6 / 12 | 4.7 / 11.6 / 10.4 | 5.3 / 15.3 / 13.0 | 5.3 / **17.5** / 14.6 |
| Free-threaded, Linux container | 50² | 1 / 4 / 8 | 4.3 / 16.7 / 23.0 | 4.6 / 16.3 / 22.3 | 4.6 / 16.3 / 21.3 |
| With GIL, Linux container | 50² | 1 / 4 / 8 | 4.4 / 13.5 / 8.6 | 4.4 / 10.2 / 6.6 | 4.4 / 15.1 / 9.3 |
| With GIL, Linux container | 25² | 1 / 4 / 8 | 3.8 / 6.3 / 2.1 | 4.0 / 3.4 / 1.6 | 4.0 / 7.3 / 2.3 |

- **On one worker, compiled copies are 5–20 % faster** on either interpreter: the ghost filling is a noticeable part of a step, and NumPy's per-copy overhead disappears.
- **On the free-threaded interpreter with several workers, the method does not matter** within the run-to-run variation (about ±15 % on the laptop). The copies run in parallel either way.
- **On the standard interpreter natively, compiled copies make the difference D05.4 asked for.** At 6 workers, throughput rises by 40 % for 50² blocks (22.6 → 31.7) and 50 % for 25² blocks (11.6 → 17.5). With one call per worker, the standard interpreter reaches the free-threaded one on 6 cores.
- **In the Linux container, the standard interpreter still collapses beyond 4 workers,** with compiled copies too (50², 8 workers: 9.3 against 21.3 free-threaded). What still holds the GIL there is the per-block calls of the kernels themselves and the loop around them. Each call reacquires the GIL. One call per worker was consistently better than one per block. The step beyond this, looping over a worker's blocks inside compiled code, belongs to the execution model (D09).

### E08.2 — Constrained transport on blocks

**Method.** [`experiments/E08.2b-ct-blocks.py`](experiments/E08.2b-ct-blocks.py) runs the field-loop test of D03 with Athena++'s upwinded edge EMFs (`ct-contact`), 128 × 64 cells, 64 SSP-RK2 steps. It uses the unchanged D03 solver ([`E08.2a-mhd2d.py`](experiments/E08.2a-mhd2d.py)) in two ways:

- **as one periodic grid,** the reference;
- **divided into blocks of 32², 16² and 8²,** each with 1, 2 or 3 ghost cells, filled before every stage from the cells and faces the neighbouring blocks own.

Every block updates its own cells and *both* faces of each of its cells, so a face shared by two blocks is computed twice, independently, from each block's own ghost zone. After every stage, the two copies of every shared face are compared. After the run, the assembled state (cells and face fields) is compared with the reference bit for bit, and the face-centred divergence of B is measured. The D03 solver wraps its stencils around the array, so wrong values land in the outermost ghost layers. Whether they reach the owned cells shows how many ghost cells the scheme needs. Full output: [`results/E08.2b-ct-blocks.md`](experiments/results/E08.2b-ct-blocks.md).

**Results.**

| Blocks | Ghost cells | State bit for bit | Shared faces whose two copies differ | Max. abs. div B |
|---|---|---|---|---|
| 8 × 32² | 1 | no (3 × 10⁻⁵ relative) | 52 260 of 65 536 | 8 × 10⁻³ |
| 8 × 32² | 2 | **yes** | **0 of 65 536** | 1.7 × 10⁻¹⁶ |
| 8 × 32² | 3 | **yes** | **0 of 65 536** | 1.7 × 10⁻¹⁶ |
| 32 × 16² | 2 | **yes** | **0 of 131 072** | 1.7 × 10⁻¹⁶ |
| 128 × 8² | 2 | **yes** | **0 of 262 144** | 1.7 × 10⁻¹⁶ |

(With one ghost cell, 16² and 8² blocks fail in the same way as 32².)

- **With enough ghost cells, the two independently computed copies of every shared face are identical,** after every stage of every step, and the decomposed run equals the single grid bit for bit, cells and face fields alike. Averaging, as Athena++ does, would change nothing here, because the copies never differ.
- **The second-order CT scheme needs two ghost cells.** With one, the stencils of reconstruction and EMF upwinding reach beyond the ghost zone. The copies disagree on most shared faces, and the divergence of B grows to 10⁻², fourteen orders of magnitude above round-off. This is the failure that a ghost width derived from the selected operators (D07.5) prevents, and it shows how a test detects it.
- **The divergence stays at round-off on blocks of every size,** 8² included. Constrained transport survives decomposition intact.

## 3. Decisions

### D08.1 — The communication layer

How is the movement of data between blocks organised?

**Options**

- **A. Exchange plans, built from the mesh and executed by a backend.**
  - **The plan:** for each centring, a plan lists every region to fill: destination block and offsets, source block (or remote process) and offsets, and extent. It covers edges and corners, all 3^d − 1 neighbours directly.
  - **When it changes:** the plan is built once from the logical locations (D07.4) and rebuilt only when the mesh changes.
  - **Backends:** a local backend executes it as direct copies within a process. A later MPI backend packs the regions for each remote neighbour into one buffer, sends it, and unpacks on arrival.
  - **Later operations:** with refinement, the plan gains restriction and prolongation steps (D08.5).
  - **Ownership:** each block fills its own ghost zones by reading the owned cells of its neighbours (pull), so workers never write into each other's blocks.
- **B. Neighbour lookups at the time of each exchange,** with slices computed on the fly, as the D05–D07 experiments did. Less structure, but the work is repeated every stage, and a later MPI version would need a different code path.
- **C. Per-block boundary objects with their own buffers per neighbour,** as Athena++. Proven at scale, but it attaches communication state to every block, where the data model of D06 keeps blocks lightweight.
- **D. Direction by direction** (x, then y, then z), as Athena (C), which fills corners without diagonal neighbours. Simpler plans, but every direction waits for the previous one, the dependency S20 found to limit scaling.

**Recommendation.** A. A plan is a small table of integers, which the compiled copy kernel of E08.1 executes directly. It is computed once, so filling ghost zones costs no Python logic per stage, and the same table is what an MPI backend needs to pack its buffers. That keeps D05.1's promise that distributed memory can be added by writing a backend, not by restructuring. Corners come from diagonal neighbours directly, so there is no direction-by-direction dependency. This serves **performance** and **extensibility**.

**Decision.** *(2026-10-12)* **A, exchange plans built from the mesh and executed by a backend.** It promises the best performance, since a plan lets ghost filling bypass Python calls entirely (D08.2), and an MPI backend can later work in the same way, from the same plan.

### D08.2 — Executing the copies

Are ghost cells copied with NumPy or by compiled code?

**Options**

- **A. NumPy slice copies,** a few per block and stage (E05–E07).
- **B. A compiled copy kernel, one call per block,** executing that block's rows of the plan without the GIL.
- **C. A compiled copy kernel, one call per worker and stage,** executing all rows of the worker's blocks at once.

**Recommendation.** C, one compiled call per worker and stage. It was never slower than NumPy, it was 5–20 % faster on one worker, and it gave the standard interpreter 40–50 % more throughput natively (E08.1). That is the measurement D05.4 asked for, and it shows that keeping GIL-held Python small works. It executes the plan of D08.1 directly. The same compiled copies will serve the local part of an MPI backend, and later the restriction and prolongation steps. This serves **performance**.

**Decision.** *(2026-10-12)* **C, one compiled call per worker and stage**, following the recommendation: performance is what matters most here.

### D08.3 — Faces and edges shared by two blocks

How are the two copies of a face or edge value shared by neighbouring blocks kept consistent, for example the face-centred magnetic field of constrained transport?

**Options**

- **A. Computed independently by both blocks, identical by construction.** Both blocks compute the shared value from identical inputs (their ghost zones are exact copies) with identical arithmetic, as D05.5 requires. The exchange then overwrites the non-owning copy with the owner's, so one copy is authoritative even if that ever failed, and a test asserts that the two agree. This requires every input to agree as well, including geometry: face positions, areas and lengths must be computed from global indices, never accumulated per block.
- **B. Average the two copies,** as Athena++ does for shared edges, as a guard against drift from round-off and nondeterministic message order.
- **C. One owner computes, the other only receives:** the non-owning block skips the computation. This saves the duplicate work, but it makes kernels aware of block boundaries.

**Recommendation.** A. E08.2 shows that the two copies are identical by construction, in hundreds of thousands of comparisons, as long as the ghost zone is wide enough. Averaging (B) would add work and hide a violation of D05.5 instead of exposing it. The exchange overwriting the non-owner's copy keeps one value authoritative in any case. C would save little and make kernels aware of block boundaries. The reasons Athena++ gives for averaging do not apply here:
- **Nondeterministic message order:** the arithmetic does not depend on the order in which messages arrive.
- **Curvilinear round-off:** it does not arise if geometry is computed from global indices.
- **Aggressive compiler optimisation:** it does not arise, since both blocks run the same compiled kernel.

A test that compares the two copies is the guard instead. This serves **correctness**: a disagreement is a bug to be found, not noise to be smoothed.

**Decision.** *(2026-10-12)* **A, computed independently by both blocks, identical by construction**, as the most logical option. The exchange keeps the owner's copy, and a test asserts that the two copies agree.

### D08.4 — Physical boundary conditions

How are physical boundary conditions specified and applied?

**Options**

- **A. One condition per face of the domain, for all variables,** as Athena++ and Ulula. The registry supplies each variable's parity (D06.6), so a reflecting boundary flips the normal components of vectors and keeps scalars.
- **B. One condition per variable and face,** as Pyro and ZEUS. Most flexible, but verbose, and easy to make inconsistent between variables.
- **C. A, with per-variable overrides and user functions.** A condition per face is the default. A variable may override it, for example a passive scalar with a fixed inflow value. A user function may fill any part of a face (ZEUS's nozzle on part of a boundary, or an inflow), and receives the block's views and geometry.

For all options:
- **Built-in conditions:** periodic, outflow (zero gradient), reflecting and, later, shear-periodic and polar.
- **Implementation:** compiled kernels, run only on blocks at the domain boundary.
- **Primitive variables:** conditions act on the primitive variables of the ghost zones, and the conserved ones follow by conversion, so that inflow conditions can be written in density, velocity and pressure. **[GK]** Athena++ applies its physical boundary conditions this way.
- **Order:** exchange between blocks first, physical conditions after, so that ghost zones at corners where a block boundary meets the domain boundary are filled consistently.

**Recommendation.** C. The default keeps simple problems simple, overrides cover the cases where variables need different treatment, and user functions cover what no built-in can, such as the inflow boundaries of wind-tunnel set-ups like the thesis problem. Parity from the registry makes reflecting boundaries correct for every registered vector, which the mirror-symmetry tests of D02 rely on. This serves **correctness** and **extensibility**.

**Decision.** *(2026-10-12)* **C, one condition per face of the domain, with per-variable overrides and user functions**, following the recommendation. The per-variable override is valuable in practice. In a set-up like the thesis problem, for example, it allows an inflow of metal-rich material, a fixed metallicity at an inflow boundary, while the hydrodynamic variables follow the face's own condition.

### D08.5 — Restriction and prolongation

How is data transferred between refinement levels (implemented with refinement, D07.7)?

**Options**

- **A. Operators registered per variable (D06.6), with defaults per centring and role, as Athena++:**
  - cell-centred data is restricted volume-weighted and prolongated with a limited linear reconstruction (minmod by default, the order selectable as D03 requires). This uses primitive variables at block boundaries, to keep pressure positive, and conserved variables when blocks are created, to keep conservation;
  - face-centred magnetic fields are restricted area-weighted and prolongated divergence-free (Tóth & Roe 2002);
  - edge and node data are restricted length-weighted or by injection.
- **B. One fixed set of operators for everything.** Simpler, but wrong for face fields, which must stay divergence-free, and for variables whose sign or range must be preserved.
- **C. Operators supplied by each physics module.** Most flexible, but it duplicates the standard operators in every module.

**Recommendation.** A. The defaults cover every variable mhdpy has planned, and they are Athena++'s proven choices. Registration lets a module override them where needed. Divergence-free prolongation of face fields is not optional with constrained transport. This serves **correctness** and **extensibility**.

**Decision.** *(2026-10-12)* **A, operators registered per variable with Athena++'s defaults**, following the recommendation.

### D08.6 — Fluxes and EMFs at fine/coarse boundaries

How are conservation and the divergence of B kept exact across refinement boundaries?

**Options**

- **A. Flux and EMF correction within the same step, as Athena++.** All levels advance with the same time step. At a fine/coarse face, the coarse block replaces its own flux by the area-weighted sum of the fine fluxes before updating, and its edge EMFs by the length-weighted sum of the fine EMFs. Kernels write the fluxes and EMFs on a block's *boundary faces and edges* into small per-block flux registers, registered in the state (D06.6). Interior fluxes stay in worker scratch (D05).
- **B. Refluxing after the fact** **[GK]** (Berger–Colella): the coarse update is corrected after the fine levels have finished their substeps. Needed if levels are subcycled, more bookkeeping.
- **C. No correction.** Conservation and ∇·B = 0 would be violated at every refinement boundary, against the correctness criterion.

**Recommendation.** A, consistent with one time step for all levels, the Athena++ choice. D11 decides whether levels are subcycled; if it chooses subcycling, B replaces A. Flux registers on boundary faces only cost a thin layer per block instead of full face arrays. This serves **correctness**.

**Decision.** *(2026-10-12)* **A, flux and EMF correction within the same step**, as the physically most correct choice and the most robust basis for the framework. It presupposes that all refinement levels advance with the same time step. Should D11 choose to subcycle levels instead, that sub-decision will have to supersede this one (with B).

## 4. Consequences for higher layers

**For every layer**

- All movement of data between blocks goes through exchange plans: tables of regions built once from the mesh and rebuilt when it changes. They are executed by a backend: a compiled copy kernel within a process, one call per worker and stage, without the GIL. A later MPI backend uses the same plans (D08.1, D08.2).
- Each block fills its own ghost zones from the owned cells and faces of its neighbours, including diagonal ones; no direction waits for another (D08.1).
- Values on faces and edges shared by two blocks are computed by both, identically. The exchange keeps the owner's copy. Nothing is averaged (D08.3).
- Every input to a kernel must agree between the blocks that share a face, including geometry: positions, areas and lengths are computed from global indices, never accumulated per block (D08.3, D07.6).

**For the verification of D02**

- A test asserts that the two copies of every shared face and edge agree bit for bit, alongside the existing invariants (1 against N workers, different block sizes).
- A test with too few ghost cells must fail visibly (E08.2: one ghost cell breaks constrained transport). That checks that the ghost width is derived correctly from the operators (D07.5).
- Conservation tests respect the boundary conditions: periodic boundaries conserve everything, reflecting ones mass and energy (as Ulula's monitor distinguishes).

**For brief D06 (data model) and the registry**

- The registry gains, per variable: its exchange flag, parity under reflection, restriction and prolongation operators (D08.5), and the boundary-condition overrides of D08.4.
- Flux registers for the boundary faces and edges of each block are registered state arrays (D08.6). Interior fluxes stay in worker scratch.

**For brief D09 (execution model)**

- Per stage, the order is: exchange between blocks, then physical boundary conditions on the primitive variables of boundary blocks, then conversion of those ghost zones to conserved variables, then the kernels (D08.4).
- In the Linux container, the standard interpreter still collapsed beyond 4 workers even with compiled ghost copies (E08.1). The per-block kernel calls themselves now hold the GIL most. D09 should consider looping over a worker's blocks inside compiled code, one call per worker and stage for the kernels too.

**For brief D10 (numerical building blocks)**

- Kernels must write the fluxes and EMFs of a block's boundary faces and edges into its flux registers when refinement is active (D08.6).
- Built-in boundary conditions are compiled kernels acting on the primitive variables of the ghost zones, using each variable's parity (D08.4).

**For brief D11 (time integration)**

- Flux and EMF correction within the step (D08.6) assumes one time step for all refinement levels. Choosing subcycling in D11 would require superseding D08.6 with refluxing after the fact.

**For brief D12 (physics module interface)**

- Modules declare per variable how it behaves at boundaries (parity, overrides) and under refinement (operators), or accept the defaults.
- User boundary conditions are functions that receive a boundary block's views and geometry and fill any part of a domain face. A per-variable override, such as a metal-rich inflow, is the typical use.

**For the MPI backend (D05.1)**

- It packs each exchange plan's regions per remote neighbour into one buffer, sends, and unpacks on arrival. Restriction for coarser neighbours happens before packing, prolongation after unpacking (D08.5).
