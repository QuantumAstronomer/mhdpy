# D06 — Data model

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-11 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how the data of a simulation is held in memory. That covers the order of the indices of a variable array, how lower-dimensional problems are stored, how variables are grouped into arrays, how face-, edge- and node-centred data are stored, how variables are declared and described, and which representations of the state are kept. The data model is the contract between nearly every other layer. Kernels (D04, D10) index into it, the mesh (D07) allocates it, communication (D08) copies it, the physics modules (D12) declare their variables in it, and I/O (D14) writes it. It is also the decision that is hardest to change later, because every one of those layers depends on it.

The earlier briefs already fix several requirements:

- **D03 (discretisation).** The data model must hold cell-, face-, edge- (line-) and node-centred data. The magnetic field must be registrable either face-centred (for constrained transport) or cell-centred (for GLM cleaning). Cells may hold several values (DG coefficients). The meaning of a stored value (cell average, point value, coefficient) is explicit metadata. Passive scalars are native and advected with the mass flux, and a dual-energy variable is optional. The number of ghost cells is a parameter.
- **D04 (backend).** Kernels are compiled functions over C-contiguous double-precision arrays, with the innermost loop along the contiguous index. They take all arrays as arguments and allocate nothing.
- **D05 (parallelism).** The block is the unit of data ownership. All blocks of a process must be storable as one array with the block index first (`[block, var, …]`), with per-block views for the kernels. Scratch arrays belong to a worker. The arithmetic of a kernel must not depend on where block boundaries lie.
- **D02 (verification).** Kernels perform the same sequence of operations in every direction, so that the same problem along x, y and z gives identical results.

**The intended layering.** Three components share the work, and the data model must fit between them. The terms themselves are fixed in D07.

- **The grid** describes the geometry of one block and holds no data. It covers the extents, active directions, ghost width, and the coordinates of cells, faces, edges and nodes. It is told the ghost width by whoever builds it, without needing to know why that width was chosen.
- **The mesh** arranges the grids into the block structure and knows how they border each other.
- **The state** describes all variables of the simulation (the registry of D06.6) and stores them for all blocks of a process. Each grid gets a view of its own part.

This is the separation of Pyro, whose `Grid2d` holds geometry only while `CellCenterData2d` registers and holds the data on it. It is also the central idea of Athena++ (S20): the mesh is independent of the physics solved on it. Two refinements follow from the earlier briefs:

- **Storage is owned by the state, process-wide, not by individual grids.** D05.6 keeps the blocks storable as one array per process, so a block's data is a view into that array rather than an allocation of its own (D06.4).
- **"Independent of the data" means independent of what the variables *mean*, not that the mesh never touches them.** The mesh exchanges ghost cells, restricts and prolongates under refinement, and redistributes blocks between processes. It does all of that generically, guided by the metadata of the registry (D06.6). The dependencies run from the mesh to the grid and to the state's metadata, never from the state into the mesh. When refinement creates or removes blocks, the mesh decides which, the state resizes its storage, and the mesh fills the new blocks through the registered operators (D07, D08).

**What the references do** (syntheses in `References/`):

| | Layout | Index order | Lower dimensions | Variables |
|---|---|---|---|---|
| Athena (C) | array of structs: each cell a `ConsS` struct | `U[k][j][i]`, x contiguous **[GK]** | separate 1D, 2D and 3D integrators | fixed order, documented as "cannot be changed" |
| Athena++ | struct of arrays (`AthenaArray`, `u(n, k, j, i)`), required by its vectorised kernels | x contiguous | always 3D arrays, extent 1 in unused directions | compile-time enums (`IDN`, `IM1`, …) plus a configured number of scalars; face fields in separate arrays per direction; arrays registered per block for refinement and load balancing |
| Pyro | array of structs | `[x, y, var]` | 2D only | registered by name (`register_var`) before allocation, then locked; views by name; derived quantities by callback; per-variable boundary conditions |
| Ulula | struct of arrays | `[var, x, y]` | 1D has a y extent of 1 | name → row dictionaries, rows present only when the physics needs them; primitive and conserved arrays both kept |

