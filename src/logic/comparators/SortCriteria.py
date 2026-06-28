"""Central registry of sortable schedule criteria."""
from __future__ import annotations

from src.logic.comparators.ScheduleScorer import (
    ALL_CRITERIA,
)
from src.logic.clustering.CriterionMetadata import SORT_CRITERION_LABELS

# criterion_id -> human-readable sort label.
CRITERION_LABELS = dict(SORT_CRITERION_LABELS)


def label_for(criterion_id: str) -> str:
    """Display label for a criterion id, falling back to the id itself."""
    return CRITERION_LABELS.get(criterion_id, criterion_id)


__all__ = ["ALL_CRITERIA", "CRITERION_LABELS", "label_for"]
