# D05 — Parallelism model

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-11 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how mhdpy uses more than one processor core. One computer is a single node, where all cores share one memory. Several computers form a cluster, where each node has its own memory. The brief decides at which granularity work is divided, which kind of worker carries it out (threads, processes or MPI ranks), how results stay deterministic when the work is divided, and what this keeps open for GPUs. How work is scheduled over blocks in detail (a fixed step function or a task graph) is left to D09. How blocks are laid out and exchange ghost cells is left to D07 and D08. This brief fixes the model those layers implement.

The choice is constrained from several sides:

- **Performance (architecture.md §1.3).** A thesis-scale run must reach about 2 × 10⁶ cell updates per second on the development laptop and 3 × 10⁷ on a small server. E04.5 measured up to 8 × 10⁶ for pure hydrodynamics on one core of the laptop. Cooling, conduction and a passive scalar will make each cell update several times more expensive (an estimate, to be refined), so the server target needs roughly a dozen cores used efficiently, and the laptop target several.
- **Installation (§1.4).** Installation must remain a single `pip` or `uv` command. Whatever the parallel model needs at run time must therefore come as wheels, or be optional.
- **Verification (D02).** Results within one environment must be deterministic: D02's consequences exclude reductions whose order depends on thread scheduling, unless that order is fixed. Bit-for-bit invariants within a run are a test method of D02.3, and a parallel model can add new ones (the same result for any number of workers).
- **Kernels (D04).** Compiled kernels in Cython's pure Python mode process one whole block per call, and Python orchestrates. Kernels can release the GIL (`nogil`) or share their loops among OpenMP threads (`prange`). Apple's compiler has no OpenMP, so OpenMP in macOS wheels means bundling an OpenMP runtime. E04.1 measured only 2.5–3× on 8 virtual CPUs with OpenMP inside one kernel.

**Python's own constraint [GK].** Standard CPython has a global interpreter lock (GIL): only one thread executes Python code at a time. Threads can still run in parallel inside compiled code that releases the GIL, but every piece of Python between kernel calls is serialised. PEP 703 introduced a *free-threaded* build without the GIL. It was experimental in Python 3.13 and became officially supported in 3.14 (PEP 779), but it is not the default. It is a separate interpreter (`python3.14t`), with separate wheels (tagged `cp314t`), and compiled modules must declare themselves safe for it, or importing them switches the GIL back on. The standard alternative to threads is processes, which have no shared interpreter state at all, at the cost of explicit shared memory or messages.

**What the references do** (syntheses in `References/`):

- **Athena** (C) decomposes the domain into *Grids*, one per MPI process (slab, pencil or block decomposition), and exchanges ghost zones direction by direction, x then y then z. S20 later identified that sequential dependency as a scaling bottleneck.
- **Athena++** makes the *MeshBlock*, a block with the same number of cells as every other, the unit of decomposition, of refinement and of threading. Even a uniform grid is a set of MeshBlocks. Parallelism is hybrid: MPI between processes, OpenMP within a process. OpenMP is **coarse-grained**: each thread updates whole MeshBlocks, because S20 found loop-level fork/join inefficient. The documentation recommends at least 32³, preferably 64³, cells per block per thread. Task lists overlap communication with computation. Load is balanced by moving blocks along a Z-order curve according to their measured cost, which needs several blocks per process. S20 reports 84 % weak-scaling efficiency on about 500 000 threads. Nondeterministic MPI ordering is one of the reasons Athena++ averages the two copies of a face-centred magnetic field shared by neighbouring blocks: otherwise round-off lets them drift apart.
- **AthenaK [GK]**, the successor of Athena++, runs on GPUs through Kokkos and processes all MeshBlocks of a process together in one kernel launch (a "MeshBlockPack").
- **Pyro** and **Ulula** have no parallelism. Ulula's author suggests JAX or Numba for threading and considers MPI too complex for a teaching code.
- **ZEUS** was serial; its successor ZEUS-MP **[GK]** added MPI domain decomposition.

## 2. Evidence

### E05.1 — Can the parallel runtimes be installed with one command?

**Method.** [`experiments/E05.1-availability.py`](experiments/E05.1-availability.py) (development machine, 2026-10-10) completes what E01.1 measured for wheels. E01.1 found that NumPy, mpi4py, SciPy, h5py and matplotlib all publish wheels for the free-threaded Python 3.14t on all four target platforms, and Cython a pure-Python wheel. This experiment adds three checks:

