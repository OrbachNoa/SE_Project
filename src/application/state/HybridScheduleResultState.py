"""
SQLite-backed schedule result state.
All schedules live in SQLite; only the current page is held in RAM.
Sorted view loads sorted gidxs (integers) on page entry, then fetches
one schedule per navigation step via the repository's batch cache.
"""
from __future__ import annotations

from typing import List
from src.logic.comparators.ScheduleScorer import ALL_CRITERIA
from src.application.dto.ScheduleDTO import ScheduleDTO
from src.application.state.ScheduleResultState import ScheduleResultState
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository

# Maximum number of schedules loaded into memory at one time.
WINDOW_SIZE = 10_000


class HybridScheduleResultState(ScheduleResultState):
    """Pages through SQLite-stored schedules; sorted pages stream DTOs on demand."""

    def __init__(
        self,
        repository: SQLiteScheduleRepository,
        window_size: int = WINDOW_SIZE,
    ) -> None:
        super().__init__()
        # Repository that stores and loads generated schedules from SQLite.
        self._repository = repository
        # Number of schedules per page.
        self._window_size = window_size
        # Zero-based index of the currently loaded page.
        self._current_page_idx: int = 0
        # Sorted gidxs for the current page; empty in unsorted mode.
        self._sorted_ids_chunk: List[int] = []

    # ── Sort control ────────────────────────────────────────────────────────

    def set_sort_priority(self, priority: list) -> None:
        """Sets the sort order; empty priority clears it and restores positional paging."""
        self._sort_priority = [cid for cid in priority if cid in ALL_CRITERIA]
        self._sorted_ids_chunk = []
        self._current_page_idx = 0
        self._current_index = 0
        self._load_current_page()

    # ── Page loader ─────────────────────────────────────────────────────────

    def _load_current_page(self) -> None:
        """
        Loads data for the current page index.
        Sorted: loads sorted gidxs for this page. 
        Unsorted: loads full DTOs.
        """
        offset = self._current_page_idx * self._window_size
        if self._sort_priority:
            # Pass 1: sorted integer IDs for this page 
            self._sorted_ids_chunk = self._repository.get_sorted_ids_page(
                self._sort_priority, offset, self._window_size
            )
            # Pass 2: actual DTOs will be fetched one at a time by get_schedule().
            self._schedules = []
        else:
            self._sorted_ids_chunk = []
            self._schedules = self._repository.get_window(offset, self._window_size)

    # ── On-demand sorted schedule fetch ─────────────────────────────────────

    def get_schedule(self, index: int) -> ScheduleDTO:
        """
        Return the schedule at the given within-page index.
        Sorted: looks up gidx from chunk and fetches via batch cache. 
        Unsorted: base class.
        """
        if self._sort_priority:
            if index < 0 or index >= len(self._sorted_ids_chunk):
                raise IndexError(
                    f"schedule index {index} out of range "
                    f"(page has {len(self._sorted_ids_chunk)} entries)"
                )
            gidx = self._sorted_ids_chunk[index]
            results = self._repository.get_schedules_by_ids([gidx])
            if results:
                return results[0]
            raise IndexError(
                f"could not resolve sorted schedule at index {index} (gidx={gidx})"
            )
        return super().get_schedule(index)

    # ── Streaming write notification ────────────────────────────────────────

    def add_schedules_batch(self, batch_size: int) -> None:
        """Reloads the page if it isn't full yet; skipped in sorted mode."""
        # In sorted mode skip per-batch re-sorting to avoid GUI hang.
        # In unsorted mode only reload while the current page isn't full yet.
        if not self._sort_priority and len(self._schedules) < self._window_size:
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
        """
        Returns the number of schedules available on the current page.
        
        """
        if self._sort_priority:
            return len(self._sorted_ids_chunk)
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
        """Loads the given page; raises IndexError if out of range."""
        total = self.total_pages()
        if page < 0 or (total > 0 and page >= total):
            raise IndexError(f"page {page} out of range (have {total})")
        self._current_page_idx = page
        self._current_index = 0
        self._load_current_page()

    # ── Reset for a new run ────────────────────────────────────────────────

    def set_schedules(self, schedules: list) -> None:
        """Resets for a new run: clears in-memory state and wipes SQLite."""
        super().set_schedules(schedules)
        self._current_page_idx = 0
        self._sorted_ids_chunk = []
        self._repository.clear()