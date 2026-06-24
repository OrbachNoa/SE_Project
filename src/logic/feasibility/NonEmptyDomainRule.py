from __future__ import annotations

from typing import List

from src.logic.feasibility.FeasibilityContext import FeasibilityContext
from src.logic.feasibility.FeasibilityRule import FeasibilityRule
from src.logic.feasibility.helpers import enum_name


class NonEmptyDomainRule(FeasibilityRule):
    """
    Checks that every exam slot has at least one possible date.

    If a slot has no candidate dates, then the scheduler has no place to put it,
    so the schedule is impossible before the search even starts.
    """

    def validate(self, context: FeasibilityContext) -> List[str]:
        """
        Fast pre-check before the full search.

        The goal is to catch slots that have empty date domain.
        """

        # Save the messeges if we get impossible assignment.
        errors = []

        # Go over all slots that need to be scheduled.
        for slot in context.slots:
            # If this slot has no candidate dates, it cannot be scheduled.
            if not slot.candidateDates:
                errors.append(
                    f"Course {slot.course.courseId} ({slot.course.name}) has no available "
                    f"dates for {enum_name(slot.semester)} {enum_name(slot.moed)}."
                )

        return errors