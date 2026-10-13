# D14 — I/O, restarts and diagnostics

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-13 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how a simulation's data leave memory, and how they come back:

- the file format;
- the layout of the block data in a file, and which tools can read it;
- the kinds of output, and how restart files relate to snapshots;
- history and log files;
- precision, compression and the choice of variables;
- whether files are written while the run continues;
- how outputs are read back for analysis and restarts.

When outputs are written is D13's (schedules per output, D13.4); how outputs are requested is D15's.

**What earlier briefs require of I/O:**

- **D02.3 and D13.5.** A restart contains everything the continuation depends on, exactly and in binary: every registered array that is not derived, the time, the cycle and the step-control state, the mesh and the unit system, every module's parameters and internal state (including random-number generators), and the output schedules. A restarted run then equals the uninterrupted one bit for bit, also with a different number of workers or a different block size.
- **D13 §4.**
  - Restart files store blocks by logical location rather than by worker, so that another decomposition can read them.
  - An interruption during writing never destroys the last good restart file.
  - The state of a failed step is written in a format the usual analysis tools can read.
  - Log files, if any, are an output whose format is decided here.
- **D05.5.** History quantities are sums over blocks in canonical block order, so that they do not depend on the number of workers.
- **D06.6.** Output and restart flags are registry metadata: writers iterate over registered variables and need no knowledge of the physics. Because the index order is reversed (`[var, k, j, i]`), files and accessors document their axis order, and users meet data through named accessors rather than raw indices.
- **D07.4.** Outputs record the root grid and the blocks' logical locations, so that the block structure can be rebuilt, also after refinement has changed it.
- **D12.** Outputs record the unit system and each module's declarations and parameters, so that a file describes itself.

**What the references do** (syntheses in `References/`):

- **Athena++** has one output class per kind, each with its own cadence and choice of variables:
  - **history** (`.hst`): a text table of global sums and user quantities;
  - **formatted tables** and **VTK** files;
  - **HDF5** (`.athdf`): the blocks as arrays `[var, block, k, j, i]`, with the root grid, logical locations and levels, and the coordinates of every block. An XDMF description next to each file lets VisIt and ParaView open it. Its precision is chosen per output (half, single or double); the default is single precision unless the code is built with double-precision HDF5 output. Slices, sums along an axis and ghost cells are options;
  - **restart** (`.rst`): its own raw binary format, written with MPI-IO without any library. It contains a header with the parameters, the mesh, time, step and cycle, then every block's arrays and user data, and it can be read with another number of processes.

  yt and Athena++'s own `athena_read.py` read the HDF5 files.
- **Pyro** writes HDF5 files with the solver and problem names, time and step, the grid, every variable with its boundary conditions, and all run-time parameters. A reader rebuilds a simulation object for analysis. There is no restart from a file.
- **Ulula** writes HDF5 files with groups for the code version, scheme, equation of state, units, domain, run state and grid (primitive variables without ghost cells). Every snapshot is also a restart file, checked against the code version.

## 2. Evidence

### E14.1 — Writing a snapshot of the thesis grid

**Method.** [`experiments/E14.1-snapshot-formats.py`](experiments/E14.1-snapshot-formats.py) writes a snapshot of the thesis grid: 4000 × 1000 cells in blocks of 50², six primitive variables (density, three velocity components, pressure and a metallicity scalar), interior cells only. That is 192 MB in double precision. For each form it measures:

- the time to write, including dropping the ghost cells and any reordering, until the file is flushed to the disk;
- the time to read it back;
- the size, and whether the data come back bit for bit.

Compression depends on the data, so two synthetic states are used:

- **a cloud in a halo:** a dense, turbulent cloud with a tail in an exactly uniform hot medium, as in the thesis run (35 % of the cells perturbed);
- **turbulent everywhere,** as a worst case.

Full output: [`results/E14.1-snapshot-formats.md`](experiments/results/E14.1-snapshot-formats.md).

