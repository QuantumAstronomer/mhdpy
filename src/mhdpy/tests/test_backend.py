"""Tests of mhdpy's compute backend."""

import pytest

from mhdpy import _backend, _kernel_mode


def test_kernels_run_as_selected() -> None:
    """Check that the kernels run compiled or uncompiled, as MHDPY_KERNELS requests."""
    assert _backend.compiled() == (_kernel_mode.selected() == "compiled")


def test_uncompiled_copy() -> None:
    """Check that an uncompiled copy of a kernel module can be loaded next to the selected one."""
    assert not _kernel_mode.load_uncompiled("mhdpy._backend").compiled()


def test_unknown_mode_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that an unknown value of MHDPY_KERNELS is an error, not a silent fallback."""
    monkeypatch.setenv("MHDPY_KERNELS", "uncomplied")
    with pytest.raises(ValueError, match="MHDPY_KERNELS"):
        _kernel_mode.selected()


def test_module_without_source() -> None:
    """Check that loading a module without a source file is refused."""
    with pytest.raises(ImportError, match="no source file"):
        _kernel_mode.load_uncompiled("mhdpy.missing")
