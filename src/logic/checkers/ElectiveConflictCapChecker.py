from __future__ import annotations
from typing import Dict, List, Set, Tuple

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.models.Enums import Requirement


class ElectiveConflictCapChecker(IConflictChecker):
    """Limits, per (program, year), the number of elective exams on the same
    date to at most k. A student in a cohort should not face more than k
    elective exams on one day; if they do, the assignment is rejected.
    """

    def __init__(self, k: int):
        self._k = k
        # (programId, year) -> set of elective courseIds for O(1) membership test.
        self._cohort_elective_sets: Dict[Tuple[str, int], Set[str]] = {}
        # courseId -> cohorts where this course is elective.
        self._course_cohorts: Dict[str, List[Tuple[str, int]]] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        selected = set(selected_programs) if selected_programs else None
        cohort_elective_sets: Dict[Tuple[str, int], Set[str]] = {}
        course_cohorts: Dict[str, List[Tuple[str, int]]] = {}
        for course in courses:
            for entry in course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if entry.requirement is not Requirement.ELECTIVE:
                    continue
                cohort = (entry.programId, entry.year)
                cohort_elective_sets.setdefault(cohort, set()).add(course.courseId)
                owned = course_cohorts.setdefault(course.courseId, [])
                if cohort not in owned:
                    owned.append(cohort)
        self._cohort_elective_sets = cohort_elective_sets
        self._course_cohorts = course_cohorts

    def check(self, assignment, schedule) -> bool:
        cohorts = self._course_cohorts.get(assignment.course.courseId)
        if not cohorts:
            return False

        # Reuse the O(1) date index; only the new date can create a new clash.
        ids_on_date = schedule.course_ids_on_date(assignment.date)

        for cohort in cohorts:
            electives_in_cohort = self._cohort_elective_sets[cohort]
            count = 1  # count the assignment being placed
            for other_id in ids_on_date:
                if other_id in electives_in_cohort:
                    count += 1
                    if count > self._k:
                        return True
        return False