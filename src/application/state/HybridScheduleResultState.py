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

WINDOW_SIZE = 10_000


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

    def set_sort_priority(self, priority: list) -> None:
        self._sort_priority = list(priority)
        if self._sort_priority:
            self._sorted_ids = self._repository.get_sorted_ids(self._sort_priority)
        else:
            self._sorted_ids = []
        self._current_page_idx = 0
        self._current_index = 0
        self._load_current_page()

    def _load_current_page(self) -> None:
        self._dto_cache.clear()
        self._schedules = []
        if self._sorted_ids:
            start = self._current_page_idx * self._window_size
            page_ids = self._sorted_ids[start:start + self._window_size]
            raw_map, score_map, slots_ref = self._repository.get_raw_by_ids(page_ids)
        else:
            offset = self._current_page_idx * self._window_size
            raw_map, score_map, slots_ref = self._repository.get_window_raw(offset, self._window_size)
        self._raw_map = raw_map
        self._score_map = score_map
        self._slots_ref = slots_ref or []

    def get_schedule(self, index: int) -> ScheduleDTO:
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
            # _raw_map is stale (sort applied mid-run; new results arrived).
            # Reload transparently so the caller gets a valid DTO instead of crash.
            self._load_current_page()
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
        if self._sort_priority:
            # During generation do NOT re-sort on every incoming batch. Calling
            # get_sorted_ids() per batch runs a full ORDER BY over the whole
            # score table hundreds of times (cost grows with table size) on the
            # GUI thread, which freezes the UI. The sorted view is refreshed
            # once, when generation finishes, via refresh_sort().
            return
        elif self.current_window_size() < self._window_size:
            self._load_current_page()

    def refresh_sort(self) -> None:
        """Re-run the global sort once. Called when generation finishes so the
        sorted view reflects every schedule produced during the run. Safe to
        call when no sort is active (it simply does nothing)."""
        if self._sort_priority:
            self._sorted_ids = self._repository.get_sorted_ids(self._sort_priority)
            self._current_page_idx = 0
            self._current_index = 0
            self._load_current_page()

    # ── Background-threaded sort (avoids freezing the GUI on Apply) ──────────
    # The heavy work (ORDER BY + first-page fetch) only READS the repository,
    # which is thread-safe (guarded by its own lock) and spends almost all its
    # time inside SQLite's C code — where the GIL is released — so running it in
    # a QThread genuinely lets the GUI stay responsive. The result is a plain
    # dict, handed back to the GUI thread which only assigns it (apply_sort_data).

    def compute_sort_data(self, priority: list) -> dict:
        """Heavy, read-only, background-safe. Computes the sorted id list AND
        the first page's raw rows, so the GUI thread has nothing slow left to do.
        Does NOT mutate any live state."""
        priority = list(priority)
        if priority:
            sorted_ids = self._repository.get_sorted_ids(priority)
            page_ids = sorted_ids[:self._window_size]
            raw_map, score_map, slots_ref = self._repository.get_raw_by_ids(page_ids)
        else:
            sorted_ids = []
            raw_map, score_map, slots_ref = self._repository.get_window_raw(0, self._window_size)
        return {
            "priority": priority,
            "sorted_ids": sorted_ids,
            "raw_map": raw_map,
            "score_map": score_map,
            "slots_ref": slots_ref or [],
        }

    def apply_sort_data(self, data: dict) -> None:
        """Light, GUI-thread only. Assigns the precomputed sort result into the
        live state — no SQLite work, no decompression, just references."""
        self._sort_priority = data["priority"]
        self._sorted_ids = data["sorted_ids"]
        self._current_page_idx = 0
        self._current_index = 0
        self._dto_cache.clear()
        self._schedules = []
        self._raw_map = data["raw_map"]
        self._score_map = data["score_map"]
        self._slots_ref = data["slots_ref"]

    def count(self) -> int:
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
        # Always derive from the true schedule count, never from len(_sorted_ids).
        # The sorted-id list is intentionally NOT refreshed on every batch during
        # generation (that caused the GUI freeze), so it goes stale mid-run.
        # count() reflects the live total and is the same whether sorted or not,
        # so the page counter keeps ticking up to 100 (1M / 10k) as it always did.
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