"""Comparator for sorting by elective-exam crowding (fewer is better).

The underlying metric is lower-is-better, so we negate it here to keep the
system-wide higher-is-better convention used by the re-rank.
"""
from __future__ import annotations

from typing import Optional

from src.logic.comparators import Metrics


class MaxElectiveConflictsComparator:
    """Sorts by how crowded the worst elective day is. For each (program, year)
    cohort we look at how many of its elective exams land on the same day; the
    schedule's score is the worst such pile-up. Fewer overlapping electives is
    better, so schedules with a smaller worst-day pile-up rank higher.
    Descending order.
    """

    criterion_id = "ELECTIVE_CONFLICTS"
    label = "Fewer elective-exam conflicts"

    def __init__(self, courses: list, selected_programs: Optional[list] = None):
        # The course list, used to tell which courses are electives in which cohort.
        self._courses = courses
        # Optional filter: only these programs count. None means all programs.
        self._selected = selected_programs

    def key(self, schedule) -> float:
        # Fewer conflicts should rank higher, so we negate the raw count.
        return -float(
            Metrics.peak_elective_conflict(schedule, self._courses, self._selected)
        )