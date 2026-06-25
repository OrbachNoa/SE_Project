"""Human-readable labels and values for the five score criteria.

The clustering engine works on the raw scores, where two criteria are *negated*
(higher = better): fewer elective conflicts and fewer exams on the busiest day are
stored as negative numbers. That is correct for the maths but confusing on screen,
so this module is the single place that turns a (criterion, raw value) pair into a
friendly label and an intuitive, de-negated number for display.
"""
from __future__ import annotations

from src.logic.clustering.ExtendedFeatureComputer import (
    AVG_MOED_GAP,
    AVG_PREP_DAYS,
    BUSIEST_WEEK_COUNT,
    DOUBLE_EXAM_DAYS,
    GAP_STD_DEV,
    MANDATORY_CONSEC,
    MAX_REST_DAYS,
    MIN_MOED_GAP,
)
from src.logic.comparators.ScheduleScorer import (
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
    MIN_MANDATORY_GAP,
)

# Friendly labels, in no particular order (lookup by criterion id).
CRITERION_LABELS = {
    MIN_MANDATORY_GAP:   "Min mandatory gap (days)",
    AVG_ALL_COURSES_GAP: "Avg gap, all courses (days)",
    ELECTIVE_CONFLICTS:  "Elective conflicts",
    MANDATORY_SPAN:      "Mandatory span (days)",
    MAX_EXAMS_PER_DAY:   "Max exams per day",
    # Extended clustering features
    AVG_MOED_GAP:        "Avg Moed A→B gap (days)",
    MIN_MOED_GAP:        "Min Moed A→B gap (days)",
    GAP_STD_DEV:         "Gap consistency",
    AVG_PREP_DAYS:       "Avg prep days (mandatory)",
    DOUBLE_EXAM_DAYS:    "Double exam days",
    BUSIEST_WEEK_COUNT:  "Busiest week (exams)",
    MAX_REST_DAYS:       "Longest rest (days)",
    MANDATORY_CONSEC:    "Consecutive mandatory days",
}

# Criteria stored negated (higher-is-better); flip the sign for display so the
# user sees a natural, positive count.
_NEGATED = {ELECTIVE_CONFLICTS, MAX_EXAMS_PER_DAY, DOUBLE_EXAM_DAYS, BUSIEST_WEEK_COUNT, MANDATORY_CONSEC, GAP_STD_DEV}


def label(criterion: str) -> str:
    """Friendly label for a criterion id."""
    return CRITERION_LABELS.get(criterion, criterion)


def display_value(criterion: str, raw: float) -> str:
    """Format a raw score for display, de-negating where needed."""
    value = -raw if criterion in _NEGATED else raw
    return f"{value:.1f}"
