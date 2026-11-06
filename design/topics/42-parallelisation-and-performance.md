# Parallelisation and performance

## 1. Overview

The cost of a run is set by its number of cell updates, and its speed by the rate at which a code performs them on one core and by how well that rate holds as cores and nodes are added. The references measure both: Zingale's text the growth of the work with resolution, Ulula the cost of a step in NumPy, Athena and Athena++ the rate per core against other codes and the scaling to hundreds of thousands of threads. Athena++ decomposes the domain into blocks that processes of MPI and threads of OpenMP update, hides communication behind computation by task lists, and balances the load by measured costs. The blocks and their tree follow in topic 36, task lists in topic 18 and refinement in topic 40.

## 2. Designs

### 2.1 The cost of a simulation

In three dimensions with $N$ cells on a side, a step costs of order $N^3$, and reaching a fixed time takes a number of steps proportional to $N$, as the step scales with the cell width, so that the work grows as $N^4$ and doubling the resolution costs sixteen times as much ([Zingale's text](#zingale-2025), §13.6). Computing centres tend to favour large jobs, which sets one large calculation against many smaller ones that test the sensitivity to parameters. **[GK]** In two dimensions the work grows as $N^3$, and a limit of the step by explicit diffusion, proportional to $\Delta x^2$, raises it to $N^4$.

Detail: [Zingale 3.2](../references/computational-hydrodynamics-synthesis.md#32-computational-cost).

### 2.2 Vectorised Python

All operations on arrays in Ulula go through NumPy and so run in C, so that the overhead of Python might be expected to dominate but does not ([Diemer](#diemer-2025) 2025, §4.3). The time per step is well described by an overhead per step, about $2 \times 10^{-4}$ s in two dimensions, plus a constant cost per cell, about $4 \times 10^{-7}$ s in two dimensions and half that in one, which sweeps once instead of twice. The overhead matters only for the smallest problems, and beyond them the speed of NumPy limits the code. pyro compiles its kernels with Numba (topic 35). **[GK]** The cost per cell corresponds to $2.5 \times 10^6$ cell updates per second on one core.

Detail: [Ulula 3.7](../references/ulula-synthesis.md#37-performance).

### 2.3 Performance on one core

Athena limits its optimisation to the locality of data and to vectorisation, since aggressive optimisation needs mature and fixed algorithms and costs clarity ([Stone et al.](#stone-et-al-2008) 2008, §7). It keeps the variables of a cell together and works on one-dimensional pencils of the grid, and although it needs up to ten times the floating-point operations of ZEUS per cell, it runs only about four times slower in MHD, as access to the cache and memory limits modern processors. The classes of Athena++ grew out of benchmarks of its core kernel against plain C code for the same steps, and the full code was built only once its mock classes matched that code, so that the object-oriented design hinders no optimisation of the compiler ([Stone et al.](#stone-et-al-2020) 2020, §3.6). In relativity, [White, Stone and Gammie](#white-et-al-2016) (2016, §6) precompute the costly functions of the metric, run the innermost loops along the direction in which the arrays lie in memory, and vectorise all innermost loops, which needs manual inlining and fixed numbers of iterations in place of loops that run to convergence.

Detail: [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop), [Athena 3.9](../references/athena-synthesis.md#39-performance).

### 2.4 Parallel execution

Every block of a decomposed domain carries ghost cells of its own, which neighbouring blocks or the physical boundaries fill (Zingale's text, §3.5). Athena exchanges ghost cells by MPI once per step of its unsplit integrator, along $x$, $y$ and $z$ in sequence, which avoids messages to diagonal neighbours. Athena++ instead lets each process of MPI hold several blocks, which threads of OpenMP update, since forking and joining threads around single loops proved inefficient; this needs a library of MPI that is safe for calls from many threads (Stone et al. 2020, §2.4). A step of a block proceeds through its task list.

1. Post non-blocking receives for the boundaries of all blocks.
2. Compute the fluxes and update the block, and send its boundaries at once.
3. Test whether the data of the neighbours have arrived; if not, run other tasks of this or another block and return later.
4. Set the boundaries, prolong between levels and finish the stage once all data are in.

Blocks are assigned to processes in Z-order by their costs, equal by default, measured from the time of their tasks, or set by the problem, and redistributed periodically and whenever blocks are created or destroyed; balancing therefore needs more than one block per process (topic 40). The size of the blocks trades the cost of the active cells against communication, proportional to the surface of the blocks, and an overhead per block (Stone et al. 2020, eq. 30):

$$W(x) = A + \frac{b}{x} + \frac{c}{x^3},$$

for blocks of $x$ cells along each direction. A port of Athena++ to GPUs with Kokkos, K-Athena ([Grete et al.](#grete-et-al-2019) 2019), shows the same design on accelerators.

Detail: [Zingale 2.2.6](../references/computational-hydrodynamics-synthesis.md#226-beyond-the-uniform-grid), [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop), [Athena 3.5](../references/athena-synthesis.md#35-task-lists-and-parallelisation), [Athena 3.9](../references/athena-synthesis.md#39-performance).

## 3. Tests

Athena measures its rate per cell on one core for several algorithms on a grid of $128^3$ cells, and its weak scaling on a Cray XT-3 up to 20,000 processors (Stone et al. 2008). Athena++ measures single cores of three Intel architectures on a blast wave of $64^3$ cells, averaged over 20 trials and compared with FLASH, PLUTO and Enzo, full nodes with threads, weak scaling up to $10^4$ cores of a Cray XC50 and 524,288 threads of Oakforest-PACS, and strong scaling of a blast wave with refinement (Stone et al. 2020, §3.6). Its blast wave on $128^3$ cells with blocks of $4^3$ to $128^3$ cells measures the cost of block size, and Ulula times steps from 10 to $10^6$ cells in one and two dimensions.

Detail: [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop), [Athena 3.9](../references/athena-synthesis.md#39-performance), [Ulula 3.7](../references/ulula-synthesis.md#37-performance).

## 4. Assessment

On a 2.2 GHz Opteron, Athena updates about 340 thousand cells per second for isothermal hydrodynamics with HLLC and 98 thousand for adiabatic MHD with HLLD, and keeps over 85 per cent of its efficiency in weak scaling to 20,000 processors (Stone et al. 2008). Athena++ updates nearly $3 \times 10^6$ cells per second per Skylake core for MHD with HLLD and PLM and half as many with PPM, faster than FLASH, PLUTO and Enzo by up to a factor of ten, spending about 85 per cent of its time in vectorised instructions; on a full node the rate per core halves, limited by the bandwidth of memory rather than by arithmetic, and weak scaling keeps 95 to 97 per cent of the efficiency from 8 to 250 nodes (Stone et al. 2020). With refinement, blocks of $16^3$ cells halve the throughput but shorten the time to solution about fivefold, communication exceeds computation below blocks of about $16^3$ cells, and blocks of $4^3$ cells run nearly ten times slower than one block. K-Athena reaches 75 to 90 per cent of the efficiency that each architecture allows. Ulula's speed is set by NumPy. **[GK]** Ulula's rate in NumPy, about $2.5 \times 10^6$ cell updates per second for two-dimensional hydrodynamics on a recent laptop, is of the same order as the rate per core of Athena++ for three-dimensional MHD on an older server, which suggests that vectorised Python can reach useful rates for simple hydrodynamics, provided it keeps its temporary arrays few, by operating in place and fusing expressions, since memory bandwidth limits such codes. A run of the production scale, $4 \times 10^6$ cells for an assumed $10^5$ steps, needs about $4 \times 10^{11}$ cell updates, nearly two days on one core at that rate, before conduction or cooling shorten the step. The six cores of the development machine can share the work by threads over blocks, as in Athena++, which NumPy permits where it releases the global interpreter lock and the free-threaded Python 3.14t permits generally, while MPI, absent on the development machine, waits for the small server. Open are the strategy of kernels, pure NumPy or compiled, the parallel strategy and its first layer, the size of blocks, and the benchmark problem by which the rate of cell updates is tracked.

## 5. Sources

- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).
- <a id="grete-et-al-2019"></a>Grete, P., Glines, F. W. and O'Shea, B. W., K-Athena: a performance portable structured grid finite volume magnetohydrodynamics code, preprint (2019), [arXiv:1905.04341](https://arxiv.org/abs/1905.04341). **[GK]** IEEE Transactions on Parallel and Distributed Systems 32, 85–97 (2021), [doi:10.1109/TPDS.2020.3010016](https://doi.org/10.1109/TPDS.2020.3010016).
- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="white-et-al-2016"></a>White, C. J., Stone, J. M. and Gammie, C. F., An extension of the Athena++ code framework for GRMHD based on advanced Riemann solvers and staggered-mesh constrained transport, ApJS 225, 22 (2016), [arXiv:1511.00943](https://arxiv.org/abs/1511.00943), [doi:10.3847/0067-0049/225/2/22](https://doi.org/10.3847/0067-0049/225/2/22).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).
