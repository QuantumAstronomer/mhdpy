# B2E2 Declarations for Cython

**Brief.** [B2D2](../../../briefs/B02-kernels.md#b2d2-the-compiler-of-the-kernels).

**Status.** Run on 2026-11-10.

## Answer

With the signatures of its four functions alone, in a file `.pxd` of 6 lines instead of 14, the loop module compiled by Cython keeps its rate under `infer_types=True`: $9.79 \times 10^6$ cell updates per second on $2048^2$ cells against $9.64 \times 10^6$ with the full declarations, and within 7 per cent on every grid, as expected. Under the default inference, the same signatures give $3.16 \times 10^5$, 21 to 37 times slower than the full declarations and slower than plain NumPy in B2E1, as expected in magnitude, since the generated C keeps the counters of the loops of `stage` as objects of Python. Contrary to the expectation, it keeps the values that `stage` reads from the arrays as objects too, and only the three typed functions that it calls hold C doubles. Every variant gives the result of plain NumPy exactly. The result holds for one module of loops, Cython 3.3.1 and Python 3.14 on the development machine. The full variant ran 18 per cent faster than the same build in B2E1, which bounds how closely rates of different sessions compare.

## Question

Does the loop module of [B2E1](../E1-rate-of-each-route/README.md), compiled by Cython, keep its rate when its file `.pxd` declares only the signatures of its functions and Cython infers the types of their local variables? B2E1 declared the type of every argument and local variable, in a `.pxd` of 14 lines, and so shows what full declarations reach but not what Cython needs. The measure is the rate of the step on $2048^2$ cells on one core under Python 3.14, for the full `.pxd` of B2E1 and for one of the signatures alone, under the default inference of Cython and under its directive `infer_types=True`. If the signatures alone keep the rate within 10 per cent under either inference, the declarations of a kernel shrink to one per function, about what the comment of Pythran declares, and option B of [B2D2](../../../briefs/B02-kernels.md#b2d2-the-compiler-of-the-kernels) gives up little readability against option C. If the rate falls by a factor of two or more under both, every local variable must be declared, and B2D2 weighs that against the inference of Pythran.

## Expectation

**[GK]** The default inference of Cython gives a variable a C type only where this changes no semantics of Python, which holds for floating-point arithmetic but not for integers, whose overflow differs. Under it, the variables of floating-point values are expected to become C doubles, but the bounds and counters of the loops in `stage` to stay objects of Python, so that the rate falls by a large factor. Under `infer_types=True`, every local variable is expected to take the C type of the expression assigned to it, the counters of the loops included, and the rate to come within a few per cent of the full `.pxd`. Every variant is expected to give the result of plain NumPy exactly.

## Method

The loop module `loops.py` of B2E1 is compiled unchanged by Cython in its pure mode on Python 3.14, with three files `.pxd`:

| Variant | File `.pxd` | Inference |
|---|---|---|
| Full | that of B2E1, with every argument and local variable | default |
| Signatures | the four signatures of B2E1 alone, without the declarations of local variables | default |
| Signatures inferred | the same signatures | `infer_types=True` |

All three keep the directives of B2E1, without checks of bounds, of negative indices and of division by zero, with `cpow=True`, `annotation_typing=False` and the declaration of compatibility with free threading. Each variant first runs one step of B2E1 from its initial state on $128^2$ cells and is compared with plain NumPy by the largest difference of each variable, relative to its largest value. It is then timed as in B2E1, on grids of $64^2$ to $2048^2$ cells, with one step to warm up and seven steps, each timed alone, reported by their median, minimum and maximum, as the rate of cell updates per second and as the hours that $9 \times 10^{10}$ of them would take. Every variant runs on one thread, and the time to build it is recorded. The lines of each file `.pxd` are counted without blank lines and comments. The results are given as tables, and the experiment draws no figure.

## Results

The run took place on 2026-11-10 on the development machine, Darwin 25.6.0 on an Intel Core i7-9750H at 2.60 GHz, with Python 3.14.8, NumPy 2.5.4, Cython 3.3.1, Apple clang 21.0.0, uv 0.13.6 and the commit 7e3d3c1 (`results/environment.json`), and took 3 min 14 s. The three variants built in 11.4, 5.4 and 5.1 s (`results/builds.csv`). The full file `.pxd` takes 14 lines and that of the signatures alone 6 (`results/lines.json`).

The medians of the seven steps give these rates, in cell updates per second (`results/rates.csv`):

| Cells | Full | Signatures | Signatures inferred |
|---|---|---|---|
| $64^2$ | $1.20 \times 10^7$ | $5.33 \times 10^5$ | $1.24 \times 10^7$ |
| $128^2$ | $1.31 \times 10^7$ | $5.52 \times 10^5$ | $1.28 \times 10^7$ |
| $256^2$ | $1.19 \times 10^7$ | $5.59 \times 10^5$ | $1.26 \times 10^7$ |
| $512^2$ | $1.02 \times 10^7$ | $3.90 \times 10^5$ | $9.53 \times 10^6$ |
| $1024^2$ | $9.64 \times 10^6$ | $2.64 \times 10^5$ | $9.63 \times 10^6$ |
| $2048^2$ | $9.64 \times 10^6$ | $3.16 \times 10^5$ | $9.79 \times 10^6$ |

On $2048^2$ cells, $9 \times 10^{10}$ cell updates would take 2.6 hours with the full declarations, 79 with the signatures alone and 2.6 with the signatures inferred. The signatures alone run 21 to 37 times slower than the full declarations on every grid, and the signatures inferred within 7 per cent of them. After one step on $128^2$ cells, every variant agrees with plain NumPy exactly (`results/agreement.csv`).

One check goes beyond the method: the C that Cython generates was searched for the declarations of the local variables of `stage`. With the full file `.pxd` and with the signatures inferred, its counters and bounds are `Py_ssize_t` and its values `double`. With the signatures alone, its counters `i` and `j`, its bound `ny4` and the values that it reads from the arrays, such as `rho`, are objects of Python, while the functions that it calls keep their arguments as `double`.

Not foreseen by the plan, the full variant, the same build as that of B2E1 on 3.14, ran 18 per cent faster than there: 0.435 s a step on $2048^2$ cells against 0.515 s.

## Rerun

The command, run in the folder of the experiment, takes about 3 minutes on the development machine, most of them for the signatures under the default inference. Beside `run.py`, the folder holds `loops.py` and `vectorised.py`, copied unchanged from B2E1, `full.pxd`, the file `.pxd` of B2E1, and `signatures.pxd`.

```
uv run run.py
```
