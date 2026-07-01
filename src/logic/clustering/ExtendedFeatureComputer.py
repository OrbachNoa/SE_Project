from __future__ import annotations

import bisect
import datetime
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict

from src.application.dto.ScheduleDTO import ScheduleDTO

# LLM-only extended features
AVG_MOED_GAP          = "AVG_MOED_GAP"
MIN_MOED_GAP          = "MIN_MOED_GAP"
DOUBLE_EXAM_DAYS      = "DOUBLE_EXAM_DAYS"
BUSIEST_WEEK_COUNT    = "BUSIEST_WEEK_COUNT"
MANDATORY_CONSEC      = "MANDATORY_CONSEC"

# Default extended features
GAP_STD_DEV           = "GAP_STD_DEV"
AVG_PREP_DAYS         = "AVG_PREP_DAYS"
MAX_REST_DAYS         = "MAX_REST_DAYS"
B2B_EXAM_INCIDENCE    = "B2B_EXAM_INCIDENCE"
DEPT_EXAM_CONCURRENCY = "DEPT_EXAM_CONCURRENCY"
INSTRUCTOR_EXAM_GAP   = "INSTRUCTOR_EXAM_GAP"

DEFAULT_EXTENDED_FEATURES = (
    GAP_STD_DEV,
    AVG_PREP_DAYS,
    MAX_REST_DAYS,
    B2B_EXAM_INCIDENCE,
    DEPT_EXAM_CONCURRENCY,
    INSTRUCTOR_EXAM_GAP,
)

LLM_EXTENDED_FEATURES = (
    AVG_MOED_GAP,
    MIN_MOED_GAP,
    DOUBLE_EXAM_DAYS,
    BUSIEST_WEEK_COUNT,
    MANDATORY_CONSEC,
)

ALL_EXTENDED_FEATURES = DEFAULT_EXTENDED_FEATURES + LLM_EXTENDED_FEATURES

LOWER_IS_BETTER_EXTENDED_FEATURES = (
    GAP_STD_DEV,
    MAX_REST_DAYS,
    B2B_EXAM_INCIDENCE,
    DEPT_EXAM_CONCURRENCY,
    DOUBLE_EXAM_DAYS,
    BUSIEST_WEEK_COUNT,
    MANDATORY_CONSEC,
)


def _lower_is_better_score(value: float) -> float:
    """Store lower-is-better feature values as higher-is-better scores."""
    return -float(value)


@dataclass
class _FeatureContext:
    dates_by_course: dict
    dates_all: list
    dates_set: set
    mandatory_dates: set
    date_counts: dict
    parsed_assignments: list


