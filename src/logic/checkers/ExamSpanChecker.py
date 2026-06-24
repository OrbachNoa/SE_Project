from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, enum_name
from src.models.Enums import Requirement


class ExamSpanChecker(IConflictChecker):
    """
    Checks the minimum exam span for obligatory exams.

    This rule says that for every program, year, semester and moed,
    the distance between the first obligatory exam and the last obligatory exam
    must be at least k days.

    Semester is part of the group because each semester has different exam period.
    For example FALL/ALEPH and SPRING/ALEPH are not same exam window,
    so we dont mix them together.

    Do not check the span before the whole group is placed.
    A future exam can still become the first or last exam and make the span bigger.
    """

    def __init__(self, k: int):
        # Minimum days required between the first exam and the last exam.
        self._min_span_days = k

        # Dict that save all obligatory courses for each group.
        # Key: program, year, semester, moed.
        # Value: set of course ids that must be in this group.
        self._exam_span_groups: Dict[Tuple[str, int, object, object], Set[str]] = {}

        # For each course save the cohorts that this course belongs to.
        # Use it in check() to know which groups need to be checked for this course.
        self._course_cohorts: Dict[str, Set[Tuple[str, int, object]]] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        """
        Builds lookup tables before the search starts.

        This keeps check() function fast, because during scheduling we dont need
        to scan all courses and all entries every time.
        """

        # Convert selected programs to set for fast lookup.
        # If there are no selected programs, check all programs.
        selected = set(selected_programs) if selected_programs else None

        group_members: Dict[Tuple[str, int, object, object], Set[str]] = {}
        course_cohorts: Dict[str, Set[Tuple[str, int, object]]] = {}

        # Go over all possible exam slots.
        for slot in (slots or []):
            course = slot.course

            for entry in course.programEntries:
                # Ignore programs that are not part of this run.
                if selected and entry.programId not in selected:
                    continue

                # Take only obligatory courses.
                if entry.requirement is not Requirement.OBLIGATORY:
                    continue

                # The entry must belong to the same semester as the slot.
                if entry.semester != slot.semester:
                    continue

                # Add this course to the relevant group.
                # The group is by program, year, semester and moed.
                group_members.setdefault(
                    (entry.programId, entry.year, slot.semester, slot.moed), set()
                ).add(course.courseId)

                # Save this course if he belongs to this program/year/semester cohort.
                # Moed is not saved here because assignment already has moed in check().
                course_cohorts.setdefault(course.courseId, set()).add(
                    (entry.programId, entry.year, slot.semester)
                )

        self._exam_span_groups = group_members
        self._course_cohorts = course_cohorts

    def check(self, assignment, schedule) -> bool:
        """
        This function use while we build the solution.

        Returns True if this assignment makes the obligatory exam span too short.
        """

        # Get the cohorts that this course belongs to.
        cohorts = self._course_cohorts.get(assignment.course.courseId)

        # If this course is not obligatory in any checked group, there is no problem.
        if not cohorts:
            return False

        moed = assignment.moed
        new_id = assignment.course.courseId

        for program_id, year, semester in cohorts:
            # Check only the cohort from the same semester as the assignment.
            if semester != assignment.semester:
                continue

            # Get all obligatory courses in this group.
            members = self._exam_span_groups.get((program_id, year, semester, moed))

            if not members:
                continue

            # Expected is how many exams should be placed in this group.
            expected = len(members)

            # If there is only one exam, there is no span to check.
            if expected < 2:
                continue

            # The exam we are trying to place is not in the schedule yet,
            # so we add its date manually.
            dates = [assignment.date]

            # Add dates of the other exams from this group that are already placed.
            for member_id in members:
                # Skip the new exam because we already added him.
                if member_id == new_id:
                    continue

                for a in schedule.assignments_for_course(member_id):
                    # Take only assignments from the same moed and semester.
                    if a.moed == moed and a.semester == semester:
                        dates.append(a.date)

            # If not all exams in the group are placed yet,
            # the span can still grow later, so dont fail now.
            if len(dates) < expected:
                continue

            # Calculate the amount of days between first exam and last exam.
            span_days = (max(dates) - min(dates)).days

            # If the span is smaller than k, this assignment creates conflict.
            if span_days < self._min_span_days:
                return True

        # There is no problem.
        return False

    def feasibility_bound(self, context) -> List[str]:
        """
        Fast pre-check before the full search.

        The goal is to catch cases where there is no chance to reach the required
        exam span, even before trying to build a full schedule.

        It returns a list of error messages.
        If the list is empty, this check did not find a problem.
        """

        # Take the programs that the user selected.
        selected = context.selected_set

        # Dict that groups obligatory slots by program, year, semester and moed.
        groups: Dict[Tuple[str, int, object, object], Set] = defaultdict(set)

        # Go over all slots that can be scheduled.
        for slot in context.slots:
            for entry in slot.course.programEntries:
                # Ignore programs that are not selected.
                if selected and entry.programId not in selected:
                    continue

                # Take only obligatory courses.
                if entry.requirement is not Requirement.OBLIGATORY:
                    continue

                # The entry must match the semester of the slot.
                if entry.semester != slot.semester:
                    continue

                # Add this slot to the relevant group.
                groups[(entry.programId, entry.year, slot.semester, slot.moed)].add(slot)

        # Save the messeges if we get impossible assignment.
        errors = []

        for (program_id, year, semester, moed), group_slots in groups.items():
            # If the group has less than 2 exams, there is no span to check.
            if len(group_slots) < 2:
                continue

            # Get all possible dates for this group.
            dates = all_dates(group_slots)

            # If there are no dates, this checker cant calculate span here.
            if not dates:
                continue

            # The biggest possible span is between the earliest and latest possible date.
            max_span = (max(dates) - min(dates)).days

            # If even the biggest possible span is smaller than k,
            # then there is no valid schedule for this group.
            if max_span < self._min_span_days:
                errors.append(
                    f"Exam span requires {self._k} days, but program {program_id} "
                    f"year {year} semester {enum_name(semester)} moed {enum_name(moed)} "
                    f"can span at most {max_span} days."
                )

        return errors