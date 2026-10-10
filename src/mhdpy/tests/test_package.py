"""Tests of the mhdpy package as a whole.

These tests check that the package is installed consistently: it can be imported, and the version it reports matches
the version in its installed metadata. They ship with the package, so an installation can be verified with
``pytest --pyargs mhdpy``.
"""

from importlib.metadata import version

import mhdpy


def test_version_matches_metadata() -> None:
    """Check that ``mhdpy.__version__`` equals the version recorded in the package metadata.

    The version is defined only in ``pyproject.toml``. A mismatch would mean that the imported package is not the
    installed one, for example a stale copy shadowing it on the import path.
    """
    assert mhdpy.__version__ == version("mhdpy")