- whether uv offers the free-threaded interpreter itself for each platform;
- which MPI libraries are published as wheels on PyPI;
- a live test of the route a user would take: a fresh virtual environment, one `uv pip install mpi4py mpich` (or `openmpi`), and an allreduce over two processes started with that environment's `mpiexec`. The test ran natively on macOS and in a Linux container, each with the standard and the free-threaded interpreter.

Full output: [`results/E05.1-availability.md`](experiments/results/E05.1-availability.md).

**Results.**

| | macOS x86-64 | macOS arm64 | Linux x86-64 | Linux aarch64 |
|---|---|---|---|---|
| Free-threaded CPython 3.14.8 from uv | ✓ | ✓ | ✓ | ✓ |
| MPICH 5.0.2 as a wheel | ✓ | ✓ | ✓ | ✓ |
| Open MPI 5.0.11 as a wheel | ✓ | ✓ | ✓ | ✓ |
| Intel MPI (`impi-rt`) as a wheel | — | — | ✓ | — |

The live test succeeded in all eight combinations (macOS and Linux, Python 3.14 and 3.14t, MPICH and Open MPI), each in 2 to 10 seconds including installation.

- **Free-threaded Python and MPI can both be installed with one command, wherever mhdpy is meant to run.** Neither needs a compiler or a system package.
- **One pitfall was found.** A first version of the test used `uv run --with mpi4py --with mpich`. That failed, because uv's layered temporary environments hide the MPI library from mpi4py. That is a property of `uv run --with`, not of the packages, but the installation documentation must avoid it.
- **[GK]** On a cluster, mpi4py is normally used with the cluster's own MPI library, which knows the fast interconnect, rather than the PyPI wheels. mpi4py supports this, but it requires building mpi4py against that library.

### E05.2 — Shared-memory strategies: scaling and determinism

**Method.** One SSP-RK2 step of the D04 hydro kernel ([`E05.2a-kernels.py`](experiments/E05.2a-kernels.py), the E04.3 kernel generalised to rectangular blocks, plus the two stage combinations of E04.5) runs on a periodic grid of 2048 × 512 cells, a thesis-like 4:1 domain of 10⁶ cells. [`E05.2b-scaling.py`](experiments/E05.2b-scaling.py) parallelises it in three ways:

- **Loop-level OpenMP:** the whole grid is one block, and every loop inside a kernel call is shared among OpenMP threads, as in E04.1.
- **Block-level, Python threads:** the grid is divided into square blocks of 32², 64² or 128² cells, each with its own ghost cells. A team of Python threads updates whole blocks; the kernels run serially inside each call and release the GIL.
- **Block-level, processes:** the same blocks and the same worker code, with a team of spawned processes and all blocks in shared memory.

In both block-level teams, each worker owns a fixed, contiguous range of blocks and keeps its own scratch arrays. Per step it fills its blocks' ghost cells from the neighbouring blocks (NumPy copies), computes the first stage, waits at a barrier, fills again, computes the second stage and waits again. Every configuration is first compared bit for bit with a single-block serial reference after four steps, then timed with 1 to 12 workers.

[`E05.2d-run.py`](experiments/E05.2d-run.py) runs the benchmark four times, one after the other:

- natively on macOS (6 cores, 12 hardware threads), with Python 3.14 and the free-threaded 3.14t. Apple's compiler has no OpenMP, so there is no loop-level variant here;
- in a Linux container like that of E04.1 ([`E05.2c-Dockerfile`](experiments/E05.2c-Dockerfile), 8 virtual CPUs, GCC with OpenMP), again with both interpreters (there Python 3.14.2 and 3.14.3).

[`E05.2e-figure.py`](experiments/E05.2e-figure.py) draws the figure. Full output: [`results/E05.2d-scaling.md`](experiments/results/E05.2d-scaling.md).

![E05.2](experiments/results/E05.2e-scaling.png)

**Results.** Million cell updates per second, with the speed-up over one thread on a single block in brackets, for blocks of 64² (other block sizes in the full output):