Athena++ moved from the array-of-structs layout of Athena to struct of arrays, and the Athena synthesis lists the old fixed variable order among the lessons learned: fragile, and in the way of new physics. Both Athena++ and Ulula keep primitive and conserved variables, and Athena++ always carries three velocity (and magnetic-field) components, also in 1D and 2D.

## 2. Evidence

### E06.1 — Memory layout, index order and dimensionality

**Method.** [`experiments/E06.1c-layouts.py`](experiments/E06.1c-layouts.py) (natively, one thread) evaluates the time derivative of the D04 hydro kernel on one block in several data layouts. The kernel here has five variables: three velocity components, as any 3D-capable code needs, also in 2D. It measures cells per second for one evaluation and compares every result with the 3D kernel in the x-contiguous layout. The kernels:

- [`E06.1a-kernel2d.py`](experiments/E06.1a-kernel2d.py), a 2D kernel in struct-of-arrays layout, `u[var, j, i]`. The same kernel in array-of-structs layout, `u[j, i, var]`, is derived from it by permuting the indices of every array access.
- [`E06.1b-kernel3d.py`](experiments/E06.1b-kernel3d.py), a 3D kernel in the layout of Athena++, `u[var, k, j, i]` with x contiguous. It is written *generically*: one stencil routine serves all three directions, with the direction given as run-time index offsets. Directions with extent 1 have no ghost cells and no fluxes, so 2D and 1D problems are 3D arrays with extent 1 in z (and y).
- [`E06.1d-kernel3d-specialised.py`](experiments/E06.1d-kernel3d-specialised.py), the same 3D kernel *direction-specific*: written in the style of the 2D kernel, with every direction written out and every variable unrolled. It was generated mechanically from the 2D kernel.
- The generic 3D kernel with x as the *slowest* index (`u[var, x, y, z]`, the order of Ulula and of the D04 and D05 experiments). In this order, lower-dimensional data has extent 1 in the contiguous direction. It is obtained by handing the kernel arrays with relabelled axes.

Full output: [`results/E06.1c-layouts.md`](experiments/results/E06.1c-layouts.md).

**Results.** Million cells per second for one evaluation of the time derivative (in brackets: relative to the generic 3D kernel with x contiguous):

| Layout and kernel | 1D, 4096 cells | 2D, 64² | 2D, 512² | 3D, 32³ | 3D, 64³ |
|---|---|---|---|---|---|
| 2D kernel, struct of arrays `[var, j, i]` | — | 17.4 (1.65) | 12.4 (1.50) | — | — |
| 2D kernel, array of structs `[j, i, var]` | — | 10.2 (0.97) | 6.5 (0.78) | — | — |
| 3D kernel, direction-specific, x contiguous | 33.3 (1.90) | 16.1 (1.53) | 12.5 (1.51) | 8.7 (1.49) | 8.1 (1.44) |
| 3D kernel, generic, x contiguous `[var, k, j, i]` | 17.6 (1.00) | 10.5 (1.00) | 8.3 (1.00) | 5.9 (1.00) | 5.6 (1.00) |
| 3D kernel, generic, x slowest `[var, i, j, k]` | 7.7 (0.44) | 8.4 (0.80) | 7.0 (0.84) | — | — |

- **Struct of arrays is 1.7–1.9× faster than array of structs** for the same 2D kernel. With all variables of a cell next to each other, a loop along the contiguous direction strides over five values at a time, and the compiler can no longer vectorise it **[GK]**. This confirms the move from Athena to Athena++.
- **One 3D kernel serves 1D and 2D at no measurable cost, if it is written direction by direction.** The direction-specific 3D kernel on 2D data is as fast as the dedicated 2D kernel (1.53 against 1.65 at 64²; equal at 512²), and its results are bit-for-bit identical.
- **Code style decides much more than generality:** the generic stencil with run-time offsets is 1.4–1.9× slower than the same arithmetic written per direction. Writing every direction out by hand triples the code, which is why the direction-specific kernel here was generated from the 2D one.
- **x must be the contiguous index.** With x slowest, a 1D problem runs at 0.44× and a 2D one at 0.8×, because the innermost loop then runs over a direction of extent 1. Only the order in which lower dimensions keep the contiguous index works well for 1D, 2D and 3D alike.
- **The x-slowest results also differ in the last bits (up to 7 × 10⁻¹² relative).** That variant permutes the roles of the velocity components, which changes the order of additions such as v_x² + v_y² + v_z². Summation order matters for the bit-for-bit invariants of D02. The same problem along x, y and z only gives identical results if kernels treat the components symmetrically, a requirement for D10.
- **3D blocks are slower per cell than 2D ones** (8 × 10⁶ against 1.25–1.6 × 10⁷), as expected for three flux directions.