class ExtendedFeatureComputer:

    @staticmethod
    def compute(schedule_dto: ScheduleDTO) -> Dict[str, float]:
        if not schedule_dto.assignments:
            return {k: 0.0 for k in ALL_EXTENDED_FEATURES}

        context = ExtendedFeatureComputer._build_context(schedule_dto)
        sorted_dates = sorted(context.dates_set)

        result: Dict[str, float] = {}
        result.update(ExtendedFeatureComputer._moed_gap_scores(context.dates_by_course))
        result.update(ExtendedFeatureComputer._spacing_scores(sorted_dates))
        result[AVG_PREP_DAYS] = ExtendedFeatureComputer._avg_prep_days(
            context.mandatory_dates, sorted_dates
        )
        result[DOUBLE_EXAM_DAYS] = ExtendedFeatureComputer._double_exam_days(
            context.date_counts
        )
        result[BUSIEST_WEEK_COUNT] = ExtendedFeatureComputer._busiest_week_count(
            context.dates_all
        )
        result[MANDATORY_CONSEC] = ExtendedFeatureComputer._mandatory_consecutive_days(
            context.mandatory_dates
        )
        result[B2B_EXAM_INCIDENCE] = ExtendedFeatureComputer._b2b_exam_incidence(
            context.parsed_assignments
        )
        result[DEPT_EXAM_CONCURRENCY] = ExtendedFeatureComputer._dept_exam_concurrency(
            context.parsed_assignments
        )
        result[INSTRUCTOR_EXAM_GAP] = ExtendedFeatureComputer._instructor_exam_gap(
            context.parsed_assignments
        )
        return result

    @staticmethod
    def _build_context(schedule_dto: ScheduleDTO) -> _FeatureContext:
        dates_by_course: dict = defaultdict(dict)
        dates_all: list = []
        dates_set: set = set()
        mandatory_dates: set = set()
        date_counts: dict = defaultdict(int)
        parsed_assignments: list = []

        for a in schedule_dto.assignments:
            try:
                d = datetime.date.fromisoformat(a.date)
            except (ValueError, TypeError, AttributeError):
                continue
            day = d.toordinal()
            parsed_assignments.append((a, d, day))
            dates_by_course[a.course_id][a.moed] = d
            dates_all.append(d)
            dates_set.add(d)
            date_counts[d] += 1
            if any(req == "OBLIGATORY" for _, req in (a.program_requirements or [])):
                mandatory_dates.add(d)

        return _FeatureContext(
            dates_by_course=dates_by_course,
            dates_all=dates_all,
            dates_set=dates_set,
            mandatory_dates=mandatory_dates,
            date_counts=date_counts,
            parsed_assignments=parsed_assignments,
        )

    @staticmethod
    def _moed_gap_scores(dates_by_course: dict) -> Dict[str, float]:
        moed_gaps = [
            abs((moeds["BET"] - moeds["ALEPH"]).days)
            for moeds in dates_by_course.values()
            if "ALEPH" in moeds and "BET" in moeds
        ]
        return {
            AVG_MOED_GAP: statistics.mean(moed_gaps) if moed_gaps else 0.0,
            MIN_MOED_GAP: float(min(moed_gaps)) if moed_gaps else 0.0,
        }

    @staticmethod
    def _spacing_scores(sorted_dates: list) -> Dict[str, float]:
        if len(sorted_dates) >= 2:
            gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days
                    for i in range(len(sorted_dates) - 1)]
            return {
                GAP_STD_DEV: _lower_is_better_score(statistics.pstdev(gaps)),
                MAX_REST_DAYS: _lower_is_better_score(max(gaps)),
            }
        return {GAP_STD_DEV: 0.0, MAX_REST_DAYS: 0.0}

    @staticmethod
    def _avg_prep_days(mandatory_dates: set, sorted_dates: list) -> float:
        if mandatory_dates:
            prep_days = []
            for d in mandatory_dates:
                idx = bisect.bisect_left(sorted_dates, d)
                if idx > 0:
                    prep_days.append(float((d - sorted_dates[idx - 1]).days))
            return statistics.mean(prep_days) if prep_days else 0.0
        return 0.0

    @staticmethod
    def _double_exam_days(date_counts: dict) -> float:
        return _lower_is_better_score(
            sum(1 for cnt in date_counts.values() if cnt >= 2)
        )

    @staticmethod
    def _busiest_week_count(dates_all: list) -> float:
        week_counts: dict = defaultdict(int)
        for d in dates_all:
            week_counts[d.isocalendar()[:2]] += 1
        return (
            _lower_is_better_score(max(week_counts.values()))
            if week_counts else 0.0
        )

    @staticmethod
    def _mandatory_consecutive_days(mandatory_dates: set) -> float:
        sorted_mandatory = sorted(mandatory_dates)
        consec = sum(
            1 for i in range(len(sorted_mandatory) - 1)
            if (sorted_mandatory[i + 1] - sorted_mandatory[i]).days == 1
        )
        return _lower_is_better_score(consec)

    @staticmethod
    def _b2b_exam_incidence(parsed_assignments: list) -> float:
        cohort_dates = defaultdict(list)
        for a, _d, day in parsed_assignments:
            for prog_id, _ in (a.program_requirements or []):
                cohort_dates[prog_id].append(day)

        all_gaps = []
        for dates in cohort_dates.values():
            if len(dates) < 2:
                continue
            dates.sort()
            for i in range(1, len(dates)):
                all_gaps.append(dates[i] - dates[i - 1])

        b2b_count = sum(1 for g in all_gaps if g == 1)
        return _lower_is_better_score(
            b2b_count / len(all_gaps) if all_gaps else 0.0
        )

    @staticmethod
    def _dept_exam_concurrency(parsed_assignments: list) -> float:
        dept_day_counts = defaultdict(int)
        for a, d, _day in parsed_assignments:
            dept = a.course_id[:2]
            dept_day_counts[(dept, d)] += 1
        max_dept = max(dept_day_counts.values()) if dept_day_counts else 0.0
        return _lower_is_better_score(max_dept)

    @staticmethod
    def _instructor_exam_gap(parsed_assignments: list) -> float:
        prof_dates = defaultdict(list)
        for a, _d, day in parsed_assignments:
            if a.instructor:
                prof_dates[a.instructor].append(day)
        min_prof_gap = None
        for dates in prof_dates.values():
            if len(dates) < 2:
                continue
            dates.sort()
            for i in range(1, len(dates)):
                gap = dates[i] - dates[i - 1]
                if min_prof_gap is None or gap < min_prof_gap:
                    min_prof_gap = gap
        return float(min_prof_gap if min_prof_gap is not None else 21.0)