**Results** (write times for the cloud; for the turbulent state where it differs):

| Form | Write, flushed to disk | In thesis steps (120 ms) | Size: cloud / turbulent | Exact |
|---|---|---|---|---|
| NumPy `.npy` | 0.13 s | 1.1 | 192 / 192 MB | yes |
| HDF5, contiguous, block layout `[block, var, …]` | 0.13 s | 1.1 | 192 / 192 MB | yes |
| HDF5, contiguous, Athena++'s layout `[var, block, …]` | 0.18 s | 1.5 | 192 / 192 MB | yes |
| HDF5, chunked | 0.21 s | 1.7 | 192 / 192 MB | yes |
| HDF5, gzip 1 + shuffle | 1.39 s (3.03 s) | 12 (25) | 40 / 113 MB | yes |
| HDF5, lzf + shuffle | 0.64 s (1.01 s) | 5 (8) | 43 / 119 MB | yes |
| HDF5, zstd 1 + shuffle (Blosc) | 0.34 s (0.51 s) | 2.8 (4.3) | 41 / 117 MB | yes |
| zarr, default (zstd), 100 chunk files | 2.20 s | 18 | 53 / 150 MB | yes |
| HDF5, single precision | 0.09 s | 0.7 | 96 / 96 MB | no (6 × 10⁻⁸) |
| HDF5, single precision, zstd 1 + shuffle | 0.19 s (0.27 s) | 1.6 (2.3) | 15 / 42 MB | no (6 × 10⁻⁸) |

- **An uncompressed snapshot of the thesis grid costs about one step.** HDF5 is as fast as NumPy's own format. With snapshots every hundred steps or more, writing them synchronously costs about 1 % of the run or less.
- **Athena++'s layout costs 0.05 s more** for reordering the blocks from mhdpy's layout, less than half a step.
- **Lossless compression pays where the state is partly uniform.** For the cloud, zstd shrinks the file 4.7× for about three steps of writing; gzip compresses no better and is four times slower. Where every cell is perturbed, compression gains only 1.6×: the last bits of double-precision values are noise to a compressor.
- **Single precision halves the size** at a relative error of 6 × 10⁻⁸, enough for analysis but not for restarts. Combined with zstd, it shrinks the cloud's file 13×.
- **zarr stores each chunk as a separate file.** Writing is fast, but flushing 100 files to the disk takes 2 s. It compressed less than HDF5 with Blosc, because its default has no shuffle filter.
- **For scale:** 200 snapshots of the thesis run take 38 GB in double precision, 8 GB with zstd and 3 GB in single precision with zstd.

### E14.2 — Writing snapshots in the background

**Method.** [`experiments/E14.2b-background-output.py`](experiments/E14.2b-background-output.py) runs SSP-RK2 steps on the thesis grid with the ranged kernels of D09 ([`E14.2a-kernels.py`](experiments/E14.2a-kernels.py), a copy of E09.1a) on a thread pool. Every five steps it writes a snapshot of the five conserved variables (160 MB), uncompressed or with zstd, in one of two ways:

- **synchronously:** the main thread copies the state, writes the file and only then continues;
- **in the background:** the main thread copies the state and hands the copy to a writer thread, then continues at once. The copy keeps the snapshot consistent while the state changes. Before the next snapshot, the main thread waits for the previous one to finish.

The cost of a snapshot is the extra time of the run over the same steps without output. Under the GIL, the writer thread can only overlap with the steps if h5py releases the GIL while it writes. The snapshots of the two ways are compared bit for bit. Full output: [`results/E14.2-background-output.md`](experiments/results/E14.2-background-output.md).

**Results** (cost per snapshot, in seconds and in steps):

