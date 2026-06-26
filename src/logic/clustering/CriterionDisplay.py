"""Human-readable labels and values for the score criteria and extended features.

Turns a (criterion, raw value) pair into a friendly label and an intuitive,
de-negated number for display.
"""
from __future__ import annotations

from src.logic.clustering.ExtendedFeatureComputer import (
    AVG_MOED_GAP,
    MIN_MOED_GAP,
    GAP_STD_DEV,
    AVG_PREP_DAYS,
    DOUBLE_EXAM_DAYS,
    BUSIEST_WEEK_COUNT,
    MAX_REST_DAYS,
    MANDATORY_CONSEC,
    MAX_REST_DAYS,
    MIN_MOED_GAP,
    B2B_EXAM_INCIDENCE,
    DEPT_EXAM_CONCURRENCY,
    INSTRUCTOR_EXAM_GAP,
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
    # Sort criteria
    MIN_MANDATORY_GAP:   "Min mandatory gap (days)",
    AVG_ALL_COURSES_GAP: "Avg gap, all courses (days)",
    ELECTIVE_CONFLICTS:  "Elective conflicts",
    MANDATORY_SPAN:      "Mandatory span (days)",
    MAX_EXAMS_PER_DAY:   "Max exams per day",
    # Extended features
    AVG_MOED_GAP:        "Avg Gap between Moed A and Moed B (days)",
    MIN_MOED_GAP:        "Min gap between Moed A and Moed B (days)",
    GAP_STD_DEV:         "Gap consistency (days)",
    AVG_PREP_DAYS:       "Avg prep days (mandatory)",
    DOUBLE_EXAM_DAYS:    "Double exam days",
    BUSIEST_WEEK_COUNT:  "Busiest week (exams)",
    MAX_REST_DAYS:       "Max gap between exams (days)",
    MANDATORY_CONSEC:    "Consecutive mandatory days",
    B2B_EXAM_INCIDENCE: "B2B Exam Incidence",
    DEPT_EXAM_CONCURRENCY: "Departmental Exam Concurrency",
    INSTRUCTOR_EXAM_GAP: "Instructor Exam Gap",
}

# Detailed summaries describing what each criterion calculates/means.
CRITERION_SUMMARIES = {
    # Sort criteria
    MIN_MANDATORY_GAP: "Minimum number of days between two mandatory exams for any student.",
    AVG_ALL_COURSES_GAP: "Average spacing (in days) between consecutive exams across all courses.",
    ELECTIVE_CONFLICTS: "Number of students experiencing overlapping exams for elective courses.",
    MANDATORY_SPAN: "The total length of the exam period (in days) spanning mandatory course exams.",
    MAX_EXAMS_PER_DAY: "The maximum number of exams scheduled on any single day.",
    # Extended features
    AVG_MOED_GAP:        "Average number of days between Moed A and Moed B exams for the same course.",
    MIN_MOED_GAP:        "Minimum number of days between Moed A and Moed B exams for the same course.",
    GAP_STD_DEV:         "Standard deviation of study gaps, measuring schedule spacing consistency.",
    AVG_PREP_DAYS:       "The average number of preparation days students have before mandatory exams.",
    DOUBLE_EXAM_DAYS:    "Number of days with two or more exams scheduled.",
    BUSIEST_WEEK_COUNT:  "The peak number of exams scheduled within any single calendar week.",
    MAX_REST_DAYS:       "The maximum gap (in days) between consecutive exams, highlighting inactive periods.",
    MANDATORY_CONSEC:    "Number of times a student has mandatory exams on consecutive days.",
    B2B_EXAM_INCIDENCE: "The percentage of all exams that are scheduled back-to-back on consecutive days.",
    DEPT_EXAM_CONCURRENCY: "The peak number of exams scheduled for a single department on any given day.",
    INSTRUCTOR_EXAM_GAP: "The minimum spacing (in days) between exams taught by the same instructor.",
}

# Criteria stored negated (higher-is-better); flip the sign for display so the
# user sees a natural, positive count.
_NEGATED = {
    ELECTIVE_CONFLICTS,
    MAX_EXAMS_PER_DAY,
    DOUBLE_EXAM_DAYS,
    BUSIEST_WEEK_COUNT,
    MANDATORY_CONSEC,
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
    elif crit_key == AVG_MOED_GAP:
        # Higher is better, optimal >= 14.0 days
        return min(100, max(0, int((val / 14.0) * 100)))
    elif crit_key == MIN_MOED_GAP:
        # Higher is better, optimal >= 10.0 days
        return min(100, max(0, int((val / 10.0) * 100)))
    elif crit_key == GAP_STD_DEV:
        # Lower is better, 0 is perfect.
        return min(100, max(0, int((1.0 / (1.0 + val)) * 100)))
    elif crit_key == AVG_PREP_DAYS:
        # Higher is better, optimal >= 4.0 days
        return min(100, max(0, int((val / 4.0) * 100)))
    elif crit_key == DOUBLE_EXAM_DAYS:
        # Lower is better, 0 is perfect.
        return min(100, max(0, int((1.0 / (1.0 + val)) * 100)))
    elif crit_key == BUSIEST_WEEK_COUNT:
        # Lower is better, optimal <= 2 exams.
        if val <= 2.0:
            return 100
        return min(100, max(0, int((2.0 / val) * 100)))
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
    elif crit_key == MANDATORY_CONSEC:
        # Lower is better, 0 is perfect.
        return min(100, max(0, int((1.0 / (1.0 + val)) * 100)))
    return min(100, max(0, int(val)))
