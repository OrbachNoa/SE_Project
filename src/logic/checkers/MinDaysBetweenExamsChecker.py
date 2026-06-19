from __future__ import annotations
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Set, Tuple

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, max_spaced_count
from src.models.Enums import Requirement


class GapScope(Enum):
    """Selects which exams the minimum-gap rule applies to."""
    OBLIGATORY_ONLY = "OBLIGATORY_ONLY"   # 2.1: only courses obligatory in the cohort
    ANY = "ANY"                           # 2.2: every course


class MinDaysBetweenExamsChecker(IConflictChecker):
    """Rejects schedules where two exams in the same (program, year) are closer
    than k calendar days. OBLIGATORY_ONLY counts only courses obligatory in that
    cohort (2.1); ANY counts every course (2.2). The same course's own moedim
    are included. Day counting is a plain calendar difference, so weekends and
    holidays count.
    """
    uses_ordinal_date_index = True

    def __init__(self, scope: GapScope, k: int):
        self._scope = scope
        self._k = k
        self._eligible_masks: Dict[str, int] = {}

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        selected = set(selected_programs) if selected_programs else None
        eligible: Dict[str, Set[Tuple[str, int]]] = {}
        cohort_ids: Dict[Tuple[str, int], int] = {}
        for course in courses:
            cohorts: Set[Tuple[str, int]] = set()
            for entry in course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if (self._scope is GapScope.OBLIGATORY_ONLY
                        and entry.requirement is not Requirement.OBLIGATORY):
                    continue
                cohorts.add((entry.programId, entry.year))
            if cohorts:
                eligible[course.courseId] = cohorts
                for cohort in cohorts:
                    if cohort not in cohort_ids:
                        cohort_ids[cohort] = len(cohort_ids)

        self._eligible_masks = {
            course_id: sum(1 << cohort_ids[cohort] for cohort in cohorts)
            for course_id, cohorts in eligible.items()
        }

    def check(self, assignment, schedule) -> bool:
        if self._k <= 0:
            return False
        new_mask = self._eligible_masks.get(assignment.course.courseId, 0)
        if not new_mask:
            return False

        new_ordinal = assignment.date.toordinal()
        eligible_masks = self._eligible_masks
        # A gap < k is a violation, so any eligible exam within (k-1) days on
        # either side breaks the rule. Scanning integer ordinals avoids creating
        # timedelta/date objects in this hot loop.
        for ordinal in range(new_ordinal - self._k + 1, new_ordinal + self._k):
            other_ids = schedule.course_ids_on_ordinal(ordinal)
            if not other_ids:
                continue
            for other_id in other_ids:
                if new_mask & eligible_masks.get(other_id, 0):
                    return True
        return False

    def feasibility_bound(self, context) -> List[str]:
        """Preflight: can enough spaced dates fit for every (program, year)
        cohort that needs this gap, given the candidate dates of its exams?
        """
        if self._k is None:
            return []

        selected = context.selected_set
        groups: Dict[Tuple[str, int], Set] = defaultdict(set)
        for slot in context.slots:
            for entry in slot.course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if (self._scope is GapScope.OBLIGATORY_ONLY
                        and entry.requirement is not Requirement.OBLIGATORY):
                    continue
                groups[(entry.programId, entry.year)].add(slot)

        label = "mandatory exams" if self._scope is GapScope.OBLIGATORY_ONLY else "all exams"
        errors = []
        for (program_id, year), group_slots in groups.items():
            required = len(group_slots)
            if required < 2:
                continue
            capacity = max_spaced_count(all_dates(group_slots), self._k)
            if required > capacity:
                errors.append(
                    f"Minimum gap for {label} requires {required} exams in "
                    f"program {program_id} year {year}, but only {capacity} "
                    f"dates can fit with a {self._k}-day gap."
                )
        return errors