### E06.2 — Ghost exchange and the grouping of variables

**Method.** [`experiments/E06.2-ghost-exchange.py`](experiments/E06.2-ghost-exchange.py) (natively, one thread) fills all ghost cells of 256 blocks of 64² cells. That is a periodic 16 × 16 arrangement with two ghost cells and six cell-centred variables: the five of hydrodynamics plus a metallicity scalar, as in the thesis problem. The variables are grouped in four ways:

- one array for all variables;
- one array per physics module (hydro, scalars);
- one array per variable;
- one array for all variables, with every ghost cell of every block filled by a single vectorised NumPy call.

Each copy is a NumPy assignment of one ghost region from the neighbouring block. Full output: [`results/E06.2-ghost-exchange.md`](experiments/results/E06.2-ghost-exchange.md).

**Results.**

| Grouping | Copies per block | Time per block | Relative to one evaluation of the time derivative |
|---|---|---|---|
| One array for all variables | 8 | 24 µs | 9 % |
| One array per module | 16 | 34 µs | 13 % |
| One array per variable | 48 | 68 µs | 26 % |
| One array, one vectorised call for everything | 1 | 27 µs | 11 % |

- **The cost is set by the number of copies, about 3 µs each,** not by the amount of data. Every separate array multiplies it.
- **Even with one array, ghost filling in NumPy costs about 10 % of a kernel evaluation,** twice per Runge–Kutta step. Under the standard interpreter it also holds the GIL (D05.4). Moving it into compiled code is a candidate for D08.
- **Vectorising the copies into one NumPy call gains nothing:** indexed copies are slower per element than slice copies.

**What the two experiments mean together.** The fast layout is struct of arrays with x contiguous and every variable of one centring in one array: `[block, var, k, j, i]`. One 3D form serves every dimensionality at no cost, provided kernels are written direction by direction, which suggests generating them rather than writing them three times.

## 3. Decisions

### D06.1 — Layout of the variables of a cell

Are the variables of a cell stored next to each other (array of structs) or is each variable a contiguous field (struct of arrays)?

**Options**

- **A. Struct of arrays,** `u[var, …]`, as Athena++ and Ulula. Each variable is a contiguous field; kernels stream through each one.
- **B. Array of structs,** `u[…, var]`, as Athena (C) and Pyro. The variables of a cell are adjacent, which suits code that handles one cell at a time. 1.7–1.9× slower in E06.1, and the fixed struct order was the fragility Athena's documentation warns about.

**Recommendation.** A, struct of arrays. It was much faster for the same kernel (E06.1), it is what the compiled-loop style of D04 needs, and it lets the number and order of variables follow from registration (D06.6) instead of a fixed struct. This serves **performance** and **extensibility**.

**Decision.** *(2026-10-11)* **A, struct of arrays**, following the recommendation: it was clearly the best-performing layout (E06.1).

### D06.2 — Index order

Which spatial index is contiguous in memory?

**Options**

- **A. x contiguous:** `u[var, k, j, i]` with i along x, j along y and k along z, as Athena++. Lower-dimensional problems keep the contiguous index; unused directions have extent 1 at the front. Indexing reads "backwards" (z, y, x) for users used to `u[x, y]`.
- **B. x slowest:** `u[var, i, j, k]`, as Ulula and the D04/D05 experiments; natural to read. Lower-dimensional problems have extent 1 in the *contiguous* direction, which made 1D 2.3× and 2D 1.2× slower in E06.1.

**Recommendation.** A, x contiguous. Only this order keeps the innermost loop long in 1D, 2D and 3D alike (E06.1). The reversed reading order is a matter of convention: users meet the data through named accessors and coordinate arrays (D07, D15), where the order can be documented once. This serves **performance**, at a small cost in **readability**.

