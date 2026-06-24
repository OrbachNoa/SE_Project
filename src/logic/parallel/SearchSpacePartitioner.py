"""
Splits the huge scheduling search space into smaller valid work units.

The idea is to run the real scheduler only for a few first slots, not until full schedules.
Every valid partial schedule that is found becomes a WorkUnit.
Later, the worker processes take these WorkUnits and continue the search from that point.

This helps us divide the work between processes without giving them invalid or duplicate starting points.
"""
from __future__ import annotations

from typing import List

from src.logic.Scheduler import Scheduler
from src.logic.SlotBuilder import Slot
from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.observers.CubeCollectorObserver import CubeCollectorObserver
from src.logic.parallel.WorkUnit import WorkUnit

# We create more work units than processes, so workers can grab another unit when they finish early.
WORK_UNITS_PER_PROCESS = 8

# Do not split too deep, because partitioning itself should stay cheap.
MAX_PARTITION_DEPTH = 4


class SearchSpacePartitioner:
    """Creates small starting points for the real schedule search.

    Each WorkUnit is a valid partial schedule.
    Later, a worker process takes that partial schedule and continues the search from there.
    """

    def __init__(self, checkers: List[IConflictChecker]) -> None:
        # These checkers are used only to avoid creating impossible work units.
        self._checkers = checkers

    def partition(self, slots: List[Slot], num_processes: int) -> List[WorkUnit]:
        """Break the search space into valid partial schedules."""

        # No exams means there is no search space to split.
        if not slots:
            return []

        # Aim for several small jobs per process, not just one job per process.
        target = max(1, num_processes * WORK_UNITS_PER_PROCESS)
        # We cannot split deeper than the number of slots we actually have.
        max_depth = min(MAX_PARTITION_DEPTH, len(slots))

        units: List[WorkUnit] = []
        # Start with a small prefix of slots, and increase it only if we need more work units.
        for depth in range(1, max_depth + 1):
            # This observer turns every partial schedule into a WorkUnit.
            observer = CubeCollectorObserver()
            # Create valid starting points, not full schedules.
            # use_mrv=False keeps the dates in the same order as the slots.
            Scheduler(self._checkers).generateSchedules(
                slots, observer, max_results=10 ** 9, target_depth=depth, use_mrv=False
            )

            # Take the work units collected at this depth.
            units = observer.units

            # Stop when we have enough units or when going deeper is not allowed anymore.
            if len(units) >= target or depth == max_depth or depth == len(slots):
                break

        return units
