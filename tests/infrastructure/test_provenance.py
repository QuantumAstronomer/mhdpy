"""Tests of the record of the code that a run uses."""

import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mhdpy.infrastructure.provenance import CodeProvenance


## the root of the checkout, the folder above tests/
ROOT = Path(__file__).resolve().parents[2]
## the version in the metadata of the installation, read as the record reads it
VERSION = importlib.metadata.version("mhdpy")


class TestVersion:
    """Tests that the record gives the version and, from a checkout, the commit and whether its tree is modified.

    A run reads the repository without changing it.
    """

    ## the files changed or added after the commit, and whether each marks the tree as modified
    CHANGES = {
        "tracked": (
            "src/mhdpy/core/__init__.py",
            True,
        ),
        "new-module": (
            "src/mhdpy/core/new.py",
            True,
        ),
        "note": (
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
        """Return a repository of git whose one commit holds the copy of the package and the .gitignore of mhdpy."""

        ## the files that mhdpy ignores, such as the __pycache__/ that a run writes into the package
        shutil.copy(ROOT / ".gitignore", copy / ".gitignore")
        self.git(copy, "init")
        self.git(copy, "add", ".")
        self.git(copy, "commit", "-m", "Copy the package")
        return copy


    def test_checkout(self, checkout: Path) -> None:
        """Checks PACK17.

        A run from a clean checkout records its version, the full hash of the commit of HEAD, and an unmodified tree.
        """

        commit = self.git(checkout, "rev-parse", "HEAD")
        assert self.provenance(checkout) == CodeProvenance(VERSION, commit, False)


    @pytest.mark.parametrize(("name", "modified"), CHANGES.values(), ids = CHANGES.keys())
    def test_changes(self, checkout: Path, name: str, modified: bool) -> None:
        """Checks PACK17.

        A tracked file that differs from the commit, or a module in the package that git does not track, marks the tree
        as modified, and a note outside the package does not.
        """

        ## a line appended to the file, which it creates where the file does not yet exist
        with open(checkout / name, "a") as file:
            file.write("## a change\n")
        assert self.provenance(checkout).modified is modified


    def test_no_repository(self, copy: Path) -> None:
        """Checks PACK15.

        A run from a copy outside any repository of git records its version alone.
        """

        assert self.provenance(copy) == CodeProvenance(VERSION, None, None)


    def test_untracked_package(self, copy: Path) -> None:
        """Checks PACK15.

        A run from a copy that a repository around it leaves untracked, as a wheel in .venv/, records its version alone.
        """

        ## a repository around the copy, whose one commit holds another file
        (copy / "note.txt").write_text("a note\n")
        self.git(copy, "init")
        self.git(copy, "add", "note.txt")
        self.git(copy, "commit", "-m", "Add a note")
        assert self.provenance(copy) == CodeProvenance(VERSION, None, None)


    def test_no_git(self, checkout: Path) -> None:
        """Checks PACK15.

        A run from a checkout on a machine without git records its version alone.
        """

        ## a path of programs that holds no git
        (checkout / "bin").mkdir()
        assert self.provenance(checkout, PATH = str(checkout / "bin")) == CodeProvenance(VERSION, None, None)


    def test_index(self, checkout: Path) -> None:
        """Checks PACK16.

        A run from a checkout whose tracked file was touched since its commit leaves the index of git as it was.
        """

        ## a tracked file touched without a change, which a plain git status would record in the index
        os.utime(checkout / "src/mhdpy/__init__.py", (0, 0))
        index = (checkout / ".git" / "index").read_bytes()
        self.provenance(checkout)
        assert (checkout / ".git" / "index").read_bytes() == index
