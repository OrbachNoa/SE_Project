from __future__ import annotations

from typing import Dict, List, Set, Tuple

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, enum_name
from src.logic.indexes.SelectedProgramIndex import SelectedProgramIndex
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
        self._k = k
        # Minimum days required between the first exam and the last exam.
        self._min_span_days = k

        # Dict that save all obligatory courses for each group.
        # Key: program, year, semester, moed.
        # Value: set of course ids that must be in this group.
        self._exam_span_groups: Dict[Tuple[str, int, object, object], Tuple[str, ...]] = {}

        # For each course save the exact groups that this course belongs to.
        # Use it in check() to know which groups need to be checked for this course.
        self._course_group_keys: Dict[str, Tuple[Tuple[str, int, object, object], ...]] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None, selected_index=None) -> None:
        """
        Builds lookup tables before the search starts.

        This keeps check() function fast, because during scheduling we dont need
        to scan all courses and all entries every time.
        """

        selected_index = selected_index or SelectedProgramIndex(courses, selected_programs, slots)

        group_members: Dict[Tuple[str, int, object, object], Set[str]] = {}
        course_group_keys: Dict[str, Set[Tuple[str, int, object, object]]] = {}

        # Go over all possible exam slots.
        for slot in (slots or []):
            course = slot.course

            for entry in selected_index.entries_for_slot(slot):
                # Take only obligatory courses.
                if entry.requirement is not Requirement.OBLIGATORY:
                    continue

                # Add this course to the relevant group.
                # The group is by program, year, semester and moed.
                group_key = (entry.programId, entry.year, slot.semester, slot.moed)
                group_members.setdefault(group_key, set()).add(course.courseId)

                # Save this course if he belongs to this exact span group.
                course_group_keys.setdefault(course.courseId, set()).add(group_key)

        self._exam_span_groups = {
            group_key: tuple(members)
            for group_key, members in group_members.items()
        }
        self._course_group_keys = {
            course_id: tuple(group_keys)
            for course_id, group_keys in course_group_keys.items()
        }

    def check(self, assignment, schedule) -> bool:
        """
        This function use while we build the solution.

        Returns True if this assignment makes the obligatory exam span too short.
        """

        # Get the span groups that this course belongs to.
        group_keys = self._course_group_keys.get(assignment.course.courseId)

        # If this course is not obligatory in any checked group, there is no problem.
        if not group_keys:
            return False

        moed = assignment.moed
        new_id = assignment.course.courseId
        course_assignments = schedule.course_assignments_index()

        for group_key in group_keys:
            program_id, year, semester, group_moed = group_key
            # Check only the cohort from the same semester as the assignment.
            if semester != assignment.semester or group_moed != moed:
                continue

            # Get all obligatory courses in this group.
            members = self._exam_span_groups.get(group_key)

            if not members:
                continue

            # Expected is how many exams should be placed in this group.
            expected = len(members)

            # If there is only one exam, there is no span to check.
            if expected < 2:
                continue

            # The exam we are trying to place is not in the schedule yet,
            # so we count its date manually.
            placed_count = 1
            first_date = assignment.date
            last_date = assignment.date

            # Add dates of the other exams from this group that are already placed.
            for member_id in members:
                # Skip the new exam because we already added him.
                if member_id == new_id:
                    continue

                for a in course_assignments.get(member_id, ()):
                    # Take only assignments from the same moed and semester.
                    if a.moed == moed and a.semester == semester:
                        placed_count += 1
                        if a.date < first_date:
                            first_date = a.date
                        elif a.date > last_date:
                            last_date = a.date

            # If not all exams in the group are placed yet,
            # the span can still grow later, so dont fail now.
            if placed_count < expected:
                continue

            # Calculate the amount of days between first exam and last exam.
            span_days = (last_date - first_date).days

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

        # Dict that groups obligatory slots by program, year, semester and moed.
        groups: Dict[Tuple[str, int, object, object], Set] = (
            context.selected_index.slots_by_program_year_semester_moed(
                requirement=Requirement.OBLIGATORY
            )
        )

        # Collect feasibility errors so the UI can show all problems at once.
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
