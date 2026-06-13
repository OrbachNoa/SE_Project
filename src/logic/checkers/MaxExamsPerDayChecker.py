from __future__ import annotations
from typing import Dict, Set

from src.logic.checkers.IConflictChecker import IConflictChecker


class MaxExamsPerDayChecker(IConflictChecker):
    """Limits the number of exams on the same day within a single program to at
    most k. Counted per program, across all years. A course holds at most one
    exam per day, so counting distinct courses equals counting exams.
    """

    def __init__(self, k: int):
        self._k = k
        self._course_programs: Dict[str, Set[str]] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        selected = set(selected_programs) if selected_programs else None
        course_programs: Dict[str, Set[str]] = {}
        for course in courses:
            programs = {
                entry.programId for entry in course.programEntries
                if not selected or entry.programId in selected
            }
            if programs:
                course_programs[course.courseId] = programs
        self._course_programs = course_programs

    def check(self, assignment, schedule) -> bool:
        if self._k <= 0:
            return False
        new_programs = self._course_programs.get(assignment.course.courseId)
        if not new_programs:
            return False

        ids_on_date = schedule.course_ids_on_date(assignment.date)
        for program in new_programs:
            count = 1  # the exam being placed
            for other_id in ids_on_date:
                other_programs = self._course_programs.get(other_id)
                if other_programs and program in other_programs:
                    count += 1
                    if count > self._k:
                        return True
        return False