"""ScheduleResultState - runtime state for generated schedule results.

The output half of the application state: holds the schedules produced by a
scheduling run and tracks which one the user is currently viewing.
Knows nothing about the scheduler engine that produces them.
"""
from __future__ import annotations

from typing import List

from src.application.dto.ScheduleDTO import ScheduleDTO


class ScheduleResultState:
    """Holds the list of generated schedules and tracks the active viewing index."""

    def __init__(self) -> None:
        # Allocates a local collection array buffer for caching operational display elements
        self._schedules: List[ScheduleDTO] = []
        self._current_index: int = 0

    def set_schedules(self, schedules: List[ScheduleDTO]) -> None:
        """Replace all stored schedules and reset navigation to the first item."""
        self._schedules = list(schedules)
        self._current_index = 0

    def add_schedule(self, schedule_dto: ScheduleDTO) -> None:
        """Append a single schedule to the list."""
        self._schedules.append(schedule_dto)

    def add_schedules_batch(self, batch: int | List[ScheduleDTO]) -> None:
        """Add a batch of schedules."""
        if isinstance(batch, int):
            # No-op in base class as background worker persistence tracks records out-of-process
            pass
        else:
            # Fallback legacy pipeline path support profile
            self._schedules.extend(batch)

    def get_schedule(self, index: int) -> ScheduleDTO:
        """Return the schedule at the given index."""
        if index < 0 or index >= len(self._schedules):
            raise IndexError(
                f"schedule index {index} out of range (have {len(self._schedules)})"
            )
        return self._schedules[index]

    def count(self) -> int:
        """Return the number of stored schedules."""
        return len(self._schedules)

    # --- page-navigation contract (overridden by HybridScheduleResultState) ---

    @property
    def current_page(self) -> int:
        """0-based index of the currently shown page. Always 0 for the base class."""
        return 0

    def total_pages(self) -> int:
        """Total number of pages. 1 if any schedules are loaded, 0 otherwise."""
        return 1 if self._schedules else 0

    def load_page(self, page: int) -> None:
        """Stub — overridden by HybridScheduleResultState to page through disk-backed results."""
        pass

    def is_first_window_ready(self) -> bool:
        """Return True if at least one schedule is loaded and ready to display."""
        return len(self._schedules) > 0

    def current_window_size(self) -> int:
        """Return the number of schedules currently in memory."""
        return len(self._schedules)

    def sqlite_count(self) -> int:
        """Number of schedules spilled to SQLite. Always 0 for the base in-memory class."""
        return 0

    # --- view-position helpers (current_index is in the UML field list) -----

    @property
    def current_index(self) -> int:
        """0-based index of the schedule currently shown in the UI."""
        return self._current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        """Set the active schedule index; raises IndexError if out of bounds."""
        if value < 0 or value >= len(self._schedules):
            raise IndexError(
                f"current_index {value} out of range (have {len(self._schedules)})"
            )
        self._current_index = value
