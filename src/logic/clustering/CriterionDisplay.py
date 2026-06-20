"""Human-readable labels and values for the five score criteria.

The clustering engine works on the raw scores, where two criteria are *negated*
(higher = better): fewer elective conflicts and fewer exams on the busiest day are
stored as negative numbers. That is correct for the maths but confusing on screen,
so this module is the single place that turns a (criterion, raw value) pair into a
friendly label and an intuitive, de-negated number for display.
"""
from __future__ import annotations

from src.logic.comparators.ScheduleScorer import (
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
    MIN_MANDATORY_GAP,
)

# Friendly labels, in no particular order (lookup by criterion id).
CRITERION_LABELS = {
    MIN_MANDATORY_GAP: "Min mandatory gap (days)",
    AVG_ALL_COURSES_GAP: "Avg gap, all courses (days)",
    ELECTIVE_CONFLICTS: "Elective conflicts",
    MANDATORY_SPAN: "Mandatory span (days)",
    MAX_EXAMS_PER_DAY: "Max exams per day",
}

# Criteria stored negated (higher-is-better); flip the sign for display so the
# user sees a natural, positive count.
_NEGATED = {ELECTIVE_CONFLICTS, MAX_EXAMS_PER_DAY}


def label(criterion: str) -> str:
    """Friendly label for a criterion id."""
    return CRITERION_LABELS.get(criterion, criterion)


def display_value(criterion: str, raw: float) -> str:
    """Format a raw score for display, de-negating where needed."""
    value = -raw if criterion in _NEGATED else raw
    return f"{value:.1f}"
