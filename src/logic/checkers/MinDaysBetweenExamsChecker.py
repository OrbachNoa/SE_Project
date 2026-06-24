from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import Dict, List, Set, Tuple

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, max_spaced_count
from src.models.Enums import Requirement


class GapScope(Enum):
    """
    Selects which exams the minimum gap rule applies to.
    """

    # Check only courses that are obligatory in the cohort.
    OBLIGATORY_ONLY = "OBLIGATORY_ONLY"

    # Check every course in the cohort.
    ANY = "ANY"


class MinDaysBetweenExamsChecker(IConflictChecker):
    """
    Checks the minimum days between exams rule.

    This rule rejects schedules where two exams in the same program and year
    are closer than k calendar days.

    If scope is OBLIGATORY_ONLY, it checks only obligatory courses in the cohort.
    If scope is ANY, it checks every course in the cohort.

    The same course's own moedim are included.
    Day counting is regular calendar days, so weekends and holidays also count.
    """

    # Tells the scheduler that this checker uses ordinal date index for faster lookup.
    uses_ordinal_date_index = True

    def __init__(self, scope: GapScope, k: int):
        # Decide if the checker works on obligatory exams only or all exams.
        self._scope = scope

        # Minimum required days between two exams.
        self._k = k

        # For each course save bit mask of cohorts that this course belongs to.
        # This makes check() faster because we can compare cohorts with bit operation.
        self._eligible_masks: Dict[str, int] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        """
        Builds lookup tables before the search starts.

        This keeps check() function fast, because during scheduling we only need
        direct lookup and bit mask comparison instead of scanning all courses.
        """

        # Convert selected programs to set for fast lookup.
        # If there are no selected programs, check all programs.
        selected = set(selected_programs) if selected_programs else None

        # For each course, save all cohorts that this course belongs to.
        eligible: Dict[str, Set[Tuple[str, int]]] = {}

        # Give each cohort an integer id, so later we can build bit masks.
        cohort_ids: Dict[Tuple[str, int], int] = {}

        for course in courses:
            cohorts: Set[Tuple[str, int]] = set()

            for entry in course.programEntries:
                # Ignore programs that are not part of this run.
                if selected and entry.programId not in selected:
                    continue

                # If scope is obligatory only, ignore non obligatory courses.
                if (
                    self._scope is GapScope.OBLIGATORY_ONLY
                    and entry.requirement is not Requirement.OBLIGATORY
                ):
                    continue

                # Add the program/year cohort of this course.
                cohorts.add((entry.programId, entry.year))

            # Save only courses that belong to at least one relevant cohort.
            if cohorts:
                eligible[course.courseId] = cohorts

                # Create id for every cohort that still doesnt have id.
                for cohort in cohorts:
                    if cohort not in cohort_ids:
                        cohort_ids[cohort] = len(cohort_ids)

        # Build bit mask for each course.
        # Every bit says that this course belongs to one cohort.
        self._eligible_masks = {
            course_id: sum(1 << cohort_ids[cohort] for cohort in cohorts)
            for course_id, cohorts in eligible.items()
        }

    def check(self, assignment, schedule) -> bool:
        """
        This function use in the search solution time.

        Returns True if this assignment is too close to another relevant exam.
        """

        # If k is 0 or negative, this rule is disabled.
        if self._k <= 0:
            return False

        # Get the cohort mask of the new course.
        new_mask = self._eligible_masks.get(assignment.course.courseId, 0)

        # If the course is not relevant for this checker, there is no problem.
        if not new_mask:
            return False

        # Convert the assignment date to ordinal number for faster date scan.
        new_ordinal = assignment.date.toordinal()

        eligible_masks = self._eligible_masks

        # A gap smaller than k is violation.
        # So we scan all dates from k-1 days before until k-1 days after.
        # Using ordinals avoids creating date or timedelta objects in this hot loop.
        for ordinal in range(new_ordinal - self._k + 1, new_ordinal + self._k):
            # Get all courses already assigned on this ordinal date.
            other_ids = schedule.course_ids_on_ordinal(ordinal)

            if not other_ids:
                continue

            for other_id in other_ids:
                # If the new course and the other course share at least one cohort,
                # then they are too close and this is conflict.
                if new_mask & eligible_masks.get(other_id, 0):
                    return True

        # There is no problem.
        return False

    def feasibility_bound(self, context) -> List[str]:
        """
        Fast pre-check before the full search.

        The goal is to check if every program/year cohort has enough possible
        dates to place its exams with at least k days gap.

        It returns a list of error messages.
        If the list is empty, this check did not find a problem.
        """

        # If k is None, this checker cant calculate bound.
        if self._k is None:
            return []

        # Take the programs that the user selected.
        selected = context.selected_set

        # Dict that groups slots by program and year.
        groups: Dict[Tuple[str, int], Set] = defaultdict(set)

        # Go over all slots that can be scheduled.
        for slot in context.slots:
            for entry in slot.course.programEntries:
                # Ignore programs that are not selected.
                if selected and entry.programId not in selected:
                    continue

                # If scope is obligatory only, ignore non obligatory courses.
                if (
                    self._scope is GapScope.OBLIGATORY_ONLY
                    and entry.requirement is not Requirement.OBLIGATORY
                ):
                    continue

                # Add this slot to the relevant program/year group.
                groups[(entry.programId, entry.year)].add(slot)

        # Text for the error message according to the scope.
        label = "mandatory exams" if self._scope is GapScope.OBLIGATORY_ONLY else "all exams"

        # Save the messeges if we get impossible assignment.
        errors = []

        for (program_id, year), group_slots in groups.items():
            # Required is how many exams this cohort needs to schedule.
            required = len(group_slots)

            # If there is only one exam, there is no gap to check.
            if required < 2:
                continue

            # Calculate how many dates can fit with k days gap.
            capacity = max_spaced_count(all_dates(group_slots), self._k)

            # If the cohort needs more exams than the spaced capacity,
            # there is no valid schedule for this cohort.
            if required > capacity:
                errors.append(
                    f"Minimum gap for {label} requires {required} exams in "
                    f"program {program_id} year {year}, but only {capacity} "
                    f"dates can fit with a {self._k}-day gap."
                )

        return errors