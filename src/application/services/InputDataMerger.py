from typing import List
from src.application.state.InputDataState import InputDataState
from src.application.ImportBoundary import ImportMode


class InputDataMerger:
    """Applies parsed data onto InputDataState according to ImportMode and file_type."""

    def __init__(self, state: InputDataState) -> None:
        self._state = state

    def merge(self, data: list, mode: ImportMode, file_type: str) -> None:
        """Merge parsed data into state.

        file_type must be 'courses' or 'periods'. It is passed explicitly so
        the merger never has to inspect the data itself to decide which state
        field to update — eliminating the fragile hasattr guard.
        """
        if mode == ImportMode.REPLACE:
            if file_type == "periods":
                self._state.replace_periods(data)
            else:
                self._state.replace_courses(data)
        elif mode == ImportMode.UPDATE:
            if file_type == "periods":
                merged = _merge_periods(self._state.get_periods(), data)
                self._state.replace_periods(merged)
            else:
                merged = _merge_courses(self._state.get_courses(), data)
                self._state.replace_courses(merged)
        else:
            raise ValueError(f"unsupported import mode: {mode}")


def _merge_courses(existing: List, incoming: List) -> List:
    by_id = {c.courseId: c for c in existing}
    for c in incoming:
        by_id[c.courseId] = c
    return list(by_id.values())


def _merge_periods(existing: List, incoming: List) -> List:
    from src.models.ExamPeriod import ExamPeriod
    by_key = {(p.semester, p.moed): p for p in existing}
    for p in incoming:
        key = (p.semester, p.moed)
        if key in by_key:
            existing_p = by_key[key]
            # Merge excluded dates from both periods, keeping only those within the new range
            merged_exclusions = {
                d for d in existing_p.excludedDates.union(p.excludedDates)
                if p.startDate <= d <= p.endDate
            }
            by_key[key] = ExamPeriod(
                semester=p.semester,
                moed=p.moed,
                start_date=p.startDate,
                end_date=p.endDate,
                excluded_dates=merged_exclusions,
            )
        else:
            by_key[key] = p
    return list(by_key.values())