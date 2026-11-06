# Data structures

## 1. Overview

The data of a finite-volume code are arrays of cells with layers of ghost cells, holding conserved and primitive variables, fluxes on faces and, in MHD, fields on faces and electric fields on edges. The designs differ in the order of the axes, in whether the variables of a cell lie together in memory or each variable forms an array of its own, in how a code names and indexes its variables, and in whether the domain is one array or many blocks of equal size. Zingale's text and pyro use NumPy arrays with the variables on the last axis, pyro wrapped in classes for grids and data with shifted views, Ulula keeps all data in one simulation object, ZEUS-2D stores scalars and vector components with shared indices on a staggered mesh, and Athena++ holds multidimensional arrays with the variable outermost in blocks of a tree. Ghost cells follow in topic 4, the driver in topic 37 and refinement and parallelisation in topics 40 and 42.

## 2. Designs

### 2.1 Arrays with ghost cells

In NumPy the state of a one-dimensional grid of $n_x$ cells with $n_\mathrm{g}$ ghost cells at each end is an array of shape $(n_x + 2n_\mathrm{g}, n_\mathrm{var})$, whose interior runs from $\mathrm{lo} = n_\mathrm{g}$ to $\mathrm{hi} = n_x + n_\mathrm{g} - 1$ ([Zingale's text](#zingale-2025), §3.4). Fluxes live on faces, which integer indices cannot address, so that element $i$ of a flux array holds the flux on the left face of cell $i$. Zingale's Fortran code hydro1d uses derived types instead: a grid with its index bounds, coordinates, areas and volumes, data on that grid, and data on its faces, with integer keys that index the variables. ZEUS-2D stores each variable per zone, ghost zones included, with the vector components on faces sharing the indices of their zone, and keeps scale factors and volume factors as one-dimensional arrays on both meshes, computed once on a fixed mesh ([Stone and Norman](#stone-norman-1992a) 1992a, §4.1).

Detail: [Zingale 3.1](../references/computational-hydrodynamics-synthesis.md#31-data-layout-on-the-grid), [Zingale 3.6](../references/computational-hydrodynamics-synthesis.md#36-hydro1d), [ZEUS 3.1](../references/zeus-synthesis.md#31-data-layout).

### 2.2 Grid and data objects with shifted views

pyro separates the grid from the data on it ([Zingale](#zingale-2014) 2014, §2). A grid object holds the sizes, extrema, index bounds and coordinates, returns scratch arrays over the whole index space, and creates the coarser and finer grids of multigrid. The object for data at cell centres is built in steps.

1. Create it on a grid with a data type, double precision by default.
2. Register each variable with its name and its boundary conditions, set auxiliary data such as the ratio of specific heats, and add functions for derived variables.
3. Allocate one array of shape $(n_x + 2n_\mathrm{g}, n_y + 2n_\mathrm{g}, n_\mathrm{var})$ and lock the object against further variables.
4. Access each variable as a view that shares the memory, or a derived variable by its function, and fill ghost cells, restrict, prolong and clone through methods.

An indexer that subclasses the NumPy array returns views of the valid cells shifted by whole cells, so that the centred difference $a_{i+1,j} - a_{i-1,j}$ reads `a.ip(1) - a.ip(-1)`, closer to the notation of the papers than slices. With the first index along $x$, the cells of equal $x$ lie next to each other in the row-major storage of NumPy. Data on faces have an object of their own, with one cell more normal to the face. pyro first wrote some kernels in Fortran, self-contained and interfaced with f2py, where slices hid the index notation.

Detail: [pyro 3.2](../references/pyro-synthesis.md#32-grids-and-data).

### 2.3 One simulation object

Ulula's solver is one class that holds the domain, the arrays of primitive and conserved variables and their copies, the scheme, the equation of state, the code units and gravity, and a second class that holds the choice of algorithm. The scheme, the equation of state, the units and gravity must be set before the domain, whose setting creates the arrays and fixes the layout, and later changes raise an error. The variables carry abbreviations of two letters, such as `DN` and `MX`, which become attributes holding their indices and name them in plots and initial conditions. Density and mass density share index 0, and the primitive array also holds the potential and its gradients, which have no conserved counterparts.

Detail: [Ulula 3.2](../references/ulula-synthesis.md#32-the-simulation-object-and-its-data).

### 2.4 Blocks of a tree

All data of Athena++ lie in arrays of one to six dimensions, contiguous in memory and addressed with the last index fastest, so that the conserved variables `u(n,k,j,i)` place each variable in a block of its own, and loops with `i` innermost run through memory in order. Arrays may be shallow slices of others and can exchange their data without copies. The domain is split into blocks of equal size, each with its own cells, ghost cells and coordinates, held by a tree, binary, quadtree or octree, whose Z-order assigns blocks to processes and keeps communication local ([Stone et al.](#stone-et-al-2020) 2020, §2.1). A block borders up to 8 neighbours in two dimensions and 26 in three, whose ghost cells it receives through MPI or by copies in memory. A new run is initialised as follows.

1. Call the problem generator of every block.
2. Set up the persistent requests of MPI, solve self-gravity once, exchange the conserved variables between blocks and prolong them between levels.
3. Convert to primitive variables in the active cells and the ghost cells beside neighbours, and apply the physical boundaries.
4. With adaptive refinement, evaluate the criteria, refine, balance the load, and repeat from step 1 until the number of blocks no longer changes.
5. Compute the first time step.

The indices of the variables, such as `IDN` and `IM1`, and their number are fixed at configuration. Each block creates its physical modules in a fixed order, the hydrodynamics always, and reserves identifiers for their messages. Athena in C, by contrast, kept all variables of a cell in one structure, with three-dimensional arrays of these structures.

Detail: [Athena 2.1.4](../references/athena-synthesis.md#214-the-variables-in-the-code), [Athena 3.2](../references/athena-synthesis.md#32-arrays-the-mesh-and-its-blocks), [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop).

## 3. Tests

pyro's unit tests cover the grids, the geometric formulas, the methods of the data object, the filling of ghost cells, the indexer and a round trip of writing and reading, and experiments of its developers compare slicing, boolean masks, `np.roll` and the indexer for a centred difference on $1024 \times 2048$ cells. Athena++ can test its mesh from the command line before a run. Neither reports the outcome of these checks beyond passing.

Detail: [pyro 3.2](../references/pyro-synthesis.md#32-grids-and-data), [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop).

## 4. Assessment

The references report no measured costs of their layouts, beyond the remark of Athena that keeping the values of a cell together and working on one-dimensional pencils serves locality (topic 42). **[GK]** In NumPy, vectorised operations act on whole arrays, so that the order of the axes decides which operations run over contiguous memory. With the variable on the first axis, as in Athena++, each variable is one contiguous array and operations on single variables, such as the equation of state or a reconstruction, stream through memory; with the variable last, as in pyro, every variable is strided, while the variables of one cell lie together, which suits conversions between variable sets cell by cell. Shifted views, as in pyro, read like the papers and copy nothing, which serves readability at no cost in performance. One object for everything, as in Ulula, is the easiest to read but hard to extend, whereas separate objects for the grid, the variables and the scheme let modules plug in without changes to the framework. Blocks of equal size cost little on a single block and prepare decomposition, threads and refinement, a provision that the order of work of the project admits only where it is cheap. The production runs, about $4 \times 10^6$ cells in two dimensions, need some tens of arrays of about 30 MB each, well within the memory of the development machine. Open are the order of the axes, whether the domain is a block of a tree from the start, how variables are named and indexed, and how face-centred fields of MHD are stored beside the cell-centred variables.

## 5. Sources

- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="zingale-2014"></a>Zingale, M., pyro: a teaching code for computational astrophysical hydrodynamics, Astronomy and Computing 6, 52–62 (2014), [arXiv:1306.6883](https://arxiv.org/abs/1306.6883), [doi:10.1016/j.ascom.2014.07.003](https://doi.org/10.1016/j.ascom.2014.07.003).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).