| Strategy | Natively, 1 worker | Natively, 6 workers | Natively, 12 workers | Container, 8 workers |
|---|---|---|---|---|
| Single block, one thread (reference) | 7.3 | — | — | 4.3 (1 worker) |
| Loop-level OpenMP, one block | (no OpenMP) | — | — | 13.9 (3.2×) |
| Python threads over blocks, Python with GIL | 6.8 | 22.2 (3.1×) | 21.3 (2.9×) | 3.4 (0.8×) |
| Processes over blocks | 7.4 | 31.6 (4.4×) | 32.5 (4.5×) | 18.0 (4.2×) |
| Python threads over blocks, free-threaded Python | 8.1 | 38.7 (5.4×) | 29.7 (4.1×) | 22.3 (5.1×) |

- **Every configuration gave a result bit-for-bit identical to the serial single-block reference.** That covered 173 runs: every strategy, block size, number of workers, interpreter and platform. Dividing the grid into blocks and the blocks among workers does not change the result, because every cell is computed with the same arithmetic, whichever block or worker it belongs to.
- **Block-level parallelism scales better than loop-level parallelism:** 4.2–5.1× against 3.2× on 8 virtual CPUs. This agrees with Athena++'s experience (S20). Loop-level OpenMP opens and closes a parallel region for every loop, and the Python orchestration between kernel calls stays serial. At block level, each worker also does its own ghost filling.
- **With the GIL, threads do not scale.** Natively they level off at about 3×. In the Linux container they get *slower* with more than three threads, ending below the speed of one thread. With 32² blocks they reach 0.3× at 8 threads. Each kernel call releases and reacquires the GIL, and the Python between calls (the loop over blocks and the ghost copies) must hold it. With many threads, waiting for the GIL dominates. Why the effect is so much stronger in the container is not established.
- **Free-threaded Python removes that limit:** threads then scale at least as well as processes, natively up to 5.4× on 6 cores. On one worker, the free-threaded interpreter was as fast as the standard one, because the time is spent in compiled code. The compiled kernels kept the GIL off (`freethreading_compatible`).
- **Processes scale as well as free-threaded threads** on either interpreter, at the cost of explicit shared memory, spawning (each process imports Python and NumPy anew) and semaphores. A first version of the experiment failed because the parent released a barrier before a child process had received it.
- **Scaling flattens beyond the 6 physical cores,** and the hardware threads of hyperthreading add nothing. Even on 6 cores, the speed-up stays below 6. Likely causes are the lower clock frequency when all cores are busy and the shared cache and memory bandwidth, but this was not measured.
- **Block size matters for parallel runs.** On one core, 128² blocks were the fastest (E04.5). With 4 or more workers, 32² and 64² blocks scale clearly better than 128², presumably because each worker's working set then fits in its share of the cache. The per-block overhead costs about 10 % at 32² on one worker.
- **For pure hydrodynamics, the laptop reaches 3–4 × 10⁷ cell updates per second on 6 cores,** the server target of architecture.md §1.3. The additional physics will lower that.

### E05.3 — Global reductions and the order of summation

**Question.** E05.2 shows that the evolved state does not depend on the decomposition. Global *reductions* are different. The total mass or energy in a history file, or a norm inside a solver, is a sum over all cells. Floating-point addition is not associative, and a parallel code sums per block and then combines the partial sums. How much does the result then depend on the block size and on the order in which the partial sums are combined?

**Method.** [`experiments/E05.3-reductions.py`](experiments/E05.3-reductions.py) (natively, one thread) sums the total energy of a smooth state on a thesis-sized grid of 4096 × 1024 cells in several ways:

- with NumPy over the whole grid;
- per block of 32², 64² and 128², the partial sums combined in block order, in reverse order and in five shuffled orders;
- exactly rounded with `math.fsum`, over all cells, and per block with an exact combination of the per-block partial results.

It also takes the minimum over all cells, which is the reduction behind the time step, in all these orders. Full output: [`results/E05.3-reductions.md`](experiments/results/E05.3-reductions.md).

**Results.** Difference from the exactly rounded sum, in ulp (one ulp is 1.7 × 10⁻¹⁶ relative here):

| Method | Difference (ulp) | Time (ms) |
|---|---|---|
| NumPy over the whole grid | 0 | 3 |
| Per block of 32², in block order / reverse / 5 shuffled orders | −16 / −8 / −35 to 0 | 28 |
| Per block of 64², likewise | −4 / −7 / −14 to +4 | 11 |
| Per block of 128², likewise | +5 / +4 / +1 to +10 | 6 |
| Exactly rounded (`math.fsum`), whole grid | 0 | 335 |
| Exactly rounded per block (in Python), any order and block size | 0 | 1700–1950 |

