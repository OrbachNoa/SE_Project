"""
Collects partial schedules and turns them into WorkUnits.
"""
from __future__ import annotations

from typing import List

from src.logic.observers.IScheduleObserver import IScheduleObserver
from src.logic.parallel.WorkUnit import WorkUnit


class CubeCollectorObserver(IScheduleObserver):
    """Observer used only while splitting the search into work units."""

    def __init__(self) -> None:
        # Stores all work units created from the partial schedules.
        self._units: List[WorkUnit] = []

    def on_schedule_found(self, schedule) -> None:
        # Save only the dates, because the worker can rebuild the assignments from its own slots.
        self._units.append(WorkUnit(seed_dates=tuple(a.date for a in schedule.assignments)))

    def on_progress(self, value: int) -> None:
        # Progress is not needed while we only collect work units.
        pass

    def should_cancel(self) -> bool:
        # This collector does not control cancellation.
        return False

    def on_finished(self) -> None:
        # Nothing to do when cube collection is finished.
        pass

    def on_error(self, message: str) -> None:
        # Errors are handled by the caller that runs the partitioning step.
        pass

    @property
    def units(self) -> List[WorkUnit]:
        """Return the work units collected so far."""
        return self._units
