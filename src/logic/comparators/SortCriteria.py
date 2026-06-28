"""Central registry of sortable schedule criteria.

Single source of truth mapping criterion ids to their display labels, built once
from the comparator classes. The sort-config GUI imports this registry instead
of importing each comparator class directly, so adding a new sort criterion only
means registering its comparator here.
"""
from __future__ import annotations

from src.logic.comparators.MinMandatoryGapComparator import MinMandatoryGapComparator
from src.logic.comparators.AvgAllCoursesGapComparator import AvgAllCoursesGapComparator
from src.logic.comparators.MaxElectiveConflictsComparator import MaxElectiveConflictsComparator
from src.logic.comparators.MandatorySpanComparator import MandatorySpanComparator
from src.logic.comparators.MaxExamsPerDayComparator import MaxExamsPerDayComparator
from src.logic.comparators.ScheduleScorer import ALL_CRITERIA

# Comparator classes that back each sortable criterion.
SORT_COMPARATORS = [
    MinMandatoryGapComparator,
    AvgAllCoursesGapComparator,
    MaxElectiveConflictsComparator,
    MandatorySpanComparator,
    MaxExamsPerDayComparator,
]

# criterion_id -> human-readable label.
CRITERION_LABELS = {c.criterion_id: c.label for c in SORT_COMPARATORS}


def label_for(criterion_id: str) -> str:
    """Display label for a criterion id, falling back to the id itself."""
    return CRITERION_LABELS.get(criterion_id, criterion_id)


__all__ = ["ALL_CRITERIA", "SORT_COMPARATORS", "CRITERION_LABELS", "label_for"]