| Interpreter | Workers | Step | Copy | Uncompressed: synchronous / background | zstd: synchronous / background | Identical |
|---|---|---|---|---|---|---|
| Free-threaded | 6 | 130 ms | 28 ms | 0.08 s (0.6) / 0.05 s (0.4) | 0.30 s (2.3) / 0.10 s (0.8) | yes |
| Free-threaded | 12 | 103 ms | 34 ms | 0.09 s (0.9) / 0.07 s (0.7) | 0.32 s (3.1) / 0.17 s (1.6) | yes |
| With GIL | 6 | 117 ms | 28 ms | 0.09 s (0.8) / 0.06 s (0.5) | 0.30 s (2.5) / 0.12 s (1.0) | yes |
| With GIL | 12 | 101 ms | 34 ms | 0.09 s (0.9) / 0.05 s (0.5) | 0.31 s (3.1) / 0.13 s (1.3) | yes |

- **Writing in the background hides most of a snapshot's cost on both interpreters.** h5py and the compression filter evidently do their work without holding the GIL, so the writer thread overlaps with the steps under the GIL as well.
- **What remains is the copy** (28–34 ms) and the writer's competition with the workers for cores and memory bandwidth. It is largest with 12 workers, which already occupy every hardware thread.
- **The gain is largest for compressed snapshots:** zstd costs about one step in the background instead of three.
- **Background writing does not change what is written:** the snapshots are identical to the synchronous ones, bit for bit.
- **The price is memory:** one copy of the written variables, 160 MB here, held until the file is written.

### E14.3 — Reading mhdpy's blocks with existing tools

**Method.** [`experiments/E14.3-yt-compatibility.py`](experiments/E14.3-yt-compatibility.py) writes a 2D state held as mhdpy holds it to a file in Athena++'s layout:

- **the state:** 400 × 100 cells in 16 blocks of 50² with ghost cells, in Morton order, `[block, var, k, j, i]`;
- **the variables:** six primitive variables, including a passive scalar, every value distinct so that a misplaced block would show;
- **extra content:** a group of mhdpy's own metadata, which Athena++'s files do not have.

It opens the file with yt 4.4 and compares yt's uniform-grid view of every variable with the original arrays. It also compares a minimal reader that assembles the blocks from their logical locations. Full output: [`results/E14.3-yt-compatibility.md`](experiments/results/E14.3-yt-compatibility.md).

**Results.**

- **yt opens the file as it is.** It recognises density, the velocities, pressure and the scalar, derives its own fields from them (density, pressure, velocity magnitude in its unit system), and ignores the mhdpy group.
- **Every value comes back bit for bit,** from yt and from the minimal reader alike; the blocks are placed by their logical locations, whatever their order in the file.
- yt recognises Athena++'s files by their extension, `.athdf` (from its source).

**What the three experiments mean together.**

- **Writing is cheap at the thesis scale:** about one step per uncompressed snapshot, less in the background. Output cost will not decide the format.
- **Compatibility with existing tools comes almost for free:** Athena++'s layout costs a reordering of less than half a step, and yt then reads mhdpy's files as they are.
- **Size is where the choices matter:** precision and compression change a snapshot from 192 MB to 15 MB for the thesis cloud.

## 3. Decisions

### D14.1 — The file format

In which format are outputs and restart files written?

**Options**

- **A. HDF5, through h5py.**
  - **Use:** the format of Athena++, Pyro and Ulula. yt, VisIt, ParaView (through an XDMF description) and any environment with h5py read it.
  - **Features:** one file per output, with attributes that describe it; parts of a file (one variable, some blocks) can be read alone; compression filters (E14.1).
  - **Installation:** h5py brings its own HDF5 library as a wheel for every target platform, also for the free-threaded interpreter (E01.1, E05.1), so installation stays one command.
  - **Drawbacks:** a compiled dependency. HDF5 serialises all calls within a process, so only one thread writes at a time (E14.2). Parallel HDF5 for several processes (MPI, D05.1) is not available as a wheel; that is a question for later (D14.6).
