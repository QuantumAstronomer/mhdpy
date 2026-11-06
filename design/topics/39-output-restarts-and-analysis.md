# Output, restarts and analysis

## 1. Overview

A run writes three kinds of data: checkpoints that hold everything needed to restart it, snapshots for analysis and plots, and diagnostics of a few numbers per step. The references differ in whether one file serves as snapshot and checkpoint, in the format and precision they write, in how a restart rebuilds a run, and in the tools that read and plot the data. Zingale's text sets out the kinds of output and their cost in storage, pyro and Ulula write files in HDF5 that serve both as snapshots and for restarts and plot with Matplotlib, and Athena++ offers a history of totals, tables, VTK, HDF5 and restart files of its own, with Python tools that read every format into NumPy. The driver that schedules outputs follows in topic 37 and the parallel input and output in topic 42.

## 2. Designs

### 2.1 Kinds of output

Checkpoint files hold all variables needed for a restart, in a portable binary format at machine precision, and only the last few need keeping ([Zingale's text](#zingale-2025), §13.7). Plotfiles hold what the analysis needs, possibly in single precision, and some codes write a few variables often, for smooth movies, and many variables rarely. As the questions of an analysis are often unknown until a run ends, raw data must be kept, and the cost is large: on $1024^3$ cells one variable in double precision takes 8 GB and a file of five conserved variables 40 GB, so that plotfiles can exceed 100 TB per simulation. Runtime diagnostics store quantities known in advance, such as the peak temperature or the total energy, as one number every step or every few steps.

Detail: [Zingale 3.3](../references/computational-hydrodynamics-synthesis.md#33-output).

### 2.2 Snapshots that are also restarts

pyro writes the solver, the problem, the time and the step as attributes of an HDF5 file, and groups for the auxiliary data, the grid, the state, the particles and all runtime parameters, to which solvers add groups of their own, such as custom boundaries or a base state. Its reader rebuilds the grid, defines the custom boundaries again through the solver's own function, restores the data and particles, and creates a simulation of the solver with its time; in 2014 the data object was pickled instead ([Zingale](#zingale-2014) 2014, §2). Ulula writes the version of the code, the parameters of the scheme, the equation of state, the units, gravity, flags for the functions of the user, the domain, the time and the step, and all primitive variables, and loads a file in four steps.

1. Reject files older than version 1.0.0.
2. Rebuild the settings in the order of the setters and the domain, and initialise gravity.
3. Restore the time, the number of steps and the direction of the last sweep.
4. Read the primitive variables, derive the conserved ones and fill the boundaries.

Functions cannot be saved, so that a run with an update or boundary function of the user needs that function again on loading. Ulula's documentation says that files hold the physical domain alone, but the code writes the whole arrays, ghost cells included.

Detail: [pyro 3.4](../references/pyro-synthesis.md#34-output-analysis-and-testing), [Ulula 3.4](../references/ulula-synthesis.md#34-files-plots-and-movies).

### 2.3 Outputs of several kinds

Each output of Athena++ is a numbered block of the input file with a type, the variables, an interval in time or in cycles, and optional slices and sums along directions. The history sums mass, momenta, energies, magnetic energies, scalars and further quantities over the domain, weighted by volume and reduced over processes, together with outputs of the user, each with its own reduction. Tables write one file per block for slices and sums, and VTK files, one per block, hold a rectilinear grid in binary single precision. HDF5 writes all blocks of an output into one file, collectively with MPI, in single precision unless configured otherwise or quantised to integers between chosen limits, with a description for tools of visualisation. A restart file holds the parameters, with the counters of outputs already advanced so that a restarted run continues their sequence, a header with the mesh, time and cycle, the data of the user, the list of blocks with their locations and costs, and the whole arrays of every block with their ghost cells, written collectively at computed offsets with MPI.

Detail: [Athena 3.7](../references/athena-synthesis.md#37-output-restarts-and-visualisation).

### 2.4 Analysis and plotting

pyro's scripts read an output, fill its ghost cells and plot it with the solver's own routine of visualisation, or one variable, or thumbnails, and named timers profile a run. In 2014 runtime plots updated every step, so that students could watch the effect of boundary and initial conditions and chase bugs. Ulula's module of plots names sixteen quantities with labels and colour maps, derives velocities, internal energy and temperature, plots lines or radial averages over annuli weighted by the area that each cell shares with them, draws colour maps of the domain, and makes movies from frames at equal intervals. Athena++ reads every format into arrays of NumPy, merges the blocks of an HDF5 file onto a uniform grid at a chosen level, prolonging coarser blocks by repetition and restricting finer ones by volume, and provides scripts for lines, slices and the outlines of blocks, expressions for VisIt and a tool that joins VTK files.

Detail: [pyro 3.4](../references/pyro-synthesis.md#34-output-analysis-and-testing), [Ulula 3.4](../references/ulula-synthesis.md#34-files-plots-and-movies), [Athena 3.7](../references/athena-synthesis.md#37-output-restarts-and-visualisation).

## 3. Tests

Athena++ runs a problem of MHD for 80 cycles with every kind of output, restarts it twice from its restart files, and checks the sizes of the density in a slice, a sum, a VTK file and an HDF5 file, the vanishing of components that the problem lacks, and the agreement of HDF5 files in all data formats with the one in single precision, within $2 \times 10^{-2}$ for 8 bits and $7 \times 10^{-5}$ for 16. pyro's unit tests include a round trip of writing and reading (topic 36), and Athena++ reads an initial state from HDF5 back exactly (topic 38). No reference checks that a restarted run reproduces an uninterrupted one bit for bit.

Detail: [Athena 3.7](../references/athena-synthesis.md#37-output-restarts-and-visualisation).

## 4. Assessment

Ulula's radial average promises any two-dimensional domain but fails for one that is not square, and neither FFmpeg nor Pillow, which its movies need, is a declared dependency. **[GK]** A single format for snapshots and restarts, as in pyro and Ulula, is the simplest and serves small runs, provided it holds everything a restart needs: the parameters, the version, the state with or without ghost cells, the counters of outputs and the state of any random generator (topic 27). Athena++ separates restarts from analysis files, so that analysis can be in single precision and quantised, which halves or quarters the storage, at the cost of two formats. HDF5 through h5py installs with one command and is read by every tool of analysis, and a history of totals per step checks conservation, one of the criteria of correctness. For the production runs, about $4 \times 10^6$ cells in two dimensions, a snapshot of five variables in double precision takes about 170 MB, so that hundreds of snapshots fit on the development machine. An exact restart, reproducing an uninterrupted run bit for bit, is cheap to test and catches missing state. Open are the format and contents of snapshots and restarts, the quantities of the history, and whether plotting belongs to the package or to separate tools.

## 5. Sources

- <a id="zingale-2014"></a>Zingale, M., pyro: a teaching code for computational astrophysical hydrodynamics, Astronomy and Computing 6, 52–62 (2014), [arXiv:1306.6883](https://arxiv.org/abs/1306.6883), [doi:10.1016/j.ascom.2014.07.003](https://doi.org/10.1016/j.ascom.2014.07.003).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).
