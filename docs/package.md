# The package

mhdpy is installed as one package. Its code lies in five strata, with tests that mirror them, under a rule of imports that a test enforces. Its metadata tells an installer what it needs, and its version is derived from git, together with a record of the code that each run can keep. This document explains each part to a reader new to the repository. The requirements that the parts meet, with their reasons, are [PACK01](../design/requirements/infrastructure/package.md#pack01) to [PACK15](../design/requirements/infrastructure/package.md#pack15) in the [requirements of the package](../design/requirements/infrastructure/package.md), and the decisions behind them are taken in the briefs [B1](../design/briefs/B01-strata-in-package.md) and [B4](../design/briefs/B04-packaging.md).

## Layout

The package lies in `src/mhdpy/`, with one subpackage for each stratum of the [overview](../design/overview.md#3-layers), from the bottom up `infrastructure`, `mesh`, `core`, `physics` and `driver` ([PACK01](../design/requirements/infrastructure/package.md#pack01)). The place of a module thus names its stratum ([B1D1](../design/briefs/B01-strata-in-package.md#b1d1-the-subpackages-of-the-strata)). The folder `src/` keeps the package from being imported from the root of the checkout by accident, so that the tests run against the package as installed ([B1D4](../design/briefs/B01-strata-in-package.md#b1d4-the-place-of-the-tests)). The tests lie in the package `tests/`, with a subpackage of the same name for each stratum ([PACK02](../design/requirements/infrastructure/package.md#pack02)).

## The rule of imports

Each stratum may use the strata below it and none above, so that it can be read and tested with those below it alone ([B1D2](../design/briefs/B01-strata-in-package.md#b1d2-the-rule-between-the-strata)). Code above a stratum is reached only through objects handed down at run time. Four rules hold:

- No stratum imports one above it, whether at the head of a module, within a function or for type checking alone ([PACK03](../design/requirements/infrastructure/package.md#pack03)).
- Within a stratum, at every level of its subpackages, the modules import each other without a cycle ([PACK04](../design/requirements/infrastructure/package.md#pack04), [B1D3](../design/briefs/B01-strata-in-package.md#b1d3-the-rule-within-a-stratum)).
- The top package, `src/mhdpy/__init__.py`, imports no stratum, as Python runs it before any of them ([PACK05](../design/requirements/infrastructure/package.md#pack05)).
- The tests of a stratum import no stratum above it ([PACK06](../design/requirements/infrastructure/package.md#pack06)).

Import Linter holds the rules as contracts in `pyproject.toml`, each named after its requirement, and the class `TestImports` of `tests/test_package.py` runs it without its cache whenever the tests run ([B1D5](../design/briefs/B01-strata-in-package.md#b1d5-the-check-of-the-rule)). The same class plants seven violations in copies of the package and requires each to break its contract ([PACK07](../design/requirements/infrastructure/package.md#pack07)), so that the check is itself shown to work.

## The metadata

The metadata is what an installer reads from the distribution, and the table `[project]` of `pyproject.toml` declares it. It admits Python from 3.14, so that an installer refuses an older Python at once ([PACK08](../design/requirements/infrastructure/package.md#pack08), [B4D1](../design/briefs/B04-packaging.md#b4d1-the-versions-of-python-and-the-platforms)). It names NumPy, from release 2.3.2 and without an upper bound, as the only dependency at run time ([PACK09](../design/requirements/infrastructure/package.md#pack09), [B4D4](../design/briefs/B04-packaging.md#b4d4-the-dependencies)). It declares no extra, as the tools of development lie in the group `dev`, which the metadata leaves out and `uv.lock` fixes ([PACK10](../design/requirements/infrastructure/package.md#pack10)). It names the licence by the SPDX expression `BSD-3-Clause`, with `LICENSE` as its only file ([PACK11](../design/requirements/infrastructure/package.md#pack11), [B4D5](../design/briefs/B04-packaging.md#b4d5-the-licence)). The class `TestMetadata` reads these lines from the metadata of the installation rather than from `pyproject.toml`.

## The version and its record

The version is written nowhere by hand. When mhdpy is built, setuptools-scm derives it from git ([PACK13](../design/requirements/infrastructure/package.md#pack13), [B4D6](../design/briefs/B04-packaging.md#b4d6-the-version-and-its-record)): at a commit that a tag marks, the version of the tag, such as `0.2.0`, and at any other commit a version whose local part names the commit, such as `0.2.1.dev1+g1a2b3c4d5`. The top package exposes the version of the metadata as `mhdpy.__version__` ([PACK12](../design/requirements/infrastructure/package.md#pack12)).

An editable installation keeps the version of its last build, however many commits follow it. The record of the code therefore reads git while mhdpy runs. The function `code_provenance` of `mhdpy.infrastructure.provenance` returns a frozen dataclass `CodeProvenance`, with the fields `version`, `commit` and `modified`. Where git tracks the file of the top package, mhdpy runs from a checkout, and the record gives the version, the full hash of the commit of `HEAD`, and whether a tracked file differs from that commit, untracked files left out ([PACK14](../design/requirements/infrastructure/package.md#pack14)). Otherwise, as after an installation from a wheel or on a machine without git, it gives the version alone, with `commit` and `modified` set to `None` ([PACK15](../design/requirements/infrastructure/package.md#pack15)). Asking whether git tracks that file, rather than whether a repository lies around it, keeps a wheel installed in `.venv/` of a checkout from taking the commit of its surroundings. Every run can thus name the code that produced it.

## Working with the package

uv builds the environment of development from `uv.lock`, with mhdpy installed editable from `src/`:

```bash
uv sync
```

The tests, the check of imports among them, and the strict check of the types then run with:

```bash
uv run pytest
uv run pyright
```

A change to `pyproject.toml` reaches the metadata at the next `uv run`, as uv then installs mhdpy again. A new commit does not, which is why the record of the code reads git.
