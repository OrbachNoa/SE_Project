"""
Splits the huge scheduling search space into smaller valid work units.

The idea is to run the real scheduler only for a few first slots, not until full schedules.
Every valid partial schedule that is found becomes a WorkUnit.
Later, the worker processes take these WorkUnits and continue the search from that point.

This helps us divide the work between processes without giving them invalid or duplicate starting points.
"""
from __future__ import annotations

from typing import List, Optional

from src.logic.Scheduler import Scheduler
from src.logic.SlotBuilder import Slot
from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.observers.CubeCollectorObserver import CubeCollectorObserver
from src.logic.parallel.WorkUnit import WorkUnit
from src.models.ExamSchedule import ExamAssignment

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

    def partition(self, slots: List[Slot], desired_units: int) -> List[WorkUnit]:
        """Break the search space into valid partial schedules."""

        # No exams means there is no search space to split.
        if not slots:
            return []

        # The caller decides how many work units are useful for its execution policy.
        target = max(1, desired_units)
        # We cannot split deeper than the number of slots we actually have.
        max_depth = min(MAX_PARTITION_DEPTH, len(slots))

        # Start with the first real frontier instead of an empty seed that covers everything.
        frontier = self._split_unit(slots, WorkUnit(seed_dates=[]), 1)

        # Keep splitting existing units until we have enough work or cannot split deeper.
        while len(frontier) < target:
            split_index = self._next_largest_frontier_index(frontier, max_depth)
            if split_index is None:
                break

            unit = frontier[split_index]
            child_depth = len(unit.seed_dates) + 1
            children = self._split_unit(slots, unit, child_depth)

            # If this seed cannot produce children, it cannot contribute any complete schedule.
            if not children:
                frontier.pop(split_index)
                continue

            # Replace one seed with all its valid children.
            frontier[split_index:split_index + 1] = children

        return frontier

    def _next_largest_frontier_index(self, frontier: List[WorkUnit], max_depth: int) -> Optional[int]:
        """Return the broadest frontier unit that can still be split."""

        best_index: Optional[int] = None
        best_depth: Optional[int] = None

        for index, unit in enumerate(frontier):
            depth = len(unit.seed_dates)
            if depth >= max_depth:
                continue
            if best_depth is None or depth < best_depth:
                best_index = index
                best_depth = depth

        return best_index

    def _split_unit(self, slots: List[Slot], unit: WorkUnit, target_depth: int) -> List[WorkUnit]:
        """Split one seed prefix into all valid child prefixes at the requested depth."""

        observer = CubeCollectorObserver()
        seed_assignments = self._seed_assignments(slots, unit)

        # Create valid starting points, not full schedules.
        # use_mrv=False keeps the dates in the same order as the slots.
        Scheduler(self._checkers).generateSchedules(
            slots,
            observer,
            max_results=10 ** 9,
            target_depth=target_depth,
            seed_assignments=seed_assignments,
            use_mrv=False,
        )
        return observer.units

    def _seed_assignments(self, slots: List[Slot], unit: WorkUnit) -> List[ExamAssignment]:
        """Rebuild real assignments from the seed dates stored in the work unit."""

        return [
            ExamAssignment(
                course=slots[i].course,
                date=unit.seed_dates[i],
                moed=slots[i].moed,
                semester=slots[i].semester,
            )
            for i in range(len(unit.seed_dates))
        ]
