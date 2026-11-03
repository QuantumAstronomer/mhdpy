# Synthesis of performance in Python

This synthesis digests a collection of papers on how finite-volume codes for hyperbolic problems reach high performance in Python, kept in `reference-works/Performance in Python/Docs`. The collection is gathered around the paper of [Bard and Dorelli](#bard-dorelli-2026) (2026, [arXiv:2503.20899](https://arxiv.org/abs/2503.20899)) on AGATE, a code for magnetohydrodynamics (MHD) written in Python (1.3). Additions found by web search, which fill gaps in the papers or check their claims, are marked **[GK]** and cited. A **[GK]** mark covers the rest of its paragraph or list item. A paper of the collection is cited by author and year, with the numbers of its sections, equations, figures and tables in the local copy, as in [Bard and Dorelli](#bard-dorelli-2026) (2026, §4.7, Table 2), and its arXiv identifier, or else its DOI, is given at its first citation. Within a paragraph, later citations of the same paper give the numbers alone. Works that the papers cite are cited as the papers cite them. Measured rates are restated with their problem, hardware, precision and number of cores, and are converted into cell updates per second where a source gives what the conversion needs.

## 1. Overview

### 1.1 Origin and publication

[Bard and Dorelli](#bard-dorelli-2026) (2026) wrote the paper at the Heliophysics Division of the NASA Goddard Space Flight Center in Greenbelt, Maryland, with funding from the Living With a Star Strategic Capabilities programme of NASA (acknowledgements). The local copy is the second version on arXiv, of 14 May 2025, which names the Journal of Computational Physics as the journal to which it was submitted. Its 24 pages hold a graphical abstract and highlights, the text in five sections with eight figures, two tables and 36 numbered equations, an appendix on the code of the modes of acceleration, and 63 references. The code is open source, in a repository of NASA at [git.smce.nasa.gov/marble/agate-open-source](https://git.smce.nasa.gov/marble/agate-open-source). **[GK]** The paper appeared in Computer Physics Communications 322, 110077 (2026), under the licence CC BY-NC-ND, according to its record at [Crossref](#web-crossref). The publisher refuses scripted downloads, so that the published version was not compared with the local copy. The [repository](#web-agate-repository) answers at its address.

### 1.2 Aims and scope

Simulations in physics demand ever more computing, and the codes that run on the largest machines are written in languages of low level, C++ or Fortran in computational physics and heliophysics alike ([Bard and Dorelli](#bard-dorelli-2026) 2026, §1). These languages give performance but bar the average scientist, while Python, among the most popular languages, makes development and debugging easier. Some frameworks for high-performance computing (HPC) offer interfaces in Python, as AMReX does through pyAMReX ([Myers et al.](#myers-et-al-2024) 2024), but the code beneath such an interface stays hard to modify or extend, and the slowness of Python has kept it out of HPC. Three libraries change this: NumPy vectorises operations on arrays ([Harris et al.](#harris-et-al-2020) 2020), Numba generates machine code that runs on several threads ([Lam, Pitrou and Seibert](#lam-et-al-2015) 2015), and CuPy reaches graphics processing units (GPUs) through the CUDA libraries of NVIDIA ([Okuta et al.](#okuta-et-al-2017) 2017). On them AGATE builds a code written entirely in Python. It solves the ideal, Hall and Chew–Goldberger–Low (CGL) equations of MHD by finite volumes, and is meant for production runs, the development of algorithms, prototyping and teaching alike.

The paper concludes that pure Python is impractical for most uses, that NumPy and Numba give useful speed-ups for small simulations on central processing units (CPUs), and that the modes on the GPU run more than 40 times faster than Numba on large problems (§5). It sees AGATE as a viable platform for MHD in research, applications and teaching, whose modular design prepares further physics, methods and geometries.

### 1.3 The collection

The paper of 2026 stands at the centre of the collection, as the code among the sources nearest to the purpose of mhdpy: a finite-volume code for MHD, written in Python, that times one problem in each of its routes to speed and against Athena++. Its sections set out the modular organisation (§2.1), the finite-volume scheme (§2.2), the modes of acceleration (§2.3, App. A), the equations of ideal, Hall and CGL MHD (§3), the tests (§4.1 to §4.6) and the timings (§4.7). The collection digests §1, §2, §4.2, §4.7, §5 and App. A in full, and §3 and the other tests in outline, as their physics lies outside the collection.

The further papers fall into six groups, in the order of the steps of `plan.md`: two on the costs of NumPy and of memory, four on compiled kernels, two that compare the routes on the same kernels, four on threads, one on MPI, and four on codes for fluids in Python. Each paper is digested in the subsections of the subjects that it serves (2), and its numbers of sections, equations, figures and tables refer to its local copy. The paper of 2026 fills 1, 2.2.1, 2.3.1, 2.7.1 and 3.1.

## 2. Techniques

The techniques fall into seven subjects: 2.1 the interpreter and vectorisation in NumPy, 2.2 compiled kernels, 2.3 measured comparisons of the routes on the same kernels, 2.4 threads, the global interpreter lock (GIL) and free threading, 2.5 processes, shared memory and MPI, 2.6 the decomposition into blocks and the exchange of ghost cells, and 2.7 whole codes for fluids against compiled codes.

### 2.2 Compiled kernels

#### 2.2.1 Five modes of one code

AGATE offers five modes of acceleration, None, Numpy, Numba, Cupy and Kernel, which decide which library carries out the numerical work at the lowest level ([Bard and Dorelli](#bard-dorelli-2026) 2026, §2.3). The first three run on CPUs and the last two on GPUs, through CuPy. The code selects the matching functions when it starts, and all code above them, the algorithms and the organisation of the program (3.1), is the same in every mode. Each class of implementation defines several versions of each of its functions, each serving one or more modes (App. A). The appendix shows them on a loop over one-dimensional arrays, which computes an intermediate value from a sine, sets it to $-1$ where it is negative, and multiplies it by the mean of two input arrays.

1. None runs the loop in pure Python. It iterates over `numba.prange` instead of `range`, which behaves as `range` outside Numba and so keeps the function valid for the next mode.
2. Numba passes the same function to its just-in-time compiler with `nopython=True` and `parallel=True`, so that the iterations of `prange` are shared among the cores.
3. Numpy needs a function of its own without loops, in operations on whole arrays: the sine of an array, the negative values replaced through a boolean mask, and the result assigned into the output array in place.
4. Cupy compiles a loop body written in Python just in time for the GPU, as Numba does for the CPU, but needs a separate function, since the index of each thread on the GPU is computed from the indices of its block and thread, which have no meaning on a CPU.
5. Kernel writes the loop body in CUDA C as a string, which CuPy compiles and calls as a raw kernel.

Each kernel thus exists in four versions: a loop shared by None and Numba, a vectorised function, a loop for CuPy and a kernel in CUDA C. CuPy also replaces the functions of NumPy on the GPU directly, but preliminary tests found this inferior to the two GPU modes, so AGATE does not offer it. Numba compiles for GPUs as well, which AGATE supports, but CuPy gave consistently faster kernels for effectively the same code, so CuPy is preferred on GPUs.

### 2.3 Measured comparisons of the routes on the same kernels

#### 2.3.1 The modes of AGATE on the Orszag–Tang vortex

AGATE times its modes on the Orszag–Tang vortex in ideal MHD with divergence cleaning, run to $t = 0.5$ with the default algorithm on grids of $32^2$ to $2048^2$ cells ([Bard and Dorelli](#bard-dorelli-2026) 2026, §4.7, Table 2). The vortex fills $[0, 1]^2$ with periodic boundaries, starting from $\rho = 25/(36\pi)$, $p = 5/(12\pi)$, $v_x = -\sin(2\pi y)$, $v_y = \sin(2\pi x)$, $B_x = -B_0 \sin(2\pi y)$ and $B_y = B_0 \sin(4\pi x)$, with $B_0 = 1/\sqrt{4\pi}$ (§4.2). The machine holds two AMD EPYC processors of 64 cores each, with two threads per core, and an NVIDIA A100 GPU. Numba runs on 16 threads, the number that performed best in preliminary tests on $256^2$ cells. Pure Python is impractical, and NumPy is about 100 times faster on $128^2$ cells, where pure Python takes 1802 s and NumPy 17.6 s. Numba compiles for about 13 s at the start of each run, and is 2 to 5 times faster than NumPy on large grids: on $1024^2$ cells, NumPy takes 7477 s and Numba 1320 s. The modes on the GPU run more than 40 times faster than Numba and more than 300 times faster than NumPy on the larger grids. The Kernel mode takes 12.0 s on $1024^2$ cells and 87.1 s on $2048^2$, where NumPy and Numba were not run, as they would have taken too long.

**[GK]** From $512^2$ to $1024^2$ cells, the times of NumPy grow by a factor of 8.4, close to the factor of 8 by which the work grows in two dimensions, 4 in cells and 2 in steps. Those of Numba grow by only 5.3 and those of the Kernel mode by 3.9, so that both parallel modes use their hardware better on larger grids. The time of Numba on $32^2$ cells, 13.3 s, shows that its times include the compilation. The paper gives neither the number of steps nor the precision, so that its times cannot be converted into cell updates per second. The examples of its appendix compute in double precision.

### 2.7 Whole codes for fluids against compiled codes

#### 2.7.1 AGATE against Athena++ and Cholla

The same benchmark runs in Athena++ ([Stone et al.](#stone-et-al-2020) 2020) on the CPUs and in Cholla ([Schneider and Robertson](#schneider-robertson-2015) 2015; [Caddy and Schneider](#caddy-schneider-2024) 2024) on the GPU, each built as its repository instructs ([Bard and Dorelli](#bard-dorelli-2026) 2026, §4.7, Table 2). Athena++ runs on one node, once without OpenMP and once with 16 threads, for which the mesh blocks are sized so that each thread has one. Cholla requires three dimensions, so it runs on $N \times N \times 3$ cells, and the Kernel mode of AGATE is timed on the same grid. Athena++ is considerably better optimised for CPUs than AGATE, which the authors expect, since they focus on GPUs. On $1024^2$ cells, Athena++ takes 1396 s without threads, about as long as Numba on 16 threads, and 214 s with them, against 7477 s for NumPy. On the GPU, Cholla runs 10 to 15 per cent faster than AGATE on the largest grids and about as fast on smaller ones, a difference that the authors accept for the advantages of Python. AGATE needs no compilation beyond the 13 s of Numba and well under a second on the GPU, where Athena++ and Cholla took 81 s and 119 s to compile. The authors find AGATE suited above all to rapid deployment, to students and to prototyping on smaller problems, and to HPC through its GPU modes.

**[GK]** The times of Athena++ without threads grow by a factor of 7.9 from $512^2$ to $1024^2$ cells, as the work does, and exceed those with 16 threads by a factor of 6.5, which suggests that it ran on one core. On $1024^2$ cells, NumPy is then 5.4 times slower than Athena++ on one core, and Numba on 16 threads 6.2 times slower than Athena++ on 16 threads.

## 3. Software architecture

The software architecture records how the codes divide the work between Python and their kernels, lay out their data, choose their physics and are installed. 3.1 digests AGATE.

### 3.1 AGATE: interfaces and implementations

AGATE builds its solver from Python classes, each step of the solution an interface paired with implementations ([Bard and Dorelli](#bard-dorelli-2026) 2026, §2.1, Fig. 1). The interfaces manage the operations of high level and shield the main program from the numerical detail, which the implementations carry out. A user may select or write any implementation that meets its interface. The code solves $\partial U/\partial t = \Delta(U, t)$, where $\Delta$ is the instantaneous rate of change of the state vector $U$, through the following classes.

- `Grid` holds the locations, sizes and connections of the cells. Only a uniform Cartesian grid exists so far.
- `Vector` stores $U$ on the grid, and `State` extends it for MHD with references to the single variables and storage for quantities outside the state, such as the ratio of specific heats.
- `Evolver` advances the state in time, by Runge–Kutta schemes from RK11, of one stage and first order, and RK22 to the strong-stability-preserving RK33, RK43 and RK53. It computes $\Delta$ through the interface `Scheme`, whose implementations are ideal, Hall and CGL MHD.
- `Scenario` sets the initial conditions and boundaries of a problem and creates the matching `State` on a `Grid`.
- `Hacker` runs tasks of the user when conditions are met during a run, from analysis on the fly to changes of the run. The test of reconnection (§4.6) uses one to compute the rate of reconnection without output files.
- `Roller` drives the loop in time from $t_0$ to $t_1$. Its functions of automatic initialisation build all classes of the algorithm from defaults and options, while every component can also be set by hand.

The default scheme is a Godunov-type finite-volume method in the form of eq. 1, with a global time step $\Delta t = C\,\Delta x_\mathrm{min}/v_\mathrm{max}$, whose Courant number defaults to 0.8, 0.45 and 0.325 in one, two and three dimensions (§2.2). Its steps are interfaces of their own: `Reconstructor`, `Speeder` for the wave speeds, `Fluxor` for the physical fluxes, `Riemann`, and `Sourceror` for the source terms. By default the conserved variables are reconstructed linearly with the monotonised central limiter, $\Delta U_i = \mathrm{minmod}[\beta(U_{i+1} - U_i), \beta(U_i - U_{i-1}), (U_{i+1} - U_{i-1})/2]$ with $\beta = 1.3$, and the HLL solver uses the signal speeds $s_\mathrm{L} = \min(v_\mathrm{L} - c_\mathrm{L}, v_\mathrm{R} - c_\mathrm{R})$ and $s_\mathrm{R} = \max(v_\mathrm{L} + c_\mathrm{L}, v_\mathrm{R} + c_\mathrm{R})$ (eqs. 2 to 6). Errors in the divergence of the magnetic field are cleaned by the generalised Lagrange multiplier of [Dedner et al.](#dedner-et-al-2002) (2002), with $c_h$ at 95 per cent of the largest local wave speed and $c_p^2/c_h = 0.18$ (§3.1). The modes of acceleration enter below the interfaces (2.2.1), so that physics and algorithm, chosen by composing objects at run time, are chosen independently of the hardware. The tests reproduce the shock tube of Brio and Wu, the Orszag–Tang vortex, whistler waves with second-order convergence, magnetosonic waves and the firehose instability in CGL MHD, and the reconnection challenge of the Geospace Environmental Modeling (GEM) project (§4.1 to §4.6). The paper names NumPy, Numba, CuPy and Matplotlib as the software that it uses (acknowledgements), but does not describe how AGATE is installed.

## 4. Sources

The papers:

- <a id="bard-dorelli-2026"></a>Bard, C. and Dorelli, J., High-performance computational magnetohydrodynamics with Python, Computer Physics Communications 322, 110077 (2026), [arXiv:2503.20899](https://arxiv.org/abs/2503.20899), [doi:10.1016/j.cpc.2026.110077](https://doi.org/10.1016/j.cpc.2026.110077). The local copy is `reference-works/Performance in Python/Docs/2503.20899v2.pdf`, the second version on arXiv.
- <a id="lam-et-al-2015"></a>Lam, S. K., Pitrou, A. and Seibert, S., Numba: a LLVM-based Python JIT compiler, in Proceedings of the Second Workshop on the LLVM Compiler Infrastructure in HPC (LLVM-HPC 2015), pp. 1–6 (2015), [doi:10.1145/2833157.2833162](https://doi.org/10.1145/2833157.2833162).

Works cited by the papers:

- <a id="caddy-schneider-2024"></a>Caddy, R. V. and Schneider, E. E., Cholla-MHD: an exascale-capable magnetohydrodynamic extension to the Cholla astrophysical simulation code, ApJ 970, 44 (2024), [doi:10.3847/1538-4357/ad464a](https://doi.org/10.3847/1538-4357/ad464a).
- <a id="dedner-et-al-2002"></a>Dedner, A., et al., Hyperbolic divergence cleaning for the MHD equations, Journal of Computational Physics 175, 645–673 (2002), [doi:10.1006/jcph.2001.6961](https://doi.org/10.1006/jcph.2001.6961).
- <a id="harris-et-al-2020"></a>Harris, C. R., et al., Array programming with NumPy, Nature 585, 357–362 (2020), [doi:10.1038/s41586-020-2649-2](https://doi.org/10.1038/s41586-020-2649-2).
- <a id="myers-et-al-2024"></a>Myers, A., et al., AMReX and pyAMReX: looking beyond the exascale computing project, The International Journal of High Performance Computing Applications 38, 599–611 (2024), [doi:10.1177/10943420241271017](https://doi.org/10.1177/10943420241271017).
- <a id="okuta-et-al-2017"></a>Okuta, R., Unno, Y., Nishino, D., Hido, S. and Loomis, C., CuPy: a NumPy-compatible library for NVIDIA GPU calculations, in Proceedings of the Workshop on Machine Learning Systems (LearningSys) at the Thirty-first Annual Conference on Neural Information Processing Systems (NIPS) (2017).
- <a id="schneider-robertson-2015"></a>Schneider, E. E. and Robertson, B. E., Cholla: a new massively parallel hydrodynamics code for astrophysical simulation, ApJS 217, 24 (2015), [doi:10.1088/0067-0049/217/2/24](https://doi.org/10.1088/0067-0049/217/2/24).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b), digested in `athena-synthesis.md`.

Web sources **[GK]**, consulted on 3 November 2026:

- <a id="web-arxiv-api"></a>[export.arxiv.org/api/query](https://export.arxiv.org/api/query): the records of the arXiv identifiers.
- <a id="web-crossref"></a>[api.crossref.org](https://api.crossref.org): the records of the DOIs.
- <a id="web-agate-repository"></a>[git.smce.nasa.gov/marble/agate-open-source](https://git.smce.nasa.gov/marble/agate-open-source): the repository of AGATE.