- **The order of combination changes a global sum by up to a few tens of ulp,** about 10⁻¹⁵ relative. Each block size and each order gives a different result. That is irrelevant to the physics, but it breaks bit-for-bit comparisons.
- **A fixed order of combination makes a sum reproducible for a given decomposition, whoever computed each block.** It costs nothing.
- **Only an exactly rounded sum is independent of the decomposition as well.** In plain Python it is 100–700× slower than NumPy. On a 4096 × 1024 grid that is 0.3–2 s, as long as a whole time step or longer. **[GK]** A compiled exact accumulator would be much cheaper, but it is extra code.
- **The minimum is identical in every order,** since taking a minimum involves no rounding. The global time step is therefore deterministic in any decomposition.

**What the three experiments mean together.**

- Parallelising whole blocks is both faster and simpler to keep correct than parallelising loops. It also needs no OpenMP, which removes the one complication D04 foresaw for the macOS wheels.
- The kind of worker matters only through the GIL. Free-threaded threads and processes are equally fast; GIL-bound threads are not.
- Determinism is cheap for the state and for minima. For sums it costs either a fixed order (free, but tied to the decomposition) or exact rounding (independent of everything, but not free).
- Everything a parallel run needs can be installed with one command: the free-threaded interpreter through uv, and MPI as wheels.

## 3. Decisions

### D05.1 — Which levels of parallelism mhdpy targets

Is mhdpy parallel within one node only, or also across nodes, and when?

**Options**

- **A. One node only (shared memory).** Simplest. It covers both performance targets of architecture.md §1.3, since the small server is one node. But it closes the door to clusters, which every reference production code uses, and to the larger problems in the eventual scope (§1.2).
- **B. One node now; distributed memory designed in from the start and implemented later, with mpi4py as an optional extra (`mhdpy[mpi]`).** "Designed in" means three rules for the lower layers:
  - a block is the unit of data ownership;
  - every movement of data between blocks goes through one communication layer (D08), which copies in memory within a process and could send messages between processes;
  - every global reduction goes through one reduction function.

  No code reads another block's data directly. E05.1 shows that mpi4py and an MPI library install with one command on every target platform, also free-threaded, so the extra would not break the installation exception.
- **C. MPI from the start, as the only model** ("flat MPI": one process per core, also on a laptop). One model everywhere, and the same code path on a laptop and a cluster. But every parallel run must then be started with `mpiexec`, all inter-block exchange is message passing from day one, and on one node it is no faster than threads over shared memory (E05.2, processes).

**Recommendation.** B. The targets that are actually committed to (laptop and small server) are single-node, and E05.2 shows that one node reaches them for hydrodynamics. Distributed memory is an aspiration, but retrofitting it into a code whose layers freely access each other's data is notoriously hard. Designing the boundaries in now costs little: blocks, one communication layer, one reduction function. Those are structures that block-level threading needs anyway (D05.2). This serves **performance** on the committed targets and **extensibility** towards clusters, while keeping the **installation exception**: MPI never becomes a requirement.

**Decision.** *(2026-10-11)* **B: one node now, with distributed memory designed in and implemented later through mpi4py as an optional extra**, following the recommendation. The development machine and the future server are both single nodes, and multi-node clusters are far in the future, if they are ever reached. Very large runs would need them, though, so the provisions are made now: the block owns its data, one communication layer and one reduction function.

### D05.2 — Granularity of shared-memory parallelism

At which level is work divided among the cores of one node?

**Options**

- **A. Loop level:** the loops inside each kernel call are shared among OpenMP threads (`prange`), with the whole grid as one or a few blocks. E05.2: at most 3.2× on 8 virtual CPUs. The orchestration between kernel calls stays serial. It needs a compiler with OpenMP, and macOS wheels must bundle an OpenMP runtime (D04).
- **B. Block level:** each worker updates whole blocks, and the kernels themselves run serially and release the GIL. E05.2: 4.2–5.4×, with ghost filling also done in parallel. No OpenMP is needed. The same unit serves threads, processes and MPI ranks, and **[GK]** GPUs, where all blocks are processed in one launch (AthenaK). Every worker needs several blocks, so blocks are small (D07).
- **C. Both, nested:** blocks among workers, and loops within each block among further threads. Useful only when there are fewer blocks than cores. Two levels to tune, and OpenMP still required.

