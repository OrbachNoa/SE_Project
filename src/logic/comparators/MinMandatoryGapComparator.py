"""Comparator for the minimum gap between mandatory exams (a bigger gap is better)."""

from __future__ import annotations

from typing import Dict, Optional, Set

from src.logic.comparators import Metrics
from src.logic.comparators.Metrics import Cohort


class IScheduleComparator:
    """One sort criterion. Its key(schedule) returns a float, higher is better."""

    # Stable identifier, shared with the sort-config UI and the DTO score map.
    criterion_id: str = ""
    # Human-readable label for the sort-config panel.
    label: str = ""

    def key(self, schedule) -> float:
        raise NotImplementedError


class MinMandatoryGapComparator(IScheduleComparator):
    """Sorts by the smallest gap between two mandatory exams that share a
    (program, year). We find the closest pair in each cohort, take the closest
    one overall, and rank a larger smallest-gap higher, since more breathing
    room is better. Descending order.
    """

    criterion_id = "MIN_MANDATORY_GAP"
    label = "Min gap between mandatory exams (larger first)"

    def __init__(self, obligatory_cohorts: Dict[str, Set[Cohort]]):
        # The obligatory cohorts each course belongs to, built once via build_cohort_index.
        self._obligatory_cohorts = obligatory_cohorts

    def key(self, schedule) -> float:
        """The schedule's smallest mandatory-exam gap. Higher means better spread."""
        return float(Metrics.min_mandatory_gap(schedule, self._obligatory_cohorts))