# Changelog

All notable changes to mhdpy are recorded here.

## Unreleased

- Project set up according to decision brief D01: src layout, uv with uv_build, ruff, pyright, pytest and continuous integration on GitHub Actions.
- Test setup according to decision brief D02: a `test` extra (pytest, Hypothesis, pytest-cov), a fast and a full test tier selected with `MHDPY_TEST_TIER`, 100 % line and branch coverage enforced in CI on the combined results of all test jobs, and a weekly workflow for the full tier.
- Build setup according to decision brief D04: meson-python with Cython kernels in pure Python mode, compiled by default and run uncompiled with `MHDPY_KERNELS=uncompiled` (both in CI, with coverage combined), and kernels typed for pyright through `.pyi` stubs.
- Requirements documents per layer (`docs/requirements/`), starting with the unit system (UNI01–UNI18), and the first part of the unit system in `mhdpy.foundation.units`: code units, units from dimensions, named units and their labels (UNI01–UNI04).