**Decision.** *(2026-10-11)* **A, x contiguous** (`[var, k, j, i]`), following the recommendation. The performance difference measured in E06.1 is too large to give up for the more familiar reading order.

### D06.3 — Dimensionality

How are 1D, 2D and 3D problems stored and computed?

**Options**

- **A. Always three-dimensional,** as Athena++. Every array has three spatial indices; unused directions have extent 1 and no ghost cells, and kernels skip them. Vector quantities always have three components (velocity, magnetic field), so that 2.5D problems, such as an out-of-plane field in 2D MHD, need nothing special. One kernel per operation, as fast as a dedicated 2D one when written direction by direction (E06.1).
- **B. Separate code per dimensionality,** as Athena (C). 1D, 2D and 3D kernels and integrators, each specialised. No overhead, but three times the code to write, test and keep consistent.
- **C. Dimension-generic code** (loops over a run-time number of dimensions, stencils as offsets). One code path, but 1.4–1.9× slower in E06.1.

**Recommendation.** A, always three-dimensional, with kernels written direction by direction. E06.1 shows it costs nothing against dedicated 2D code, and it gives every operation a single implementation, tested once. The triplication of code within a kernel (three directions written out) is better handled by generating it than by abstracting it at run time, which E06.1 shows is expensive. How kernels are generated is a question for D10. This serves **performance** and **readability**: one kernel per operation, plain loops in each.

**Decision.** *(2026-10-11)* **A, always three-dimensional**, with kernels written direction by direction. E06.1 shows this is the clear way forward.

### D06.4 — Grouping of variables into arrays

How are the variables of a block grouped into arrays?

**Options**

- **A. One array per process for each kind of data:** all blocks, all registered variables of one centring and role. An example is the conserved cell-centred state, `[block, var, k, j, i]`, holding hydrodynamics, passive scalars and an optional dual-energy variable. Each physics module owns a contiguous range of variable indices in it. Ghost exchange, restriction and output treat the whole array at once. 9 % of a kernel evaluation for the ghost exchange in E06.2. Scalars sit next to the hydro variables, so one kernel can compute their fluxes with the mass flux, as D03.6 wants.
- **B. One array per physics module,** as Athena++ (hydro `u`, passive scalars `s` and the face field `b` are separate objects). Modules are more independent of each other, but every array needs its own exchange (13 % in E06.2), and kernels that couple modules take more arguments.
- **C. One array per variable,** as Pyro's per-name views suggest at the interface. Most flexible, but the most copies (26 % in E06.2).

**Recommendation.** A. It keeps the number of arrays, and therefore of copies, kernel arguments and exchange operations, at the minimum. It is the "pack" that D05.6 asks for. Module independence is preserved at the level that matters: modules declare their variables and get index ranges (D06.6), and they never need to know what else is in the array. This serves **performance** and **readability**.

For the layering of §1, A (like B and C, as long as the block index comes first) places the storage with the state, process-wide, and gives each grid a view (`pack[b]`) instead of arrays of its own. The alternative, every block allocating its own arrays as in Athena++, would keep data and grid closer together, but it would give up the per-process pack that D05.6 kept possible for GPUs. AthenaK **[GK]** moved from the first arrangement to the second for exactly that reason. Under refinement, the pack is resized when the mesh adds or removes blocks.

**Decision.** *(2026-10-11)* **A, one array per process for each centring and role**, following the recommendation. The choice shapes how new physics modules are written: a module does not own arrays, but declares variables and receives index ranges in shared arrays. It must therefore be explained in the documentation for developers of physics modules (§4).

### D06.5 — Storage of face-, edge- and node-centred data

How are staggered quantities, such as the face-centred magnetic field of constrained transport and the edge-centred EMFs, stored?

**Options**