- **B. zarr:** chunked arrays stored as a directory of files (or a zip file).
  - **Advantages:** pure Python with compiled codecs. Designed for writing in parallel, since every chunk is a file of its own, and for cloud storage.
  - **Drawbacks:**
    - many files per output: flushing them to the disk took 2 s in E14.1, against 0.3 s for one HDF5 file;
    - yt and the astrophysical analysis tools do not read it;
    - its current format version is recent.
- **C. NumPy's own files** with a JSON description next to them.
  - **Advantages:** no dependency beyond NumPy, and as fast as HDF5 (E14.1).
  - **Drawbacks:** an output becomes several files, no tool reads them, and compressed files cannot be read in parts.
- **D. An own binary format,** as Athena++'s restart files: no dependency and full control, but every tool needs a reader written for it.

**Recommendation.** A, for snapshots and restart files alike. It is what the reference codes and the analysis tools use. It is as fast as the alternatives without compression and has the best compression (E14.1). It installs with one command everywhere. Its one limitation, writing from several processes, belongs to the MPI path that D05.1 has deferred. This serves **ease of use** (files every tool reads) without cost to **performance**.

**Decision.** *(2026-10-13)* **A, HDF5 through h5py**, following the recommendation: the most common way forward, without reinventing what exists.

### D14.2 — The layout of the block data, and who can read it

How are the blocks laid out in a file?

**Options**

- **A. Athena++'s layout, plus a group of mhdpy's own.**
  - **The Athena++ part:** the attributes and datasets of Athena++'s HDF5 files:
    - the root grid, block size, logical locations and levels;
    - the coordinates of every block;
    - the cell-centred variables as `[var, block, k, j, i]`, named as yt knows them.
  - **The mhdpy group** holds everything Athena++'s format has no place for:
    - the registry (D06.6);
    - face-centred arrays (needed for restarts);
    - the unit system and every module's declarations and parameters (D12);
    - the schedules and the step-control state (D13.5);
    - provenance: format version, mhdpy version and commit, Python version and interpreter (free-threaded or not), NumPy version, compiler and build options, platform.

  yt then reads the files as they are (E14.3), as do Athena++'s reader and, with an XDMF description, VisIt and ParaView. The reordering from mhdpy's layout costs 0.05 s per snapshot (E14.1).
- **B. mhdpy's own layout,** the blocks as in memory, `[block, var, k, j, i]`, with a schema of its own. No reordering, but yt would need a reader of its own, written and maintained for mhdpy.
- **C. Global arrays,** assembled per variable. The simplest for users of uniform grids, but it does not extend to refinement (D07.7), and writing it means assembling the blocks first.

**Recommendation.** A. Compatibility with yt and the visualisation tools comes for free and costs less than half a step per snapshot. The mhdpy group makes every file self-describing in the sense of D06, D07 and D12. Provenance matters because D02.3 guarantees bit-for-bit restarts only *within the same environment*. A restart in another environment is allowed, but the reader can then say that its continuation may differ in the last bits. yt recognises Athena++'s files by their extension, so snapshot files end in `.athdf`. A small yt reader of mhdpy's own would remove that tie; it is noted for later. This serves **ease of use** and **correctness** (files that describe themselves completely).

**Decision.** *(2026-10-13)* **A, Athena++'s layout plus a group of mhdpy's own**, following the recommendation, given the wide support for the format.

### D14.3 — Kinds of output, and what a restart file is

Which kinds of output are there, and how do restart files relate to snapshots?

**Options**

