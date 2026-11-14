"""The record of the code that a run uses."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import mhdpy


@dataclass(frozen = True)
class CodeProvenance:
    """The code that a run uses, by its version and, from a checkout, its commit and the state of its tree.

    Implements PACK14 and PACK15.
    """

    ## the version of the package
    version: str
    ## the commit of the checkout, or None if not in a checkout
    commit: str | None
    ## whether the tracked files differ from the commit, or None if not in a checkout
    modified: bool | None


def code_provenance() -> CodeProvenance:
    """Return the record of the code that this run uses.

    Implements PACK14 and PACK15.
    """

    top = Path(mhdpy.__file__)
    try:
        ## the file of the top package, which git tracks in a checkout and not in an installation from a wheel
        _git(top.parent, "ls-files", "--error-unmatch", top.name)
    except (OSError, subprocess.CalledProcessError):
        ## no repository, a repository that does not track the file, or no git
        return CodeProvenance(version = mhdpy.__version__, commit = None, modified = None)

    commit = _git(top.parent, "rev-parse", "HEAD")

    ## the tracked files that differ from the commit, untracked files left out
    modified = _git(top.parent, "status", "--porcelain", "--untracked-files=no") != ""
    return CodeProvenance(version = mhdpy.__version__, commit = commit, modified = modified)


def _git(folder: Path, *arguments: str) -> str:
    """Run git in folder and return what it prints."""

    result = subprocess.run(["git", *arguments], cwd = folder, capture_output = True, text = True, check = True)
    return result.stdout.strip()
