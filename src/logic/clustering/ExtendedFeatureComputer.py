from __future__ import annotations

import bisect
import datetime
import statistics
from collections import defaultdict
from typing import Dict

from src.application.dto.ScheduleDTO import ScheduleDTO

AVG_MOED_GAP       = "AVG_MOED_GAP"        # f_0
MIN_MOED_GAP       = "MIN_MOED_GAP"         # f_1
GAP_STD_DEV        = "GAP_STD_DEV"          # f_2 — negated
AVG_PREP_DAYS      = "AVG_PREP_DAYS"        # f_3
DOUBLE_EXAM_DAYS   = "DOUBLE_EXAM_DAYS"     # f_4 — negated
BUSIEST_WEEK_COUNT = "BUSIEST_WEEK_COUNT"   # f_5 — negated
MAX_REST_DAYS      = "MAX_REST_DAYS"        # f_6
MANDATORY_CONSEC   = "MANDATORY_CONSEC"     # f_7 — negated

ALL_EXTENDED_FEATURES = (
    AVG_MOED_GAP, MIN_MOED_GAP, GAP_STD_DEV, AVG_PREP_DAYS,
    DOUBLE_EXAM_DAYS, BUSIEST_WEEK_COUNT, MAX_REST_DAYS, MANDATORY_CONSEC,
)


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

        # f_0: AVG_MOED_GAP, f_1: MIN_MOED_GAP
        moed_gaps = [
            abs((moeds["BETH"] - moeds["ALEPH"]).days)
            for moeds in dates_by_course.values()
            if "ALEPH" in moeds and "BETH" in moeds
        ]
        result[AVG_MOED_GAP] = statistics.mean(moed_gaps) if moed_gaps else 0.0
        result[MIN_MOED_GAP] = float(min(moed_gaps)) if moed_gaps else 0.0

        # f_2: GAP_STD_DEV (negated), f_6: MAX_REST_DAYS
        sorted_dates = sorted(dates_set)
        if len(sorted_dates) >= 2:
            gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days
                    for i in range(len(sorted_dates) - 1)]
            result[GAP_STD_DEV] = -statistics.pstdev(gaps)
            result[MAX_REST_DAYS] = float(max(gaps))
        else:
            result[GAP_STD_DEV] = 0.0
            result[MAX_REST_DAYS] = 0.0

        # f_3: AVG_PREP_DAYS — mean gap-before-exam for mandatory exams
        if mandatory_dates:
            prep_days = []
            for d in mandatory_dates:
                idx = bisect.bisect_left(sorted_dates, d)
                if idx > 0:
                    prep_days.append(float((d - sorted_dates[idx - 1]).days))
            result[AVG_PREP_DAYS] = statistics.mean(prep_days) if prep_days else 0.0
        else:
            result[AVG_PREP_DAYS] = 0.0

        # f_4: DOUBLE_EXAM_DAYS (negated)
        result[DOUBLE_EXAM_DAYS] = -float(sum(1 for cnt in date_counts.values() if cnt >= 2))

        # f_5: BUSIEST_WEEK_COUNT (negated) — counts assignments, not unique dates
        week_counts: dict = defaultdict(int)
        for d in dates_all:
            week_counts[d.isocalendar()[:2]] += 1
        result[BUSIEST_WEEK_COUNT] = -float(max(week_counts.values())) if week_counts else 0.0

        # f_7: MANDATORY_CONSEC (negated)
        sorted_mandatory = sorted(mandatory_dates)
        consec = sum(
            1 for i in range(len(sorted_mandatory) - 1)
            if (sorted_mandatory[i + 1] - sorted_mandatory[i]).days == 1
        )
        result[MANDATORY_CONSEC] = -float(consec)

        return result
