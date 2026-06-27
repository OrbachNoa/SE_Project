"""Comparator for sorting by the span between the first and last mandatory exam."""
from __future__ import annotations

from typing import Dict, Set

from src.logic.comparators import Metrics
from src.logic.comparators.Metrics import Cohort


class MandatorySpanComparator:
    """Sorts by how spread out the mandatory exams are. For each
    (program, year, semester, moed) group we take the days between its
    earliest and latest mandatory exam, and use the largest such spread as
    the schedule's score. A wider spread is better, so those schedules rank
    higher. Descending order.
    """

    criterion_id = "MANDATORY_SPAN"
    label = "Span of mandatory exams (larger first)"

    def __init__(self, span_index: Dict[str, Set[Cohort]]):
        # The obligatory cohorts each course belongs to, built once via build_span_index.
        # The moed is added later, at scoring time, from each exam's own moed.
        self._span_index = span_index

    def key(self, schedule) -> float:
        """The schedule's widest mandatory-exam span. Higher means more spread."""
        return float(Metrics.mandatory_span(schedule, self._span_index))