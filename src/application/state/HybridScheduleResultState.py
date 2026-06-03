"""HybridScheduleResultState — windowed, overflow-to-SQLite schedule storage.

Invariants at all times:
  _schedules      — the *currently visible* window, loaded on demand from SQLite.
  _current_page   — 0-based page index currently in _schedules.
  SQLite contains 100% of the generated schedules directly from the worker thread.
"""
from __future__ import annotations

from typing import List

from application.dto.schedule_dto import ScheduleDTO
from application.state.schedule_result_state import ScheduleResultState
from infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository

# Globally defined rendering frame block limit size
WINDOW_SIZE = 10_000


class HybridScheduleResultState(ScheduleResultState):
    """
    Extends ScheduleResultState with SQLite overflow and paged navigation tracking.
    Operates purely as an SQLite reader cache proxy since the background worker thread 
    handles downstream write transactions directly.
    """

    def __init__(
        self,
        repository: SQLiteScheduleRepository,
        window_size: int = WINDOW_SIZE,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._window_size = window_size
        # Tracks the zero-based index cursor of the currently active display frame
        self._current_page_idx: int = 0

    # ── Streaming write notification ────────────────────────────────────────

    def add_schedules_batch(self, batch_size: int) -> None:
        """
        Triggered asynchronously whenever the background worker completes a disk write transaction.
        Reloads the current active window slot dynamically if it hasn't filled to window capacity,
        allowing the UI layout to refresh discovered configurations live.
        """
        if len(self._schedules) < self._window_size:
            # Re-fetch the current active block window range to synchronize matching offsets
            offset = self._current_page_idx * self._window_size
            self._schedules = self._repository.get_window(offset, self._window_size)

    # ── Totals ─────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Returns the global total volume of schedules captured across the database repository at O(1)."""
        return self._repository.count()

    def sqlite_count(self) -> int:
        """All computed schedule profiles live in SQLite storage, making this value equivalent to count()."""
        return self.count()

    def is_first_window_ready(self) -> bool:
        """Checks if the system has persisted at least one entry, validating if display routes can safely open."""
        return self.count() > 0

    def current_window_size(self) -> int:
        """Returns the allocation size footprint of the currently buffered frame segment."""
        return len(self._schedules)

    # ── Paged navigation ───────────────────────────────────────────────────

    @property
    def current_page(self) -> int:
        """Exposes the active navigation page context tracking register."""
        return self._current_page_idx

    def total_pages(self) -> int:
        """Computes the total page ceiling bounds dynamically as the background engine adds records."""
        total = self.count()
        if total == 0:
            return 0
        return (total + self._window_size - 1) // self._window_size

    def load_page(self, page: int) -> None:
        """
        Swaps the internal active memory cache block frame over to the requested target page index.
        Queries the localized SQLite repository using indexed window offset markers.
        """
        total = self.total_pages()
        if page < 0 or (total > 0 and page >= total):
            raise IndexError(f"page {page} out of range (have {total})")

        # Map page numbers directly to database row seek configurations
        sqlite_offset = page * self._window_size
        self._schedules = self._repository.get_window(
            sqlite_offset, self._window_size
        )

        # Synchronize tracking registers and reset within-page iterator cursors
        self._current_page_idx = page
        self._current_index = 0  

    # ── Reset for a new run ────────────────────────────────────────────────

    def set_schedules(self, schedules: list) -> None:
        """Clears localized tracking memory properties and flushes active repository records for subsequent runs."""
        super().set_schedules(schedules)
        self._current_page_idx = 0
        self._repository.clear()