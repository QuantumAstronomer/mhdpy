# mhdpy

A Python-first package for astrophysical (magneto)hydrodynamics.

mhdpy is in early development: its foundation layer is being built, starting with the unit system. Its purpose, priorities and architectural decisions are documented in [`docs/architecture.md`](docs/architecture.md).

## Verifying an installation

The test suite ships with the package. To run it on an installed copy of mhdpy:

```bash
pip install "mhdpy[test]"
pytest --pyargs mhdpy
```

This runs the fast test tier. The full tier (high-resolution and three-dimensional convergence series, all benchmark problems) takes considerably longer and is included by setting `MHDPY_TEST_TIER=full`.

## Development

mhdpy is developed with [uv](https://docs.astral.sh/uv/). After cloning the repository:

```bash
uv sync                                 # create the virtual environment with all development and test tools
uv run nox                              # run every check CI runs: lint, types, tests in both kernel modes, coverage
uv run nox -s tests -- -k TestRecords   # run a selection of tests, in both kernel modes
MHDPY_TEST_TIER=full uv run nox         # include the full test tier
uv run pytest                           # a quick test run, compiled kernels only
uv run ruff format                      # format the code
uv run nox -s readmes                   # regenerate the layer READMEs after changing a module docstring
```

`uv run nox` runs the sessions defined in `noxfile.py`, the same ones CI runs. The tests run twice, once with the kernels compiled and once uncompiled, and line and branch coverage must reach 100 % on the two runs combined. Each layer of the package (for example `src/mhdpy/foundation/`) has a README made of the docstrings of its modules; `uv run nox` also checks that the READMEs agree with the docstrings.

## Licence

mhdpy is licensed under the BSD 3-Clause License; see [`LICENSE`](LICENSE). Licences of third-party code reused in mhdpy are kept in [`LICENSES/`](LICENSES/README.md).
