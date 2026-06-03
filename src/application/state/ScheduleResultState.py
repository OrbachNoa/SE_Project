"""ScheduleResultState - runtime state for generated schedule results.

The output half of the application state: holds the schedules produced by a
scheduling run and tracks which one the user is currently viewing.
Knows nothing about the scheduler engine that produces them.
"""
from __future__ import annotations

from typing import List

from application.dto.SchedulDTO import ScheduleDTO


class ScheduleResultState:
    """Holds the list of generated schedules and tracks the active UI rendering view index cursor."""

    def __init__(self) -> None:
        # Allocates a local collection array buffer for caching operational display elements
        self._schedules: List[ScheduleDTO] = []
        self._current_index: int = 0

    def set_schedules(self, schedules: List[ScheduleDTO]) -> None:
        """Replaces the entire stored reference collection buffer and resets the navigation view to the start."""
        self._schedules = list(schedules)
        self._current_index = 0

    def add_schedule(self, schedule_dto: ScheduleDTO) -> None:
        """Appends a single distinct schedule record object directly to the active collection block."""
        self._schedules.append(schedule_dto)

    def add_schedules_batch(self, batch: int | List[ScheduleDTO]) -> None:
        """
        Accepts incoming structural frames into memory.
        Supports both legacy lists and raw scalar integers to maintain contract polymorphic balance.
        """
        if isinstance(batch, int):
            # No-op in base class as background worker persistence tracks records out-of-process
            pass
        else:
            # Fallback legacy pipeline path support profile
            self._schedules.extend(batch)

    def get_schedule(self, index: int) -> ScheduleDTO:
        """Retrieves the schedule record residing at the specified index position boundary."""
        if index < 0 or index >= len(self._schedules):
            raise IndexError(
                f"schedule index {index} out of range (have {len(self._schedules)})"
            )
        return self._schedules[index]

    def count(self) -> int:
        """Returns the immediate volumetric count dimension sizing of the held collection segment."""
        return len(self._schedules)

    # --- page-navigation contract (overridden by HybridScheduleResultState) ---

    @property
    def current_page(self) -> int:
        """0-based index of the page currently shown. Always returns 0 for non-hybrid memory structures."""
        return 0

    def total_pages(self) -> int:
        """Returns total calculated frame pages available. Constrained to 1 frame max for raw layouts."""
        return 1 if self._schedules else 0

    def load_page(self, page: int) -> None:
        """
        Rotates visible pipeline elements onto an active window frame target page index.
        Acts as a clean stub hook overridden completely inside polymorphic subclasses.
        """
        pass

    def is_first_window_ready(self) -> bool:
        """Validates if elements have entered the active view cache frame to open display pipelines safely."""
        return len(self._schedules) > 0

    def current_window_size(self) -> int:
        """Measures the active memory footprint sizing parameters of the currently visible rendering view."""
        return len(self._schedules)

    def sqlite_count(self) -> int:
        """Tracks records spilled into disk overflow database blocks. Static at 0 for base memory arrays."""
        return 0

    # --- view-position helpers (current_index is in the UML field list) -----

    @property
    def current_index(self) -> int:
        """Exposes the active navigation item element cursor tracking location coordinate."""
        return self._current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        """Mutates the internal item position tracker, enforcing strict collection out-of-bounds safety guards."""
        if value < 0 or value >= len(self._schedules):
            raise IndexError(
                f"current_index {value} out of range (have {len(self._schedules)})"
            )
        self._current_index = value