- **A. One kind: every snapshot is a restart file,** as in Ulula. Simple, but every snapshot then carries everything in double precision, uncompressible module state included. For the thesis grid that is 192 MB where an analysis snapshot needs 15–96 MB (E14.1).
- **B. Separate kinds in separate formats,** as in Athena++: HDF5 snapshots, and restart files in a raw binary format of their own. Two writers and two readers, and restart files that no tool can open.
- **C. Separate kinds in one format.** All three are written by the same writer:
  - **snapshot:** chosen variables, derived quantities, chosen precision and compression (D14.5);
  - **restart file:** a snapshot that contains everything D13.5 lists, in double precision, lossless;
  - **history:** D14.4.

  A restart file is then readable by yt like any snapshot. The state of a failed step (D13.6) is written as a restart file, complete for inspection.

**Recommendation.** C. It keeps one format, one writer and one reader for everything (D14.1), lets analysis snapshots be small, and makes restart files as inspectable as snapshots. A user who wants every snapshot to be a restart file, as in Ulula, sets the two schedules equal. This serves **ease of use** and **performance** (small snapshots).

**Decision.** *(2026-10-13)* **C, separate kinds in one format**, following the recommendation. It serves ease of use well, and restart files and snapshots being interchangeable is very convenient.

### D14.4 — History and log files

How are history quantities and log messages written?

**Options**

- **A. A text table for the history, plain text for the log.**
  - **History:** as Athena++'s `.hst`. One line per entry, with a header of names and units. Values are written in full precision: the shortest representation that reads back to the same number, unlike the 10 digits of E13.2. Each line is flushed as it is written.
    - **Contents:** global sums in canonical block order (D05.5); quantities that modules and users declare; and the step's diagnostics (time step, limiting constraint, floor and flux-correction counts, cell updates per second, D13.7).
    - **Use:** it can be followed during the run, survives a crash up to its last line, and loads with `numpy.loadtxt`.
    - **On restart,** lines after the restart time are discarded before appending, so that the history has no duplicates.
  - **Log:** a plain-text file with the lines the run reports (D13.7) and its warnings. Which lines also go to the terminal is D15's.
- **B. The history as an HDF5 dataset** that grows with every entry: binary and structured, but it cannot be followed during the run with ordinary tools, and a crash while writing can damage the file.
- **C. Both,** at the cost of two writers for the same data.

**Recommendation.** A. A history is read most often during the run, to see whether it behaves, and after a crash, to see what happened. Text serves both, and at full precision it loses nothing. Putting the step's diagnostics in the history keeps them machine-readable, so the log can stay text for people. This serves **ease of use**.

**Decision.** *(2026-10-13)* **A, a text table for the history and plain text for the log**, following the recommendation.

### D14.5 — Precision, compression and the choice of variables

What does a snapshot contain, and at which precision?

**Options**

- **A. Fixed:** every registered variable, double precision, uncompressed.
- **B. Chosen per output:**
  - **Variables:** by name or by registry flag. Derived quantities (temperature, vorticity, slices, sums along an axis) are computed by functions over ranges of blocks (D12.4), as diagnostics are.
  - **Precision:** double by default, single on request.
  - **Compression:** lossless zstd with shuffle on request (through hdf5plugin, as a dependency). A file compressed this way can only be read by tools that load the same filter: in Python, `import hdf5plugin` before h5py or yt opens it. mhdpy's reader does this itself (D14.7).

  Restart files are always double precision and lossless, and may be compressed, because compression is lossless.
- **C. Lossy compression with a bounded error** (zfp, SZ): much smaller files, at an error the user chooses. A research topic of its own; noted for later.

**Recommendation.** B. Production runs need small analysis outputs (E14.1: 192 MB per snapshot in double precision against 15 MB in single precision with zstd, for the thesis cloud). Tests and convergence studies need double precision. Athena++ allows the same choices per output, though its default is single precision. Double precision is the default here because correctness comes first: a user who reduces it does so knowingly. Uncompressed is the default because every tool can read it. Of the lossless filters, zstd is the clear choice: as small as gzip and four times faster (E14.1), and about one step per snapshot in the background (E14.2). This serves **correctness** (exact by default) and **performance** (small files on request).