- **A. Natural extents, one array per direction,** as Athena++: x-faces have one more entry along x (`(nk, nj, ni + 1)` plus ghost cells), y-faces one more along y, and so on. No wasted memory, but three differently shaped arrays per staggered quantity, so no single pack per centring, and three times the exchange and argument lists.
- **B. Padded to a common shape:** every face-, edge- and node-centred array has extent n + 2g + 1 in *every* active direction, with the component as an index (`[block, component, k, j, i]`). Index i of an x-face is the face between cells i − 1 and i. The entries that a component does not need (for x-faces, the last layer in y and z) are simply unused. All components of a staggered quantity share one array, and all staggered quantities of one centring can share one pack. The memory overhead is one layer per direction: about 1.5 % per component for a 64² block in 2D and 3 % for a 64³ block in 3D, compared with natural extents.
- **C. Staggered data in the shape of the cell arrays,** with the face at i − ½ stored at index i. Uniform with cell data, but the outermost face of the ghost region does not exist, which complicates boundary handling and refinement.

**Recommendation.** B. It gives staggered data the same "one array per centring" structure as cell data (D06.4), at an overhead of a few per cent of memory. Kernels index all components the same way, and the convention (index i ↔ the face at i − ½) is uniform for faces, edges and nodes. A avoids that overhead, but triples the arrays, exchanges and kernel arguments. This serves **readability** and **performance**.

**Decision.** *(2026-10-11)* **B, padded to a common shape**, following the recommendation. With natural extents, the three components of a face- or edge-centred quantity would each have a different shape and could not share one array. That would undo, for staggered data, the choice of one array per centring made in D06.4. Padding keeps the rule uniform. Cell-centred and staggered data still live in separate arrays, since their extents differ by one; the rule is one array per centring, not one array for everything.

### D06.6 — Declaring and describing variables

How do physics modules declare their variables, and what is known about each?

**Options**

- **A. Fixed indices, decided before the run starts,** as Athena's and Athena++'s compile-time enums (`IDN`, `IM1`, …) plus a configured number of scalars. Simple and fast, but every new variable means editing a central list, which is the extensibility problem Athena++ has with its preprocessor flags.
- **B. A registry filled at set-up and then frozen,** as Pyro (`register_var` before `create()`, which locks the container) and Ulula (name → row dictionaries). Each physics module registers its variables with metadata before allocation. The registry then assigns every variable its array and index range and is frozen for the run. Kernels receive integer indices and ranges, never names; Python code and users access variables by name through views.
- **C. Free-form named arrays,** added and removed at any time. Most flexible, but nothing could rely on the set of variables, and grouping into packs (D06.4) would be impossible.

