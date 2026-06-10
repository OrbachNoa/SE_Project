"""Keeps only the currently visible schedule window in memory. 
All generated schedules are stored in SQLite by the background worker. 
This state object loads only one page/window of schedules at a time, so the UI 
can browse many results without keeping all of them in RAM.
"""
from __future__ import annotations

from typing import List

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.application.state.ScheduleResultState import ScheduleResultState
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository

# Maximum number of schedules loaded into memory at one time.
WINDOW_SIZE = 10_000


class HybridScheduleResultState(ScheduleResultState):
    """
    Manages schedule results using SQLite as the main storage. 
    SQLite contains all generated schedules. 
    This class keeps only the current window/page in memory for the GUI.
    """

    def __init__(
        self,
        repository: SQLiteScheduleRepository,
        window_size: int = WINDOW_SIZE,
    ) -> None:
        super().__init__()
        # Repository that stores and loads generated schedules from SQLite.
        self._repository = repository
        # Number of schedules to load into memory for one page/window.
        self._window_size = window_size
        # Zero-based index of the currently loaded page.
        self._current_page_idx: int = 0

    # ── Streaming write notification ────────────────────────────────────────

    def add_schedules_batch(self, batch_size: int) -> None:
        """
        Updates the current window after a new batch was saved to SQLite. 
        The worker already saved the schedules to SQLite. 
        This method only reloads the current window if it is not full yet, so the GUI 
        can show new results while the search is still running.
        """
        if len(self._schedules) < self._window_size:
            # Load again from the current page offset, because new schedules may now exist in SQLite.
            offset = self._current_page_idx * self._window_size
            self._schedules = self._repository.get_window(offset, self._window_size)

    # ── Totals ─────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Returns the total number of schedules stored in SQLite."""
        return self._repository.count()

    def sqlite_count(self) -> int:
        """Returns the number of schedules stored in SQLite."""
        return self.count()

    def is_first_window_ready(self) -> bool:
        """Returns True once at least one schedule was saved and can be displayed."""
        return self.count() > 0

    def current_window_size(self) -> int:
        """Returns how many schedules are currently loaded in memory."""
        return len(self._schedules)

    # ── Paged navigation ───────────────────────────────────────────────────

    @property
    def current_page(self) -> int:
        """Returns the zero-based index of the currently loaded page."""
        return self._current_page_idx

    def total_pages(self) -> int:
        """Returns how many pages are needed to browse all saved schedules."""
        total = self.count()
        if total == 0:
            return 0
        return (total + self._window_size - 1) // self._window_size

    def load_page(self, page: int) -> None:
        """
        Loads one page of schedules from SQLite into memory. 
        The page number is converted to a SQLite offset. 
        For example, page 2 with window size 10,000 starts at offset 20,000.
        """
        total = self.total_pages()
        if page < 0 or (total > 0 and page >= total):
            raise IndexError(f"page {page} out of range (have {total})")

        # Convert the page number into the first schedule index for this page.
        sqlite_offset = page * self._window_size
        # Load only this page/window from SQLite, not all schedules.
        self._schedules = self._repository.get_window(
            sqlite_offset, self._window_size
        )

        # Update the current page and reset the index inside the loaded page.
        self._current_page_idx = page
        self._current_index = 0  

    # ── Reset for a new run ────────────────────────────────────────────────

    def set_schedules(self, schedules: list) -> None:
        """
        Resets the state before a new scheduling run. 
        This clears the in-memory state and removes old generated schedules 
        from SQLite, so old results will not mix with the new run."""
        super().set_schedules(schedules)
        self._current_page_idx = 0
        self._repository.clear()
