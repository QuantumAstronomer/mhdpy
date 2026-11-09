# B1E1 Violations found by each check

**Brief.** [B1D5](../../../briefs/B01-strata-in-package.md#b1d5-the-check-of-the-rule), with [B1D2](../../../briefs/B01-strata-in-package.md#b1d2-the-rule-between-the-strata), [B1D3](../../../briefs/B01-strata-in-package.md#b1d3-the-rule-within-a-stratum) and [B1D4](../../../briefs/B01-strata-in-package.md#b1d4-the-place-of-the-tests), whose rules it breaks on purpose.

**Status.** Run on 2026-11-09.

## Answer

Import Linter and the test of its own each report the nine violations that the source shows, V1 to V9, and pass the clean package, on Python 3.13, 3.14 and 3.14t alike, as expected. Neither sees V10, the import by a name given at run time, which no check that reads the source can see. Import Linter 2.16 installs from wheels on all three versions, the test of its own takes 85 lines, fewer than the 100 expected, and each runs in under a second. Not foreseen was that Import Linter follows chains of imports, so that one upward import also breaks the contracts of every folder of tests whose modules reach it. The result holds for a small package of eleven variants, for Import Linter 2.16 with grimp 3.19 and for the development machine, and says nothing of violations of other forms than these ten. As Import Linter counts imports within functions, its contract on the top package would also refuse an import there that runs only when called, which B1D2 allows, a case that no variant tested.

## Question

Which violations of the rule of B1 does each candidate check report, and does each install and run on the development machine? The references check no rule of imports, and the documentation of Import Linter leaves open whether imports within functions count, and whether a tree of tests beside the package, or the top package apart from its subpackages, can be bound. The measure is, for each check and each of Python 3.13, 3.14 and 3.14t, the set of the ten planted violations that it reports, together with a pass on the package without violation. A check that misses a violation which the source shows, or that fails on the clean package, cannot carry the rule alone, and a check that does not install on one of the versions would break the single command of development there. The lines of the test of its own tell what option C of B1D5 would cost to write and to keep.

## Expectation

**[GK]** Import Linter builds its graph with the library grimp, which reads every import statement of a module, at its head, within functions and under `TYPE_CHECKING` alike. It is therefore expected to report V1 to V9, V9 through a forbidden contract that takes the top package as a module alone, and V8 once `tests/` is a package. No check that reads the source sees an import by a name given at run time, so that V10 is expected to pass unreported by both checks. The test of its own is expected to report V1 to V9 in fewer than 100 lines. Import Linter is expected to install from wheels on all three versions, as its release notes name Python 3.14 and the free-threaded build.

## Method

A small package `toy` is laid out as B1D4 decides. `src/toy/` holds the five strata `infrastructure`, `mesh`, `core`, `physics` and `driver`, each with two modules, `core` also with two subpackages `a` and `b`, and `tests/` holds a package for each stratum with one test module. Eleven variants are generated, each with one change from the clean package.

| Variant | Planted violation | Rule broken |
|---|---|---|
| V0 | none | none |
| V1 | a module of `mesh` imports `toy.driver` at its head | B1D2 |
| V2 | a module of `core` imports from the driver by `from ..driver import run` | B1D2 |
| V3 | a module of `mesh` imports `toy.driver` within a function | B1D2 |
| V4 | a module of `mesh` imports `toy.driver` under `if TYPE_CHECKING:` | B1D2 |
| V5 | two modules of `core` import each other at their heads | B1D3 |
| V6 | `core.a.x` imports `core.b.y`, and `core.b.z` imports `core.a.w` | B1D3 |
| V7 | two modules of `infrastructure` import each other, one of them within a function | B1D3 |
| V8 | a module of `tests/core/` imports `toy.driver` | B1D4 |
| V9 | `toy/__init__.py` imports `toy.driver` at its head | B1D2 |
| V10 | a module of `mesh` imports `toy.driver` by `importlib.import_module` | B1D2 |

Two checks run on every variant. Import Linter, in its latest release on the Package Index, holds a contract of layers over the strata, one of acyclic siblings with the strata as ancestors, a forbidden contract from the top package taken as a module alone, and one forbidden contract for each folder of tests, with `tests/` a package and both `src/` and the root of the variant on the path of Python. The test of its own, a function of `run.py` that uses the standard library alone, reads every module with `ast`, maps it to its stratum and checks the same rules. A check reports a variant when it fails and names the planted import, and it must pass V0. Both checks run on Python 3.13, 3.14 and 3.14t, each in an environment that uv builds from the Package Index, and whether Import Linter installs from wheels or by a build is recorded. The time of each check on V0 under 3.14 is the median of five runs after one warm-up, with the minimum and maximum. The lines of the test of its own are counted without blank lines, comments and docstrings. The experiment draws no figure.

## Results

The run took place on 2026-11-09 on the development machine, Darwin 25.6.0 on an Intel Core i7-9750H at 2.60 GHz, with uv 0.13.6, at commit 1be42fc (`results/environment.json`). Import Linter 2.16, with grimp 3.19, installed from wheels alone on Python 3.13.16, 3.14.8 and the free-threaded 3.14.8 (`results/installs.csv`). Each check gave the same reports on all three versions (`results/reports.csv`).

| Variant | Rule broken | Import Linter | Test of its own |
|---|---|---|---|
| V0 | none | passes | passes |
| V1 | B1D2 | reported | reported |
| V2 | B1D2 | reported | reported |
| V3 | B1D2 | reported | reported |
| V4 | B1D2 | reported | reported |
| V5 | B1D3 | reported | reported |
| V6 | B1D3 | reported | reported |
| V7 | B1D3 | reported | reported |
| V8 | B1D4 | reported | reported |
| V9 | B1D2 | reported | reported |
| V10 | B1D2 | not reported | not reported |

The test of its own takes 85 lines without blank lines, comments and docstrings (`results/own_check.json`). On V0 under Python 3.14, a run of Import Linter through uvx takes a median of 0.687 s, from 0.673 s to 0.714 s, and a run of the test of its own through uv 0.307 s, from 0.306 s to 0.315 s, both with the start of uv included (`results/timings.csv`).

One deviation from the plan concerns the reading of the reports. Import Linter names the siblings of a cycle by their parent and by their names relative to it, as `.b -> .a` in `toy.core`, and a report counts as naming the planted import when it names it in either form.

Not foreseen by the plan: Import Linter follows chains of imports, so that one upward import also breaks the contracts of the folders of tests whose modules reach it. V1, V3 and V4 each break four contracts, that of the layers and those of the tests of `mesh`, `core` and `physics`, while the test of its own, which reads direct imports alone, reports only the planted import. In V8, Import Linter also names the import of `toy.physics` that follows from the planted import of the driver.

## Rerun

The command, run in the folder of the experiment, fetches Import Linter and its dependencies from the Package Index on its first run and takes about 45 s on the development machine.

```
uv run run.py
```
