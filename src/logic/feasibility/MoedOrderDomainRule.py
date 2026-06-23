from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from src.logic.SlotBuilder import Slot
from src.logic.feasibility.FeasibilityContext import FeasibilityContext
from src.logic.feasibility.FeasibilityRule import FeasibilityRule
from src.logic.feasibility.helpers import enum_name, first_after
from src.models.Enums import Moed


class MoedOrderDomainRule(FeasibilityRule):
    _MOED_RANK = {
        Moed.ALEPH: 1,
        Moed.BET: 2,
        Moed.GIMEL: 3,
    }

    def validate(self, context: FeasibilityContext) -> List[str]:
        errors = []
        by_course: Dict[str, List[Slot]] = defaultdict(list)
        for slot in context.slots:
            by_course[slot.course.courseId].append(slot)

        for course_id, course_slots in by_course.items():
            course_name = course_slots[0].course.name
            if any(not slot.candidateDates for slot in course_slots):
                continue

            by_moed: Dict[object, List[Slot]] = defaultdict(list)
            for slot in course_slots:
                by_moed[slot.moed].append(slot)

            duplicate_moed = next(
                (moed for moed, same_moed_slots in by_moed.items() if len(same_moed_slots) > 1),
                None,
            )
            if duplicate_moed is not None:
                errors.append(
                    f"Course {course_id} ({course_name}) has more than one "
                    f"{enum_name(duplicate_moed)} exam slot, which cannot satisfy moed order."
                )
                continue

            previous: Optional[date] = None
            for slot in sorted(course_slots, key=lambda s: self._MOED_RANK.get(s.moed, 0)):
                next_date = first_after(slot.candidateDates, previous)
                if next_date is None:
                    errors.append(
                        f"Course {course_id} ({course_name}) has no possible date "
                        "sequence that keeps the moed order."
                    )
                    break
                previous = next_date

        return errors
