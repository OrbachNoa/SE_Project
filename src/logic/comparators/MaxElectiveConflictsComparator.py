"""Comparator for sorting by elective-exam crowding (fewer is better).

The underlying metric is lower-is-better, so we negate it here to keep the
system-wide higher-is-better convention used by the re-rank.
"""
from __future__ import annotations

from typing import Optional

from src.logic.comparators import Metrics


class MaxElectiveConflictsComparator:
    """Sorts by the worst per-program elective same-day pair-conflict total.
    For each program (year is ignored, mirroring ElectiveConflictCapChecker)
    we count same-day elective pairs; the schedule's score is the worst
    program's total. Fewer conflict pairs is better, so schedules with a
    smaller total rank higher. Descending order.
    """

    criterion_id = "ELECTIVE_CONFLICTS"
    label = "Fewer elective-exam conflicts"

    def __init__(self, courses: list, selected_programs: Optional[list] = None):
        # The programs where each course is elective, built once via build_elective_program_index.
        self._elective_programs = Metrics.build_elective_program_index(courses, selected_programs)

    def key(self, schedule) -> float:
        # Fewer conflicts should rank higher, so we negate the raw count.
        return -float(
            Metrics.elective_conflict_pairs(schedule, self._elective_programs)
        )