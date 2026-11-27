"""The record of the code that a run uses.

Every run can name the code that produced it, by the version of mhdpy and, where it runs from a checkout, by the commit
of the checkout and whether its tracked files differ from that commit. The version alone does not suffice there, as an
editable installation keeps the version of its last build, however many commits follow it, which is why the record
reads git while mhdpy runs.

The record belongs to the infrastructure, stratum 1, and relies on the top package for the version, on the standard
library, and on git where git is installed. Outside a checkout, as after an installation from a wheel or on a machine
without git, it gives the version alone.

Contents
========================================================================================================================
CodeProvenance
    The code that a run uses, by its version and, from a checkout, its commit and the state of its tree.
code_provenance
    Return the record of the code that this run uses.

Its requirements are in design/requirements/infrastructure/package.md, and docs/package.md explains it.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import mhdpy


@dataclass(frozen = True)
class CodeProvenance:
    """The code that a run uses, by its version and, from a checkout, its commit and the state of its tree.

    Parameters
    ====================================================================================================================
    version : str
        The version of the package.
    commit : str | None
        The commit of the checkout, or None if not in a checkout.
    modified : bool | None
        Whether the tracked files differ from the commit, or None if not in a checkout.

    Implements PACK14 and PACK15.
    """

    version: str
    commit: str | None
    modified: bool | None


def code_provenance() -> CodeProvenance:
    """Return the record of the code that this run uses.

    Returns
    ====================================================================================================================
    CodeProvenance
        The version, with the commit of HEAD and whether a tracked file differs from it, both None outside a checkout.

    Implements PACK14, PACK15 and PACK16.
    """

    top = Path(mhdpy.__file__)
    try:
        ## the file of the top package, which git tracks in a checkout and not in an installation from a wheel
        _git(top.parent, "ls-files", "--error-unmatch", top.name)
    except (OSError, subprocess.CalledProcessError):
        ## no repository, a repository that does not track the file, or no git
        return CodeProvenance(version = mhdpy.__version__, commit = None, modified = None)

    commit = _git(top.parent, "rev-parse", "HEAD")

    ## the tracked files that differ from the commit, untracked files left out, without a refresh of the index (PACK16)
    modified = _git(top.parent, "--no-optional-locks", "status", "--porcelain", "--untracked-files=no") != ""
    return CodeProvenance(version = mhdpy.__version__, commit = commit, modified = modified)


def _git(folder: Path, *arguments: str) -> str:
    """Run git in folder and return what it prints.

    Parameters
    ====================================================================================================================
    folder : Path
        The folder in which git runs.
    *arguments : str
        The arguments of git, as "rev-parse" and "HEAD".

    Returns
    ====================================================================================================================
    str
        What git prints, without the whitespace at its ends.

    Raises
    ====================================================================================================================
    OSError
        If git cannot be run, as where it is not installed.
    subprocess.CalledProcessError
        If git exits with a status other than zero, as where the folder lies in no repository.
    """

    result = subprocess.run(["git", *arguments], cwd = folder, capture_output = True, text = True, check = True)
    return result.stdout.strip()
