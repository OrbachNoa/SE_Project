"""Plain state model for calendar exclusion editing."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel


class ExclusionModel:
    """Owns editable exam-period date ranges and excluded dates."""

    def __init__(self, view_models: List[PeriodEditViewModel]) -> None:
        if not view_models:
            raise ValueError("ExclusionModel requires at least one period.")

        self._view_models = view_models
        self._current_index = 0
        self._current_vm: PeriodEditViewModel
        self._start_date = ""
        self._end_date = ""
        self._excluded_dates: set[str] = set()
        self._load_current_period()

    @property
    def current_period(self) -> PeriodEditViewModel:
        return self._current_vm

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def total(self) -> int:
        return len(self._view_models)

    @property
    def start_date(self) -> str:
        return self._start_date

    @property
    def end_date(self) -> str:
        return self._end_date

    @property
    def excluded_dates(self) -> set[str]:
        return set(self._excluded_dates)

    def can_move_previous(self) -> bool:
        return self._current_index > 0

    def can_move_next(self) -> bool:
        return self._current_index < len(self._view_models) - 1

    def set_date_range(self, start_date: str, end_date: str) -> None:
        self._start_date = start_date
        self._end_date = end_date

    def toggle(self, date_str: str) -> bool:
        """Toggle a date and return True when it is now excluded."""
        if date_str in self._excluded_dates:
            self._excluded_dates.remove(date_str)
            return False

        self._excluded_dates.add(date_str)
        return True

    def move_previous(self) -> None:
        if not self.can_move_previous():
            return
        self.save_current_period()
        self._current_index -= 1
        self._load_current_period()

    def move_next(self) -> None:
        if not self.can_move_next():
            return
        self.save_current_period()
        self._current_index += 1
        self._load_current_period()

    def save_current_period(self) -> None:
        self._current_vm.start_date = self._start_date
        self._current_vm.end_date = self._end_date
        self._current_vm.excluded_dates = sorted(self._excluded_dates)

    def apply(self) -> List[PeriodEditViewModel]:
        self.save_current_period()
        return self._view_models

    def date_list(self) -> list[str]:
        return self.dates_between(self._start_date, self._end_date)

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

    def _load_current_period(self) -> None:
        self._current_vm = self._view_models[self._current_index]
        self._start_date = self._current_vm.start_date
        self._end_date = self._current_vm.end_date
        self._excluded_dates = set(self._current_vm.excluded_dates)
