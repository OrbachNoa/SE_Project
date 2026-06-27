"""Comparator for sorting by the busiest exam day overall (fewer is better).

The underlying metric is lower-is-better, so we negate it here to keep the
system-wide higher-is-better convention used by the re-rank.
"""
from __future__ import annotations


from src.logic.comparators import Metrics


class MaxExamsPerDayComparator:
    """Sorts by the most exams scheduled on any single day, across the whole
    schedule (no program grouping, mirroring MaxExamsPerDayChecker). Fewer
    exams crammed into one day is better, so those schedules rank higher.
    Descending order.
    """

    criterion_id = "MAX_EXAMS_PER_DAY"
    label = "Fewer exams on the busiest day"

    def key(self, schedule) -> float:
        # Fewer exams on the busiest day should rank higher, so we negate the raw count.
        return -float(Metrics.max_exams_per_day(schedule))