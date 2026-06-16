"""Builds the sort comparators once per run and scores each schedule.

The worker builds one ScheduleScorer from the course list and selected programs,
then calls score(schedule) on every schedule it finds. The resulting dict of
{criterion_id: float} is stored on the DTO, so the runtime re-rank only ever
sorts numbers we already computed.

Convention: every score is higher-is-better. The two metrics that are naturally
lower-is-better (elective conflicts, exams-per-day) are negated here, so the
re-rank can always sort descending with no per-criterion direction flag.
"""
from __future__ import annotations

from typing import Dict, Optional

from src.logic.comparators import Metrics


# Stable criterion ids, shared with the sort-config UI and the DTO score map.
# Criterion 1
MIN_MANDATORY_GAP = "MIN_MANDATORY_GAP"
# Criterion 2
AVG_ALL_COURSES_GAP = "AVG_ALL_COURSES_GAP"
# Criterion 3, negated because fewer is better.
ELECTIVE_CONFLICTS = "ELECTIVE_CONFLICTS"
# Criterion 4
MANDATORY_SPAN = "MANDATORY_SPAN"
# Criterion 5, negated because fewer is better.
MAX_EXAMS_PER_DAY = "MAX_EXAMS_PER_DAY"

ALL_CRITERIA = (
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
)


class ScheduleScorer:
    """Computes all five sort scores for a schedule. Built once per run."""

    def __init__(self, courses: list, selected_programs: Optional[list] = None):
        # Build every index once, the same way the checkers prepare once.
        self._courses = courses
        self._selected = selected_programs
        self._obligatory, self._any = Metrics.build_cohort_index(
            courses, selected_programs
        )
        self._span_idx = Metrics.build_span_index(courses, selected_programs)
        self._program_idx = Metrics.build_program_index(courses, selected_programs)

    def score(self, schedule) -> Dict[str, float]:
        """Return one score per criterion, higher is better for every entry."""
        return {
            MIN_MANDATORY_GAP: float(
                Metrics.min_mandatory_gap(schedule, self._obligatory)
            ),
            AVG_ALL_COURSES_GAP: float(
                Metrics.avg_all_courses_gap(schedule, self._any)
            ),
            # Fewer conflicts is better, so negate.
            ELECTIVE_CONFLICTS: -float(
                Metrics.peak_elective_conflict(
                    schedule, self._courses, self._selected
                )
            ),
            MANDATORY_SPAN: float(
                Metrics.mandatory_span(schedule, self._span_idx)
            ),
            # Fewer exams on the busiest day is better, so negate.
            MAX_EXAMS_PER_DAY: -float(
                Metrics.max_exams_per_day(schedule, self._program_idx)
            ),
        }