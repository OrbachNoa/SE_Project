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

    Both the unsorted and sorted views use lazy DTO materialization: on page
    load only raw packed integer tuples are held in _raw_map; a full ScheduleDTO
    is created on demand in get_schedule() only for the one result being shown.
    This means a sorted page of 10,000 results takes no longer to load than an
    unsorted one -- the expensive zlib+struct work happens once per navigation.
    """

    def __init__(
        self,
        repository: SQLiteScheduleRepository,
        window_size: int = WINDOW_SIZE,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._window_size = window_size
        self._current_page_idx: int = 0
        self._sorted_ids: List[int] = []
        self._raw_map: Dict[int, Any] = {}
        self._score_map: Dict[int, dict] = {}
        self._slots_ref: list = []
        self._dto_cache: Dict[int, ScheduleDTO] = {}

    def set_sort_priority(self, priority: list) -> None:
        """Sets the global sort order and reloads the first page.

        Empty priority clears the sort and returns to position-based paging.
        """
        self._sort_priority = list(priority)
        if self._sort_priority:
            self._sorted_ids = self._repository.get_sorted_ids(self._sort_priority)
        else:
            self._sorted_ids = []
        self._current_page_idx = 0
        self._current_index = 0
        self._load_current_page()

    def _load_current_page(self) -> None:
        """Loads the current view into _raw_map using lazy materialization."""
        self._dto_cache.clear()
        self._schedules = []

        if self._sorted_ids:
            start = self._current_page_idx * self._window_size
            page_ids = self._sorted_ids[start:start + self._window_size]
            raw_map, score_map, slots_ref = self._repository.get_raw_by_ids(page_ids)
        else:
            offset = self._current_page_idx * self._window_size
            raw_map, score_map, slots_ref = self._repository.get_window_raw(
                offset, self._window_size
            )

        self._raw_map = raw_map
        self._score_map = score_map
        self._slots_ref = slots_ref or []

    def get_schedule(self, index: int) -> ScheduleDTO:
        """Return the ScheduleDTO at local page index (lazy -- one DTO at a time)."""
        if not self._raw_map:
            return super().get_schedule(index)

        if self._sorted_ids:
            start = self._current_page_idx * self._window_size
            page_ids = self._sorted_ids[start:start + self._window_size]
            if index < 0 or index >= len(page_ids):
                raise IndexError(
                    f"schedule index {index} out of range "
                    f"(sorted page has {len(page_ids)} items)"
                )
            global_idx = page_ids[index]
        else:
            if index < 0 or index >= len(self._raw_map):
                raise IndexError(
                    f"schedule index {index} out of range "
                    f"(window has {len(self._raw_map)} items)"
                )
            global_idx = self._current_page_idx * self._window_size + index

        if index in self._dto_cache:
            return self._dto_cache[index]

        raw = self._raw_map.get(global_idx)
        if raw is None:
            raise IndexError(f"global index {global_idx} not in raw_map")

        if isinstance(raw, ScheduleDTO):
            dto = raw
        else:
            score = self._score_map.get(global_idx)
            dto = row_to_dto(raw, self._slots_ref, score)

        _CACHE_MAX = 32
        if len(self._dto_cache) >= _CACHE_MAX:
            self._dto_cache.pop(next(iter(self._dto_cache)))
        self._dto_cache[index] = dto
        return dto

    def add_schedules_batch(self, batch_size: int) -> None:
        """Updates the current view after a new batch was saved to SQLite."""
        if self._sort_priority:
            self._sorted_ids = self._repository.get_sorted_ids(self._sort_priority)
            if self.current_window_size() < self._window_size:
                self._load_current_page()
        elif self.current_window_size() < self._window_size:
            self._load_current_page()

    def count(self) -> int:
        """Returns the total number of schedules stored in SQLite."""
        return self._repository.count()

    def sqlite_count(self) -> int:
        return self.count()

    def is_first_window_ready(self) -> bool:
        return self.count() > 0

    def current_window_size(self) -> int:
        if self._raw_map:
            return len(self._raw_map)
        return len(self._schedules)

    @property
    def current_page(self) -> int:
        return self._current_page_idx

    def total_pages(self) -> int:
        total = len(self._sorted_ids) if self._sorted_ids else self.count()
        if total == 0:
            return 0
        return (total + self._window_size - 1) // self._window_size

    def load_page(self, page: int) -> None:
        total = self.total_pages()
        if page < 0 or (total > 0 and page >= total):
            raise IndexError(f"page {page} out of range (have {total})")
        self._current_page_idx = page
        self._current_index = 0
        self._load_current_page()

    def set_schedules(self, schedules: list) -> None:
        """Resets the state before a new scheduling run."""
        super().set_schedules(schedules)
        self._current_page_idx = 0
        self._sorted_ids = []
        self._sort_priority = []
        self._raw_map = {}
        self._score_map = {}
        self._slots_ref = []
        self._dto_cache = {}
        self._repository.clear()
