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
    "quality_label",
    "spread_label",
    "COMPOSITE_LABEL_RECIPES",
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


from src.logic.comparators.ScheduleScorer import (
    MIN_MANDATORY_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
)
from src.logic.clustering.ExtendedFeatureComputer import (
    AVG_PREP_DAYS,
    B2B_EXAM_INCIDENCE,
    DOUBLE_EXAM_DAYS,
    DEPT_EXAM_CONCURRENCY,
    INSTRUCTOR_EXAM_GAP,
    MAX_REST_DAYS,
)


def quality_label(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 45:
        return "Fair"
    if score >= 25:
        return "Poor"
    return "Critical"


def spread_label(score: int) -> str:
    if score >= 85:
        return "Wide"
    if score >= 65:
        return "Balanced"
    if score >= 45:
        return "Moderate"
    if score >= 25:
        return "Narrow"
    return "Compressed"


COMPOSITE_LABEL_RECIPES = {
    "student_comfort": (
        ((MIN_MANDATORY_GAP, 0.5), (B2B_EXAM_INCIDENCE, 0.3), (AVG_PREP_DAYS, 0.2)),
        quality_label,
    ),
    "admin_load": (
        ((ELECTIVE_CONFLICTS, 0.6), (DOUBLE_EXAM_DAYS, 0.4)),
        quality_label,
    ),
    "faculty_impact": (
        ((DEPT_EXAM_CONCURRENCY, 0.5), (INSTRUCTOR_EXAM_GAP, 0.5)),
        quality_label,
    ),
    "schedule_spread": (
        ((MANDATORY_SPAN, 0.6), (MAX_REST_DAYS, 0.4)),
        spread_label,
    ),
}
