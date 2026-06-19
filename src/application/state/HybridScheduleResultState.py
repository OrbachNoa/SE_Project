"""Keeps only the currently visible schedule window in memory. 
All generated schedules are stored in SQLite by the background worker. 
This state object loads only one page/window of schedules at a time, so the UI 
can browse many results without keeping all of them in RAM.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.application.dto.PackedScheduleCodec import row_to_dto
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

        # Lazy materialization state (unsorted page view).
        # Instead of creating 10,000 ScheduleDTOs on page load we store the raw
        # packed integer tuples and call row_to_dto() only for the one schedule
        # the GUI asks for.  None when a sort is active (sorted view is small
        # enough to materialise fully).
        self._raw_map: Dict[int, Any] = {}    # global_index -> raw tuple | ScheduleDTO
        self._score_map: Dict[int, dict] = {} # global_index -> {criterion_id: float}
        self._slots_ref: list = []            # slot list needed by row_to_dto()
        self._dto_cache: Dict[int, ScheduleDTO] = {}  # local_index -> ScheduleDTO

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
        Loads the current view into memory.

        Sort view: fetches the top_k best schedules by their sorted ids and
        materialises them fully (small count, unchanged behaviour).

        Unsorted view (lazy): stores raw packed integer tuples and defers
        ScheduleDTO creation to get_schedule().  Only the one schedule being
        displayed is ever materialised, cutting page-load time from ~2 s to
        ~50 ms (zlib decompression only, no Python object construction).
        """
        self._dto_cache.clear()
        if self._sorted_ids:
            # Sort view: only the best top_k, never the full page window.
            top_ids = self._sorted_ids[:self._top_k]
            self._schedules = self._repository.get_schedules_by_ids(top_ids)
            self._raw_map = {}
        else:
            offset = self._current_page_idx * self._window_size
            raw_map, score_map, slots_ref = self._repository.get_window_raw(
                offset, self._window_size
            )
            self._raw_map = raw_map
            self._score_map = score_map
            self._slots_ref = slots_ref or []
            # Keep _schedules empty; current_window_size() and get_schedule()
            # use _raw_map in this mode.
            self._schedules = []

    # ── Lazy DTO access (unsorted page view) ───────────────────────────────

    def get_schedule(self, index: int) -> ScheduleDTO:
        """Return the schedule at local index.

        In sort view (self._sorted_ids set) delegates to the base class which
        reads from self._schedules (already fully materialised).

        In unsorted page view (lazy mode) materialises exactly one ScheduleDTO
        from the raw packed row, caches it for repeated access (e.g. period
        switching shows the same schedule in different periods), and evicts old
        cache entries to stay near constant memory.
        """
        if not self._raw_map:
            # Sort view or legacy: use fully-materialised list from base class.
            return super().get_schedule(index)

        if index < 0 or index >= len(self._raw_map):
            raise IndexError(
                f"schedule index {index} out of range (window has {len(self._raw_map)})"
            )

        if index in self._dto_cache:
            return self._dto_cache[index]

        # Materialise the one DTO we need right now.
        global_idx = self._current_page_idx * self._window_size + index
        raw = self._raw_map.get(global_idx)
        if raw is None:
            raise IndexError(f"global index {global_idx} not in raw_map")

        if isinstance(raw, ScheduleDTO):
            # Legacy pickle batch — already a DTO.
            dto = raw
        else:
            score = self._score_map.get(global_idx)
            dto = row_to_dto(raw, self._slots_ref, score)

        # Cache with a small eviction bound so memory stays flat.
        _CACHE_MAX = 32
        if len(self._dto_cache) >= _CACHE_MAX:
            self._dto_cache.pop(next(iter(self._dto_cache)))
        self._dto_cache[index] = dto
        return dto

    # ── Streaming write notification ────────────────────────────────────────

    def add_schedules_batch(self, batch_size: int) -> None:
        """
        Updates the current view after a new batch was saved to SQLite.
        The worker already saved the schedules to SQLite.
        This refreshes the view so the GUI can show new results while the search
        is still running.
        """
        if self._sort_priority:
            self._sorted_ids = self._repository.get_sorted_ids(self._sort_priority)
            self._load_current_page()
        elif self.current_window_size() < self._window_size:
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
        if self._raw_map:
            return len(self._raw_map)
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
        from SQLite, so old results will not mix with the new run.
        """
        super().set_schedules(schedules)
        self._current_page_idx = 0
        self._sorted_ids = []
        # Clear lazy-materialization state from any previous run.
        self._raw_map = {}
        self._score_map = {}
        self._slots_ref = []
        self._dto_cache = {}
        self._repository.clear()