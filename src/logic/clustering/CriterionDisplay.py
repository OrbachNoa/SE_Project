"""Human-readable formatting for score criteria and extended features."""
from __future__ import annotations

from src.logic.clustering.CriterionMetadata import (
    CLUSTER_STANDOUT_PHRASES,
    CRITERION_LABELS,
    CRITERION_SUMMARIES,
    criterion_summary,
    display_bar_score,
    is_lower_better,
    is_percentage,
    label,
    standout_phrases,
)

__all__ = [
    "CLUSTER_STANDOUT_PHRASES",
    "CRITERION_LABELS",
    "CRITERION_SUMMARIES",
    "criterion_summary",
    "display_value",
    "display_value_to_percentage",
    "is_lower_better",
    "label",
    "standout_phrases",
]


def display_value(criterion: str, raw: float) -> str:
    """Format a raw higher-is-better score for natural display."""
    value = -raw if is_lower_better(criterion) else raw
    if is_percentage(criterion):
        formatted = f"{value * 100:.1f}%"
    else:
        formatted = f"{value:.1f}"
    if formatted == "-0.0" or formatted == "-0.0%":
        return "0.0%" if is_percentage(criterion) else "0.0"
    return formatted


def display_value_to_percentage(crit_key: str, val_str: str) -> int:
    """Convert a display value string back to a 0-100 score for bar visualization."""
    try:
        val = float(val_str.replace("%", "")) if isinstance(val_str, str) and "%" in val_str else float(val_str)
    except ValueError:
        val = 0.0
    return display_bar_score(crit_key, val)
