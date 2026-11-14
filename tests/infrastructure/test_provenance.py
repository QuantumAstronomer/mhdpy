"""Tests of the record of the code that a run uses."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import mhdpy
from mhdpy.infrastructure.provenance import CodeProvenance


## the root of the checkout, the folder above tests/
ROOT = Path(__file__).resolve().parents[2]


class TestVersion:
    """Tests that the record gives the version and, from a checkout, the commit and whether its tree is modified."""

    ## the files changed after the commit, and whether each marks the tree as modified
    CHANGES = {
        "tracked": (
            "src/mhdpy/core/__init__.py",
            True,
        ),
        "untracked": (
            "note.txt",
            False,
        ),
    }

    @staticmethod
    def git(root: Path, *arguments: str) -> str:
        """Run git in the repository at root, under an identity of its own, and return what it prints."""

        command = ["git", "-c", "user.name=mhdpy", "-c", "user.email=mhdpy@example.invalid", *arguments]
        return subprocess.run(command, cwd = root, capture_output = True, text = True, check = True).stdout.strip()


    @staticmethod
    def provenance(root: Path, **changes: str) -> CodeProvenance:
        """Return the record of a run of the copy of the package below root, with changes to its environment."""

        ## a run that prints its record as JSON
        script = "\n".join([
            "import dataclasses, json",
            "from mhdpy.infrastructure.provenance import code_provenance",
            "print(json.dumps(dataclasses.asdict(code_provenance())))",
        ])

        ## the package from the copy, ahead of the installed package
        environment = os.environ | {"PYTHONPATH": str(root / "src")} | changes
        command = [sys.executable, "-c", script]
        result = subprocess.run(command, cwd = root, env = environment, capture_output = True, text = True)
        assert result.returncode == 0, result.stderr
        return CodeProvenance(**json.loads(result.stdout))


    @pytest.fixture
    def copy(self, tmp_path: Path) -> Path:
        """Return a copy of the package, outside any repository of git."""

        ignore = shutil.ignore_patterns("__pycache__", "*.egg-info")
        shutil.copytree(ROOT / "src", tmp_path / "src", ignore = ignore)
        return tmp_path


    @pytest.fixture
    def checkout(self, copy: Path) -> Path:
        """Return a repository of git whose one commit holds the copy of the package."""

        self.git(copy, "init")
        self.git(copy, "add", ".")
        self.git(copy, "commit", "-m", "Copy the package")
        return copy


    def test_checkout(self, checkout: Path) -> None:
        """Checks PACK14.

        A run from a clean checkout records its version, the full hash of the commit of HEAD, and an unmodified tree.
        """

        commit = self.git(checkout, "rev-parse", "HEAD")
        assert self.provenance(checkout) == CodeProvenance(mhdpy.__version__, commit, False)


    @pytest.mark.parametrize(("name", "modified"), CHANGES.values(), ids = CHANGES.keys())
    def test_changes(self, checkout: Path, name: str, modified: bool) -> None:
        """Checks PACK14.

        A tracked file that differs from the commit marks the tree as modified, and an untracked file does not.
        """

        ## a line appended to the file, which it creates where the file does not yet exist
        with open(checkout / name, "a") as file:
            file.write("## a change\n")
        assert self.provenance(checkout).modified is modified


    def test_no_repository(self, copy: Path) -> None:
        """Checks PACK15.

        A run from a copy outside any repository of git records its version alone.
        """

        assert self.provenance(copy) == CodeProvenance(mhdpy.__version__, None, None)


    def test_untracked_package(self, copy: Path) -> None:
        """Checks PACK15.

        A run from a copy that a repository around it leaves untracked, as a wheel in .venv/, records its version alone.
        """

        ## a repository around the copy, whose one commit holds another file
        (copy / "note.txt").write_text("a note\n")
        self.git(copy, "init")
        self.git(copy, "add", "note.txt")
        self.git(copy, "commit", "-m", "Add a note")
        assert self.provenance(copy) == CodeProvenance(mhdpy.__version__, None, None)


    def test_no_git(self, checkout: Path) -> None:
        """Checks PACK15.

        A run from a checkout on a machine without git records its version alone.
        """

        ## a path of programs that holds no git
        (checkout / "bin").mkdir()
        assert self.provenance(checkout, PATH = str(checkout / "bin")) == CodeProvenance(mhdpy.__version__, None, None)