The metadata a registered variable would carry, from what earlier briefs require:
- its name, owning module and description;
- its centring (cell, face, edge, node) and number of components;
- for vectors, which component belongs to which direction, needed for mirror-symmetry tests, reflecting boundaries and the rotation of components in direction-specific kernels;
- the meaning of its values (cell average, point value, DG coefficients) and the number of values per cell (D03);
- its role: conserved, primitive, auxiliary or derived;
- its behaviour at a reflecting boundary (even or odd, as Pyro's per-variable boundary types);
- how it is restricted and prolongated under refinement (D08);
- whether it is exchanged, written to outputs and saved in restarts.

**Recommendation.** B, a registry that is frozen before allocation. It is the mechanism that makes D03's requirements expressible: centrings, multi-valued cells, value meaning, and a magnetic field registered face- or cell-centred. It also lets layers such as communication, refinement and I/O handle any variable without knowing the physics, which is the central design idea of Athena++ (S20). Freezing it keeps the fast path simple: after set-up, every index is a plain integer. This serves **extensibility** without costing **performance**.

**Decision.** *(2026-10-11)* **B, a registry filled at set-up and then frozen**, following the recommendation, as the most logical choice.

### D06.7 — Which representations of the state are stored

Are only the conserved variables stored, or the primitive variables as well?

**Options**

- **A. Conserved variables only.** Every kernel that needs primitives (fluxes, time step, source terms, output) converts them itself, into scratch arrays, as the D04–D06 experiments did. Least memory, one source of truth. But the conversion is repeated in every kernel that needs it, and so are floors and other corrections applied during the conversion. For MHD with a general equation of state, or for relativistic flows, the conversion is iterative and expensive **[GK]**.
- **B. Conserved and primitive variables both stored,** as Athena++ and Ulula. Primitives are computed once per stage, ghost cells included, with floors applied in one place, and every later kernel reads them. Costs a second cell-centred array per process and a rule for when primitives are valid.

**Recommendation.** B. A conversion done once, in one place, is cheaper whenever more than one kernel needs primitives, and the thesis problem has several: fluxes, cooling, conduction and the time step. More importantly, it guarantees that every kernel sees the same primitives with the same floors, which matters for **correctness**. It also makes output and analysis direct, which Ulula lists among its strengths. The memory cost, one more array of cell-centred variables, is small next to the scratch and stage registers a run needs anyway.

**Decision.** *(2026-10-11)* **B, conserved and primitive variables both stored**, following the recommendation.

## 4. Consequences for higher layers

**For every layer**

- All field data is double precision, C-contiguous, in struct-of-arrays layout with x contiguous. Each array is `[block, var, k, j, i]` for one centring and role, per process. A block's data is the view `array[b]`, and kernels receive such views or whole arrays (D06.1–D06.4).
- Every array is three-dimensional. Directions with extent 1 have no ghost cells, and vector quantities always have three components. Code never branches on "the dimension of the problem", only on whether a direction is active (D06.3).
- Cell-centred arrays have extent n + 2g in every active direction. Face-, edge- and node-centred arrays have n + 2g + 1, with the component as the variable index, and index i of a staggered quantity refers to the position i − ½ along each staggered direction (D06.5).
- Variables are declared through the registry before allocation and never afterwards. After set-up, kernels see only integer indices and ranges; Python code and users access variables by name through views (D06.6).
- The layering of §1 holds: grids describe geometry and hold no data, the mesh arranges grids and moves state data generically through registry metadata, and the state owns all storage.

**For brief D07 (mesh and geometry)**

- D07 fixes the terms grid, block, mesh and state, along the layering of §1.
- Grids provide the shape of the state's arrays (extents, active directions, ghost width) and the coordinates of every centring.
- Kernels also need geometry as arrays: cell widths, and in curvilinear coordinates face areas and volumes. For the same reason as the state (D05.6), that geometry should be available packed per process, `[block, …]`.
- Under refinement, the mesh decides which blocks are created and removed. The state then resizes its arrays, and the mesh fills new blocks through the registered operators.

**For brief D08 (boundaries and communication)**

- Exchange, restriction and prolongation work per array and centring, guided by the registry's metadata: whether a variable is exchanged, its refinement operator and its reflection parity. One array per centring keeps the number of copies at its minimum. Even then, ghost filling in NumPy costs about 10 % of a kernel evaluation and holds the GIL (E06.2), which makes compiled ghost copies a candidate (D05.4).
- Faces shared by two blocks appear in both blocks' padded staggered arrays. Their two copies must agree (D05.5).

**For brief D10 (numerical building blocks)**

- Kernels are written direction by direction. A generic stencil with run-time offsets was 1.4–1.9× slower (E06.1). Since three directions written out by hand triple the code, D10 decides how direction-specific kernels are produced, for example generated from one template, as the E06.1 kernel was.
- For the bit-for-bit direction-symmetry tests of D02, kernels must treat velocity and field components symmetrically, including the order of additions such as v_x² + v_y² + v_z² (E06.1).

**For brief D11 (time integration)**

- Stage registers (copies of the conserved state for multi-stage integrators) are additional arrays of the same layout, declared through the registry. Their number follows from the integrator chosen there.

**For brief D12 (physics module interface) and the developer documentation**

- A physics module does not allocate arrays. It registers its variables with their metadata and receives index ranges in shared arrays: hydrodynamics, scalars and dual energy share the conserved cell-centred array, for example.
- Primitive variables are a second registered array, computed once per stage, with floors applied in one place. Modules read primitives from there rather than converting themselves (D06.7).
- Because this differs from the usual picture of a module owning its arrays, the documentation for writing physics modules explains the data model: arrays per centring and role, index ranges, views by name, and the frozen registry (D06.4).

**For brief D14 (I/O)**

- Output and restart flags are registry metadata. Writers iterate over registered variables and need no knowledge of the physics.
- Because of the reversed index order (`[var, k, j, i]`), output formats and user-facing accessors document the axis order explicitly. Users meet data through named, documented accessors rather than raw indices.
