# mhdpy

A Python-first package for astrophysical (magneto)hydrodynamics.

mhdpy is in its planning stage. Its purpose, priorities and architectural decisions are documented in [`docs/architecture.md`](docs/architecture.md).

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
uv sync                               # create the virtual environment with all development and test tools
uv run pytest                         # run the fast test tier
uv run pytest --cov                   # ... with line and branch coverage, which must be 100 %
MHDPY_TEST_TIER=full uv run pytest    # run the full test tier as well
uv run ruff format                    # format the code
uv run ruff check                     # lint the code
uv run pyright                        # type-check the code
```

## Licence

mhdpy is licensed under the BSD 3-Clause License; see [`LICENSE`](LICENSE). Licences of third-party code reused in mhdpy are kept in [`LICENSES/`](LICENSES/README.md).
