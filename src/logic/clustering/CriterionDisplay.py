"""Human-readable labels and values for the score criteria and extended features.

Turns a (criterion, raw value) pair into a friendly label and an intuitive,
de-negated number for display.
"""
from __future__ import annotations

from src.logic.comparators.ScheduleScorer import (
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
    MIN_MANDATORY_GAP,
)
from src.logic.clustering.ExtendedFeatureComputer import (
    GAP_STD_DEV,
    AVG_PREP_DAYS,
    MAX_REST_DAYS,
    B2B_EXAM_INCIDENCE,
    DEPT_EXAM_CONCURRENCY,
    INSTRUCTOR_EXAM_GAP,
)

# Friendly labels, in no particular order (lookup by criterion id).
CRITERION_LABELS = {
    MIN_MANDATORY_GAP: "Min mandatory gap (days)",
    AVG_ALL_COURSES_GAP: "Avg gap, all courses (days)",
    ELECTIVE_CONFLICTS: "Elective conflicts",
    MANDATORY_SPAN: "Mandatory span (days)",
    MAX_EXAMS_PER_DAY: "Max exams per day",
    GAP_STD_DEV: "Exam gaps std-dev (days)",
    AVG_PREP_DAYS: "Avg prep time (days)",
    MAX_REST_DAYS: "Max gap between exams (days)",
    B2B_EXAM_INCIDENCE: "Back-to-back exam rate",
    DEPT_EXAM_CONCURRENCY: "Dept exam concurrency",
    INSTRUCTOR_EXAM_GAP: "Instructor exam spacing (days)",
}

# Detailed summaries describing what each criterion calculates/means.
CRITERION_SUMMARIES = {
    MIN_MANDATORY_GAP: "Minimum number of days between two mandatory exams for any student.",
    AVG_ALL_COURSES_GAP: "Average spacing (in days) between consecutive exams across all courses.",
    ELECTIVE_CONFLICTS: "Number of students experiencing overlapping exams for elective courses.",
    MANDATORY_SPAN: "The total length of the exam period (in days) spanning mandatory course exams.",
    MAX_EXAMS_PER_DAY: "The maximum number of exams scheduled on any single day.",
    GAP_STD_DEV: "Standard deviation of study gaps, measuring schedule spacing consistency.",
    AVG_PREP_DAYS: "The average number of preparation days students have before mandatory exams.",
    MAX_REST_DAYS: "The maximum gap (in days) between consecutive exams, highlighting inactive periods.",
    B2B_EXAM_INCIDENCE: "The percentage of all exams that are scheduled back-to-back on consecutive days.",
    DEPT_EXAM_CONCURRENCY: "The peak number of exams scheduled for a single department on any given day.",
    INSTRUCTOR_EXAM_GAP: "The minimum spacing (in days) between exams taught by the same instructor.",
}

# Criteria stored negated (higher-is-better); flip the sign for display so the
# user sees a natural, positive count.
_NEGATED = {
    ELECTIVE_CONFLICTS,
    MAX_EXAMS_PER_DAY,
    GAP_STD_DEV,
    B2B_EXAM_INCIDENCE,
    DEPT_EXAM_CONCURRENCY,
}

_PERCENTAGE_CRITERIA = {
    B2B_EXAM_INCIDENCE,
}


def label(criterion: str) -> str:
    """Friendly label for a criterion id."""
    return CRITERION_LABELS.get(criterion, criterion)


def criterion_summary(criterion: str) -> str:
    """Help description/summary for a criterion id."""
    return CRITERION_SUMMARIES.get(criterion, "")


def display_value(criterion: str, raw: float) -> str:
    """Format a raw score for display, de-negating where needed."""
    value = -raw if criterion in _NEGATED else raw
    if criterion in _PERCENTAGE_CRITERIA:
        formatted = f"{value * 100:.1f}%"
    else:
        formatted = f"{value:.1f}"
    if formatted == "-0.0" or formatted == "-0.0%":
        return "0.0%" if criterion in _PERCENTAGE_CRITERIA else "0.0"
    return formatted


def display_value_to_percentage(crit_key: str, val_str: str) -> int:
    """Convert a display value string back to a 0-100 score for bar visualization."""
    try:
        val = float(val_str.replace("%", "")) if isinstance(val_str, str) and "%" in val_str else float(val_str)
    except ValueError:
        val = 0.0

    # Since val is already de-negated (positive):
    if crit_key == MIN_MANDATORY_GAP:
        # Higher is better, optimal >= 4.0 days
        return min(100, max(0, int((val / 4.0) * 100)))
    elif crit_key == AVG_ALL_COURSES_GAP:
        # Higher is better, optimal >= 6.0 days
        return min(100, max(0, int((val / 6.0) * 100)))
    elif crit_key == ELECTIVE_CONFLICTS:
        # Lower is better, 0 is perfect.
        return min(100, max(0, int((1.0 / (1.0 + val)) * 100)))
    elif crit_key == MANDATORY_SPAN:
        # Higher is better, optimal >= 14.0 days
        return min(100, max(0, int((val / 14.0) * 100)))
    elif crit_key == MAX_EXAMS_PER_DAY:
        # Lower is better, 1 is perfect.
        if val <= 1.0:
            return 100
        return min(100, max(0, int((1.0 / val) * 100)))
    elif crit_key == GAP_STD_DEV:
        # Lower is better, 0 is perfect.
        return min(100, max(0, int((1.0 / (1.0 + val)) * 100)))
    elif crit_key == AVG_PREP_DAYS:
        # Higher is better, optimal >= 4.0 days
        return min(100, max(0, int((val / 4.0) * 100)))
    elif crit_key == MAX_REST_DAYS:
        # Lower is better. optimal <= 5.0.
        if val <= 5.0:
            return 100
        return min(100, max(0, int((5.0 / val) * 100)))
    elif crit_key == B2B_EXAM_INCIDENCE:
        # Lower is better (0.0% is perfect, 100.0% is bad).
        # Since B2B_EXAM_INCIDENCE is percentage (val is in [0.0, 100.0])
        return min(100, max(0, int(100.0 - val)))
    elif crit_key == DEPT_EXAM_CONCURRENCY:
        # Lower is better, 1 is perfect.
        if val <= 1.0:
            return 100
        return min(100, max(0, int((1.0 / val) * 100)))
    elif crit_key == INSTRUCTOR_EXAM_GAP:
        # Higher is better. optimal >= 7.0 days.
        return min(100, max(0, int((val / 7.0) * 100)))
    return min(100, max(0, int(val)))

