from __future__ import annotations

import bisect
import datetime
import statistics
from collections import defaultdict
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


class ExtendedFeatureComputer:

    @staticmethod
    def compute(schedule_dto: ScheduleDTO) -> Dict[str, float]:
        if not schedule_dto.assignments:
            return {k: 0.0 for k in ALL_EXTENDED_FEATURES}

        dates_by_course: dict = defaultdict(dict)
        dates_all: list = []
        dates_set: set = set()
        mandatory_dates: set = set()
        date_counts: dict = defaultdict(int)

        for a in schedule_dto.assignments:
            try:
                d = datetime.date.fromisoformat(a.date)
            except (ValueError, TypeError, AttributeError):
                continue
            dates_by_course[a.course_id][a.moed] = d
            dates_all.append(d)
            dates_set.add(d)
            date_counts[d] += 1
            if any(req == "OBLIGATORY" for _, req in (a.program_requirements or [])):
                mandatory_dates.add(d)

        result: Dict[str, float] = {}

        # 1. Moed Gaps (LLM only)
        moed_gaps = [
            abs((moeds["BET"] - moeds["ALEPH"]).days)
            for moeds in dates_by_course.values()
            if "ALEPH" in moeds and "BET" in moeds
        ]
        result[AVG_MOED_GAP] = statistics.mean(moed_gaps) if moed_gaps else 0.0
        result[MIN_MOED_GAP] = float(min(moed_gaps)) if moed_gaps else 0.0

        # 2. GAP_STD_DEV, MAX_REST_DAYS
        sorted_dates = sorted(dates_set)
        if len(sorted_dates) >= 2:
            gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days
                    for i in range(len(sorted_dates) - 1)]
            result[GAP_STD_DEV] = -statistics.pstdev(gaps)
            result[MAX_REST_DAYS] = -float(max(gaps))
        else:
            result[GAP_STD_DEV] = 0.0
            result[MAX_REST_DAYS] = 0.0

        # 3. AVG_PREP_DAYS
        if mandatory_dates:
            prep_days = []
            for d in mandatory_dates:
                idx = bisect.bisect_left(sorted_dates, d)
                if idx > 0:
                    prep_days.append(float((d - sorted_dates[idx - 1]).days))
            result[AVG_PREP_DAYS] = statistics.mean(prep_days) if prep_days else 0.0
        else:
            result[AVG_PREP_DAYS] = 0.0

        # 4. DOUBLE_EXAM_DAYS (LLM only)
        result[DOUBLE_EXAM_DAYS] = -float(sum(1 for cnt in date_counts.values() if cnt >= 2))

        # 5. BUSIEST_WEEK_COUNT (LLM only)
        week_counts: dict = defaultdict(int)
        for d in dates_all:
            week_counts[d.isocalendar()[:2]] += 1
        result[BUSIEST_WEEK_COUNT] = -float(max(week_counts.values())) if week_counts else 0.0

        # 6. MANDATORY_CONSEC (LLM only)
        sorted_mandatory = sorted(mandatory_dates)
        consec = sum(
            1 for i in range(len(sorted_mandatory) - 1)
            if (sorted_mandatory[i + 1] - sorted_mandatory[i]).days == 1
        )
        result[MANDATORY_CONSEC] = -float(consec)

        # 7. B2B_EXAM_INCIDENCE
        cohort_dates = defaultdict(list)
        for a in schedule_dto.assignments:
            try:
                d = datetime.date.fromisoformat(a.date)
            except (ValueError, TypeError, AttributeError):
                continue
            day = d.toordinal()
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
        result[B2B_EXAM_INCIDENCE] = -float(b2b_count / len(all_gaps) if all_gaps else 0.0)

        # 8. DEPT_EXAM_CONCURRENCY
        dept_day_counts = defaultdict(int)
        for a in schedule_dto.assignments:
            try:
                d = datetime.date.fromisoformat(a.date)
            except (ValueError, TypeError, AttributeError):
                continue
            dept = a.course_id[:2]
            dept_day_counts[(dept, d)] += 1
        max_dept = max(dept_day_counts.values()) if dept_day_counts else 0.0
        result[DEPT_EXAM_CONCURRENCY] = -float(max_dept)

        # 9. INSTRUCTOR_EXAM_GAP
        prof_dates = defaultdict(list)
        for a in schedule_dto.assignments:
            try:
                d = datetime.date.fromisoformat(a.date)
            except (ValueError, TypeError, AttributeError):
                continue
            if a.instructor:
                prof_dates[a.instructor].append(d.toordinal())
        min_prof_gap = None
        for dates in prof_dates.values():
            if len(dates) < 2:
                continue
            dates.sort()
            for i in range(1, len(dates)):
                gap = dates[i] - dates[i - 1]
                if min_prof_gap is None or gap < min_prof_gap:
                    min_prof_gap = gap
        result[INSTRUCTOR_EXAM_GAP] = float(min_prof_gap if min_prof_gap is not None else 21.0)

        return result


class ExtendedFeatureComputerProvider:
    """Adapts ExtendedFeatureComputer to IExtensionScoreProvider.

    Wires the clustering feature set into the core engine's observer without
    the observer importing this module directly -- the caller that wants
    clustering features passes an instance of this class in.
    """

    def compute(self, dto) -> Dict[str, float]:
        return ExtendedFeatureComputer.compute(dto)

    def feature_ids(self) -> list:
        return list(ALL_EXTENDED_FEATURES)
