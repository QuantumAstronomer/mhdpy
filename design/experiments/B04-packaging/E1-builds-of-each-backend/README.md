# B4E1 Builds of each backend

**Brief.** [B4D2](../../../briefs/B04-packaging.md#b4d2-the-build-backend), on the versions of Python that [B4D1](../../../briefs/B04-packaging.md#b4d1-the-versions-of-python-and-the-platforms) chooses.

**Status.** Run on 2026-11-10.

## Answer

All three backends build the kernel of [B2E2](../../B02-kernels/E2-declarations-for-cython/README.md) in its pure mode into a source distribution and a wheel on Python 3.14, 3.14t, 3.15 and 3.15t. Every wheel gives the result of plain NumPy exactly, leaves the GIL disabled in the free-threaded builds and updates $8.9$ to $9.8 \times 10^6$ cells per second, so that, as expected, no backend changes the rate. They differ in the editable installation. Under meson-python and scikit-build-core, a change to the module `.py` or to its file `.pxd` reaches the next process without a step, in 5 to 7 s, and only the changed kernel is compiled again. Under setuptools it needs a new installation, which takes 9 to 10 s and compiles every kernel again, as expected. Not expected was that Import Linter fails under the editable installation of meson-python, which hides the folders of the package behind its loader, while it passes under the other two. setuptools takes the fewest lines of configuration, 11 against 17 for scikit-build-core and 18 for meson-python, but its source distribution carried the declarations only once they were named as package data. The result holds for one kernel and its copy in two subpackages, for the development machine and for the releases of the tools recorded. With more kernels, the time of a change would grow under setuptools alone, as only setuptools compiles every kernel again.

## Question

Does each backend of [B4D2](../../../briefs/B04-packaging.md#b4d2-the-build-backend), setuptools, meson-python and scikit-build-core, build a kernel in the pure mode of Cython, with its signatures in a file `.pxd`, into a wheel and into an editable installation of a package in the layout of [B1D4](../../../briefs/B01-strata-in-package.md#b1d4-the-place-of-the-tests), on Python 3.14, 3.14t, 3.15 and 3.15t, and what does a change to a kernel take before a test sees it? The references compile no module of Python ([topic 35, §2.1](../../../topics/35-packaging-configuration-and-build.md#21-python-packages), [§2.5](../../../topics/35-packaging-configuration-and-build.md#25-compiled-kernels-and-their-builds)). The documentation of the backends leaves open how each handles a module in the pure mode, whose suffix `.py` Meson does not take as Cython, and whether its editable installation serves Import Linter, which [B1D5](../../../briefs/B01-strata-in-package.md#b1d5-the-check-of-the-rule) runs with the tests.

The measures are, for each backend and version: whether the source distribution and the wheel build, whether the compiled kernel gives the result of plain NumPy exactly, whether the GIL stays disabled on the free-threaded builds, and its rate of cell updates; for the editable installation, whether a change to a file `.py` and to a file `.pxd` reaches a new process, by which step and after how many seconds, and whether Import Linter passes; and the lines of configuration. A backend that fails to build on one of the four versions, or to give the exact result, cannot serve B4D1. Among the others, the step and the time by which a change reaches the tests and the lines of configuration weigh in B4D2. A rate that differs between backends by more than the 18 per cent that [B2E2](../../B02-kernels/E2-declarations-for-cython/README.md) found between sessions would show that the flags with which a backend compiles matter.

## Expectation

**[GK]** All three build on all four versions, since each hands the module to Cython 3.3.1, which supports Python 3.15, and to clang. Each kernel then gives the exact result, leaves the GIL disabled through the directive `freethreading_compatible` and reaches the rate of B2E2 within its spread. meson-python takes the most lines, as each module `.py` needs a step of its own that runs Cython. Its editable installation sees both changes at the next import within a few seconds, scikit-build-core's only through its experimental rebuild on import, and that of setuptools only after a new installation, which compiles both kernels again. Whether Import Linter finds the package through the hooks of import that the editable installations of meson-python and scikit-build-core install cannot be argued in advance.

## Method

A package `mhdpy` in the layout of B1D4 holds the subpackages `infrastructure` and `core` in `src/mhdpy/`. `core` holds two kernels: the module `loops.py` of [B2E2](../../B02-kernels/E2-declarations-for-cython/README.md) with its signatures in `loops.pxd`, and a copy of both named `loops2`, so that a rebuild shows whether it compiles an unchanged kernel too. Both are compiled under the directives of B2E2: bounds and negative indices unchecked, C division, `cpow`, annotations not typed, `infer_types=True` and `freethreading_compatible=True`. Each kernel also defines a function `marker`, declared in its `.pxd` as `cpdef double marker()`, whose body returns `1`, as the target of the changes. A module `core/eos.py` imports `infrastructure/units.py`, so that Import Linter has an import to check. The package is a repository of git with its files committed, as meson-python makes its source distribution from the files that git tracks.

Each backend builds the same package from the smallest configuration that its documentation gives.

| Backend | Files of configuration |
|---|---|
| setuptools | `pyproject.toml`, and `setup.py`, which hands both kernels to `cythonize` with the directives |
| meson-python | `pyproject.toml`, and `meson.build`, which runs Cython on each `.py` by a custom target with its `.pxd` as a dependency and installs the modules of Python |
| scikit-build-core | `pyproject.toml`, and `CMakeLists.txt`, which transpiles each `.py` with `cython_transpile` of cython-cmake and builds it with `python_add_library` |

For each backend and each of Python 3.14, 3.14t, 3.15 and 3.15t, in environments that uv makes afresh:

1. `uv build` builds the source distribution and, from it, the wheel. The time of both is recorded, and the files of the wheel are listed.
2. The wheel is installed with NumPy into an environment of its own. A worker process imports both kernels, compares one step of B2E2 on $128^2$ cells with plain NumPy, records whether the GIL is enabled after the imports, and times the step on $2048^2$ cells as B2E2 does: one step to warm up, then the median of seven with the minimum and maximum, in cell updates per second.
3. An editable installation is made in a third environment, without build isolation and with the build tools installed beforehand, as each documentation advises, that of scikit-build-core with its experimental rebuild on import and a lasting folder of the build. A worker checks that `marker()` returns `1.0`.
4. The body of `marker` in `loops.py` is changed to return `2`. A new process imports `loops` and prints `marker()`. If it still prints `1.0`, the step that the backend documents is taken, a new editable installation for setuptools, and the process is repeated. Recorded are whether the change was seen without a step, the step that made it seen, the seconds from the start of the step or process to the print, and whether the module of `loops2` was compiled again, by the time of its file.
5. The declaration of `marker` in `loops.pxd` is changed to `cpdef long marker()`, so that the same body now returns `2` rather than `2.0`, and step 4 is repeated.
6. In the editable environment, Import Linter runs with a contract of layers that puts `mhdpy.core` above `mhdpy.infrastructure`, from its configuration in `pyproject.toml`, and its pass or failure is recorded.

The lines of configuration are counted in `pyproject.toml`, without the table `[project]`, which all three share, and in `setup.py`, `meson.build` or `CMakeLists.txt`, without blank lines and comments. `results/environment.json` records the versions of the backends, Cython, Meson, ninja and CMake. The experiment draws no figure.

## Results

The run took place on 2026-11-10 on the development machine, Darwin 25.6.0 on an Intel Core i7-9750H at 2.60 GHz, with uv 0.13.6, at commit b0c4663, on Python 3.14.8 and 3.15.2 in both builds (`results/environment.json`). Every environment held Cython 3.3.1, NumPy 2.5.4, and Import Linter 2.16 with grimp 3.19, besides setuptools 84.2.1, meson-python 0.22.1 with Meson 1.12.1 and ninja 1.13.2, or scikit-build-core 1.1.2 with cython-cmake 0.3.0, CMake 4.4.4 and ninja 1.13.2.

Every backend built the source distribution, the wheel and the editable installation on all four versions (`results/builds.csv`). The times below range over the four versions.

| Backend | Source distribution and wheel, s | Editable installation, s | Platform of the wheel |
|---|---|---|---|
| setuptools | 18.7 to 25.1 | 7.9 to 11.9 | `macosx_10_15_x86_64` |
| meson-python | 18.9 to 24.3 | 10.9 to 14.8 | `macosx_26_0_x86_64` |
| scikit-build-core | 11.6 to 16.3 | 10.7 to 14.0 | `macosx_26_0_x86_64` |

In every wheel, both kernels loaded as compiled modules and gave the result of plain NumPy exactly, and the GIL stayed disabled on 3.14t and 3.15t (`results/checks.csv`). The rate on $2048^2$ cells, the median of seven steps in millions of cell updates per second, is the following.

| Backend | 3.14 | 3.14t | 3.15 | 3.15t |
|---|---|---|---|---|
| setuptools | 9.58 | 9.58 | 9.66 | 9.58 |
| meson-python | 9.66 | 9.65 | 9.66 | 9.77 |
| scikit-build-core | 9.45 | 9.64 | 9.68 | 8.94 |

The slowest of the seven steps of scikit-build-core on 3.15t took 0.68 s against a median of 0.47 s. Both changes, to the module `.py` and to its file `.pxd`, behaved alike in every case (`results/changes.csv`).

| Backend | Change seen without a step | Step | Seconds until the change is seen | `loops2` compiled again |
|---|---|---|---|---|
| setuptools | in no case | a new editable installation, 8.0 to 9.2 s | 9.0 to 10.3 | in every case |
| meson-python | in every case | none | 5.1 to 5.9 | in no case |
| scikit-build-core | in every case | none | 5.3 to 7.4 | in no case |

Import Linter kept the contract under the editable installations of setuptools and scikit-build-core on all four versions, and failed under that of meson-python on all four with the report "Missing layer 'mhdpy.core': module mhdpy.core does not exist." (`results/linter.csv`). The configuration takes 11 lines for setuptools, 5 in `pyproject.toml` and 6 in `setup.py`, 18 for meson-python, 3 and 15 in `meson.build`, and 17 for scikit-build-core, 6 and 11 in `CMakeLists.txt` (`results/lines.json`). Beside each compiled kernel, the wheel of setuptools holds its source, its declarations and its C, that of scikit-build-core its source and declarations, and that of meson-python nothing (`results/contents.json`).

Four deviations from the plan arose in the trials before the run. The configuration of setuptools gained the table `[tool.setuptools.package-data]`, which names the files `.pxd`, for the reason given below. Every worker and every run of Import Linter ran with the environment activated, its folder `bin` first on the path, as `uv run` and `activate` set it, since the rebuild of scikit-build-core calls `cmake` by name. The worker skips the timing on $2048^2$ cells of a kernel slower than plain NumPy on $128^2$, which no case of the run met. The table `[tool.importlinter]`, the same for all three backends, is left out of the count of lines, as `[project]` is. The names of the wheels were recorded beyond the plan, as they show the platform.

Not foreseen by the plan:

- In the first trial of setuptools, the source distribution held the C that Cython had written beside each module, but not its declarations. The wheel built from it compiled the kernels without them, so that they gave the result of NumPy exactly but ran so slowly that their timing was stopped after ten minutes. Naming the files `.pxd` as package data restored the declarations.
- The editable installation of meson-python gives the package a search location within the file of its loader, `_mhdpy_editable_loader.py/mhdpy`, rather than a folder, so that Import Linter finds no subpackage.
- The rebuild of scikit-build-core on import fails, with an error, in a process whose path lacks the folder `bin` of the environment.
- meson-python and scikit-build-core tag their wheels for the version of macOS on which they are built, 26.0, and setuptools for that of the build of Python, 10.15.

## Rerun

The command, run in the folder of the experiment, needs Python 3.14, 3.14t, 3.15 and 3.15t installed by uv. It fetches the build tools from the Package Index on its first run, takes about 12 minutes on the development machine and leaves some 1.5 GB of environments and builds in `results/raw/`. A single case runs alone with its backend and version, as `uv run run.py meson-python 3.14`.

```
uv run run.py
```
