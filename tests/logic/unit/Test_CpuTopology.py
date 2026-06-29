"""
Test suite for CpuTopology.

Scope   : Deterministic coverage of the platform-independent parts of CPU
          topology detection — the non-Windows short circuit for
          _windows_pcore_groups(), the psutil-backed logical/physical core
          counters, the HT-arithmetic fallback grouping for both a
          recognizable hybrid layout and a non-hybrid layout, and
          recommended_worker_count()'s reservation behaviour on the hybrid
          path versus the full-physical-count behaviour on the non-hybrid
          path.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CPU-001 .. TC-CPU-010
Fixtures: none

Not covered: the real Windows GetSystemCpuSetInformation ctypes call inside
_windows_pcore_groups() when sys.platform == "win32". That path talks
directly to a live Windows kernel32 API and depends on the actual hardware's
efficiency-class layout, which cannot be meaningfully mocked without
reimplementing the ctypes Structure parsing under test rather than testing
the production code — it is left unverified as genuinely OS-API-dependent,
per the task brief.
"""
import psutil
import pytest

from src.infrastructure.concurrency import CpuTopology


# TC-CPU-001
# On any non-Windows platform, _windows_pcore_groups() must return None
# immediately without attempting any ctypes/ wintypes import or call.
def test_windows_pcore_groups_returns_none_on_non_windows(monkeypatch):
    # Arrange
    monkeypatch.setattr(CpuTopology.sys, "platform", "linux")

    # Act
    result = CpuTopology._windows_pcore_groups()

    # Assert
    assert result is None


# TC-CPU-002
# _logical_count() must return psutil's logical core count, cast to int.
def test_logical_count_uses_psutil_logical_true(monkeypatch):
    # Arrange
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: 16 if logical else 8)

    # Act
    result = CpuTopology._logical_count()

    # Assert
    assert result == 16


# TC-CPU-003
# _physical_count() must return psutil's physical core count, cast to int.
def test_physical_count_uses_psutil_logical_false(monkeypatch):
    # Arrange
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: 16 if logical else 8)

    # Act
    result = CpuTopology._physical_count()

    # Assert
    assert result == 8


# TC-CPU-004
# When psutil.cpu_count returns None for a query (as it sometimes does),
# _logical_count() must fall back to os.cpu_count() rather than crashing on
# `int(None)`.
def test_logical_count_falls_back_to_os_cpu_count_when_psutil_returns_none(monkeypatch):
    # Arrange
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: None)
    monkeypatch.setattr(CpuTopology.os, "cpu_count", lambda: 4)

    # Act
    result = CpuTopology._logical_count()

    # Assert
    assert result == 4


# TC-CPU-005
# A recognizable hybrid layout (logical > physical, with a real split) must
# produce one HT-paired group per inferred P-core, ordered by core index.
def test_arithmetic_pcore_groups_detects_recognizable_hybrid_layout(monkeypatch):
    # Arrange — 6 P-cores (HT, 12 logical ids) + 4 E-cores (no HT) => logical=16, physical=10.
    monkeypatch.setattr(CpuTopology, "_logical_count", lambda: 16)
    monkeypatch.setattr(CpuTopology, "_physical_count", lambda: 10)

    # Act
    result = CpuTopology._arithmetic_pcore_groups()

    # Assert
    assert result == [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]]


# TC-CPU-006
# A non-hybrid layout (logical == 2 * physical uniformly, i.e. p_cores would
# equal physical, no actual split) must make the fallback return None so the
# caller treats the CPU as uniform.
def test_arithmetic_pcore_groups_returns_none_for_non_hybrid_layout(monkeypatch):
    # Arrange — every core is HT-paired uniformly: logical=8, physical=4 => p_cores=4=physical.
    monkeypatch.setattr(CpuTopology, "_logical_count", lambda: 8)
    monkeypatch.setattr(CpuTopology, "_physical_count", lambda: 4)

    # Act
    result = CpuTopology._arithmetic_pcore_groups()

    # Assert
    assert result is None


# TC-CPU-007
# A layout with no HT at all (logical == physical, p_cores == 0) must also
# return None — there is no split to report.
def test_arithmetic_pcore_groups_returns_none_when_no_hyperthreading(monkeypatch):
    # Arrange
    monkeypatch.setattr(CpuTopology, "_logical_count", lambda: 8)
    monkeypatch.setattr(CpuTopology, "_physical_count", lambda: 8)

    # Act
    result = CpuTopology._arithmetic_pcore_groups()

    # Assert
    assert result is None


# TC-CPU-008
# performance_core_groups() must fall back to the arithmetic grouping when
# the Windows-specific detection yields nothing (e.g. non-Windows platform
# or an unrecognized layout there).
def test_performance_core_groups_falls_back_to_arithmetic(monkeypatch):
    # Arrange
    monkeypatch.setattr(CpuTopology, "_windows_pcore_groups", lambda: None)
    monkeypatch.setattr(CpuTopology, "_arithmetic_pcore_groups", lambda: [[0, 1], [2, 3]])

    # Act
    result = CpuTopology.performance_core_groups()

    # Assert
    assert result == [[0, 1], [2, 3]]


# TC-CPU-009
# On the hybrid path, recommended_worker_count() must return one worker per
# detected P-core group, minus the reservation for the main thread (floored
# at 1 so it never recommends zero workers).
def test_recommended_worker_count_subtracts_reservation_on_hybrid_path(monkeypatch):
    # Arrange — 6 P-core groups detected.
    monkeypatch.setattr(
        CpuTopology, "performance_core_groups",
        lambda: [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]],
    )

    # Act
    result_with_reservation = CpuTopology.recommended_worker_count(reserved_for_main=2)
    result_without_reservation = CpuTopology.recommended_worker_count(reserved_for_main=0)

    # Assert
    assert result_with_reservation == 4
    assert result_without_reservation == 6


# TC-CPU-010
# On the non-hybrid path (no P/E split detected), recommended_worker_count()
# must return the full physical core count, completely unreduced by the
# reservation — the reservation only applies once P-cores are known.
def test_recommended_worker_count_returns_full_physical_count_on_non_hybrid_path(monkeypatch):
    # Arrange
    monkeypatch.setattr(CpuTopology, "performance_core_groups", lambda: [])
    monkeypatch.setattr(CpuTopology, "_physical_count", lambda: 8)

    # Act
    result = CpuTopology.recommended_worker_count(reserved_for_main=3)

    # Assert
    assert result == 8
