# B1 Strata in the package

**Status.** Open.

**Topics.** [Topic 35, §2.1](../topics/35-packaging-configuration-and-build.md#21-python-packages).

**Supersedes.** None.

## Scope

The brief settles how the five strata of the overview ([§3](../overview.md#3-layers)) take shape in the package mhdpy: the subpackages that hold them and their names, the imports that the rule of use allows between the strata and within each of them, where the tests of each stratum lie and whether the rule binds them, and how the rule is checked. It leaves the modules within each subpackage to the briefs of their stratum, the layout of the repository, the build and the dependencies to the brief on the package and its installation, and the interface that the package offers its users to the briefs of stratum 5. It is the first brief and builds on no earlier one.

- [B1D1](#b1d1-the-subpackages-of-the-strata) The subpackages of the strata: decided.

Still to be written: the rule between the strata, the rule within a stratum, the place of the tests, and the check of the rule.

## B1D1 The subpackages of the strata

**Decision.** In the context of a package that must hold the five strata of the overview, facing imports whose stratum should be plain and a check that should cover every later module, one subpackage per stratum, named `infrastructure`, `mesh`, `core`, `physics` and `driver` (option A), is chosen over one subpackage per component (B). This achieves readability, and extensibility through a check that covers every new module, accepting import paths one level longer. Decided on 2026-11-09, as recommended, except that stratum 1 bears its name in full rather than as `infra`, since a full word reads at once while an abbreviation must be learnt.

**Question.** The strata need a form in the package before the first module of stratum 1 is written, since every import names it and the check of the rule reads it. Each stratum can become one subpackage, or each component a subpackage of its own, with the strata kept only in the configuration of the check. The subpackages also need names. [Topic 35, §2.1](../topics/35-packaging-configuration-and-build.md#21-python-packages) covers how pyro and Ulula are packaged, and the syntheses record how the references divide their code: [Ulula 3.1](../references/ulula-synthesis.md#31-packaging-and-installation) and [3.5](../references/ulula-synthesis.md#35-units), [pyro 3.2](../references/pyro-synthesis.md#32-grids-and-data) and [3.3](../references/pyro-synthesis.md#33-driver-simulations-and-runtime-parameters), [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop) and [Performance in Python 3.9](../references/performance-in-python-synthesis.md#39-pace-components-compiled-at-initialisation).

**Option A: one subpackage per stratum.** Five subpackages directly below `mhdpy`, one to a stratum, each holding the modules of its components and named after the overview: `infra`, `mesh`, `core`, `physics` and `driver`. Ulula divides its package by role rather than by component: `utils`, `physics` with its constants and units, `core` with the solver, its driver and its plots, `setups` with the problems, and `examples` ([Ulula 3.1](../references/ulula-synthesis.md#31-packaging-and-installation), [3.5](../references/ulula-synthesis.md#35-units)). Pace keeps its dynamics, its microphysics and its utilities in separate packages ([Performance in Python 3.9](../references/performance-in-python-synthesis.md#39-pace-components-compiled-at-initialisation)). For mhdpy, the place of a module names its stratum, so that an import shows at a glance whether it runs downwards, and a stratum can be read as one folder while it is built. The check names five subpackages and covers every later module without change, extensions included, since the overview assigns each extension to a stratum ([§3](../overview.md#3-layers)). Import paths grow by one level, as `mhdpy.core.riemann`, and a listing shows the folders in alphabetical order rather than in that of the strata. A component whose code spans strata is split as the overview assigns it, so that the standard boundaries lie in `mesh` and the characteristic ones in `core`.

**Option B: one subpackage per component.** Each component a subpackage directly below `mhdpy`, such as `eos`, `riemann` or `cooling`. Athena++ gives each component a folder of `src/`, among them `eos`, `hydro`, `reconstruct`, `bvals` and `pgen` ([Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop)), and pyro gives each solver a package of its own beside `mesh` and `util` ([pyro 3.2](../references/pyro-synthesis.md#32-grids-and-data), [3.3](../references/pyro-synthesis.md#33-driver-simulations-and-runtime-parameters)). The strata then exist only in the configuration of the check, as an ordered list of groups of subpackages. For mhdpy, import paths are one level shorter, as `mhdpy.riemann`, and the tree resembles that of Athena++. The stratum of a module no longer shows from its place, so that a reader looks it up in the configuration or in the overview. Each new component must also be entered in the configuration, or it escapes the rule unnoticed, unless a further test requires every subpackage to belong to a group. The risk grows with every extension.

**Experiments.** None, since the options differ in how the code reads and in what the check covers, which no measurement decides.

**Recommendation.** Option A, since the tree then shows the strata of the overview, and the check covers every later module, extensions included, without being changed. Its names follow the overview, shortened where the overview's name is long: `infra` for the infrastructure, `core` for the numerical core and `driver` for the driver and problems. The option serves readability, the third priority of §1, and extensibility, the fourth, and gives up none.

**Set aside.** Option B would return if components came to move between strata often, since a move then changes only the configuration of the check, while under option A it changes every import of the component.