**Recommendation.** B, block-level parallelism. It was the faster strategy in every comparison (E05.2), it is what Athena++ arrived at for the same reason (S20), and it removes OpenMP from the build entirely. That simplifies the macOS wheels, which serves the **installation exception**, and avoids the known conflicts between several OpenMP runtimes in one Python process **[GK]**. It also makes the block the single unit of decomposition, as D05.1 B needs. This serves **performance** and **readability**: kernels stay plain serial loops.

**Decision.** *(2026-10-11)* **B, block-level parallelism**, following the recommendation: it was the best-performing strategy in every test of E05.2.

### D05.3 — Kind of worker on one node

Which workers carry out the block-level work within one node?

**Options**

- **A. Python threads.** All workers share one interpreter and one memory: the state, the problem setup and user functions are simply visible to all of them. Kernels release the GIL. On free-threaded Python they scale best of all (5.4× on 6 cores, E05.2). On standard Python they level off at 3×, or even slow down beyond three threads (Linux container, E05.2). Python code that runs in the workers must be thread-safe.
- **B. Processes with shared memory** (`multiprocessing`). They scale as well as free-threaded threads on any interpreter (E05.2). But every array that workers share must be allocated in shared memory, and everything else (problem setup, user functions such as boundary conditions or source terms) must be picklable and importable by the workers. Start-up takes seconds, since each process imports Python and NumPy, and errors in a worker are harder to report. That is a second, parallel infrastructure next to MPI.
- **C. MPI ranks, also within one node** (flat MPI, D05.1 C). As B, with messages instead of shared memory, and started with `mpiexec`.
- **D. A team abstraction with both threads and processes,** chosen at run time. E05.2 ran exactly this: one worker loop, two kinds of team. Best scaling on every interpreter, but two infrastructures to maintain and test, and user functions must still satisfy B's restrictions whenever processes are used.

**Recommendation.** A, Python threads, with free-threaded Python as the recommended interpreter for parallel runs (D05.4). Threads keep the code and the user interface simplest, and with the free-threaded build they are the fastest option measured. Processes would solve a problem that free-threaded Python already removes, at a large cost in complexity. They would also duplicate what MPI (D05.1) later provides anyway: several processes, for users who stay on the standard interpreter, and for clusters. The result is the same hybrid model as Athena++: threads over blocks within a process, MPI between processes. On the standard interpreter, threads remain correct but scale poorly. mhdpy should then default to a small number of workers and say why. This serves **performance** (on the free-threaded interpreter) and **readability**; the cost falls on **ease of use** for users of the standard interpreter, who must either install `python3.14t` (one uv command, E05.1) or accept limited scaling.

**Decision.** *(2026-10-11)* **A, Python threads**, with development focused on free-threaded Python. That interpreter is widely available (E05.1), and the real performance targets will need it anyway. Any limitations it turns out to have will be dealt with as they appear. Several processes, where needed, come from MPI (D05.1), not from a separate `multiprocessing` infrastructure.

### D05.4 — Support for free-threaded Python

How does mhdpy relate to the free-threaded build of Python?

**Options**

- **A. Not supported.** mhdpy runs on the standard interpreter only. Threads then scale poorly (D05.3 A), and parallel speed requires processes or MPI.
- **B. Supported as a first-class target from Python 3.14 on, next to the standard interpreter.** Wheels are built for `cp314t` as well (cibuildwheel supports it), CI runs the tests on 3.14t, and the compiled modules declare themselves free-threading compatible. Python code that runs inside workers must be thread-safe: no unsynchronised shared mutable state. Python 3.13t is excluded: it was experimental. The standard interpreter remains fully supported, in serial and with limited thread scaling.
- **C. Required:** mhdpy runs on free-threaded Python only. Simplest to test, but it drops Python 3.13 (D01.2), and users with a standard Python cannot even run a test problem.

**Recommendation.** B. It is what makes threads (D05.3) fast, and E01.1 and E05.1 show that the stack mhdpy depends on already supports it on every target platform. The cost is one more entry in the wheel and CI matrix, and the discipline of thread-safe orchestration, which a parallel code needs anyway. C would be premature while the free-threaded build is not yet Python's default. **[GK]** It is expected to become the default in a later Python version, at which point C would happen by itself. This serves **performance**, keeping the **installation exception** intact.

