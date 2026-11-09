# B2 Kernels

**Status.** Open.

**Topics.** [Topic 41](../topics/41-vectorised-and-compiled-kernels.md), with [topic 36, §2.5](../topics/36-data-structures.md#25-layouts-for-kernels) for the layouts that the kernels favour.

**Supersedes.** None.

## Scope

The brief settles the route in which the loops over cells of strata 2 to 4 are written ([§5](../overview.md#5-crosscutting-concepts) of the overview): vectorised in NumPy or compiled, and by which compiler, whether compiled kernels may later join a vectorised route and in which form, whether a simple version of each kernel stands beside the fast one to check it, and the benchmark by which the rate of cell updates per second is measured and tracked during development. For the brief on execution in parallel, it records whether each route runs on the free-threaded build. It leaves the order of the axes and the layout of the state to the brief on the arrays of the state, which serves the route chosen here, the sharing of the work among cores to the brief on execution in parallel, the build backend, the versions of Python and the dependencies to the brief on the package and its installation, and the time within which the production run must complete to the brief on the problems that verify the first pass. In place of that time, the rate of each route is also stated as the hours that the production run would take on the development machine. The brief builds on [B1D1](B01-strata-in-package.md#b1d1-the-subpackages-of-the-strata), which places what the route provides to the strata above in `mhdpy.infrastructure`, on [B1D2](B01-strata-in-package.md#b1d2-the-rule-between-the-strata), under which a stratum reaches code above it only through objects handed down, and on [B1D4](B01-strata-in-package.md#b1d4-the-place-of-the-tests), which places the tests in `tests/`.

Still to be written: the route of the kernels, vectorised or compiled, whether compiled kernels may join a vectorised route, which falls away if the route is compiled, a simple version beside the fast one, and the benchmark.
