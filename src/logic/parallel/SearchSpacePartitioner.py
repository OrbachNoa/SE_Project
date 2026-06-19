"""Adaptive-depth cube generation (cube-and-conquer) that replaces the old
static round-robin slot partitioning.

It runs the real backtracking engine at increasing shallow depths until it has
produced enough partial schedules ("cubes") to keep every process busy. Each
cube becomes one WorkUnit. Because generation walks slots in fixed leading-index
order (use_mrv=False), the cubes are the complete, disjoint set of valid
prefixes over slots[0..depth-1]: every full schedule extends exactly one cube,
so the union of the per-cube searches reproduces the whole solution set with no
gaps and no duplicates.

Placement note: this is logic (search-space decomposition over slots+checkers),
not infrastructure - it knows nothing about queues or processes. It only emits
WorkUnits, which the infrastructure layer then distributes.
"""
from __future__ import annotations

from typing import List

from src.logic.Scheduler import Scheduler
from src.logic.SlotBuilder import Slot
from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.observers.CubeCollectorObserver import CubeCollectorObserver
from src.logic.parallel.WorkUnit import WorkUnit

# Aim for several units per process so a process that drains a cheap cube can
# steal another instead of going idle. Tunable; benchmark before changing.
WORK_UNITS_PER_PROCESS = 8

# Never split deeper than this. Cube generation at shallow depths is cheap;
# going deep would itself become an expensive search.
MAX_PARTITION_DEPTH = 4


class SearchSpacePartitioner:
    """Generates work units (cubes) from the slots, using the real checkers for
    pruning so that obviously dead prefixes are never emitted as units. The
    checkers are used here only for cube generation and are then discarded; each
    worker still builds its own checkers locally.
    """

    def __init__(self, checkers: List[IConflictChecker]) -> None:
        self._checkers = checkers

    def partition(self, slots: List[Slot], num_processes: int) -> List[WorkUnit]:
        if not slots:
            return []

        target = max(1, num_processes * WORK_UNITS_PER_PROCESS)
        max_depth = min(MAX_PARTITION_DEPTH, len(slots))

        units: List[WorkUnit] = []
        for depth in range(1, max_depth + 1):
            observer = CubeCollectorObserver()
            # Fixed leading-index order keeps cubes disjoint and aligned to the
            # leading slots; a large cap lets the whole frontier at this depth
            # be enumerated (it is shallow, so this stays cheap).
            Scheduler(self._checkers).generateSchedules(
                slots, observer, max_results=10 ** 9, target_depth=depth, use_mrv=False
            )
            units = observer.units

            # Enough granularity, hit the depth ceiling, or split as deep as
            # there are slots - stop and use what this depth produced. (Zero
            # units means infeasible up to this depth, which is also a valid,
            # if empty, answer.)
            if len(units) >= target or depth == max_depth or depth == len(slots):
                break

        return units
