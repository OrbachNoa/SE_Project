from typing import Callable, Dict, List, Tuple
from src.application.state.InputDataState import InputDataState
from src.application.ImportBoundary import ImportMode


class InputDataMerger:
    """Applies parsed data onto InputDataState according to ImportMode and file_type."""

    def __init__(self, state: InputDataState) -> None:
        self._state = state
        self._handlers: Dict[ImportMode, Callable[[list, str], None]] = {
            ImportMode.REPLACE: self._merge_replace,
            ImportMode.UPDATE:  self._merge_update,
        }

    def merge(self, data: list, mode: ImportMode, file_type: str) -> None:
        """Merge parsed data into state.

        file_type must be 'courses' or 'periods'. It is passed explicitly so
        the merger never has to inspect the data itself to decide which state
        field to update — eliminating the fragile hasattr guard.
        """
        handler = self._handlers.get(mode)
        if handler is None:
            raise ValueError(f"unsupported import mode: {mode}")
        handler(data, file_type)

    def _merge_replace(self, data: list, file_type: str) -> None:
        if file_type == "periods":
            self._state.replace_periods(data)
        else:
            self._state.replace_courses(data)

    def _merge_update(self, data: list, file_type: str) -> None:
        if file_type == "periods":
            merged = _merge_periods(self._state.get_periods(), data)
            self._state.replace_periods(merged)
        else:
            merged = _merge_courses(self._state.get_courses(), data)
            self._state.replace_courses(merged)


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