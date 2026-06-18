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
        # Option B: when a sort is active, this holds the GLOBALLY sorted list of
        # schedule ids (lightweight integers). Pages are then served by fetching
        # the schedules for the ids in the current page slice. Empty when no sort
        # is active, in which case paging falls back to position-based windows.
        self._sorted_ids: List[int] = []
        # Number of top-ranked schedules to show while a sort is active.
        self._top_k: int = self.DEFAULT_TOP_K

    # Default number of top-ranked schedules shown in the sort view. The sort
    # is global over all schedules, but only the best K are fetched for display,
    # since no user reviews more than that. Tunable by the team.
    DEFAULT_TOP_K = 100

    def set_sort_priority(self, priority: list, top_k: int = DEFAULT_TOP_K) -> None:
        """
        Sets the global sort order (Option B) and shows the top_k best schedules.

        The sort is global over every generated schedule (via the narrow score
        table), but only the best top_k are fetched and held for display — the
        default 10,000 page window is for the unsorted view, not this one.
        Empty priority clears the sort and returns to position-based paging of
        the full result set.
        """
        self._sort_priority = list(priority)
        self._top_k = top_k
        if self._sort_priority:
            # Pass 1: global sort, held as a lightweight id list in memory.
            self._sorted_ids = self._repository.get_sorted_ids(self._sort_priority)
        else:
            self._sorted_ids = []
        self._current_page_idx = 0
        self._current_index = 0
        self._load_current_page()

    def _load_current_page(self) -> None:
        """
        Loads the current view into memory. When a sort is active, fetches just
        the top_k best schedules by their sorted ids (Pass 2, lazy: only the
        batches holding them are decompressed). Otherwise loads a position-based
        window of the full result set (unchanged default behaviour).
        """
        if self._sorted_ids:
            # Sort view: only the best top_k, never the full page window.
            top_ids = self._sorted_ids[:self._top_k]
            self._schedules = self._repository.get_schedules_by_ids(top_ids)
        else:
            offset = self._current_page_idx * self._window_size
            self._schedules = self._repository.get_window(offset, self._window_size)

    # ── Streaming write notification ────────────────────────────────────────

    def add_schedules_batch(self, batch_size: int) -> None:
        """
        Updates the current view after a new batch was saved to SQLite. 
        The worker already saved the schedules to SQLite. 
        This refreshes the view so the GUI can show new results while the search
        is still running.
        """
        if self._sort_priority:
            # Sort view: new schedules may change which are the top_k best, so
            # refresh the global order and reload the top_k. (Cheap: sorting the
            # narrow score table is ~hundreds of ms even at hundreds of
            # thousands of rows, and only happens once per incoming batch.)
            self._sorted_ids = self._repository.get_sorted_ids(self._sort_priority)
            self._load_current_page()
        elif len(self._schedules) < self._window_size:
            # Unsorted view: only reload while the current page isn't full yet.
            self._load_current_page()

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
        self._current_page_idx = page
        self._current_index = 0
        # Load this page — globally sorted (by id list) or position-based.
        self._load_current_page()

    # ── Reset for a new run ────────────────────────────────────────────────

    def set_schedules(self, schedules: list) -> None:
        """
        Resets the state before a new scheduling run. 
        This clears the in-memory state and removes old generated schedules 
        from SQLite, so old results will not mix with the new run."""
        super().set_schedules(schedules)
        self._current_page_idx = 0
        self._sorted_ids = []
        self._repository.clear()