# B4E2 Cost of choices at run time

**Brief.** [B4D3](../../../briefs/B04-packaging.md#b4d3-when-the-physics-is-chosen).

**Status.** Run on 2026-11-10.

## Answer

Fixing the ratio of specific heats and the number of scalars when the kernel is compiled raises the rate of the step 1.4 to 2.1 times over giving them as a run starts. On $2048^2$ cells, the rate rises from $5.98$ to $9.68 \times 10^6$ cell updates per second without a scalar, and from $5.64$ to $7.99 \times 10^6$ with one. The gain holds even without a scalar, where the loops over the scalars of the variant given run no iteration. It is far more than the tenth expected, and beyond the fifth at which the question gives weight to option C. A solver called through a pointer at each face ran 8 to 9 per cent slower than the variant given with one scalar, but up to 23 per cent faster without one, so that its cost cannot be told from that of the sizes given at run time, which it shares. Every variant gave the result of the variant given exactly, and without a scalar that of plain NumPy. The fixed variants fix both choices at once, so that the experiment does not tell their shares apart. The rates on $256^2$ cells, a hundredth of a second per step, varied more between processes than those on $2048^2$ cells. The result holds for this stage, for Cython 3.3.1 with Apple clang 21 and for the development machine.

## Question

How much faster does the step of [B2E2](../../B02-kernels/E2-declarations-for-cython/README.md) run when its choices are fixed as its kernel is compiled, as the macros that the configuration of Athena++ writes fix them, than when they are given as a run starts, and what does a choice made within the loop over faces cost? The choices are those that the first pass makes: the ratio of specific heats of the equation of state, the number of passive scalars, of which the production run carries one, and the Riemann solver. [Topic 35, §4](../../../topics/35-packaging-configuration-and-build.md#4-assessment) holds that a configuration at build time lets the compiler specialise loops and branches to the chosen physics, but no reference measures what this gains for a kernel of Python compiled by Cython.

The measure is the rate of cell updates of the step on one core, for each variant, on $256^2$ cells, the size of the blocks that ran fastest in [B3E2](../../B03-parallel-execution/E2-cost-of-each-share/README.md), and on $2048^2$ cells. A gain of the fixed choices below a tenth costs option A of B4D3 little. A gain of a fifth or more gives weight to option C, which compiles versions specialised to chosen values within the wheel, while option B stays bound by the exception of §1 in any case. The variant that calls the solver through a pointer within the loop over faces shows what option A must avoid, and by how much.

## Expectation

**[GK]** Fixing the choices at build time gains less than a tenth. The cost of the step lies in the arithmetic of the solver at each face and in the traffic of memory, which no choice changes. A loop over one scalar whose bound is given at run time adds a comparison per face, and a ratio of specific heats given at run time costs a few operations per cell that a constant would let the compiler fold. A solver called through a pointer at each face runs a fifth or more slower, as the compiler can no longer inline it, and its arguments and four results pass through the stack.

## Method

The stage of [B2E2](../../B02-kernels/E2-declarations-for-cython/README.md) gains passive scalars. Their conserved densities $\rho C$ follow the four variables of the gas in the arrays of the state, their concentrations $C$ are reconstructed with the limiter of the gas, and their fluxes are the mass flux of the solver times the concentration upwind, as Athena++ forms them ([topic 21, §2.2](../../../topics/21-passive-scalars.md#22-upwinded-fluxes)). Without scalars, the stage is that of B2E2. Three variants of it are compiled by Cython in its pure mode, each with its signatures in a file `.pxd`, under the directives of B2E2, and built by setuptools through `cythonize`, as [B4D2](../../../briefs/B04-packaging.md#b4d2-the-build-backend) decides.

| Variant | Ratio of specific heats | Number of scalars | Riemann solver |
|---|---|---|---|
| fixed | a constant of a header `config.h` that the `.pxd` declares, as the macros of Athena++ | a constant of the same header, with one build for each number | HLLE, called directly |
| given | an argument of the stage | an argument of the stage | HLLE, called directly, as by a stage compiled for it and chosen once per call |
| pointer | an argument of the stage | an argument of the stage | HLLE, called within the loop over faces through a pointer that a function sets as the run starts |

Each variant takes the problem, the step and the timing of B2E2: the Kelvin–Helmholtz layer with $\gamma = 5/3$, Heun's method, one step to warm up, then the median of seven steps with the minimum and maximum, in cell updates per second. The scalar starts as the concentration of the dense layer, $C = \rho - 1$, so that it jumps across both shear layers. The variants run on $256^2$ and $2048^2$ cells, without a scalar and with one, each in a process of its own, on Python 3.14 alone, as they differ in their compiled code alone. Before the timing, the state of each variant after one step on $128^2$ cells is compared with that of the variant "given" for exact agreement, and, without a scalar, with plain NumPy as in B2E2. The experiment draws no figure.

## Results

The run took place on 2026-11-10 on the development machine, Darwin 25.6.0 on an Intel Core i7-9750H at 2.60 GHz, with Python 3.14.8, NumPy 2.5.4, Cython 3.3.1, setuptools 84.2.1 and Apple clang 21.0.0, at commit ad8027f (`results/environment.json`). The four builds took 5.1 to 10.0 s (`results/builds.csv`). After one step on $128^2$ cells, every variant gave the state of the variant given exactly, and, without a scalar, that of plain NumPy (`results/agreement.csv`). The rates are the median of seven steps, in millions of cell updates per second (`results/rates.csv`).

| Scalars | Cells | fixed | given | pointer |
|---|---|---|---|---|
| 0 | $256^2$ | 11.73 | 5.63 | 6.95 |
| 0 | $2048^2$ | 9.68 | 5.98 | 6.17 |
| 1 | $256^2$ | 9.62 | 6.69 | 6.07 |
| 1 | $2048^2$ | 7.99 | 5.64 | 5.19 |

The variant fixed ran 2.08 and 1.62 times as fast as the variant given without a scalar, on $256^2$ and $2048^2$ cells, and 1.44 and 1.42 times with one. The variant pointer ran 1.23 and 1.03 times as fast as the variant given without a scalar, and 0.91 and 0.92 times with one. At the rates on $2048^2$ cells with one scalar, the production run would take 3.1 hours on one core with the variant fixed, 4.4 with the variant given and 4.8 with the variant pointer. The run kept to the plan.

Not foreseen by the plan: a trial of the same script, run in a scratch copy a few minutes before, gave rates within 2 per cent of these on $2048^2$ cells. On $256^2$ cells, two of its six rates differed from these by 19 and 40 per cent, the variant given without a scalar reaching $7.89 \times 10^6$ rather than $5.63 \times 10^6$.

## Rerun

The command, run in the folder of the experiment, builds the four variants and runs the six workers in about 70 s on the development machine.

```
uv run run.py
```
