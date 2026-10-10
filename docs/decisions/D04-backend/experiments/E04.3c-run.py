"""Experiment E04.3 (driver): run ``E04.3b-purepython.py`` in the E04.1 Linux container (build it first with E04.1h-run.py).

Uses only the standard library. Run from this directory with (Docker must be running):

    uv run --no-project --python 3.14 E04.3c-run.py

Results are written to results/E04.3b-purepython.json.
"""

import subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()


def main() -> None:
    (HERE / "results").mkdir(exist_ok=True)
    subprocess.run(
        [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "-v", f"{HERE}:/work:ro", "-v", f"{HERE / 'results'}:/out", "-v", "mhdpy-e041-uv-cache:/root/.cache/uv",
            "-w", "/work", "mhdpy-e041",
            "uv", "run", "--locked", "--script", "E04.3b-purepython.py", "/out/E04.3b-purepython.json",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
