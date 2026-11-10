# B3E2 Cost of each share

**Brief.** [B3D2](../../../briefs/B03-parallel-execution.md#b3d2-the-share-of-each-worker).

**Status.** Run on 2026-11-10.

## Answer

On six threads and $2048^2$ cells, blocks of $128^2$ and $256^2$ cells update $2.70$ to $3.14 \times 10^7$ cells per second, 9 to 19 per cent more than the faster share of one array, B, which A matches there, and blocks of $512^2$ cells as many as B, so that the price of blocks that the plan feared is not paid at the size of the production run. Blocks of $1024^2$ cells, four for six threads, fall 9 to 11 per cent behind, and blocks of $64^2$ cells run fastest of all in the free-threaded build, 30 per cent above B, but 8 per cent below it in the default build. On the uneven problem, whose dense cells take about four times the work of the others, blocks of $256^2$ cells or less run 39 to 69 per cent faster than B, while A, B and the slabs, whose rows are fixed, run alike at about five eighths of the rate of the best blocks, as expected. On $512^2$ cells, A falls 19 per cent behind B in the default build and 3 per cent in the free-threaded one, more than the few per cent expected. Every share gives the serial result exactly. The result holds for the step of B2E1 split into three kernels, on one laptop with an Intel processor of 2019 under macOS and the versions of Python recorded, whose rates on one thread, $8.4$ to $10.3 \times 10^6$, lie above those of B3E1, with its kernel unsplit, in an earlier session.

## Question

What rate of cell updates does the step of [B2E1](../../B02-kernels/E1-rate-of-each-route/README.md) reach on the six cores of the development machine when each of six threads updates a share of the loops of each kernel (option A of B3D2), a fixed part of one array (B), or whole blocks with ghost cells of their own (C), from blocks of $64^2$ cells to slabs of whole rows, and how much of its rate does each share keep when the work differs between cells? No reference measures these shares in Python. Athena++ gave up forking and joining threads around single loops in C++, and measures the cost of small blocks on one core alone ([Athena 3.5](../../../references/athena-synthesis.md#35-task-lists-and-parallelisation), [3.9](../../../references/athena-synthesis.md#39-performance)), while [B3E1](../E1-speed-up-of-each-means/README.md) shared the step by slabs only. The measure is the rate of the whole step on six threads on $2048^2$ cells, about the size of the production run, for each share, set against that of the faster share of one array, A or B, together with its course on $512^2$ cells and on a problem whose dense half takes several times the work of the rest. If blocks of $256^2$ cells or more keep within a tenth of the faster of A and B, the price of C in performance is small and B3D2 rests on its other grounds, while if no size of block comes within a fifth, that price weighs against C by the second priority of §1. On the uneven problem, blocks that keep their rate better than B by more than a tenth confirm that more blocks than threads balance the work, and equal rates leave the balance without weight. Small blocks faster than slabs would show that blocks that fit the cache raise the ceiling that B3E1 found, for the brief on the domain in blocks to weigh. Every share must give the serial result exactly.

## Expectation

**[GK]** Two layers of ghost cells add 3 per cent to the cells of a block of $256^2$ and 13 per cent to one of $64^2$, which the conversion and the copies of the ghost cells cost, while the 1024 blocks of $64^2$ cells that cover $2048^2$ cells also call their kernels and copy their ghost cells some 14,000 times a step from Python. Blocks of $256^2$ cells or more are therefore expected to keep within a few per cent of A and B, and blocks of $64^2$ cells to fall a tenth or more behind, unless their arrays, which with their scratch fit the share of the cache that each core holds, lift the ceiling of B3E1, whose cause would then be the bandwidth of memory. A, which forks and joins its threads three times a stage, is expected to lose a few per cent to B on $512^2$ cells and nothing on $2048^2$, more in the default build. On the uneven problem, fixed parts of whole rows, as in A, B and the slabs of C, are expected to lose about a third of their rate, since the threads of the dense rows set the pace, and blocks of $256^2$ cells or less, which the threads take as they finish, to keep most of it. Every share is expected to give the serial result exactly.

## Method

The step is that of B2E1 and B3E1: the Kelvin–Helmholtz layer on a periodic grid of $N \times N$ cells, advanced by Heun's method with linear reconstruction, the limiter of van Leer and the HLLE solver, at a step fixed from the initial state. Its stage is split into three kernels, compiled by Cython in its pure mode with the directives of B2E1 and releasing the GIL, each over a range of rows: the conversion to primitive variables, the fluxes along both axes, and the update, which also forms the combination of Heun's method by the operations of B2E1 in the same order. The uneven problem adds after each step a fourth kernel, a source that takes fifty substeps, each a square root, a product and a difference, in every cell whose density exceeds 1.5, the dense half of the layer, as the integration of cooling might in cold gas.

Three shares divide the work among $T$ threads:

| Share | Work of a thread | Waits |
|---|---|---|
| A, the loops of each kernel | an equal range of rows of every call of a kernel on the one array, from a pool of `concurrent.futures` | the end of every call |
| B, a part of one array | a fixed range of rows of the one array through every kernel, from threads that last the whole run | a barrier of `threading` between the kernels |
| C, blocks | whole blocks of $b^2$ cells, or slabs of whole rows, each with ghost cells of its own, from a pool that hands each thread the next block | the end of every stage |

In A and B, the main thread fills the ghost cells of the one array before each stage. In C, each block fills its ghost cells from the interiors of its neighbours at the start of its stage, which is safe, since a stage of Heun's method reads one array and writes another.

Each share runs on Python 3.14 and 3.14t, on one thread and on six, one to each core of the development machine. On $2048^2$ cells, C takes blocks of $64^2$, $128^2$, $256^2$, $512^2$ and $1024^2$ cells and six slabs, and on $512^2$ cells blocks of $64^2$, $128^2$ and $256^2$ cells and six slabs. The uneven problem runs on $2048^2$ cells with the same shares on six threads, and with A alone on one thread. Each case runs one step to warm up, whose result is compared with that of the plain NumPy step of B2E1, followed by the source in NumPy where the problem has one, by the largest difference of each variable relative to its largest value. Seven steps follow, each timed alone, reported by their median, minimum and maximum, as the rate $N^2$ over the median, and as the speed-up over A on one thread, the serial step on one array. The environments, the installations and the builds are made and recorded as in B3E1, and the lines of each share are counted without blank lines, comments and docstrings. The results are given as tables, and the experiment draws no figure.

## Results

The run took place on 2026-11-10 on the development machine, Darwin 25.6.0 on an Intel Core i7-9750H at 2.60 GHz with six cores, twelve hardware threads and 32 GB, with uv 0.13.6, Apple clang 21.0.0 and the commit 516a4fc (`results/environment.json`), and took 265 s. NumPy 2.5.4, Cython 3.3.1 and setuptools 84.2.1 installed from wheels alone on Python 3.14.8 and the free-threaded 3.14.8 (`results/installs.csv`). Cython built the kernels in 16.3 and 8.2 s, and on 3.14t the GIL stayed disabled once they were loaded (`results/builds.csv`).

On the uniform problem on $2048^2$ cells, the medians of the seven steps give these rates, in millions of cell updates per second (`results/rates.csv`):

| Share | Block | 3.14, 1 thread | 3.14, 6 threads | 3.14t, 1 thread | 3.14t, 6 threads |
|---|---|---|---|---|---|
| A | | 10.1 | 26.2 | 9.75 | 24.6 |
| B | | 10.2 | 26.4 | 9.79 | 24.8 |
| C | $64^2$ | 9.17 | 24.2 | 9.19 | 32.3 |
| C | $128^2$ | 10.2 | 31.4 | 9.52 | 29.2 |
| C | $256^2$ | 9.94 | 30.5 | 9.26 | 27.0 |
| C | $512^2$ | 9.15 | 26.4 | 9.36 | 25.4 |
| C | $1024^2$ | 9.00 | 23.5 | 8.35 | 22.5 |
| C | six slabs | 9.98 | 29.2 | 9.47 | 27.1 |

On six threads, the blocks of $128^2$, $256^2$ and $512^2$ cells and the slabs thus run 19, 15, 0 and 11 per cent faster than B in the default build and 18, 9, 2 and 9 per cent in the free-threaded one, the blocks of $64^2$ cells 8 per cent slower and 30 per cent faster, and those of $1024^2$ cells 11 and 9 per cent slower. A runs 1 per cent slower than B in both builds. On $512^2$ cells, the rates on six threads are:

| Share | Block | 3.14 | 3.14t |
|---|---|---|---|
| A | | 21.8 | 23.6 |
| B | | 26.9 | 24.2 |
| C | $64^2$ | 22.5 | 29.5 |
| C | $128^2$ | 28.2 | 28.6 |
| C | $256^2$ | 22.1 | 21.7 |
| C | six slabs | 29.4 | 26.2 |

On the uneven problem on $2048^2$ cells, A on one thread updates $4.05$ and $3.83 \times 10^6$ cells per second in the two builds, against $10.1$ and $9.75 \times 10^6$ on the uniform problem, so that a dense cell takes about four times the work of another. The rates on six threads are:

| Share | Block | 3.14 | 3.14t |
|---|---|---|---|
| A | | 11.1 | 10.7 |
| B | | 11.1 | 10.6 |
| C | $64^2$ | 15.4 | 17.9 |
| C | $128^2$ | 17.5 | 15.9 |
| C | $256^2$ | 16.7 | 15.7 |
| C | $512^2$ | 14.2 | 13.1 |
| C | $1024^2$ | 12.7 | 11.7 |
| C | six slabs | 11.2 | 10.7 |

After its first step, every case agrees exactly with the plain NumPy step of B2E1, followed by the source in NumPy where the problem has one (`results/agreement.csv`). The shares take 29 lines for A, 45 for B and 46 for C, beside the 36 lines that they share (`results/lines.json`).

Not foreseen by the plan:

- At the size of the production run, blocks of $128^2$ and $256^2$ cells run faster than both shares of one array, by 9 to 19 per cent, where the plan expected them a few per cent slower.
- Blocks of $64^2$ cells run fastest of all shares in the free-threaded build on both grids, but slower than B in the default build, by 8 per cent on $2048^2$ cells and 16 on $512^2$.
- On $512^2$ cells, the blocks of $256^2$ cells, four for six threads, run 10 to 18 per cent slower than B.
- On one thread, the uniform problem runs at $8.4$ to $10.3 \times 10^6$ cell updates per second, above the $6.0$ to $8.3 \times 10^6$ of B3E1 and about the rates of B2E1, and six threads on $2048^2$ cells reach speed-ups of 2.30 to 3.31, above the 2.05 to 2.29 of B3E1.
- The spread of the seven steps, from the shortest to the longest over their median, is 0.3 or less in 67 of the 74 cases, but single steps took up to 4.4 times the median, as for the blocks of $128^2$ cells on six threads on 3.14, which the medians pass over.

## Rerun

The command, run in the folder of the experiment, makes an environment for each version of Python in `results/raw/`, fetching the packages from the Package Index on its first run, and takes about 5 minutes on the development machine. Beside `run.py`, the folder holds the kernels in `kernels.py` with `kernels.pxd`, the NumPy step of B2E1 in `vectorised.py`, what the shares have in common in `common.py`, and the three shares in `loops.py`, `parts.py` and `blocks.py`. The experiment draws no figure, so that it has no `plot.py`.

```
uv run run.py
```
