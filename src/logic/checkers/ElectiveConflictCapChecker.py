from __future__ import annotations
from typing import Dict, List, Set

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.models.Enums import Requirement


class ElectiveConflictCapChecker(IConflictChecker):
    """Limits, per program (across all years), the number of elective exams
    on the same date to at most k. A student in that program should not face
    more than k elective exams on one day; if they do, the assignment is
    rejected.
    """

    def __init__(self, k: int):
        self._k = k
        # programId -> set of elective courseIds for O(1) membership test.
        self._program_elective_sets: Dict[str, Set[str]] = {}
        # courseId -> programs where this course is elective.
        self._course_programs: Dict[str, List[str]] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        selected = set(selected_programs) if selected_programs else None
        program_elective_sets: Dict[str, Set[str]] = {}
        course_programs: Dict[str, List[str]] = {}
        for course in courses:
            for entry in course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if entry.requirement is not Requirement.ELECTIVE:
                    continue
                program_elective_sets.setdefault(entry.programId, set()).add(course.courseId)
                owned = course_programs.setdefault(course.courseId, [])
                if entry.programId not in owned:
                    owned.append(entry.programId)
        self._program_elective_sets = program_elective_sets
        self._course_programs = course_programs

    def check(self, assignment, schedule) -> bool:
        programs = self._course_programs.get(assignment.course.courseId)
        if not programs:
            return False

        # Reuse the O(1) date index; only the new date can create a new clash.
        ids_on_date = schedule.course_ids_on_date(assignment.date)

        for program_id in programs:
            electives_in_program = self._program_elective_sets[program_id]
            count = 1  # count the assignment being placed
            for other_id in ids_on_date:
                if other_id in electives_in_program:
                    count += 1
                    if count > self._k:
                        return True
        return False