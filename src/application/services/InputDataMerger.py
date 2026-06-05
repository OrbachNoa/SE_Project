from typing import Callable, Dict, List
from src.application.state.InputDataState import InputDataState
from src.application.ImportBoundary import ImportMode


class InputDataMerger:
    """Applies parsed data onto InputDataState according to ImportMode."""

    def __init__(self, state: InputDataState) -> None:
        self._state = state
        self._handlers: Dict[ImportMode, Callable[[list], None]] = {
            ImportMode.REPLACE: self._merge_replace,
            ImportMode.UPDATE:  self._merge_update,
        }

    def merge(self, data: list, mode: ImportMode) -> None:
        handler = self._handlers.get(mode)
        if handler is None:
            raise ValueError(f"unsupported import mode: {mode}")
        handler(data)

    def _merge_replace(self, data: list) -> None:
        if self._is_periods(data):
            self._state.replace_periods(data)
        else:
            self._state.replace_courses(data)

    def _merge_update(self, data: list) -> None:
        if self._is_periods(data):
            merged = _merge_periods(self._state.get_periods(), data)
            self._state.replace_periods(merged)
        else:
            merged = _merge_courses(self._state.get_courses(), data)
            self._state.replace_courses(merged)

    @staticmethod
    def _is_periods(data: list) -> bool:
        return bool(data) and hasattr(data[0], "moed")


def _merge_courses(existing: List, incoming: List) -> List:
    by_id = {c.courseId: c for c in existing}
    for c in incoming:
        by_id[c.courseId] = c
    return list(by_id.values())


def _merge_periods(existing: List, incoming: List) -> List:
    by_key = {(p.semester, p.moed): p for p in existing}
    for p in incoming:
        by_key[(p.semester, p.moed)] = p
    return list(by_key.values())
