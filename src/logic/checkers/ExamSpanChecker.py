from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, enum_name
from src.models.Enums import Requirement


class ExamSpanChecker(IConflictChecker):
    """Requires, per (program, year, semester, moed), that the span in days
    between the first and last obligatory exam is at least k. Semester is part
    of the group key because exam periods are defined per (semester, moed): a
    FALL/ALEPH period and a SPRING/ALEPH period are unrelated date windows, and
    mixing their obligatory exams into one span group would be meaningless. The
    span can only grow while a group is incomplete, so it is validated once
    every obligatory exam of the group is placed. Completion is detected by
    counting placed exams against the expected total, derived from the slots
    (so only courses that truly have an exam in that semester/moed are
    counted).
    """

    def __init__(self, k: int):
        self._k = k
        self._group_members: Dict[Tuple[str, int, object, object], Set[str]] = {}
        self._course_cohorts: Dict[str, Set[Tuple[str, int, object]]] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        selected = set(selected_programs) if selected_programs else None
        group_members: Dict[Tuple[str, int, object, object], Set[str]] = {}
        course_cohorts: Dict[str, Set[Tuple[str, int, object]]] = {}
        for slot in (slots or []):
            course = slot.course
            for entry in course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if entry.requirement is not Requirement.OBLIGATORY:
                    continue
                if entry.semester != slot.semester:
                    continue
                group_members.setdefault(
                    (entry.programId, entry.year, slot.semester, slot.moed), set()
                ).add(course.courseId)
                course_cohorts.setdefault(course.courseId, set()).add(
                    (entry.programId, entry.year, slot.semester)
                )
        self._group_members = group_members
        self._course_cohorts = course_cohorts

    def check(self, assignment, schedule) -> bool:
        cohorts = self._course_cohorts.get(assignment.course.courseId)
        if not cohorts:
            return False

        moed = assignment.moed
        new_id = assignment.course.courseId
        for program_id, year, semester in cohorts:
            if semester != assignment.semester:
                continue
            members = self._group_members.get((program_id, year, semester, moed))
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
                    if a.moed == moed and a.semester == semester:
                        dates.append(a.date)

            # The group is not complete yet, so the span can still grow.
            if len(dates) < expected:
                continue

            span_days = (max(dates) - min(dates)).days
            if span_days < self._k:
                return True
        return False

    def feasibility_bound(self, context) -> List[str]:
        """Preflight: can the span between first/last obligatory exam reach k
        days at all, given each course's candidate dates?
        """
        selected = context.selected_set
        groups: Dict[Tuple[str, int, object, object], Set] = defaultdict(set)
        for slot in context.slots:
            for entry in slot.course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if entry.requirement is not Requirement.OBLIGATORY:
                    continue
                if entry.semester != slot.semester:
                    continue
                groups[(entry.programId, entry.year, slot.semester, slot.moed)].add(slot)

        errors = []
        for (program_id, year, semester, moed), group_slots in groups.items():
            if len(group_slots) < 2:
                continue
            dates = all_dates(group_slots)
            if not dates:
                continue
            max_span = (max(dates) - min(dates)).days
            if max_span < self._k:
                errors.append(
                    f"Exam span requires {self._k} days, but program {program_id} "
                    f"year {year} semester {enum_name(semester)} moed {enum_name(moed)} "
                    f"can span at most {max_span} days."
                )
        return errors
