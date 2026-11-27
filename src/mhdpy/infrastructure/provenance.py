"""The record of the code that a run uses.

Every run can name the code that produced it, by the version of mhdpy and, where it runs from a checkout, by the commit
of the checkout and whether its code differs from that commit. The version alone does not suffice there, as an
editable installation keeps the version of its last build, however many commits follow it, which is why the record
reads git while mhdpy runs.

The record belongs to the infrastructure, stratum 1, and relies on the standard library and on git where git is
installed. It reads the version from the metadata as the top package does, rather than import the top package.
Outside a checkout, as after an installation from a wheel or on a machine without git, it gives the version alone.

Contents
========================================================================================================================
CodeProvenance
    The code that a run uses, by its version and, from a checkout, its commit and the state of its tree.
code_provenance
    Return the record of the code that this run uses.

Its requirements are in design/requirements/infrastructure/package.md, and docs/package.md explains it.
"""

import importlib.metadata
import subprocess
from dataclasses import dataclass
from pathlib import Path


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
        Whether the code differs from the commit, untracked files in the package included, or None outside a checkout.

    Implements PACK15 and PACK17.
    """

    version: str
    commit: str | None
    modified: bool | None


def code_provenance() -> CodeProvenance:
    """Return the record of the code that this run uses.

    Returns
    ====================================================================================================================
    CodeProvenance
        The version, with the commit of HEAD and whether the code differs from it, both None outside a checkout.

    Implements PACK15, PACK16 and PACK17.
    """

    ## the version and the file of the top package, found without importing it (PACK03, PACK05)
    version = importlib.metadata.version("mhdpy")
    top = Path(__file__).parents[1] / "__init__.py"
    try:
        ## the file of the top package, which git tracks in a checkout and not in an installation from a wheel
        _git(top.parent, "ls-files", "--error-unmatch", top.name)
    except (OSError, subprocess.CalledProcessError):
        ## no repository, a repository that does not track the file, or no git
        return CodeProvenance(version = version, commit = None, modified = None)

    commit = _git(top.parent, "rev-parse", "HEAD")

    ## the tracked files that differ from the commit, without a refresh of the index (PACK16)
    changed = _git(top.parent, "--no-optional-locks", "status", "--porcelain", "--untracked-files=no") != ""
    ## the files below the package that git neither tracks nor ignores, as a module not yet committed (PACK17)
    added = _git(top.parent, "ls-files", "--others", "--exclude-standard") != ""
    return CodeProvenance(version = version, commit = commit, modified = changed or added)


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
