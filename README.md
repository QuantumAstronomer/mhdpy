# mhdpy

A Python-first package for astrophysical (magneto)hydrodynamics.

mhdpy is in its planning stage. Its purpose, priorities and architectural decisions are documented in [`docs/architecture.md`](docs/architecture.md).

## Development

mhdpy is developed with [uv](https://docs.astral.sh/uv/). After cloning the repository:

```bash
uv sync                 # create the virtual environment with all development tools
uv run pytest           # run the test suite
uv run ruff format      # format the code
uv run ruff check       # lint the code
uv run pyright          # type-check the code
```

## Licence

mhdpy is licensed under the BSD 3-Clause License; see [`LICENSE`](LICENSE). Licences of third-party code reused in mhdpy are kept in [`LICENSES/`](LICENSES/README.md).
