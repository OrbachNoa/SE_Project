"""Comparator for sorting by elective-exam crowding (fewer is better).

The underlying metric is lower-is-better, so we negate it here to keep the
system-wide higher-is-better convention used by the re-rank.
"""
from __future__ import annotations

from typing import Optional

from src.logic.comparators import Metrics


class MaxElectiveConflictsComparator:
    """Legacy comparator for worst elective same-day crowding.

    The threshold checker still enforces pair-conflict caps separately. This
    comparator ranks by the same peak-minus-one score exposed by ScheduleScorer.
    """

    criterion_id = "ELECTIVE_CONFLICTS"
    label = "Fewer elective-exam conflicts"

    def __init__(self, courses: list, selected_programs: Optional[list] = None):
        self._elective_cohorts = Metrics.build_elective_index(courses, selected_programs)

    def key(self, schedule) -> float:
        # Fewer conflicts should rank higher, so we negate the raw count.
        return -float(
            Metrics.peak_elective_conflict(schedule, self._elective_cohorts)
        )
