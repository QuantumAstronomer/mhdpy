# B3E1 Speed-up of each means

**Brief.** [B3D1](../../../briefs/B03-parallel-execution.md#b3d1-threads-or-processes), with [B3D3](../../../briefs/B03-parallel-execution.md#b3d3-whether-it-enters-the-first-pass), which follows it.

**Status.** Run on 2026-11-10.

## Answer

On six workers, one to each core of the development machine, the step on $2048^2$ cells runs 2.05 to 2.29 times faster than on one, alike for threads whose kernel releases the GIL, in either build of Python, and for processes with MPI, well below the three to four and a half expected. Threads and processes thus differ by less than a fifth at that size, and twelve workers on the twelve hardware threads gain 1.87 to 2.82, little more than six. Threads whose kernel holds the GIL gain 1.14 on six workers in the default build of 3.14, as expected, and as much as the others in the free-threaded build. In the default build, threads whose kernel releases the GIL gain within a tenth as much as in the free-threaded build on $2048^2$ cells, as expected, but on 3.14 they fall behind on smaller grids, to 0.95 on six workers on $256^2$ cells against 2.42 in the free-threaded build. At the rates of this run, the production run would take 3.0 to 4.2 hours on one worker and 1.3 to 2.0 hours on six. mpi4py 4.1.2 and MPICH 5.0.2 install from wheels on all three versions and leave the GIL disabled on 3.14t, and every run agrees with the plain NumPy step exactly, as expected. The result holds for one step of hydrodynamics in two dimensions, its domain cut into slabs of rows, on one laptop with an Intel processor of 2019 under macOS, whose rates on one worker ran 12 to 36 per cent below those of the same kernel in B2E1, and part of whose cores served the desktop during the run. It does not tell whether the bandwidth of memory or the clock of the cores sets the ceiling.

## Question

How many times faster than on one worker does the step of [B2E1](../../B02-kernels/E1-rate-of-each-route/README.md) run when two to twelve workers of the development machine share it, as threads whose kernel releases the GIL, in the default and in the free-threaded build of Python, or as processes with MPI, and does each means install from wheels on Python 3.13, 3.14 and 3.14t? No reference measures what threads or processes gain for a finite-volume step of Python on one machine. AGATE times its loops compiled by Numba on 16 threads against NumPy rather than against one thread ([Performance in Python 2.3.1](../../../references/performance-in-python-synthesis.md#231-the-modes-of-agate-on-the-orszagtang-vortex)), Montoya Salazar times threads of pure Python on six cores under Linux, Diehl et al. threads over arrays of NumPy under the GIL of Python 3.10, and PetClaw processes on a supercomputer ([topic 42, §2.5](../../../topics/42-parallelisation-and-performance.md#25-threads-and-processes-in-python)), while the kernel of B2E1 holds the GIL. The measure is the speed-up of the whole step on six workers, one to each core, on $2048^2$ cells, about the $4 \times 10^6$ of the production run, together with its course with the number of workers and on smaller grids, on which each worker does less work between two exchanges. If threads and processes reach speed-ups within about a fifth of each other, the sub-decision rests on what each costs in code, dependencies and installation, while a means clearly faster at that size weighs for itself by the second priority of §1. If threads gain as much in the default build as in the free-threaded one, they need no particular build of Python, and if threads whose kernel holds the GIL gain nothing in the default build, every kernel must release it. A speed-up below about two on six workers would weigh against execution in parallel in the first pass, whatever the means, and one near six for it. The agreement of every run with the serial step tells whether a means changes the result.

## Expectation

**[GK]** The step of B2E1 moves of the order of 1 kB to and from memory per cell update, so that one core at its rate of about $9 \times 10^6$ cell updates per second streams some 10 GB/s, while the two channels of DDR4 of the development machine, at 2667 MT/s, deliver at most about 43 GB/s, and its six cores run at a lower clock together than one alone. The speed-up on six workers on $2048^2$ cells is therefore expected to stay between three and four and a half for every means, as the rate per core of Athena++ halves on a full node ([Athena 3.9](../../../references/athena-synthesis.md#39-performance)). On $256^2$ cells, whose arrays nearly fit the 12 MB of cache that the cores share, it is expected to be higher. Threads whose kernel releases the GIL are expected to gain within a tenth as much in the default build as in the free-threaded one, since the Python between two kernels takes tens of microseconds against milliseconds for the kernel of a slab. Threads whose kernel holds the GIL are expected to gain nothing in the default build and as much as the others in the free-threaded one. The exchange of the ghost rows, some hundreds of kilobytes per stage, is expected to cost MPI no more than a few per cent, and twelve workers on the twelve hardware threads to gain little over six. mpi4py 4.1.2 and MPICH 5.0.2 are expected to install from wheels on all three versions and to leave the GIL disabled on 3.14t, as a trial of two processes found, and every run to agree with the plain NumPy step exactly, as the compiled stage of B2E1 does, since the slabs change no operation of any cell.

## Method

The step is that of B2E1: the Euler equations of an ideal gas with $\gamma = 5/3$ on a periodic grid of $N \times N$ cells over $[0, 1]^2$ in double precision, from the same Kelvin–Helmholtz layer, advanced by Heun's method, whose two stages each convert the conserved variables to primitive ones, reconstruct these linearly with the limiter of van Leer, compute the fluxes on all faces by the HLLE solver and update the cells, with the step fixed from the initial state at a Courant number of 0.4. The stage is the module of loops of B2E1, compiled by Cython in its pure mode with the same directives and the clang of the machine, in two variants: one whose loops run within a section `with cython.nogil:`, which releases the GIL, and that of B2E1, which holds it.

The domain is cut into $P$ slabs of whole rows, as equal as the rows allow, each an array of its own with two ghost rows and two ghost columns on each side. A worker advances its slab through each stage, by the compiled stage and the combination of Heun's method in NumPy, and fills the ghost columns of its slab from its own interior. Between the stages, the ghost rows of each slab are filled from its neighbours, periodically along $y$. Three means share the slabs:

| Means | Workers | Kernel | Ghost rows |
|---|---|---|---|
| Threads | $P$ threads of a pool of `concurrent.futures`, one slab each, all awaited after each stage | releases the GIL | copied by NumPy in the main thread |
| Threads, GIL held | the same | holds the GIL | the same |
| MPI | $P$ processes that `mpiexec` of MPICH starts, through mpi4py | releases the GIL | exchanged with the neighbours by `Sendrecv` |

The threads run on Python 3.13, 3.14 and 3.14t, those whose kernel holds the GIL on 3.14 and 3.14t alone, and MPI on all three, each with $P$ of 1, 2, 3, 4, 6 and 12, the last on the twelve hardware threads of the six cores, on grids of $256^2$, $512^2$, $1024^2$ and $2048^2$ cells. Each case runs one step to warm up, then seven steps, each timed alone by the wall clock, under MPI between two barriers on the first process. They are reported by their median, minimum and maximum, as the rate $N^2$ over the median, as the speed-up, the median of the same means and version on one worker over that on $P$, and as the hours that $9 \times 10^{10}$ cell updates would take at that rate. Before the timings, every means advances $256^2$ cells by one step on each $P$, and its result, gathered into one array, is compared with that of the plain NumPy step of B2E1 on one array by the largest difference of each variable, relative to its largest value. For each version of Python, an environment of uv receives NumPy, Cython, mpi4py and MPICH from wheels alone, and the experiment records whether each installs, the time to build each variant, the time from the launch of a worker to its first step, and on 3.14t whether the GIL is enabled once NumPy, the modules and mpi4py are loaded. The variables of OpenMP and BLAS are set to one. The lines that each means adds to the step are counted without blank lines, comments and docstrings. The results are given as tables, and the experiment draws no figure.

## Results

The run took place on 2026-11-10 on the development machine, Darwin 25.6.0 on an Intel Core i7-9750H at 2.60 GHz with six cores, twelve hardware threads and 32 GB, with uv 0.13.6, Apple clang 21.0.0 and the commit 87240be (`results/environment.json`), and took 418 s. NumPy 2.5.4, Cython 3.3.1, mpi4py 4.1.2 and MPICH 5.0.2 installed from wheels alone on Python 3.13.16, 3.14.8 and the free-threaded 3.14.8, as did setuptools 84.2.1, which Cython needs to build in place and the plan did not name (`results/installs.csv`). Cython built the variants in 6.8 to 16.7 s (`results/builds.csv`).

On $2048^2$ cells, the medians of the seven steps give these speed-ups over one worker of the same means, kernel and version (`results/rates.csv`):

| Means | Kernel | Python | 2 | 3 | 4 | 6 | 12 |
|---|---|---|---|---|---|---|---|
| Threads | releases the GIL | 3.13 | 1.62 | 1.87 | 1.97 | 2.20 | 2.82 |
| Threads | releases the GIL | 3.14 | 1.54 | 1.86 | 2.00 | 2.05 | 2.22 |
| Threads | releases the GIL | 3.14t | 1.55 | 1.86 | 2.02 | 2.22 | 2.39 |
| Threads | holds the GIL | 3.14 | 1.03 | 1.01 | 0.97 | 1.14 | 1.12 |
| Threads | holds the GIL | 3.14t | 1.57 | 1.88 | 2.04 | 2.25 | 2.42 |
| MPI | releases the GIL | 3.13 | 1.56 | 1.91 | 2.06 | 2.29 | 1.87 |
| MPI | releases the GIL | 3.14 | 1.54 | 1.86 | 2.06 | 2.17 | 2.42 |
| MPI | releases the GIL | 3.14t | 1.68 | 1.72 | 2.03 | 2.23 | 2.42 |

On one worker, these cases update $5.99$ to $8.26 \times 10^6$ cells per second, so that $9 \times 10^{10}$ cell updates would take 3.0 to 4.2 hours, and on six workers $1.27$ to $1.89 \times 10^7$, 1.3 to 2.0 hours, apart from the threads whose kernel holds the GIL in the default build, with $6.94 \times 10^6$ and 3.6 hours. On six workers, the speed-up changes with the size of the grid as follows:

| Means | Kernel | Python | $256^2$ | $512^2$ | $1024^2$ | $2048^2$ |
|---|---|---|---|---|---|---|
| Threads | releases the GIL | 3.13 | 1.99 | 2.17 | 2.15 | 2.20 |
| Threads | releases the GIL | 3.14 | 0.95 | 1.27 | 1.45 | 2.05 |
| Threads | releases the GIL | 3.14t | 2.42 | 2.23 | 2.11 | 2.22 |
| Threads | holds the GIL | 3.14 | 1.01 | 1.11 | 1.08 | 1.14 |
| Threads | holds the GIL | 3.14t | 2.68 | 2.01 | 2.24 | 2.25 |
| MPI | releases the GIL | 3.13 | 2.62 | 2.56 | 2.38 | 2.29 |
| MPI | releases the GIL | 3.14 | 2.15 | 1.98 | 2.24 | 2.17 |
| MPI | releases the GIL | 3.14t | 2.30 | 2.20 | 2.23 | 2.23 |

After one step on $256^2$ cells, every means agrees with the plain NumPy step exactly, on every number of workers and every version of Python (`results/agreement.csv`). On 3.14t, the GIL stayed disabled once NumPy, the variants and mpi4py were loaded. A worker of threads began its first step 1.0 to 2.4 s after its launch, the first in each environment 1.7 to 2.4 s, and the processes of MPI began theirs 2.6 to 4.0 s after the first launch of `mpiexec` in each environment and 0.4 to 1.6 s after the later ones, the longer the more processes (`results/starts.csv`). Threads add 11 lines to the step and MPI 16, beside the 31 lines of the slabs that both share (`results/lines.json`).

Not foreseen by the plan:

- The speed-ups on six workers stay between 2.05 and 2.29 on $2048^2$ cells for every means and version, below the three to four and a half expected, and the gain from four workers to six is 3 to 12 per cent.
- On one worker, the rates on $2048^2$ cells lie 12 to 36 per cent below those of the same kernel in B2E1, $8.15$ to $9.34 \times 10^6$, the threads on 3.13 lowest and MPI on 3.13 highest.
- Threads in the default build of 3.14 gain less on the smaller grids than those of 3.13, on six workers on $256^2$ cells 0.95 against 1.99, while their rate on one worker is the higher, $8.55$ against $6.33 \times 10^6$.
- MPI on 3.13 gains less on twelve workers than on six, 1.87 against 2.29 on $2048^2$ cells.
- The spread of the seven steps, from the shortest to the longest over their median, is 0.07 in the median of the cases on $2048^2$ cells and 0.17 over all grids, but single steps took up to four times the median, as on one worker on $1024^2$ cells on 3.14, which the medians pass over.
- Right after the run, the window server and the desktop application through which the work was done took about 1.6 cores together, and served the desktop during part of the run as well. The machine drew mains power, without low-power mode and without a limit of its clock. The experiment did not record the load during the run.

## Rerun

The command, run in the folder of the experiment, makes an environment for each version of Python in `results/raw/`, fetching the packages from the Package Index on its first run, and takes about 7 minutes on the development machine. Beside `run.py`, the folder holds the two variants of the stage, `held.py` and `released.py` with their files `.pxd`, the NumPy step of B2E1 in `vectorised.py`, the slabs in `slabs.py`, and the two means in `threads.py` and `processes.py`. The experiment draws no figure, so that it has no `plot.py`.

```
uv run run.py
```