**Decision.** *(2026-10-11)* **B, free-threaded Python as a first-class target from 3.14 on, next to the standard interpreter**, following the recommendation. Although development focuses on the free-threaded build (D05.3), mhdpy must also perform well on the standard interpreter. E05.2 shows what that can mean:
- **On one thread,** the standard interpreter is exactly as fast, since the time is spent in compiled kernels. That speed must be kept.
- **With several threads,** what limits the standard interpreter is the Python that runs *while holding the GIL* between kernel calls: the loop over blocks and the ghost copies. Keeping that share small is therefore a design requirement for the layers that orchestrate the work (§4), not an optimisation to be added later. **[Assumption]** Done consistently, for example with ghost copies as compiled kernels that release the GIL, this should raise the thread scaling of the standard interpreter well above the 3× of E05.2. It is to be measured when D08 and D09 are designed.
- **Where threads on the standard interpreter still fall short,** several processes through MPI (D05.1) remain the route to more cores.

### D05.5 — Determinism of parallel runs

Which results must be identical, bit for bit, regardless of how the work is divided?

**Options**

- **A. The state is independent of everything; reductions are combined in a fixed order.**
  - The evolved state is identical for any number of workers, any scheduling, any block size and any decomposition. E05.2 shows this holds by construction, as long as every cell is computed with the same arithmetic in whichever block it lies.
  - Minima (the time step) are exact anyway (E05.3).
  - Sums are formed per block and combined in a fixed, canonical order of the blocks, independent of the worker or MPI rank that computed them. They are then independent of the number of workers and of scheduling, but not of the block size.
  - Where a test needs a sum that is independent of the decomposition as well, an exactly rounded sum is available.
- **B. Everything independent of everything:** all reductions exactly rounded. The strongest guarantee, but 100–700× the cost of a NumPy sum in Python (E05.3). It needs a compiled exact accumulator to be affordable.
- **C. Deterministic only for a fixed configuration** (same block size, same number of workers): sums combined in the order of the workers. Cheapest, but then a result changes with the number of cores, and "1 worker equals N workers" can no longer be tested.

**Recommendation.** A. It makes the strongest guarantee that costs nothing, and E05.2 shows it is attainable:

- **The state** is invariant to everything, and that adds two powerful invariant tests to D02.3: the same run with 1 and with N workers, and with different block sizes, must agree bit for bit.
- **Fixed-order sums** keep history output and solver norms independent of the hardware a run happens to use.
- **Exact rounding** remains a tool where a test needs it, not a cost every run pays.

The requirement this places on lower layers is concrete. No kernel's arithmetic may depend on where a block boundary lies. Values on faces shared by two blocks, such as fluxes and the EMFs of constrained transport, must be computed by both blocks from identical inputs with identical arithmetic, so that the two copies agree exactly. Athena++ instead averages shared face fields (D08). This serves **correctness**.

**Decision.** *(2026-10-11)* **A**, following the recommendation: the state is bit-for-bit independent of the number of workers, the scheduling and the decomposition, minima are exact, and sums are combined in a fixed block order, with exactly rounded sums available where a test needs them.

### D05.6 — The path to GPUs

What, if anything, does this layer do now for possible GPU execution, an aspiration rather than a target (§1.2)?

**Options**

- **A. Nothing beyond D04.2's kernel interface** (arrays in, arrays out, no state).
- **B. Keep the blocks batchable.** The data of all blocks of a process can live in one array with the block as its first index, as E05.2 used for all three strategies (`[block, var, i, j]`). A device backend could then hold all blocks in device memory and process them in one launch, as **[GK]** AthenaK does with its MeshBlockPacks. Combined with the rule of D05.1 B (no code touches block data outside kernels and the communication layer), data never needs to leave the device during a step. The cost falls on D06: block storage must allow one contiguous allocation.
- **C. An array abstraction now**, for example the Python Array API standard **[GK]**, so that orchestration code runs unchanged on CuPy or JAX arrays. Speculative, an extra layer in every piece of orchestration, and no GPU is available to test it.

**Recommendation.** B. It costs almost nothing beyond what block-level threading already needs, and E05.2 shows that the same layout also serves shared memory between processes. It keeps the decisive property for GPUs, that whole steps can run without moving data, without building anything speculative. This serves **extensibility**.

**Decision.** *(2026-10-11)* **B, keep the blocks batchable**, since it costs very little now. To be precise about what it buys: it keeps GPU acceleration *possible* without restructuring the data or the orchestration, which is the part that is hard to change later. It does not make it easy. A GPU backend would still need its own implementation of every kernel, since Cython does not run on GPUs (D04.1).

