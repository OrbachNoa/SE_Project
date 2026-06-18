from __future__ import annotations
from typing import Dict, List, Set

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.models.Enums import Requirement


class ElectiveConflictCapChecker(IConflictChecker):
    """Limits elective exam pair-conflicts per program to at most k.

    Years are intentionally ignored for this rule: every elective course in the
    same program participates in the same conflict count. A same-day group of n
    elective exams creates n * (n - 1) / 2 pair-conflicts.
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
                    pair_conflicts = count * (count - 1) // 2
                    if pair_conflicts > self._k:
                        return True
        return False
