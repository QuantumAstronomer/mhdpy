# B2E1 Rate of each route

**Brief.** [B2D1](../../../briefs/B02-kernels.md#b2d1-vectorised-or-compiled), with [B2D2](../../../briefs/B02-kernels.md#b2d2-the-compiler-of-the-kernels) and the simple version beside the fast one, which follow it.

**Status.** Run on 2026-11-09.

## Answer

On one core of the development machine and on $2048^2$ cells, the step reaches about $7 \times 10^5$ cell updates per second in plain NumPy, $1.0$ to $1.5 \times 10^6$ in NumPy in place, $4.2 \times 10^6$ compiled by Numba and $8.1$ to $9.5 \times 10^6$ compiled by Cython or Pythran, depending on the version of Python. Cython and Pythran thus gain 11 to 15 times over plain NumPy, more than the 3 to 10 expected, and 5 to 9 times over NumPy in place, which itself gains 1.6 to 2.1 times over plain NumPy, about the factor of two expected, while Numba gains 6.7 and 4.2 times on 3.13. The production run would take 34 to 40 hours on one core in plain NumPy, 16 to 25 in place, 6 by Numba and about 3 by Cython or Pythran. Numba installs from wheels on Python 3.13 alone, as expected, while Cython and Pythran install on all three versions, build their modules in 7 to 12 s with the compiler of the machine, and leave the GIL disabled on 3.14t, as NumPy does. The loop run uncompiled updates about $1.8 \times 10^4$ cells per second, 46 to 124 times fewer than plain NumPy on $128^2$ cells, and agrees with it to within $2.2 \times 10^{-15}$, while every other version agrees exactly. The result holds for one step of hydrodynamics with linear reconstruction and HLLE, in double precision with the variable on the first axis, on one core of an Intel processor of 2019 under macOS, and for the versions recorded in `results/`. Numba was timed on 3.13 alone, and the first workers, on 3.13, ran with a wider spread than the later ones.

## Question

What rate of cell updates per second does a step of hydrodynamics in two dimensions reach on one core of the development machine, written as vectorised operations of NumPy and as loops compiled by Numba, Cython or Pythran, and does each route install from wheels and run on Python 3.13, 3.14 and 3.14t? No reference times one finite-volume kernel of hydrodynamics in every route on one machine ([topic 41, §1](../../../topics/41-vectorised-and-compiled-kernels.md#1-overview)), and the gains that the references report differ with the kernel, from about 2 on a horizontal diffusion to about 20 on a Jacobi iteration, on a node of 32 cores whose threads the paper does not count ([Performance in Python 2.3.3](../../../references/performance-in-python-synthesis.md#233-fifty-two-kernels-in-numpy-numba-pythran-and-dace)). The measure is the rate of the whole step on one core on $2048^2$ cells, about the $4 \times 10^6$ of the production run, together with its course from $64^2$ cells upwards. A gain of the compiled loops below about two at that size would weigh little against the installation and readability of NumPy, a gain of five or more would weigh for them by the second priority of §1, provided that one compiler installs with one command, and a gain in between would be weighed against what the compiler costs to install. Whether each route installs from wheels alone, builds with the compiler of the machine and leaves the GIL disabled on 3.14t decides which compilers remain for the sub-decision on the compiler, and serves the brief on execution in parallel. The rate of the loop run uncompiled tells what a simple version costs in the tests, and the agreement of the versions whether a route changes the result.

## Expectation

**[GK]** NumPy is expected to reach about $10^6$ cell updates per second on the larger grids, below Ulula's $2.5 \times 10^6$ ([Ulula 3.7](../../../references/ulula-synthesis.md#37-performance)), since the step here takes two stages where Ulula's sweeps once in each direction, and since the processor of 2019 reads memory more slowly than that of 2025. On small grids, the overhead of each call of NumPy, about a microsecond, is expected to lower its rate. Operations in place are expected to gain up to a factor of two over plain expressions, as for the polynomial of [Performance in Python 2.1.3](../../../references/performance-in-python-synthesis.md#213-temporaries-and-the-memory-bus). The compiled loops are expected to run 3 to 10 times faster than plain NumPy on one core, as they pass over memory a few times per stage rather than once per operation. Numba is expected to install from wheels on 3.13 alone, and Cython and Pythran on all three versions, each building its module with the compiler of the machine. On 3.14t, NumPy and a module of Cython that declares itself compatible with free threading are expected to leave the GIL disabled, while for Pythran no expectation can be argued. The loop run uncompiled is expected to be about a hundred times slower than NumPy, as in AGATE ([Performance in Python 2.3.1](../../../references/performance-in-python-synthesis.md#231-the-modes-of-agate-on-the-orszagtang-vortex)), and every version to agree with plain NumPy to within $10^{-12}$ of the largest value of each variable.

## Method

The step advances the Euler equations of an ideal gas with $\gamma = 5/3$ in two dimensions, on a periodic grid of $N \times N$ cells over $[0, 1]^2$ in double precision, with two ghost cells on each side. The initial state is a Kelvin–Helmholtz layer: two smooth shear layers at $y = 1/4$ and $3/4$ between gas of density 1 moving at $-1/2$ and gas of density 2 moving at $+1/2$, at a pressure of 2.5, with a small sinusoidal perturbation of the transverse velocity. The step is Heun's method, a Runge–Kutta method of two stages, whose stages each convert the conserved variables to primitive ones, reconstruct these linearly with the limiter of van Leer, compute the fluxes on all faces by the HLLE solver and update the cells. The time step is fixed from the initial state at a Courant number of 0.4, so that every step does the same work, and the ghost cells are filled by the same copies of NumPy in every version. The state lies with the variable on the first axis, as an array of shape $(4, N + 4, N + 4)$, so that each variable is contiguous.

Six versions compute the same step by the same formulas:

| Version | Route |
|---|---|
| NumPy | expressions on whole arrays, with slices |
| NumPy in place | the same, with every intermediate array allocated once and written through the argument `out` |
| Loop | one module of plain Python, with loops over faces and cells, run uncompiled |
| Numba | the loop module compiled by `njit`, without threads and without fast arithmetic |
| Cython | the loop module compiled in its pure mode, with the types in a file `.pxd` beside it, without checks of bounds, and declared compatible with free threading |
| Pythran | the loop module compiled from a comment that exports its function, without OpenMP |

Each version first runs one step from the same initial state on $128^2$ cells, and its result is compared with that of the plain NumPy version by the largest difference of each variable, relative to its largest value. Each version is then timed on grids of $64^2$, $128^2$, $256^2$, $512^2$, $1024^2$ and $2048^2$ cells, the uncompiled loop on the two smallest alone: one step to warm up, which leaves compilation out, then seven steps, each timed alone, reported by their median, minimum and maximum, and as the rate $N^2$ over the median and the hours that $9 \times 10^{10}$ cell updates would take at that rate. Cython and Pythran build with the compiler of the machine, Apple clang, and their default flags. Every version runs on one thread, with the variables of OpenMP and BLAS set to one, on Python 3.13, 3.14 and 3.14t, wherever its package installs. For each version of Python, the experiment records whether each package installs from wheels alone, the time to build each compiled module, or for Numba to compile on its first call, and on 3.14t whether the GIL is enabled once the module is loaded. The lines of the plain NumPy version, of the version in place and of the loop module are counted without blank lines, comments and docstrings, and those of the file `.pxd` and the comment of Pythran apart. The results are given as tables, and the experiment draws no figure.

## Results

The run took place on 2026-11-09 on the development machine, Darwin 25.6.0 on an Intel Core i7-9750H at 2.60 GHz, with uv 0.13.6, Apple clang 21.0.0 and the commit 657a9a4 (`results/environment.json`), and took 7 min 54 s. NumPy 2.5.4, Cython 3.3.1 and Pythran 0.19.0 installed from wheels alone on Python 3.13.16, 3.14.8 and the free-threaded 3.14.8, and Numba 0.62.1, with NumPy 2.3.5, on 3.13 alone. On 3.14, the Package Index holds no wheel of llvmlite, on which Numba depends, for the machine, and on 3.14t none of Numba (`results/installs.csv`, `results/absent.csv`).

On $2048^2$ cells, the medians of the seven steps give these rates, in cell updates per second, and the hours that $9 \times 10^{10}$ cell updates would take at them (`results/rates.csv`):

| Version | 3.13 | 3.14 | 3.14t | Hours |
|---|---|---|---|---|
| NumPy | $6.29 \times 10^5$ | $7.41 \times 10^5$ | $6.85 \times 10^5$ | 34 to 40 |
| NumPy in place | $1.00 \times 10^6$ | $1.53 \times 10^6$ | $1.43 \times 10^6$ | 16 to 25 |
| Numba | $4.23 \times 10^6$ | | | 5.9 |
| Cython | $9.34 \times 10^6$ | $8.15 \times 10^6$ | $8.45 \times 10^6$ | 2.7 to 3.1 |
| Pythran | $9.47 \times 10^6$ | $8.55 \times 10^6$ | $8.65 \times 10^6$ | 2.6 to 2.9 |

On 3.14, the rate changes with the size of the grid as follows, with the uncompiled loop on the two smallest grids alone and Numba from 3.13:

| Cells | NumPy | In place | Loop | Numba, 3.13 | Cython | Pythran |
|---|---|---|---|---|---|---|
| $64^2$ | $1.95 \times 10^6$ | $2.99 \times 10^6$ | $1.78 \times 10^4$ | $3.91 \times 10^6$ | $9.18 \times 10^6$ | $9.78 \times 10^6$ |
| $128^2$ | $2.19 \times 10^6$ | $2.91 \times 10^6$ | $1.77 \times 10^4$ | $4.69 \times 10^6$ | $1.04 \times 10^7$ | $1.05 \times 10^7$ |
| $256^2$ | $1.09 \times 10^6$ | $2.25 \times 10^6$ | | $4.67 \times 10^6$ | $9.90 \times 10^6$ | $1.02 \times 10^7$ |
| $512^2$ | $8.04 \times 10^5$ | $1.82 \times 10^6$ | | $4.35 \times 10^6$ | $8.32 \times 10^6$ | $8.58 \times 10^6$ |
| $1024^2$ | $8.08 \times 10^5$ | $1.61 \times 10^6$ | | $4.26 \times 10^6$ | $8.14 \times 10^6$ | $8.26 \times 10^6$ |
| $2048^2$ | $7.41 \times 10^5$ | $1.53 \times 10^6$ | | $4.23 \times 10^6$ | $8.15 \times 10^6$ | $8.55 \times 10^6$ |

On $128^2$ cells, the uncompiled loop updates $1.89 \times 10^4$, $1.77 \times 10^4$ and $1.75 \times 10^4$ cells per second on 3.13, 3.14 and 3.14t, 46, 124 and 89 times fewer than plain NumPy, 88 to 164 times fewer than NumPy in place and 576 to 664 times fewer than Cython and Pythran, so that the production run would take some 1,300 to 1,400 hours in it. Cython built its module in 11.5, 10.9 and 7.7 s and Pythran in 8.4, 6.8 and 7.5 s on 3.13, 3.14 and 3.14t, and Numba compiled and ran its first step, on $16^2$ cells, in 1.35 s (`results/builds.csv`). On 3.14t, the GIL stayed disabled once NumPy and the modules of Cython and Pythran were loaded.

After one step on $128^2$ cells, NumPy in place, Numba, Cython and Pythran agree with plain NumPy exactly, on every version of Python. The uncompiled loop differs by $2.2 \times 10^{-15}$ of the largest value in the momentum along $y$ and by $1.1 \times 10^{-16}$ in the momentum along $x$ and in the energy (`results/agreement.csv`). The plain NumPy version takes 49 lines, the version in place 146 and the loop module 68, with 14 lines of the file `.pxd` and one comment of Pythran beside it (`results/lines.json`).

Two details of the code go beyond the method. Cython compiles with the checks of negative indices and of division by zero off as well as those of bounds, and with two directives that its pure mode needs here, `cpow=True`, which makes a power of one half a call of C, and `annotation_typing=False`, which leaves the annotations to pyright. Every version writes the square root of the speed of sound as a power of one half, for the reason given below.

Not foreseen by the plan:

- Pythran compiles the annotations of a module and accepts no import of `typing` or `numpy.typing`, so that the loop module annotates its arrays by strings, which Pythran passes over and pyright reads. Cython's pure mode cannot take the square root from C while the module imports it from `math`, so that every version writes it as a power of one half, which clang turns into the instruction of the square root.
- Numba runs at about half the rate of Cython and Pythran on the same source.
- The rates of Cython and Pythran fall by 14 to 25 per cent from $128^2$ to $2048^2$ cells and that of Numba by 10, while those of plain NumPy fall by 28 to 66 per cent and of NumPy in place by 40 to 47, most of it between $128^2$ and $512^2$.
- The first workers, plain NumPy and NumPy in place on 3.13, ran with a wider spread, and plain NumPy with lower rates on small grids, than on 3.14 and 3.14t. On $64^2$ cells, plain NumPy took from 2.6 to 6.6 ms a step on 3.13 against 1.9 to 2.8 ms on 3.14, and on $2048^2$ cells NumPy in place took from 2.69 to 4.40 s on 3.13 against 2.65 to 2.75 s on 3.14.

## Rerun

The command, run in the folder of the experiment, builds an environment for each version of Python and route, fetching the packages from the Package Index on its first run, and takes about 8 minutes on the development machine. Beside `run.py`, the folder holds the four versions of the stage, `vectorised.py`, `inplace.py`, `loops.py` and `loops.pxd`. The experiment draws no figure, so that it has no `plot.py`.

```
uv run run.py
```
