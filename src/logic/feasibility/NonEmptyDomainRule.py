from __future__ import annotations

from typing import List

from src.logic.feasibility.FeasibilityContext import FeasibilityContext
from src.logic.feasibility.FeasibilityRule import FeasibilityRule
from src.logic.feasibility.helpers import enum_name


class NonEmptyDomainRule(FeasibilityRule):
    def validate(self, context: FeasibilityContext) -> List[str]:
        errors = []
        for slot in context.slots:
            if not slot.candidateDates:
                errors.append(
                    f"Course {slot.course.courseId} ({slot.course.name}) has no available "
                    f"dates for {enum_name(slot.semester)} {enum_name(slot.moed)}."
                )
        return errors
