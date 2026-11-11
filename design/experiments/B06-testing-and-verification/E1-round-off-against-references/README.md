# B6E1 Round-off between kernels and their references

**Brief.** [B6D4](../../../briefs/B06-testing-and-verification.md#b6d4-exact-and-round-off-comparisons)

**Status.** Run on 2026-11-11.

## Answer

Fusion and a reference written apart from the loop each change the result by round-off of the same size, and neither keeps exact agreement, while the build without fusion equals plain NumPy exactly over all 64 steps, as in B2E1. In the state, the largest difference of $\rho$, $m_x$ and $E$ is at most $1.25\epsilon$ of the largest value of each after one step and $8\epsilon$ after 64. $m_y$, whose largest value, about 0.016, is small beside the pressure in its flux, differs by up to $61\epsilon$ after one step and $597\epsilon$ after 64. The differences grow seven- to thirteenfold from one step to 64, near the eightfold growth of the square root that was expected, but fusion across statements, as GCC makes it, differs no more than fusion within statements, against the expectation. Measured against its own largest value, the change of one stage differs by $8 \times 10^2$ to $5.8 \times 10^4\,\epsilon$, far more than the 10 to $100\epsilon$ expected, and four to nine times more on $512^2$ cells than on $128^2$, since the change of a stage shrinks with the cell while the round-off of the fluxes does not. The result holds for one stage of hydrodynamics without transcendental functions, on a periodic layer, on x86-64 with Apple clang imitating the fusion of ARM64, and for the versions recorded in `results/environment.json`.

## Question

How far apart, by round-off alone, do a compiled kernel and an independent version in NumPy come after one stage and over a few steps, when the compiler fuses products and sums into one rounding, as compilers for ARM64 do by default, and when the reference orders its operations otherwise than the loop? [B2E1](../../B02-kernels/E1-rate-of-each-route/README.md) found the compiled loops equal to plain NumPy on the development machine, without fusion and with the operations of both in one order, while the references give the tolerances of their own ports, $10^{-14}$ for Pace and $10^{-6}$ for Veros after one step, without separating their causes ([Performance in Python 3.9](../../../references/performance-in-python-synthesis.md#39-pace-components-compiled-at-initialisation), [3.10](../../../references/performance-in-python-synthesis.md#310-veros-backends-behind-one-code)). The measure is the largest difference of each variable relative to its largest value, in units of $\epsilon = 2^{-52}$, after one stage and in the state after 1 to 64 steps. If fusion and reordering keep it within about $10^2\epsilon$ after one stage and in the state over a few steps, one $k$ of some $10^3$ separates round-off from a fault of the algorithm, whose differences are of the size of a truncation error, and option B of B6D4 can fix one $k$ for every test. If it grows with the number of steps, comparisons of different code must stay at one stage or let $k$ grow with the steps. If fusion leaves the results equal to plain NumPy, which is not expected, option A stays open without fusion switched off.

## Expectation

**[GK]** Without fusion, the compiled loop is expected to equal plain NumPy, as in B2E1. Fusion rounds a product and a sum once instead of twice, so that most fluxes change in their last bit or two. A stage subtracts the fluxes of neighbouring faces, which nearly cancel, so that its change is expected to differ by some 10 to 100 $\epsilon$ of its largest value. In the state, to which a step adds a small change, the difference is expected to stay at a few $\epsilon$ after one step and to grow about as the square root of the number of steps, to some $10\epsilon$ after 64. Fusion across statements, as GCC makes it, is expected to differ somewhat more than fusion within statements, as clang makes it, and the reordered reference about as much as fusion.

## Method

The kernel is the stage of B2E1 in the form of [B2E2](../../B02-kernels/E2-declarations-for-cython/README.md): one stage of a step of hydrodynamics in two dimensions, with linear reconstruction under van Leer's limiter and the HLLE fluxes, copied as `loops.py` with the file of signatures `loops.pxd`. Cython compiles it with the directives of B2E2, `infer_types=True` among them, in three builds that differ only in the flags given to Apple clang through `CFLAGS`: none, as a wheel for x86-64 is built (`plain`); `-mfma`, under which clang fuses within statements by default, as it does on ARM64 (`within`); and `-mfma -ffp-contract=fast`, which fuses across statements, as GCC does on ARM64 (`across`). The assembly of each build, which clang writes with `-S`, is searched for the instructions of fusion, `vfmadd`, so that each build is known to fuse as intended.

Two references in NumPy stand beside the builds. The plain version of B2E1, `vectorised.py`, follows the order of operations of the loop. A version written apart from the loop, `reordered.py`, takes van Leer's limiter in the form $(\Delta_l|\Delta_r| + |\Delta_l|\Delta_r)/(|\Delta_l| + |\Delta_r|)$, the pressure as $(\gamma - 1)[E - (m_x^2 + m_y^2)/(2\rho)]$, and the HLLE fluxes divided by $b_+ - b_-$ rather than multiplied by its inverse, as an independent reference written from the formulas might.

The problem is the periodic Kelvin–Helmholtz layer of B2E1 with $\gamma = 5/3$, on $128^2$ and $512^2$ cells, advanced by Heun's method of two stages with the step that a Courant number of 0.4 allows on the initial state, the same step for every version. Each of the three builds and the reordered reference is compared with plain NumPy, and each build also with the reordered reference: once by the change of one stage from the initial state, and once by the state after 1, 2, 4, 8, 16, 32 and 64 steps. Each comparison gives, for each conserved variable, the largest difference relative to the largest magnitude of that variable in the reference, in units of $\epsilon$, and whether either result holds a NaN. The run uses Python 3.14 on one thread, and its results are tables, without a figure.

## Results

The run took 147 s on 2026-11-11 at commit `ec1a302`, with Python 3.14.8, NumPy 2.5.4, Cython 3.3.1, setuptools 84.2.1 and Apple clang 21.0.0 on the Intel Core i7-9750H of the development machine (`results/environment.json`). Each build holds the fused instructions intended (`results/builds.csv`):

| Build | Flags beyond those of Python | Fused instructions in the assembly | In the module |
|---|---|---:|---:|
| plain | none | 0 | 0 |
| within | `-mfma` | 125 | 125 |
| across | `-mfma -ffp-contract=fast` | 88 | 88 |

The largest difference over the four conserved variables, in units of $\epsilon$, relative to the largest magnitude of each variable in plain NumPy, is the following (`results/differences.csv`). The change of one stage is measured against its own largest value, the state after each number of steps against that of the state.

| Compared with plain NumPy | Cells | One stage | 1 step | 8 steps | 64 steps |
|---|---|---:|---:|---:|---:|
| plain | $128^2$ | 0 | 0 | 0 | 0 |
| within | $128^2$ | 10 900 | 47.1 | 113 | 597 |
| across | $128^2$ | 10 900 | 47.1 | 118 | 522 |
| reordered | $128^2$ | 10 900 | 46.9 | 113 | 557 |
| plain | $512^2$ | 0 | 0 | 0 | 0 |
| within | $512^2$ | 58 000 | 54.8 | 128 | 374 |
| across | $512^2$ | 58 000 | 54.8 | 134 | 333 |
| reordered | $512^2$ | 58 000 | 56.3 | 136 | 339 |

In every comparison the largest difference lies in $m_y$. That of $\rho$, $m_x$ and $E$ is at most 1.25 after one step and 8 after 64 steps, and after one stage it lies between 808 and 4 750 on $128^2$ cells and between 3 280 and 26 900 on $512^2$. Against the reordered reference, the builds within and across differ by at most 14 600 after one stage on $128^2$ cells and 58 100 on $512^2$, 61.2 after one step and 505 after 64 steps. No result holds a NaN.

The plan had the builds differ only in the flags given to Apple clang through `CFLAGS`. As setuptools 84.2.1 compiles with `CFLAGS` instead of the flags of Python once the variable is set, a trial of the plan built without `-O3`, so that the builds within and across receive the flags of Python followed by their own and the build plain no `CFLAGS` at all. The fused instructions are counted in the compiled module as well as in the assembly, and the run took 147 s rather than about two minutes.

Beyond the plan: in that trial, built without `-O3`, clang called the function `pow` of the C library for the square root of the sound speed instead of `sqrt`, so that the build without fusion differed from plain NumPy after one step by one unit in the last place of values of order unity, as the uncompiled loop of B2E1 did, and `-ffp-contract=fast` formed no fused instruction.

## Rerun

Run in the folder of the experiment; it takes about two and a half minutes on the development machine.

```
uv run run.py
```
