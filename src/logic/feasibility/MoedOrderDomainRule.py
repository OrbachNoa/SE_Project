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
    """
    Checks if every course can keep the moed order.

    For each course, moed ALEPH must be before moed BET,
    and moed BET must be before moed GIMEL.

    This rule checks only the possible date domains before the search starts.
    It does not choose final dates, it only checks if there is at least one
    possible increasing date sequence.
    """

    # Rank for each moed, used to sort the slots in the correct moed order.
    _MOED_RANK = {
        Moed.ALEPH: 1,
        Moed.BET: 2,
        Moed.GIMEL: 3,
    }

    def validate(self, context: FeasibilityContext) -> List[str]:
        """
        Fast pre-check before the full search.

        The goal is to catch courses where there is no possible way to place
        their moedim in the correct order.
        """

        # Save the messeges if we get impossible assignment.
        errors = []

        # Dict that groups all slots by course id.
        by_course: Dict[str, List[Slot]] = defaultdict(list)

        # Go over all slots and group them by course.
        for slot in context.slots:
            by_course[slot.course.courseId].append(slot)

        for course_id, course_slots in by_course.items():
            # Take course name for readable error messages.
            course_name = course_slots[0].course.name

            # If one of the slots has no dates, another rule will report it.
            # Here we skip it because moed order cannot be checked without dates.
            if any(not slot.candidateDates for slot in course_slots):
                continue

            # Group this course slots by moed.
            by_moed: Dict[object, List[Slot]] = defaultdict(list)

            for slot in course_slots:
                by_moed[slot.moed].append(slot)

            # Find if the course has more than one slot for the same moed.
            duplicate_moed = next(
                (moed for moed, same_moed_slots in by_moed.items() if len(same_moed_slots) > 1),
                None,
            )

            # If there are duplicate slots for the same moed,
            # we cannot build one clear moed order sequence.
            if duplicate_moed is not None:
                errors.append(
                    f"Course {course_id} ({course_name}) has more than one "
                    f"{enum_name(duplicate_moed)} exam slot, which cannot satisfy moed order."
                )
                continue

            # The last date we chose in the moed order.
            previous: Optional[date] = None

            # Go over the slots by moed order: ALEPH, then BET, then GIMEL.
            for slot in sorted(course_slots, key=lambda s: self._MOED_RANK.get(s.moed, 0)):
                # Find the first possible date that comes after the previous moed date.
                next_date = first_after(slot.candidateDates, previous)

                # If there is no date after previous, moed order is impossible.
                if next_date is None:
                    errors.append(
                        f"Course {course_id} ({course_name}) has no possible date "
                        "sequence that keeps the moed order."
                    )
                    break

                # Save this date as previous for the next moed.
                previous = next_date

        return errors