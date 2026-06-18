from __future__ import annotations
from typing import Dict, Set, Tuple

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.models.Enums import Requirement


class ExamSpanChecker(IConflictChecker):
    """Requires, per (program, year, moed), that the span in days between the
    first and last obligatory exam is at least k. The span can only grow while a
    group is incomplete, so it is validated once every obligatory exam of the
    group is placed. Completion is detected by counting placed exams against the
    expected total, derived from the slots (so only courses that truly have an
    exam in that moed are counted).
    """

    def __init__(self, k: int):
        self._k = k
        self._group_members: Dict[Tuple[str, int, object], Set[str]] = {}
        self._course_cohorts: Dict[str, Set[Tuple[str, int]]] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        selected = set(selected_programs) if selected_programs else None
        group_members: Dict[Tuple[str, int, object], Set[str]] = {}
        course_cohorts: Dict[str, Set[Tuple[str, int]]] = {}
        for slot in (slots or []):
            course = slot.course
            for entry in course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if entry.requirement is not Requirement.OBLIGATORY:
                    continue
                group_members.setdefault((entry.programId, entry.year, slot.moed), set()).add(course.courseId)
                course_cohorts.setdefault(course.courseId, set()).add((entry.programId, entry.year))
        self._group_members = group_members
        self._course_cohorts = course_cohorts

    def check(self, assignment, schedule) -> bool:
        cohorts = self._course_cohorts.get(assignment.course.courseId)
        if not cohorts:
            return False

        moed = assignment.moed
        new_id = assignment.course.courseId
        for program_id, year in cohorts:
            members = self._group_members.get((program_id, year, moed))
            if not members:
                continue
            expected = len(members)
            if expected < 2:
                continue

            # The exam being placed is not in the schedule yet, so seed with it.
            dates = [assignment.date]
            for member_id in members:
                if member_id == new_id:
                    continue
                for a in schedule.assignments_for_course(member_id):
                    if a.moed == moed:
                        dates.append(a.date)

            # The group is not complete yet, so the span can still grow.
            if len(dates) < expected:
                continue

            span_days = (max(dates) - min(dates)).days
            if span_days < self._k:
                return True
        return False
