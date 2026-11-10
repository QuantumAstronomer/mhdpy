# B3 Parallel execution

**Status.** Open.

**Topics.** [Topic 42](../topics/42-parallelisation-and-performance.md), with [topic 36, §2.4](../topics/36-data-structures.md#24-blocks-of-a-tree) for the blocks over which the work may be shared.

**Supersedes.** None.

## Scope

The brief settles how the work of a step is shared among the cores of a machine ([§5](../overview.md#5-crosscutting-concepts) of the overview): by threads within one process, by processes that exchange their data through MPI, or by both, what each thread or process updates, and whether execution in parallel enters the first pass or follows it as an extension. For the brief on the domain in blocks, it names what the share of each worker demands of the domain. It leaves the number, size and tree of the blocks to that brief, the exchange of ghost cells between blocks to the brief on ghost cells and boundaries, the versions of Python and the dependencies to the brief on the package and its installation, and the time within which the production run must complete to the brief on the problems that verify the first pass. In place of that time, the gain of each means is also stated as the hours that the production run would take on one core and on six. Graphics processors are left out, as the development machine has none that CUDA serves. The brief builds on [B1D1](B01-strata-in-package.md#b1d1-the-subpackages-of-the-strata), which places what the infrastructure provides in `mhdpy.infrastructure`, on [B1D2](B01-strata-in-package.md#b1d2-the-rule-between-the-strata), under which a stratum reaches the code above it only through objects handed down, and on [B2D1](B02-kernels.md#b2d1-vectorised-or-compiled) and [B2D2](B02-kernels.md#b2d2-the-compiler-of-the-kernels), which make every kernel a loop compiled by Cython, whose modules leave the GIL disabled on the free-threaded build ([B2E1](../experiments/B02-kernels/E1-rate-of-each-route/README.md)).

Still to be written: threads or processes, the share of each worker, and whether execution in parallel enters the first pass.
