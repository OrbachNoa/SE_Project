from __future__ import annotations
from typing import List

from logic.observers.IScheduleObserver import IScheduleObserver
from models.ExamSchedule import ExamAssignment


class _ScheduleSnapshot:
    """A lightweight snapshot containing only the list of exam assignments."""
    __slots__ = ('assignments',)

    def __init__(self, assignments: List[ExamAssignment]) -> None:
        self.assignments = assignments


class CollectingScheduleObserver(IScheduleObserver):
    """Collects generated schedules into a list for synchronous retrieval."""

    def __init__(self) -> None:
        self._schedules: List[_ScheduleSnapshot] = []
        self._error: str | None = None

    def on_schedule_found(self, schedule) -> None:
        """Saves a lightweight snapshot of the schedule's assignments."""
        self._schedules.append(_ScheduleSnapshot(list(schedule.assignments)))

    def on_progress(self, value: int) -> None:
        """No-op for the CLI execution path."""
        pass

    def should_cancel(self) -> bool:
        """Returns False as the CLI path always runs to completion."""
        return False

    def on_finished(self) -> None:
        """No-op for the CLI execution path."""
        pass

    def on_error(self, message: str) -> None:
        """Stores any fatal error message encountered during the search."""
        self._error = message

    @property
    def schedules(self) -> List[_ScheduleSnapshot]:
        """Returns the collected schedule snapshots."""
        return self._schedules

    @property
    def error(self) -> str | None:
        """Returns the recorded error message, or None if no error occurred."""
        return self._error