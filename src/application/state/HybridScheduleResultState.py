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
from src.config import WINDOW_SIZE, SCHEDULE_DTO_CACHE_SIZE


class HybridScheduleResultState(ScheduleResultState):
    def __init__(self, repository: SQLiteScheduleRepository, window_size: int = WINDOW_SIZE) -> None:
        super().__init__()
        self._repository = repository
        self._window_size = window_size
        self._current_page_idx: int = 0
        self._sorted_ids: List[int] = []
        self._raw_map: Dict[int, Any] = {}
        self._score_map: Dict[int, dict] = {}
        self._slots_ref: list = []
        self._dto_cache: Dict[int, ScheduleDTO] = {}
        self._page_ids = None

    def set_sort_priority(self, priority: list) -> None:
        self._sort_priority = list(priority)
        if self._sort_priority:
            self._sorted_ids = [1]  # truthy marker; _load_current_page fetches the page
        else:
            self._sorted_ids = []
        self._current_page_idx = 0
        self._current_index = 0
        self._load_current_page()

    def _load_current_page(self) -> None:
        self._dto_cache.clear()
        self._schedules = []
        if self._sort_priority:
            # Fetch THIS page's globally-sorted ids via LIMIT/OFFSET. SQLite sorts
            # the whole score table (true global order) but returns only this page
            # (~150ms, vs ~1.2s+ to return all ids). Schedules materialise lazily.
            offset = self._current_page_idx * self._window_size
            self._page_ids = self._repository.get_sorted_ids_page(
                self._sort_priority, offset, self._window_size)
            self._sorted_ids = self._page_ids
            self._raw_map = {}
            self._score_map = {}
            if not self._slots_ref:
                _, _, slots_ref = self._repository.get_raw_by_ids([])
                self._slots_ref = slots_ref or []
        else:
            self._page_ids = None
            offset = self._current_page_idx * self._window_size
            raw_map, score_map, slots_ref = self._repository.get_window_raw(offset, self._window_size)
            self._raw_map = raw_map
            self._score_map = score_map
            self._slots_ref = slots_ref or []

    def get_schedule(self, index: int) -> ScheduleDTO:
        # Fall back to the base list only when there is neither a loaded window
        # nor an active sort. In sorted mode raw_map is intentionally empty
        # (schedules are fetched lazily), so we must NOT short-circuit here.
        if not self._raw_map and not self._sorted_ids:
            return super().get_schedule(index)

        if self._sorted_ids:
            page_ids = getattr(self, "_page_ids", None)
            if page_ids is None:
                self._load_current_page()
                page_ids = self._page_ids
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
            # Lazy fetch: pull just this one schedule (one batch-decode). In sorted
            # mode raw_map starts empty so we never fetch the scattered page at once.
            one_raw, one_score, slots_ref = self._repository.get_raw_by_ids([global_idx])
            if slots_ref and not self._slots_ref:
                self._slots_ref = slots_ref
            self._raw_map.update(one_raw)
            self._score_map.update(one_score)
            raw = self._raw_map.get(global_idx)
        if raw is None:
            raise IndexError(f"global index {global_idx} not in raw_map")

        score = self._score_map.get(global_idx)
        if isinstance(raw, ScheduleDTO):
            dto = raw
            if score:
                dto.scores = score
        else:
            dto = row_to_dto(raw, self._slots_ref, score)

        if len(self._dto_cache) >= SCHEDULE_DTO_CACHE_SIZE:
            self._dto_cache.pop(next(iter(self._dto_cache)))
        self._dto_cache[index] = dto
        return dto

    def add_schedules_batch(self, batch_size: int) -> None:
        if self._sort_priority:
            # During generation do NOT re-sort per batch (freezes the GUI). The
            # sorted view is refreshed once when generation finishes.
            return
        elif self.current_window_size() < self._window_size:
            self._load_current_page()

    def refresh_sort(self) -> None:
        """Re-run the global sort once when generation finishes. Kept light: it
        only recomputes the sorted-id list and resets to the first page. No page
        raw is fetched here (schedules are materialised lazily on display)."""
        if self._sort_priority:
            self._sorted_ids = [1]  # truthy marker; _load_current_page fetches the page
            self._current_page_idx = 0
            self._current_index = 0
            self._load_current_page()

    def get_active_sort_priority(self) -> list:
        """Return the currently active sort priority (empty list if none)."""
        return list(self._sort_priority) if self._sort_priority else []

    def compute_sort_data(self, priority: list) -> dict:
        """Heavy part, background-safe: the global ORDER BY only. No page fetch."""
        priority = list(priority)
        if priority:
            sorted_ids = self._repository.get_sorted_ids_page(priority, 0, self._window_size)
        else:
            sorted_ids = []
        return {"priority": priority, "sorted_ids": sorted_ids}

    def apply_sort_data(self, data: dict) -> None:
        """Light, GUI-thread: use the precomputed page-0 ids directly (no
        re-fetch) so Apply is ~instant on the GUI thread."""
        self._sort_priority = data["priority"]
        self._current_page_idx = 0
        self._current_index = 0
        self._dto_cache.clear()
        self._schedules = []
        if data["priority"]:
            self._page_ids = data["sorted_ids"]
            self._sorted_ids = self._page_ids if self._page_ids else [1]
            self._raw_map = {}
            self._score_map = {}
            if not self._slots_ref:
                _, _, slots_ref = self._repository.get_raw_by_ids([])
                self._slots_ref = slots_ref or []
        else:
            self._sorted_ids = []
            self._load_current_page()

    def count(self) -> int:
        return self._repository.count()

    def sqlite_count(self) -> int:
        return self.count()

    def is_first_window_ready(self) -> bool:
        return self.count() > 0

    def current_window_size(self) -> int:
        if self._sorted_ids:
            # full page of sorted ids (10k), even though raw is fetched lazily
            return len(getattr(self, "_page_ids", []) or [])
        if self._raw_map:
            return len(self._raw_map)
        return len(self._schedules)

    @property
    def current_page(self) -> int:
        return self._current_page_idx

    def total_pages(self) -> int:
        total = self.count()
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

    def get_repository(self) -> SQLiteScheduleRepository:
        """Expose the backing repository (used by the clustering feature, which
        reads score vectors and fetches schedules by global id)."""
        return self._repository

    def set_schedules(self, schedules: list) -> None:
        super().set_schedules(schedules)
        self._current_page_idx = 0
        self._sorted_ids = []
        self._sort_priority = []
        self._raw_map = {}
        self._score_map = {}
        self._slots_ref = []
        self._dto_cache = {}
        self._repository.clear()