from __future__ import annotations

from typing import List

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, slots_by_domain


class MaxExamsPerDayChecker(IConflictChecker):
    """Limits the total number of exams on the same day, across all programs, to at most k."""

    def __init__(self, k: int):
        self._k = k

    def check(self, assignment, schedule) -> bool:
        if self._k <= 0:
            return False
        return len(schedule.course_ids_on_date(assignment.date)) + 1 > self._k

    def feasibility_bound(self, context) -> List[str]:
        """Preflight: can all exams fit into their candidate dates without
        exceeding k exams per day?
        """
        k = self._k
        errors = []
        dates = all_dates(context.slots)
        if dates and len(context.slots) > k * len(dates):
            errors.append(
                f"Max exams per day is {k}, but {len(context.slots)} exams must fit into "
                f"only {len(dates)} possible dates."
            )
            return errors

        for domain, same_domain_slots in slots_by_domain(context.slots).items():
            if len(same_domain_slots) > k * len(domain):
                errors.append(
                    f"Max exams per day is {k}, but {len(same_domain_slots)} exams "
                    f"share the same {len(domain)} possible dates."
                )
        return errors