## 4. Consequences for higher layers

**For every layer**

- The block is the unit of data ownership and of parallel work. Workers are Python threads, and each updates whole blocks. Kernels run serially within a call and release the GIL; they use no OpenMP and no `prange`. Every compiled module declares itself free-threading compatible (`freethreading_compatible`), or importing it would switch the GIL back on (D05.2–D05.4).
- No code reads or writes another block's data directly. All data movement between blocks goes through one communication layer, and all global reductions through one reduction function (D05.1).
- Python code that runs inside the workers must be thread-safe: no shared mutable state without synchronisation. Scratch arrays belong to a worker, not to a block or to a module (E05.2).
- The Python that runs in the workers while holding the GIL must stay small, so that the standard interpreter also scales (D05.4). Work on whole blocks or their edges, such as ghost copies, should run in compiled code that releases the GIL.
- Kernel arithmetic must not depend on where block boundaries lie. Values on faces shared by two blocks, such as fluxes and the edge EMFs of constrained transport, are computed by both blocks from identical inputs with identical arithmetic (D05.5).

**For the verification of D02**

- Two new bit-for-bit invariants within a run (D02.3): the same problem with 1 and with N workers, and with different block sizes, must give identical states. Both run on both interpreters.
- CI gains a test job on free-threaded Python 3.14t. Tests that use several threads run there with real parallelism, which is where races show up.
- Conservation tests that compare global sums across decompositions use exactly rounded sums. Sums within one configuration may use the fixed-order reduction (D05.5, E05.3).

**For brief D06 (data model)**

- The data of all blocks of a process must be storable as one array with the block as its first index (`[block, var, i, j]`), from which kernels receive per-block views (D05.6). E05.2 used exactly this layout for threads and for shared memory between processes.
- Scratch arrays are allocated per worker, sized for one block.

**For brief D07 (mesh)**

- Every worker needs several blocks. In parallel runs, blocks of 32² to 64² cells scaled best, while 128² fell behind from 4 workers on (E05.2). On one core, 64² to 128² was fastest (E04.5). Together that makes 64² the starting point.
- The decomposition into blocks must not change the result (D05.5). A uniform grid is also a set of blocks, as in Athena++.

**For brief D08 (boundaries and communication)**

- One communication layer handles every exchange between blocks: in-memory copies now, MPI messages later (D05.1). Ghost filling reads only the neighbours' interior cells.
- With one shared memory, two synchronisation points per two-stage Runge–Kutta step suffice (E05.2): after each stage, before the next ghost filling.
- Whether shared face fields are averaged, as in Athena++, is decided there. With identical arithmetic on both sides (D05.5), their two copies agree exactly within a process.

**For brief D09 (execution model)**

- Blocks are assigned to workers. E05.2 used a fixed assignment of contiguous ranges, and the result must not depend on the assignment or on scheduling.
- Reductions are formed per block and combined in a canonical block order, independent of the worker or rank (D05.5). The minimum for the time step needs no special care.
- The default number of workers is the number of physical cores on the free-threaded interpreter. Hardware threads added nothing in E05.2. On the standard interpreter, the default is chosen once the GIL-held share of D05.4 has been measured, and mhdpy explains why it is smaller.

**For brief D14 (I/O and diagnostics)**

- History quantities are sums over blocks, computed through the reduction function in canonical block order, so that they do not depend on the number of workers.

**For the project setup (D01, D04.5)**

- Wheels are built for `cp314t` as well as for the standard interpreters, and CI tests on 3.14t (D05.4). Python 3.13t is not supported.
- The build needs no OpenMP. That resolves the concern D04 raised about bundling an OpenMP runtime with the macOS wheels.
- When distributed memory is implemented, mpi4py becomes an optional extra (`mhdpy[mpi]`).
- The installation documentation:
  - describes how to install the free-threaded interpreter with one uv command, and recommends it for parallel runs;
  - installs MPI into a normal environment, not through `uv run --with` (E05.1);
  - notes that on clusters, mpi4py is built against the cluster's own MPI library.

**For the aspiration of GPU acceleration**

- All blocks of a process can be held in one array and processed in one launch (D05.6), and no code touches block data outside kernels and the communication layer (D05.1). A GPU backend would then need GPU implementations of the kernels and of the communication layer, but no change to the data model or the orchestration.
