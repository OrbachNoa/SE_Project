from __future__ import annotations

from src.logic.clustering.ExtendedFeatureComputer import (
    AVG_MOED_GAP,
    AVG_PREP_DAYS,
    B2B_EXAM_INCIDENCE,
    BUSIEST_WEEK_COUNT,
    DEPT_EXAM_CONCURRENCY,
    DOUBLE_EXAM_DAYS,
    GAP_STD_DEV,
    INSTRUCTOR_EXAM_GAP,
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


CRITERION_LABELS = {
    MIN_MANDATORY_GAP: "Min mandatory gap (days)",
    AVG_ALL_COURSES_GAP: "Avg gap, all courses (days)",
    ELECTIVE_CONFLICTS: "Elective conflicts",
    MANDATORY_SPAN: "Mandatory span (days)",
    MAX_EXAMS_PER_DAY: "Max exams per day",
    AVG_MOED_GAP: "Avg Gap between Moed A and Moed B (days)",
    MIN_MOED_GAP: "Min gap between Moed A and Moed B (days)",
    GAP_STD_DEV: "Gap consistency (days)",
    AVG_PREP_DAYS: "Avg prep days (mandatory)",
    DOUBLE_EXAM_DAYS: "Double exam days",
    BUSIEST_WEEK_COUNT: "Busiest week (exams)",
    MAX_REST_DAYS: "Max gap between exams (days)",
    MANDATORY_CONSEC: "Consecutive mandatory days",
    B2B_EXAM_INCIDENCE: "Back-to-back exam rate",
    DEPT_EXAM_CONCURRENCY: "Dept exam concurrency (peak)",
    INSTRUCTOR_EXAM_GAP: "Min instructor gap (days)",
}

SORT_CRITERION_LABELS = {
    MIN_MANDATORY_GAP: "Min gap between mandatory exams (larger first)",
    AVG_ALL_COURSES_GAP: "Avg gap between all exams (larger first)",
    ELECTIVE_CONFLICTS: "Fewer elective-exam conflicts",
    MANDATORY_SPAN: "Span of mandatory exams (larger first)",
    MAX_EXAMS_PER_DAY: "Fewer exams on the busiest day",
}

CRITERION_SUMMARIES = {
    MIN_MANDATORY_GAP: "Minimum number of days between two mandatory exams for any student.",
    AVG_ALL_COURSES_GAP: "Average spacing (in days) between consecutive exams across all courses.",
    ELECTIVE_CONFLICTS: "Number of students experiencing overlapping exams for elective courses.",
    MANDATORY_SPAN: "The total length of the exam period (in days) spanning mandatory course exams.",
    MAX_EXAMS_PER_DAY: "The maximum number of exams scheduled on any single day.",
    AVG_MOED_GAP: "Average number of days between Moed A and Moed B exams for the same course.",
    MIN_MOED_GAP: "Minimum number of days between Moed A and Moed B exams for the same course.",
    GAP_STD_DEV: "Standard deviation of study gaps, measuring schedule spacing consistency.",
    AVG_PREP_DAYS: "The average number of preparation days students have before mandatory exams.",
    DOUBLE_EXAM_DAYS: "Number of days with two or more exams scheduled.",
    BUSIEST_WEEK_COUNT: "The peak number of exams scheduled within any single calendar week.",
    MAX_REST_DAYS: "The maximum gap (in days) between consecutive exams, highlighting inactive periods.",
    MANDATORY_CONSEC: "Number of times a student has mandatory exams on consecutive days.",
    B2B_EXAM_INCIDENCE: "The percentage of all exams that are scheduled back-to-back on consecutive days.",
    DEPT_EXAM_CONCURRENCY: "The peak number of exams scheduled for a single department on any given day.",
    INSTRUCTOR_EXAM_GAP: "The minimum spacing (in days) between exams taught by the same instructor.",
}

LOWER_IS_BETTER_CRITERIA = {
    ELECTIVE_CONFLICTS,
    MAX_EXAMS_PER_DAY,
    DOUBLE_EXAM_DAYS,
    BUSIEST_WEEK_COUNT,
    MANDATORY_CONSEC,
    GAP_STD_DEV,
    MAX_REST_DAYS,
    B2B_EXAM_INCIDENCE,
    DEPT_EXAM_CONCURRENCY,
}

PERCENTAGE_CRITERIA = {
    B2B_EXAM_INCIDENCE,
}

CLUSTER_STANDOUT_PHRASES = {
    MIN_MANDATORY_GAP: (
        "More breathing room between mandatory exams",
        "Mandatory exams packed close together",
    ),
    AVG_ALL_COURSES_GAP: (
        "Exams spread out across the period",
        "Exams bunched closely in time",
    ),
    ELECTIVE_CONFLICTS: (
        "Few elective clashes",
        "More elective clashes",
    ),
    MANDATORY_SPAN: (
        "Mandatory exams span a wide window",
        "Mandatory exams kept within a short window",
    ),
    MAX_EXAMS_PER_DAY: (
        "A light busiest-day load",
        "A heavy busiest-day load",
    ),
    AVG_MOED_GAP: (
        "Longer Moed A to B grading gaps",
        "Shorter Moed A to B grading gaps",
    ),
    MIN_MOED_GAP: (
        "A generous minimum Moed A to B gap",
        "A tight minimum Moed A to B gap",
    ),
    GAP_STD_DEV: (
        "Highly consistent study gaps",
        "Unevenly distributed study gaps",
    ),
    AVG_PREP_DAYS: (
        "Abundant study prep days before mandatory exams",
        "Limited study prep days before mandatory exams",
    ),
    DOUBLE_EXAM_DAYS: (
        "Fewer days with multiple exams",
        "More days with multiple exams",
    ),
    B2B_EXAM_INCIDENCE: (
        "Fewer consecutive days with exams",
        "More consecutive days with exams",
    ),
    BUSIEST_WEEK_COUNT: (
        "A lighter busiest-week exam load",
        "A heavier busiest-week exam load",
    ),
    DEPT_EXAM_CONCURRENCY: (
        "Low department-specific exam concurrency",
        "High department-specific exam concurrency",
    ),
    MAX_REST_DAYS: (
        "Compact exam spacing overall",
        "Longer inactive gaps between exams",
    ),
    INSTRUCTOR_EXAM_GAP: (
        "Excellent instructor grading gaps",
        "Tight grading windows for instructors",
    ),
    MANDATORY_CONSEC: (
        "Fewer back-to-back mandatory exams",
        "More back-to-back mandatory exams",
    ),
}


def label(criterion: str) -> str:
    return CRITERION_LABELS.get(criterion, criterion)


def is_lower_better(criterion: str) -> bool:
    return criterion in LOWER_IS_BETTER_CRITERIA


def is_percentage(criterion: str) -> bool:
    return criterion in PERCENTAGE_CRITERIA


def criterion_summary(criterion: str) -> str:
    return CRITERION_SUMMARIES.get(criterion, "")


def standout_phrases(criterion: str) -> tuple[str, str] | None:
    return CLUSTER_STANDOUT_PHRASES.get(criterion)


def _bounded_score(value: float) -> int:
    return min(100, max(0, int(value)))


def display_bar_score(criterion: str, display_value: float) -> int:
    """Convert a natural display value to a 0-100 bar score."""

    val = float(display_value)
    if criterion == MIN_MANDATORY_GAP:
        return _bounded_score((val / 4.0) * 100)
    if criterion == AVG_ALL_COURSES_GAP:
        return _bounded_score((val / 6.0) * 100)
    if criterion == ELECTIVE_CONFLICTS:
        return _bounded_score((1.0 / (1.0 + val)) * 100)
    if criterion == MANDATORY_SPAN:
        return _bounded_score((val / 14.0) * 100)
    if criterion == MAX_EXAMS_PER_DAY:
        if val <= 1.0:
            return 100
        return _bounded_score((1.0 / val) * 100)
    if criterion == AVG_MOED_GAP:
        return _bounded_score((val / 14.0) * 100)
    if criterion == MIN_MOED_GAP:
        return _bounded_score((val / 10.0) * 100)
    if criterion == GAP_STD_DEV:
        return _bounded_score((1.0 / (1.0 + val)) * 100)
    if criterion == AVG_PREP_DAYS:
        return _bounded_score((val / 4.0) * 100)
    if criterion == DOUBLE_EXAM_DAYS:
        return _bounded_score((1.0 / (1.0 + val)) * 100)
    if criterion == BUSIEST_WEEK_COUNT:
        if val <= 2.0:
            return 100
        return _bounded_score((2.0 / val) * 100)
    if criterion == MAX_REST_DAYS:
        if val <= 5.0:
            return 100
        return _bounded_score((5.0 / val) * 100)
    if criterion == B2B_EXAM_INCIDENCE:
        return _bounded_score(100.0 - val)
    if criterion == DEPT_EXAM_CONCURRENCY:
        if val <= 1.0:
            return 100
        return _bounded_score((1.0 / val) * 100)
    if criterion == INSTRUCTOR_EXAM_GAP:
        return _bounded_score((val / 7.0) * 100)
    if criterion == MANDATORY_CONSEC:
        return _bounded_score((1.0 / (1.0 + val)) * 100)
    return _bounded_score(val)
