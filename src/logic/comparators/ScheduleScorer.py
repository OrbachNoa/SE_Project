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

from bisect import bisect_left
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
        obligatory, any_req = Metrics.build_cohort_index(
            courses, selected_programs
        )
        program_idx = Metrics.build_program_index(courses, selected_programs)
        elective_idx = Metrics.build_elective_index(courses, selected_programs)

        all_cohorts = set()
        for groups in obligatory.values():
            all_cohorts.update(groups)
        for groups in any_req.values():
            all_cohorts.update(groups)
        for groups in elective_idx.values():
            all_cohorts.update(groups)
        cohort_ids = {cohort: i for i, cohort in enumerate(all_cohorts)}

        all_programs = set()
        for programs in program_idx.values():
            all_programs.update(programs)
        program_ids = {program: i for i, program in enumerate(all_programs)}

        # Course objects are stable inside a worker process, so identity-keyed
        # lookup avoids repeating courseId string hashing in the hot path.
        self._course_data = {}
        for course in courses:
            cid = course.courseId
            obligatory_ids = tuple(cohort_ids[c] for c in obligatory.get(cid, ()))
            any_ids = tuple(cohort_ids[c] for c in any_req.get(cid, ()))
            elective_ids = tuple(cohort_ids[c] for c in elective_idx.get(cid, ()))
            program_id_tuple = tuple(program_ids[p] for p in program_idx.get(cid, ()))

            self._course_data[course] = (
                obligatory_ids,
                any_ids,
                elective_ids,
                program_id_tuple,
            )

        self._obligatory_dates = [[] for _ in range(len(cohort_ids))]
        self._any_dates = [[] for _ in range(len(cohort_ids))]

    def create_state(self):
        return _IncrementalScoreState(self._course_data, len(self._obligatory_dates), len(self._any_dates))

    def score(self, schedule) -> Dict[str, float]:
        """Return one score per criterion, higher is better for every entry.

        This is called once per generated schedule, often up to one million
        times. Keep it allocation-light and compute all criteria in one pass
        over the assignments instead of invoking five independent metric
        functions that each rebuild their own grouping dictionaries.
        """
        obligatory_dates = self._obligatory_dates
        any_dates = self._any_dates
        touched_obligatory = []
        touched_any = []
        span_bounds = {}
        elective_peak = 0
        elective_counts = {}
        max_per_day = 0
        program_day_counts = {}
        key_factor = 1_000_000
        course_data = self._course_data

        for assignment in schedule.assignments:
            course_data_for_assignment = course_data.get(assignment.course)
            if course_data_for_assignment is None:
                continue
            obligatory_groups, any_groups, elective_groups, programs = course_data_for_assignment
            day = assignment.date.toordinal()

            if obligatory_groups:
                moed = assignment.moed
                for group_id in obligatory_groups:
                    dates = obligatory_dates[group_id]
                    if not dates:
                        touched_obligatory.append(group_id)
                    dates.append(day)

                    span_key = (group_id, moed)
                    bounds = span_bounds.get(span_key)
                    if bounds is None:
                        span_bounds[span_key] = [day, day, 1]
                    else:
                        if day < bounds[0]:
                            bounds[0] = day
                        elif day > bounds[1]:
                            bounds[1] = day
                        bounds[2] += 1

            if any_groups:
                for group_id in any_groups:
                    dates = any_dates[group_id]
                    if not dates:
                        touched_any.append(group_id)
                    dates.append(day)

            if elective_groups:
                for group_id in elective_groups:
                    key = group_id * key_factor + day
                    count = elective_counts.get(key, 0) + 1
                    elective_counts[key] = count
                    if count > elective_peak:
                        elective_peak = count

            if programs:
                for program_id in programs:
                    key = program_id * key_factor + day
                    count = program_day_counts.get(key, 0) + 1
                    program_day_counts[key] = count
                    if count > max_per_day:
                        max_per_day = count

        min_mandatory_gap = None
        for group_id in touched_obligatory:
            dates = obligatory_dates[group_id]
            if len(dates) < 2:
                dates.clear()
                continue
            dates.sort()
            for i in range(1, len(dates)):
                gap = dates[i] - dates[i - 1]
                if min_mandatory_gap is None or gap < min_mandatory_gap:
                    min_mandatory_gap = gap
            dates.clear()

        avg_total = 0
        avg_count = 0
        for group_id in touched_any:
            dates = any_dates[group_id]
            if len(dates) < 2:
                dates.clear()
                continue
            dates.sort()
            for i in range(1, len(dates)):
                avg_total += dates[i] - dates[i - 1]
                avg_count += 1
            dates.clear()

        mandatory_span = 0
        for first_day, last_day, count in span_bounds.values():
            if count >= 2:
                span = last_day - first_day
                if span > mandatory_span:
                    mandatory_span = span

        return {
            MIN_MANDATORY_GAP: float(
                min_mandatory_gap if min_mandatory_gap is not None else 10_000
            ),
            AVG_ALL_COURSES_GAP: float(
                (avg_total / avg_count) if avg_count else 0.0
            ),
            # Fewer conflicts is better, so negate.
            ELECTIVE_CONFLICTS: -float(max(0, elective_peak - 1)),
            MANDATORY_SPAN: float(mandatory_span),
            # Fewer exams on the busiest day is better, so negate.
            MAX_EXAMS_PER_DAY: -float(max_per_day),
        }


