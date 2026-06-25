from __future__ import annotations

from typing import List

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, slots_by_domain


class MaxExamsPerDayChecker(IConflictChecker):
    """
    Checks the max exams per day rule.

    This rule limits the total number of exams that can be on the same date,
    across all programs, to at most k exams.
    """

    def __init__(self, k: int):
        self._k = k
        self._max_exams_per_day = k

    def check(self, assignment, schedule) -> bool:
        """
        This function use in the search solution time.

        Returns True if adding this assignment makes the date have more than k exams.
        """

        # If k is 0 or negative, this rule is disabled.
        if self._max_exams_per_day <= 0:
            return False

        # Count how many exams already exist on this date.
        # Add 1 for the new assignment that we want to place.
        courses_on_date = schedule.date_course_ids_index().get(assignment.date)
        return (len(courses_on_date) if courses_on_date else 0) + 1 > self._max_exams_per_day

    def feasibility_bound(self, context) -> List[str]:
        """
        Fast pre-check before the full search.

        The goal is to check if all exams can fit inside their possible dates
        without passing the max exams per day limit.

        It returns a list of error messages.
        If the list is empty, this check did not find a problem.
        """

        # Save k in local variable for shorter use.
        k = self._max_exams_per_day

        # Save the messeges if we get impossible assignment.
        errors = []

        # Get all possible dates from all slots.
        dates = all_dates(context.slots)

        # Global capacity check.
        # If all exams together are more than k times the amount of possible dates,
        # there is no way to place them without passing the limit.
        if dates and len(context.slots) > k * len(dates):
            errors.append(
                f"Max exams per day is {k}, but {len(context.slots)} exams must fit into "
                f"only {len(dates)} possible dates."
            )
            return errors

        # Check slots that share the exact same date options.
        # These slots are more restricted because they can only use the same domain.
        for domain, same_domain_slots in slots_by_domain(context.slots).items():
            # If this restricted group has more exams than the capacity of its domain,
            # there is no valid spread for this group.
            if len(same_domain_slots) > k * len(domain):
                errors.append(
                    f"Max exams per day is {k}, but {len(same_domain_slots)} exams "
                    f"share the same {len(domain)} possible dates."
                )

        return errors
