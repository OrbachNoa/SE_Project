"""Detect CPU topology (performance vs efficiency cores) for worker placement.

Modern Intel "hybrid" CPUs (12th gen and later, e.g. the i7-13620H) mix fast
*performance* cores (P-cores, with hyper-threading) and slow *efficiency* cores
(E-cores, no hyper-threading). When CPU-bound scheduler workers are spread across
the E-cores they become end-of-run stragglers that everyone waits on, and on a
mobile chip running every core flat-out triggers thermal throttling. Both make a
"use all physical cores" pool slower than a smaller pool placed on the P-cores.

This module finds the P-core logical-CPU ids, grouped by physical core, so the
pool can size itself to the P-cores and pin each worker onto one of them.

Detection order (each step falls back to the next, never raises):
  1. Windows CPU Sets (``GetSystemCpuSetInformation``) -> exact ``EfficiencyClass``
     per logical CPU. This is the only reliable source on Windows; ``psutil``'s
     per-cpu frequency is uniform there and cannot distinguish the tiers.
  2. Hyper-threading arithmetic: on a hybrid chip only P-cores have an HT sibling,
     so ``logical - physical`` is the P-core count and the leading logical ids
     (HT-paired) are the P-cores.
  3. Give up on a split and report every logical CPU as one tier (the old
     "use everything" behaviour) so callers keep working on non-hybrid CPUs.
"""
from __future__ import annotations

import os
import sys
from typing import List

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a project dependency
    psutil = None


def _logical_count() -> int:
    count = (psutil.cpu_count(logical=True) if psutil else None) or os.cpu_count() or 1
    return int(count)


def _physical_count() -> int:
    count = (psutil.cpu_count(logical=False) if psutil else None) or _logical_count()
    return int(count)


def _windows_pcore_groups() -> "List[List[int]] | None":
    """P-core logical ids grouped by physical core, via the Windows CPU Set API.

    Returns None when not on Windows, when the call fails, or when the CPU is not
    hybrid (only one efficiency class present), so the caller can fall back.
    """
    if sys.platform != "win32":
        return None

    import ctypes
    from ctypes import wintypes

    class _CpuSetInfo(ctypes.Structure):
        # Mirrors SYSTEM_CPU_SET_INFORMATION's CpuSet variant. Records are
        # variable-length in general, so we still walk the buffer by .Size.
        _fields_ = [
            ("Size", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("Id", wintypes.DWORD),
            ("Group", wintypes.WORD),
            ("LogicalProcessorIndex", ctypes.c_ubyte),
            ("CoreIndex", ctypes.c_ubyte),
            ("LastLevelCacheIndex", ctypes.c_ubyte),
            ("NumaNodeIndex", ctypes.c_ubyte),
            ("EfficiencyClass", ctypes.c_ubyte),
            ("AllFlags", ctypes.c_ubyte),
            ("SchedulingClassOrReserved", wintypes.DWORD),
            ("AllocationTag", ctypes.c_ulonglong),
        ]

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_info = kernel32.GetSystemCpuSetInformation
        get_info.argtypes = [
            ctypes.c_void_p,
            wintypes.ULONG,
            ctypes.POINTER(wintypes.ULONG),
            wintypes.HANDLE,
            wintypes.ULONG,
        ]
        get_info.restype = wintypes.BOOL
        current_process = kernel32.GetCurrentProcess
        current_process.restype = wintypes.HANDLE

        # First call sizes the buffer; second call fills it.
        needed = wintypes.ULONG(0)
        get_info(None, 0, ctypes.byref(needed), current_process(), 0)
        size = needed.value
        if size == 0:
            return None
        buffer = (ctypes.c_ubyte * size)()
        if not get_info(buffer, size, ctypes.byref(needed), current_process(), 0):
            return None

        # (efficiency_class, core_index, logical_id) for every CPU set record.
        records = []
        base = ctypes.addressof(buffer)
        offset = 0
        while offset < size:
            rec = _CpuSetInfo.from_address(base + offset)
            if rec.Size == 0:
                break
            if rec.Type == 0:  # CpuSetInformation
                records.append(
                    (rec.EfficiencyClass, rec.CoreIndex, rec.LogicalProcessorIndex)
                )
            offset += rec.Size
    except OSError:
        return None

    if not records:
        return None

    efficiency_classes = {eff for eff, _, _ in records}
    # Only one tier -> not a hybrid CPU; let the caller fall back.
    if len(efficiency_classes) < 2:
        return None

    top = max(efficiency_classes)
    groups: dict[int, List[int]] = {}
    for eff, core, logical in records:
        if eff == top:
            groups.setdefault(core, []).append(logical)
    ordered = [sorted(ids) for _, ids in sorted(groups.items())]
    return ordered or None


def _arithmetic_pcore_groups() -> "List[List[int]] | None":
    """Fallback P-core grouping from HT arithmetic (no OS topology query).

    On a hybrid chip only the performance cores carry a hyper-threaded sibling,
    so ``p_cores = logical - physical`` and the leading ``2 * p_cores`` logical
    ids are the HT-paired P-cores. Returns None when the numbers do not describe
    a recognisable hybrid layout.
    """
    logical = _logical_count()
    physical = _physical_count()
    p_cores = logical - physical
    # Need a real split: at least one P-core and at least one E-core.
    if p_cores <= 0 or p_cores >= physical:
        return None
    return [[2 * i, 2 * i + 1] for i in range(p_cores)]


def performance_core_groups() -> List[List[int]]:
    """Logical-CPU ids of the performance cores, grouped by physical core.

    Each inner list holds the logical ids (HT siblings) of one P-core, so a
    caller can pin one worker per physical P-core. Returns an empty list when no
    hybrid split is detected, meaning "no special placement -- use everything".
    """
    groups = _windows_pcore_groups()
    if groups is None:
        groups = _arithmetic_pcore_groups()
    return groups or []


def recommended_worker_count(reserved_for_main: int = 0) -> int:
    """Worker count that fits the fast cores: one per physical P-core.

    ``reserved_for_main`` leaves that many P-cores free for the main/GUI/writer
    threads -- it only makes sense once we actually know which cores are P-cores,
    so it is subtracted **only on the hybrid path**. On non-hybrid CPUs (no P/E
    split detected) this returns the full physical core count, unreduced -- the
    previous "use every physical core" behaviour, with nothing regressed there.
    """
    groups = performance_core_groups()
    if groups:
        return max(1, len(groups) - max(0, reserved_for_main))
    return max(1, _physical_count())