**Decision.** *(2026-10-13)* **B, chosen per output, with lossless compression, but compressed by default:** lossless zstd with shuffle is the default for snapshots and restart files, deviating from the recommendation's uncompressed default. Lossless compression is preferred over lossy (C). Single precision as an option is welcome for the significant storage it saves. Uncompressed output remains available per output, for tools that cannot load the filter.

### D14.6 — Writing while the run continues

Does the run wait while a file is written?

**Options**

- **A. Synchronously:** the main thread writes between steps. Simplest; costs about one step per uncompressed snapshot and three with compression (E14.2).
- **B. In the background:** the main thread copies the variables to be written, a dedicated writer thread writes them while the run continues, and the next output waits for the previous one. On both interpreters, this hid most of the cost of a snapshot (E14.2), at the price of one copy of the written data in memory. Details:
  - **Restart files** are flushed to the disk and renamed into place by the writer (D13 §4).
  - **At the end of a run,** on a signal or after a failed step (D13.6), the main thread waits for the writer before it exits.
  - **Errors** in the writer are reported at the next output, or at the latest at the end of the run.
  - **A synchronous mode** remains available for tests and for machines short of memory.
- **C. In parallel by the workers,** each writing its own blocks. HDF5 serialises all calls within a process, so this gains nothing with h5py; it would need zarr (D14.1 B).

**Recommendation.** B. It removes most of the cost of output at the price of one copy, whatever the interpreter. That matters most for compressed snapshots and frequent outputs, such as frames for a film. Writing from several processes (MPI, D05.1) is a separate question and noted for later. Options are one file per process joined by an HDF5 virtual dataset, gathering to one writer, or parallel HDF5 where the system provides it. This serves **performance**.

**Decision.** *(2026-10-13)* **B, in the background.** That writing a file then takes longer is acceptable.

### D14.7 — Reading outputs back

How are outputs read for analysis and for restarts?

**Options**

- **A. A reader of mhdpy's own, next to yt.** `mhdpy.load(path)` returns an object with:
  - named accessors for the variables (D06), coordinates, time, units (D12.5) and the recorded parameters;
  - global arrays assembled from the blocks for uniform meshes, and blocks per level once refinement exists.

  A restart file opens as a `Simulation` ready to `run()` (D13.1). yt remains available for everything else (D14.2).
- **B. yt and h5py only:** no reader of mhdpy's own. yt becomes a dependency of every analysis, there is no path from a file back to a simulation, and the mhdpy group (D14.2) has no reader.

**Recommendation.** A. Restarts need a reader in any case (D13.5), and the same reader serves analysis with mhdpy's names and units. E14.3 shows that assembling the blocks from their logical locations takes a few lines. yt then adds its analysis and visualisation without being required. This serves **ease of use**.

**Decision.** *(2026-10-13)* **A, a reader of mhdpy's own, next to yt**, with one addition: **parameters can be changed on restart**, for example to extend the simulated time. Without that, restarts would serve little purpose. A restarted run takes its parameters from the restart file, and values given anew replace them. Parameters whose change would make the restart file inconsistent (the variables, the mesh) are refused. Changing a parameter that affects the steps (the CFL number, output times, physics) ends the bit-for-bit equality with an uninterrupted run, deliberately.

## 4. Consequences for higher layers

**For every layer**

- **One format, one writer, one reader:** HDF5 through h5py, a required dependency (D14.1). Snapshots, restart files and the state of a failed step are written by the same writer in the same layout (D14.3); the history and the log are text (D14.4).
- **The layout** (D14.2):
  - **Athena++'s part:** root grid, block size, logical locations and levels, block coordinates, and cell-centred variables as `[var, block, k, j, i]` under the names yt knows. The registry (D06.6) maps each variable to that name.
  - **mhdpy's group:** the registry, face-centred arrays, the unit system, every module's declarations, parameters and internal state, the schedules, the step-control state, and provenance (format version, mhdpy version and commit, Python version and interpreter, NumPy version, compiler and build options, platform).
  - Snapshot and restart files end in `.athdf`, with an XDMF description next to snapshots for VisIt and ParaView.
