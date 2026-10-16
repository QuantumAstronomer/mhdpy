"""Tests of the kernel modes: kernels run compiled or uncompiled as selected, and both ways are available (D04.3)."""

import pytest

from mhdpy.foundation.kernels import backend, mode


def test_kernels_run_as_selected() -> None:
    """Check that the kernels run compiled or uncompiled, as MHDPY_KERNELS requests."""
    assert backend.compiled() == (mode.selected() == "compiled")


def test_uncompiled_copy() -> None:
    """Check that an uncompiled copy of a kernel module can be loaded next to the selected one."""
    assert not mode.load_uncompiled("mhdpy.foundation.kernels.backend").compiled()


def test_unknown_mode_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that an unknown value of MHDPY_KERNELS is an error, not a silent fallback."""
    monkeypatch.setenv("MHDPY_KERNELS", "uncomplied")
    with pytest.raises(ValueError, match="MHDPY_KERNELS"):
        mode.selected()


def test_module_without_source() -> None:
    """Check that loading a module without a source file is refused."""
    with pytest.raises(ImportError, match="no source file"):
        mode.load_uncompiled("mhdpy.missing")
