"""Clustering-specific evaluation metrics and scores constants.

Isolates clustering-specific evaluation criteria from the core schedule
ranking/priority engine (ScheduleScorer.py).
"""
from __future__ import annotations

from src.logic.comparators.ScheduleScorer import (
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
    ALL_CRITERIA,
)
from src.logic.clustering.ExtendedFeatureComputer import ALL_EXTENDED_FEATURES

EXTENDED_CRITERIA = ALL_CRITERIA + ALL_EXTENDED_FEATURES
