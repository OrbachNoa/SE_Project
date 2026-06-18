from __future__ import annotations

from src.logic.checkers.IConflictChecker import IConflictChecker


class MaxExamsPerDayChecker(IConflictChecker):
    """Limits the total number of exams on the same day, across all programs, to at most k."""

    def __init__(self, k: int):
        self._k = k

    def check(self, assignment, schedule) -> bool:
        if self._k <= 0:
            return False
        return len(schedule.course_ids_on_date(assignment.date)) + 1 > self._k