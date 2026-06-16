"""Comparator for sorting by the busiest exam day in a program (fewer is better).

The underlying metric is lower-is-better, so we negate it here to keep the
system-wide higher-is-better convention used by the re-rank.
"""
from __future__ import annotations

from typing import Dict, Set

from src.logic.comparators import Metrics


class MaxExamsPerDayComparator:
    """Sorts by the most exams any single program has on any single day. For each
    program we count exams per day, across all years, and take the highest count
    anywhere as the schedule's score. Fewer exams crammed into one day is better,
    so those schedules rank higher. Descending order.
    """

    criterion_id = "MAX_EXAMS_PER_DAY"
    label = "Fewer exams on the busiest day"

    def __init__(self, program_index: Dict[str, Set[str]]):
        # The programs each course belongs to, built once via build_program_index.
        self._program_index = program_index

    def key(self, schedule) -> float:
        # Fewer exams on the busiest day should rank higher, so we negate the raw count.
        return -float(Metrics.max_exams_per_day(schedule, self._program_index))