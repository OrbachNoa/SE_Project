"""ScheduleResultState - runtime state for generated schedule results.

The output half of the application state: holds the schedules produced by a
scheduling run and tracks which one the user is currently viewing.
Knows nothing about the scheduler engine that produces them.
"""
from __future__ import annotations

from typing import List

from src.application.dto_viewmodel.schedule_dto import ScheduleDTO


class ScheduleResultState:
    """Holds the list of generated schedules and the current view index."""

    def __init__(self) -> None:
        self._schedules: List[ScheduleDTO] = []
        self._current_index: int = 0

    def set_schedules(self, schedules: List[ScheduleDTO]) -> None:
        """Replace all schedules and reset the view to the first one."""
        self._schedules = list(schedules)
        self._current_index = 0

    def add_schedule(self, schedule_dto: ScheduleDTO) -> None:
        """Append a single schedule (used as results stream in from the worker)."""
        self._schedules.append(schedule_dto)

    def get_schedule(self, index: int) -> ScheduleDTO:
        """Return the schedule at index, raising IndexError if out of bounds."""
        if index < 0 or index >= len(self._schedules):
            raise IndexError(
                f"schedule index {index} out of range (have {len(self._schedules)})"
            )
        return self._schedules[index]

    def count(self) -> int:
        """Return how many schedules are currently held."""
        return len(self._schedules)

    # --- view-position helpers (current_index is in the UML field list) -----

    @property
    def current_index(self) -> int:
        """The index of the schedule currently shown in the UI."""
        return self._current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        if value < 0 or value >= len(self._schedules):
            raise IndexError(
                f"current_index {value} out of range (have {len(self._schedules)})"
            )
        self._current_index = value