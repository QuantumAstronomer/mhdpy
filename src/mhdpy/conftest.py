"""Test configuration of mhdpy: the two test tiers of decision D02.5.

The fast tier runs by default, on every change in CI and for users who verify their installation with
``pytest --pyargs mhdpy``. Tests that belong to the full tier (high-resolution and three-dimensional convergence series,
the complete set of benchmark problems) are marked with ``@pytest.mark.full`` and are skipped unless the environment
variable ``MHDPY_TEST_TIER`` is set to ``full``, for example ``MHDPY_TEST_TIER=full pytest --pyargs mhdpy``. They are
skipped rather than deselected, so that the test summary always shows how many full-tier tests exist.

The tier is chosen with an environment variable rather than a command-line option, because pytest parses the command
line before it finds this file when an installed package is tested with ``--pyargs``; an option defined here would then
be rejected. This file lives inside the package, so that an installed copy of mhdpy behaves the same as the source tree.
"""

import os

import pytest

TIERS = ("fast", "full")


def selected_tier() -> str:
    """Return the test tier requested through ``MHDPY_TEST_TIER``, which defaults to the fast tier.

    An unknown value is an error rather than silently falling back to the fast tier, so that a typing error can never
    make a full-tier run quietly skip the tests it was meant to run.
    """
    tier = os.environ.get("MHDPY_TEST_TIER", "fast")
    if tier not in TIERS:
        raise pytest.UsageError(f"MHDPY_TEST_TIER must be one of {', '.join(TIERS)}, got: {tier!r}.")
    return tier


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``full`` marker, so that pytest recognises it and documents it in ``pytest --markers``."""
    config.addinivalue_line("markers", "full: test of the full tier, skipped unless MHDPY_TEST_TIER=full")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip every test marked ``full``, unless the full tier was requested."""
    if selected_tier() == "full":
        return
    skip_full = pytest.mark.skip(reason="full test tier; set MHDPY_TEST_TIER=full to include it")
    for item in items:
        if "full" in item.keywords:
            item.add_marker(skip_full)
