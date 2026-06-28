from __future__ import annotations

from typing import Dict, Optional, Tuple

from src.logic.clustering.ExtendedFeatureComputer import (
    ALL_EXTENDED_FEATURES,
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
    ALL_CRITERIA,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
    MIN_MANDATORY_GAP,
)


TOPIC_CRITERIA: Dict[str, Tuple[list, dict]] = {
    "retake_time": ([AVG_MOED_GAP, MIN_MOED_GAP], {AVG_MOED_GAP: 2.0}),
    "study_prep": ([AVG_PREP_DAYS, MIN_MANDATORY_GAP], {AVG_PREP_DAYS: 3.0}),
    "daily_load": (
        [MAX_EXAMS_PER_DAY, DOUBLE_EXAM_DAYS, BUSIEST_WEEK_COUNT, DEPT_EXAM_CONCURRENCY],
        {MAX_EXAMS_PER_DAY: 2.0, DEPT_EXAM_CONCURRENCY: 1.2},
    ),
    "weekly_load": ([BUSIEST_WEEK_COUNT, MAX_EXAMS_PER_DAY], {BUSIEST_WEEK_COUNT: 2.0}),
    "rest": ([MIN_MANDATORY_GAP, AVG_ALL_COURSES_GAP, MAX_REST_DAYS], {}),
    "consistency": ([GAP_STD_DEV, AVG_ALL_COURSES_GAP], {GAP_STD_DEV: 2.0}),
    "consecutive": (
        [B2B_EXAM_INCIDENCE, MANDATORY_CONSEC, MIN_MANDATORY_GAP],
        {MANDATORY_CONSEC: 3.0, B2B_EXAM_INCIDENCE: 3.0},
    ),
    "span": ([MANDATORY_SPAN, AVG_ALL_COURSES_GAP], {}),
    "conflicts": ([ELECTIVE_CONFLICTS, MAX_EXAMS_PER_DAY], {}),
    "balance": (
        [BUSIEST_WEEK_COUNT, GAP_STD_DEV, AVG_ALL_COURSES_GAP],
        {BUSIEST_WEEK_COUNT: 1.5, GAP_STD_DEV: 1.5},
    ),
    "faculty_load": (
        [INSTRUCTOR_EXAM_GAP, DEPT_EXAM_CONCURRENCY],
        {INSTRUCTOR_EXAM_GAP: 2.0},
    ),
    "general": (list(ALL_CRITERIA) + list(ALL_EXTENDED_FEATURES), {}),
}

FUZZY_TOPIC_MAP: Dict[str, str] = {
    "load": "daily_load",
    "daily": "daily_load",
    "cramming": "daily_load",
    "cramped": "daily_load",
    "weekly": "weekly_load",
    "heavy": "weekly_load",
    "light": "weekly_load",
    "retake": "retake_time",
    "retake_gap": "retake_time",
    "moed": "retake_time",
    "prep": "study_prep",
    "preparation": "study_prep",
    "study": "study_prep",
    "revision": "study_prep",
    "gap": "rest",
    "gaps": "rest",
    "rest_time": "rest",
    "spacing": "consistency",
    "spread": "span",
    "compact": "span",
    "concentrated": "span",
    "distribution": "balance",
    "even": "balance",
    "balanced": "balance",
    "uniform": "balance",
    "back_to_back": "consecutive",
    "backtoback": "consecutive",
    "back2back": "consecutive",
    "consecutive_days": "consecutive",
    "faculty": "faculty_load",
    "instructor": "faculty_load",
    "instructor_time": "faculty_load",
    "grading": "faculty_load",
    "dept_load": "faculty_load",
    "department": "faculty_load",
    "מרצה": "faculty_load",
    "מרצים": "faculty_load",
}

SMART_K: Dict[str, Optional[int]] = {
    "retake_time": 2,
    "daily_load": 4,
    "weekly_load": 3,
    "rest": 4,
    "study_prep": 3,
    "consistency": None,
    "consecutive": 2,
    "span": None,
    "conflicts": 3,
    "balance": 4,
    "faculty_load": 3,
    "general": None,
}
