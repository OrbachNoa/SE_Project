"""Builds the sort comparators once per run and scores each schedule.

The worker builds one ScheduleScorer from the course list and selected programs,
then calls score(schedule) on every schedule it finds. The resulting dict of
{criterion_id: float} is stored on the DTO, so the runtime re-rank only ever
sorts numbers we already computed.

Convention: every score is higher-is-better. The two metrics that are naturally
lower-is-better (elective conflicts, exams-per-day) are negated here, so the
re-rank can always sort descending with no per-criterion direction flag.

Grouping keys (which exams count, and how they're grouped per criterion) must
match the corresponding threshold checker exactly, so filtering and sorting
agree — Metrics.py's index builders are the canonical definitions; this module
mirrors their grouping inline for performance instead of calling them per
schedule.
"""
from __future__ import annotations

from bisect import bisect_left
from typing import Dict, Optional

from src.logic.comparators import Metrics
from src.logic.indexes.SelectedProgramIndex import SelectedProgramIndex


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

LOWER_IS_BETTER_CRITERIA = (
    ELECTIVE_CONFLICTS,
    MAX_EXAMS_PER_DAY,
)


def _lower_is_better_score(value: float) -> float:
    """Store lower-is-better sort values as higher-is-better scores."""
    return -float(value)


class ScheduleScorer:
    """Computes all sort scores for a schedule. Built once per run."""

    def __init__(
        self,
        courses: list,
        selected_programs: Optional[list] = None,
        selected_index: Optional[SelectedProgramIndex] = None,
        slots: Optional[list] = None,
    ):
        # Build every index once, the same way the checkers prepare once.
        selected_index = selected_index or SelectedProgramIndex(courses, selected_programs, slots)
        obligatory, any_req, _ = Metrics.build_metric_indices(
            courses, selected_programs, selected_index
        )
        # Program-only (year dropped), mirroring ElectiveConflictCapChecker.
        elective_programs = Metrics.build_elective_program_index(
            courses, selected_programs, selected_index
        )
        # (program, year, semester) groups, mirroring ExamSpanChecker. Pass
        # slots so semester actually participates -- without them this falls
        # back to one semester=None bucket per (program, year).
        span_cohorts = Metrics.build_span_index(
            courses, slots, selected_programs, selected_index
        )

        # Gap criteria (min-gap, avg-gap) share one cohort-id space, (program, year).
        all_cohorts = set()
        for groups in obligatory.values():
            all_cohorts.update(groups)
        for groups in any_req.values():
            all_cohorts.update(groups)
        cohort_ids = {cohort: i for i, cohort in enumerate(all_cohorts)}

        # Elective conflicts use a separate, program-only id space.
        all_programs = set()
        for programs in elective_programs.values():
            all_programs.update(programs)
        program_ids = {program: i for i, program in enumerate(all_programs)}
        self._elective_program_count = len(program_ids)

        # Mandatory span uses its own (program, year, semester) id space,
        # distinct from the gap cohorts above -- span is checker-scoped by
        # semester (req 2.4/3.4) while min-gap is not (req 2.1/3.1).
        all_span_groups = set()
        for groups in span_cohorts.values():
            all_span_groups.update(groups)
        span_group_ids = {group: i for i, group in enumerate(all_span_groups)}

        # Course objects are stable inside a worker process, so identity-keyed
        # lookup avoids repeating courseId string hashing in the hot path.
        self._course_data = {}
        for course in courses:
            cid = course.courseId
            obligatory_ids = tuple(cohort_ids[c] for c in obligatory.get(cid, ()))
            any_ids = tuple(cohort_ids[c] for c in any_req.get(cid, ()))
            elective_program_ids = tuple(program_ids[p] for p in elective_programs.get(cid, ()))
            span_group_id_tuple = tuple(span_group_ids[g] for g in span_cohorts.get(cid, ()))

            self._course_data[course] = (
                obligatory_ids,
                any_ids,
                elective_program_ids,
                span_group_id_tuple,
            )

        self._obligatory_dates = [[] for _ in range(len(cohort_ids))]
        self._any_dates = [[] for _ in range(len(cohort_ids))]

    def create_state(self):
        return _IncrementalScoreState(
            self._course_data,
            len(self._obligatory_dates),
            len(self._any_dates),
        )

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
        elective_counts = {}
        elective_pair_totals = [0] * self._elective_program_count
        day_counts = {}
        max_per_day = 0
        key_factor = 1_000_000
        course_data = self._course_data

        for assignment in schedule.assignments:
            # Counted globally, unconditionally, before any course-data lookup --
            # MaxExamsPerDayChecker rejects on every exam on the date, not just
            # ones tied to a tracked obligatory/any/elective cohort.
            day = assignment.date.toordinal()
            day_count = day_counts.get(day, 0) + 1
            day_counts[day] = day_count
            if day_count > max_per_day:
                max_per_day = day_count

            course_data_for_assignment = course_data.get(assignment.course)
            if course_data_for_assignment is None:
                continue
            obligatory_groups, any_groups, elective_programs, span_groups = course_data_for_assignment

            if obligatory_groups:
                for group_id in obligatory_groups:
                    dates = obligatory_dates[group_id]
                    if not dates:
                        touched_obligatory.append(group_id)
                    dates.append(day)

            if span_groups:
                moed = assignment.moed
                for span_group_id in span_groups:
                    span_key = (span_group_id, moed)
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

            if elective_programs:
                for program_id in elective_programs:
                    key = program_id * key_factor + day
                    old_count = elective_counts.get(key, 0)
                    elective_counts[key] = old_count + 1
                    elective_pair_totals[program_id] += old_count

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

        # Elective conflicts are pair-conflicts per program, matching
        # ElectiveConflictCapChecker: adding the n-th same-day elective creates
        # n-1 new conflicting pairs, accumulated above as old_count.
        elective_conflicts = max(elective_pair_totals, default=0)

        return {
            MIN_MANDATORY_GAP: float(
                min_mandatory_gap if min_mandatory_gap is not None else 10_000
            ),
            AVG_ALL_COURSES_GAP: float(
                (avg_total / avg_count) if avg_count else 0.0
            ),
            # Fewer conflicts is better, so negate.
            ELECTIVE_CONFLICTS: _lower_is_better_score(elective_conflicts),
            MANDATORY_SPAN: float(mandatory_span),
            # Fewer exams on the busiest day is better, so negate.
            MAX_EXAMS_PER_DAY: _lower_is_better_score(max_per_day),
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
    def __init__(self, course_data: dict, obligatory_group_count: int, any_group_count: int,
                 allowed_window_size: int = 21, has_slots: bool = False):
        self._course_data = course_data
        self._mandatory_gaps = _GapTracker(obligatory_group_count)
        self._any_gaps = _GapTracker(any_group_count)
        self._span_bounds = {}
        self._elective_counts = {}
        self._elective_pair_totals = {}
        self._day_counts = {}
        self._max_per_day = 0
        self._stack = []
        self._key_factor = 1_000_000
        self._allowed_window_size = allowed_window_size
        self._has_slots = has_slots

    def add_assignment(self, assignment) -> None:
        # Counted globally, unconditionally, before any course-data lookup --
        # mirrors MaxExamsPerDayChecker, which never skips an exam regardless
        # of obligatory/any/elective membership.
        day = assignment.date.toordinal()
        old_day_count = self._day_counts.get(day, 0)
        new_day_count = old_day_count + 1
        self._day_counts[day] = new_day_count
        old_max_per_day = self._max_per_day
        if new_day_count > self._max_per_day:
            self._max_per_day = new_day_count

        course_data = self._course_data.get(assignment.course)
        if course_data is None:
            self._stack.append({
                "day": day,
                "old_day_count": old_day_count,
                "old_max_per_day": old_max_per_day,
                "no_course_data": True,
            })
            return

        obligatory_groups, any_groups, elective_programs, span_groups = course_data
        undo = {
            "day": day,
            "old_day_count": old_day_count,
            "old_max_per_day": old_max_per_day,
            "mandatory": [],
            "any": [],
            "span": [],
            "elective": [],
        }

        for group_id in obligatory_groups:
            undo["mandatory"].append(self._mandatory_gaps.add(group_id, day))

        if span_groups:
            moed = assignment.moed
            for span_group_id in span_groups:
                span_key = (span_group_id, moed)
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

        # Pair-conflict total per program: removing the n-th elective from a
        # date shifts that date's contribution from n*(n-1)//2 to
        # (n-1)*(n-2)//2, so the running total must shift by that delta.
        key_factor = self._key_factor
        for program_id in elective_programs:
            key = program_id * key_factor + day
            old_count = self._elective_counts.get(key, 0)
            new_count = old_count + 1
            self._elective_counts[key] = new_count
            delta = new_count * (new_count - 1) // 2 - old_count * (old_count - 1) // 2
            old_total = self._elective_pair_totals.get(program_id, 0)
            self._elective_pair_totals[program_id] = old_total + delta
            undo["elective"].append((key, old_count, program_id, old_total))

        self._stack.append(undo)

    def pop_assignment(self) -> None:
        undo = self._stack.pop()

        if undo["old_day_count"]:
            self._day_counts[undo["day"]] = undo["old_day_count"]
        else:
            self._day_counts.pop(undo["day"], None)
        self._max_per_day = undo["old_max_per_day"]

        if undo.get("no_course_data"):
            return

        for key, old_count, program_id, old_total in reversed(undo["elective"]):
            if old_count:
                self._elective_counts[key] = old_count
            else:
                self._elective_counts.pop(key, None)
            if old_total:
                self._elective_pair_totals[program_id] = old_total
            else:
                self._elective_pair_totals.pop(program_id, None)

        for item in reversed(undo["any"]):
            self._any_gaps.pop(item)

        for span_key, old_bounds in reversed(undo["span"]):
            if old_bounds is None:
                self._span_bounds.pop(span_key, None)
            else:
                self._span_bounds[span_key] = old_bounds

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

        scores = {
            MIN_MANDATORY_GAP: float(
                min_mandatory_gap if min_mandatory_gap is not None else (self._allowed_window_size if self._has_slots else 10_000)
            ),
            AVG_ALL_COURSES_GAP: float(self._any_gaps.avg_gap()),
            ELECTIVE_CONFLICTS: _lower_is_better_score(
                max(self._elective_pair_totals.values(), default=0)
            ),
            MANDATORY_SPAN: float(mandatory_span),
            MAX_EXAMS_PER_DAY: _lower_is_better_score(self._max_per_day),
        }
        return scores
