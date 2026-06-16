"""Comparator for sorting by the average gap between back-to-back exams (any course)."""
from __future__ import annotations

from typing import Dict, Set

from src.logic.comparators import Metrics
from src.logic.comparators.Metrics import Cohort


class AvgAllCoursesGapComparator:
    """Sorts by the average number of days between back-to-back exams. Within
    each cohort the exams are put in date order and the gaps between neighbours
    are measured, then all those gaps are pooled into one average. A larger
    average means better spacing, so those schedules rank higher. Descending order.
    """

    criterion_id = "AVG_ALL_COURSES_GAP"
    label = "Avg gap between all exams (larger first)"

    def __init__(self, any_cohorts: Dict[str, Set[Cohort]]):
        # Every cohort each course belongs to, any requirement, built once via build_cohort_index.
        self._any_cohorts = any_cohorts

    def key(self, schedule) -> float:
        return float(Metrics.avg_all_courses_gap(schedule, self._any_cohorts))