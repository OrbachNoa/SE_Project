"""Small helper for navigating loaded exam periods."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel


class PeriodNavigator:
    """Tracks the selected period and produces the date list for it."""

    def __init__(self, periods: List[PeriodEditViewModel] | None = None) -> None:
        self._periods: List[PeriodEditViewModel] = []
        self._current_index = 0
        self.reset(periods or [])

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def total(self) -> int:
        return len(self._periods)

    @property
    def current_period(self) -> PeriodEditViewModel | None:
        if not self._periods:
            return None
        return self._periods[self._current_index]

    def reset(self, periods: List[PeriodEditViewModel]) -> None:
        self._periods = list(periods)
        self._current_index = 0

    def can_move_previous(self) -> bool:
        return self._current_index > 0

    def can_move_next(self) -> bool:
        return self._current_index < len(self._periods) - 1

    def move_previous(self) -> bool:
        if not self.can_move_previous():
            return False
        self._current_index -= 1
        return True

    def move_next(self) -> bool:
        if not self.can_move_next():
            return False
        self._current_index += 1
        return True

    def label(self) -> str:
        period = self.current_period
        if period is None:
            return ""
        return (
            f"Semester {period.semester} - Moed {period.moed} "
            f"({self._current_index + 1}/{len(self._periods)})"
        )

    def date_list(self) -> list[str]:
        period = self.current_period
        if period is None:
            return []
        return self.dates_between(period.start_date, period.end_date)

    @staticmethod
    def dates_between(start_date: str, end_date: str) -> list[str]:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if end < start:
            return []

        return [
            (start + timedelta(days=offset)).strftime("%Y-%m-%d")
            for offset in range((end - start).days + 1)
        ]