class _GapTracker:
    def __init__(self, group_count: int):
        self._dates = [[] for _ in range(group_count)]
        self._gap_sum = [0] * group_count
        self._gap_count = [0] * group_count
        self._min_gap = [None] * group_count
        self._touched = set()

    def add(self, group_id: int, day: int):
        dates = self._dates[group_id]
        old_sum = self._gap_sum[group_id]
        old_count = self._gap_count[group_id]
        old_min = self._min_gap[group_id]

        index = bisect_left(dates, day)
        before = dates[index - 1] if index > 0 else None
        after = dates[index] if index < len(dates) else None

        delta_sum = 0
        if before is not None and after is not None:
            delta_sum -= after - before
        if before is not None:
            delta_sum += day - before
        if after is not None:
            delta_sum += after - day

        dates.insert(index, day)
        self._gap_sum[group_id] += delta_sum
        if len(dates) >= 2:
            self._gap_count[group_id] = len(dates) - 1
            self._min_gap[group_id] = min(
                dates[i] - dates[i - 1]
                for i in range(1, len(dates))
            )
        else:
            self._gap_count[group_id] = 0
            self._min_gap[group_id] = None

        self._touched.add(group_id)
        return (group_id, index, old_sum, old_count, old_min)

    def pop(self, undo):
        group_id, index, old_sum, old_count, old_min = undo
        dates = self._dates[group_id]
        dates.pop(index)
        self._gap_sum[group_id] = old_sum
        self._gap_count[group_id] = old_count
        self._min_gap[group_id] = old_min
        if not dates:
            self._touched.discard(group_id)

    def min_gap(self):
        best = None
        for group_id in self._touched:
            value = self._min_gap[group_id]
            if value is not None and (best is None or value < best):
                best = value
        return best

    def avg_gap(self):
        total = 0
        count = 0
        for group_id in self._touched:
            total += self._gap_sum[group_id]
            count += self._gap_count[group_id]
        return (total / count) if count else 0.0


class _IncrementalScoreState:
    def __init__(self, course_data: dict, obligatory_group_count: int, any_group_count: int):
        self._course_data = course_data
        self._mandatory_gaps = _GapTracker(obligatory_group_count)
        self._any_gaps = _GapTracker(any_group_count)
        self._span_bounds = {}
        self._elective_counts = {}
        self._elective_peak = 0
        self._program_day_counts = {}
        self._max_per_day = 0
        self._stack = []
        self._key_factor = 1_000_000

    def add_assignment(self, assignment) -> None:
        course_data = self._course_data.get(assignment.course)
        if course_data is None:
            self._stack.append(None)
            return

        obligatory_groups, any_groups, elective_groups, programs = course_data
        day = assignment.date.toordinal()
        undo = {
            "mandatory": [],
            "any": [],
            "span": [],
            "elective": [],
            "program": [],
            "elective_peak": self._elective_peak,
            "max_per_day": self._max_per_day,
        }

        for group_id in obligatory_groups:
            undo["mandatory"].append(self._mandatory_gaps.add(group_id, day))
            span_key = (group_id, assignment.moed)
            old_bounds = self._span_bounds.get(span_key)
            undo["span"].append((span_key, old_bounds))
            if old_bounds is None:
                self._span_bounds[span_key] = [day, day, 1]
            else:
                self._span_bounds[span_key] = [
                    min(old_bounds[0], day),
                    max(old_bounds[1], day),
                    old_bounds[2] + 1,
                ]

        for group_id in any_groups:
            undo["any"].append(self._any_gaps.add(group_id, day))

        key_factor = self._key_factor
        for group_id in elective_groups:
            key = group_id * key_factor + day
            old_count = self._elective_counts.get(key, 0)
            count = old_count + 1
            self._elective_counts[key] = count
            if count > self._elective_peak:
                self._elective_peak = count
            undo["elective"].append((key, old_count))

        for program_id in programs:
            key = program_id * key_factor + day
            old_count = self._program_day_counts.get(key, 0)
            count = old_count + 1
            self._program_day_counts[key] = count
            if count > self._max_per_day:
                self._max_per_day = count
            undo["program"].append((key, old_count))

        self._stack.append(undo)

    def pop_assignment(self) -> None:
        undo = self._stack.pop()
        if undo is None:
            return

        for item in reversed(undo["program"]):
            key, old_count = item
            if old_count:
                self._program_day_counts[key] = old_count
            else:
                self._program_day_counts.pop(key, None)
        self._max_per_day = undo["max_per_day"]

        for item in reversed(undo["elective"]):
            key, old_count = item
            if old_count:
                self._elective_counts[key] = old_count
            else:
                self._elective_counts.pop(key, None)
        self._elective_peak = undo["elective_peak"]

        for span_key, old_bounds in reversed(undo["span"]):
            if old_bounds is None:
                self._span_bounds.pop(span_key, None)
            else:
                self._span_bounds[span_key] = old_bounds

        for item in reversed(undo["any"]):
            self._any_gaps.pop(item)
        for item in reversed(undo["mandatory"]):
            self._mandatory_gaps.pop(item)

    def score(self) -> Dict[str, float]:
        min_mandatory_gap = self._mandatory_gaps.min_gap()
        mandatory_span = 0
        for first_day, last_day, count in self._span_bounds.values():
            if count >= 2:
                span = last_day - first_day
                if span > mandatory_span:
                    mandatory_span = span

        return {
            MIN_MANDATORY_GAP: float(
                min_mandatory_gap if min_mandatory_gap is not None else 10_000
            ),
            AVG_ALL_COURSES_GAP: float(self._any_gaps.avg_gap()),
            ELECTIVE_CONFLICTS: -float(max(0, self._elective_peak - 1)),
            MANDATORY_SPAN: float(mandatory_span),
            MAX_EXAMS_PER_DAY: -float(self._max_per_day),
        }