- **Kinds of output** (D14.3):
  - **snapshot:** variables by name or registry flag, derived quantities from functions over ranges of blocks (D12.4), precision and compression per output (D14.5);
  - **restart file:** everything D13.5 lists, double precision, lossless; readable by yt like any snapshot;
  - **history:** D14.4.

  Every file is written under a temporary name, flushed and renamed into place, so that an interruption never leaves a damaged file under the final name (D13 §4).
- **Precision and compression** (D14.5): double precision by default, single precision per output on request. Every file is compressed by default with lossless zstd and shuffle through hdf5plugin, a required dependency; uncompressed output is available per output. Restart files are always double precision and lossless, and compressed by default like snapshots.
- **Reading compressed files elsewhere:** h5py and yt read them after `import hdf5plugin`; VisIt and ParaView need the filter on their HDF5 plugin path. The user documentation says so, and points to uncompressed output for tools that cannot load the filter.
- **History** (D14.4): a text table, one line per entry, values in their shortest exact representation, flushed per line. Columns are the global sums in canonical block order (D05.5), the quantities declared by modules and users, and the step's diagnostics (D13.7). On restart, lines after the restart time are discarded before appending. The log file is plain text.
- **Background writing** (D14.6): the main thread copies the variables to be written between steps and hands them to one writer thread; the next output waits for the previous one. Memory for one copy of the largest output is part of a run's footprint. The writer flushes and renames files, and its errors are reported at the next output or at the end. At the end of a run, on a signal or after a failed step, the main thread waits for the writer before exiting (D13.6). A synchronous mode exists for tests.
- **Reading** (D14.7): `mhdpy.load(path)` returns named variables, coordinates, time, units and parameters, with global arrays assembled from the blocks for uniform meshes (and per level once refinement exists). It loads hdf5plugin itself, so compressed files open without further steps. A restart file opens as a `Simulation` ready to run.
- **Parameters on restart** (D14.7): a restarted run takes its parameters from the restart file; values given anew replace them. Every parameter declares whether it may change on restart (part of the module's declaration, D12.1). Those that would make the restart file inconsistent, such as the registered variables or the mesh, may not. Changes are recorded in the history's header and in the provenance of later files.

**For the verification of D02**

- **Round trip:** every variable written and read back is bit-for-bit identical in double precision, and within single-precision rounding in single precision; with and without compression.
- **Restarts:** the D13 tests (bit-for-bit continuation, also with another number of workers or block size) read and write through this format.
- **Changed parameters:** a run restarted at its end with a later end time equals, bit for bit, a run to that later time that has an output at the original end time (the end time, like an output time, is hit exactly by shortening a step); a restart that changes a parameter declared fixed is refused.
- **Compatibility:** yt opens a snapshot, compressed (with hdf5plugin loaded) and uncompressed, and returns the written values bit for bit (E14.3), in the full tier.
- **Background writing:** files written in the background equal those written synchronously, bit for bit; an interruption during writing leaves the previous file intact.
- **History:** its values read back exactly; a restart leaves no duplicate lines.

**For brief D15 (configuration and user interface)**

- How outputs are requested: their kind, schedule, variables, derived quantities, precision and compression.
- How parameters are changed on restart: the command line and the Python interface give new values next to the restart file.
- **Open question from D13.7:** which lines go to the terminal and which only to the log file.

**Noted for later**

- A yt reader of mhdpy's own, which would remove the tie to the `.athdf` extension (D14.2).
- Lossy compression with a bounded error, such as zfp or SZ (D14.5 C).
- Writing from several processes once MPI arrives (D05.1): one file per process joined by an HDF5 virtual dataset, gathering to one writer, or parallel HDF5 where the system provides it (D14.6).
