"""Observer used only during cube generation.

It is handed to the Scheduler with a small target_depth, so every
on_schedule_found call carries a *partial* schedule (a cube). It snapshots that
cube's dates into a WorkUnit. It is intentionally minimal: no cancellation, no
progress, no error/finish handling.
"""
from __future__ import annotations

from typing import List

from src.logic.observers.IScheduleObserver import IScheduleObserver
from src.logic.parallel.WorkUnit import WorkUnit


class CubeCollectorObserver(IScheduleObserver):
    """Collects partial schedules from cube generation into WorkUnits."""

    def __init__(self) -> None:
        self._units: List[WorkUnit] = []

    def on_schedule_found(self, schedule) -> None:
        # The schedule keeps mutating during backtracking, so copy the dates
        # into a fresh list now instead of holding a reference to it. The
        # partitioner runs with fixed leading-index order, so assignment i
        # belongs to slot i and the dates are already aligned by position.
        self._units.append(WorkUnit(seed_dates=[a.date for a in schedule.assignments]))

    def on_progress(self, value: int) -> None:
        pass

    def should_cancel(self) -> bool:
        return False

    def on_finished(self) -> None:
        pass

    def on_error(self, message: str) -> None:
        pass

    @property
    def units(self) -> List[WorkUnit]:
        """The cubes collected so far, one per partial schedule found."""
        return self._units
