"""Domain-layer metric functions for ranking complete exam schedules.

Each function takes a finished schedule plus the course list and returns one
number saying how good that schedule is on a single sort criterion. Which exams
count, and how they are grouped, follows the same rules as the threshold
checkers, so filtering and sorting always agree.

A "cohort" is one (program, year). Whether a course is obligatory or elective
is decided per program-entry.

ScheduleScorer mirrors the grouping logic below inline, for performance
(its hot path must not rebuild these dict-based indices per schedule) — keep
both in sync if a grouping key changes here.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from src.logic.indexes.SelectedProgramIndex import SelectedProgramIndex
from src.models.Enums import Requirement

# One (program, year).
Cohort = Tuple[str, int]
# One (program, year, semester).
SpanCohort = Tuple[str, int, object]


# ── Cohort eligibility (same rule the checkers use in prepare()) ────────────

def build_cohort_index(
    courses: list,
    selected_programs: Optional[list] = None,
    selected_index: Optional[SelectedProgramIndex] = None,
) -> Tuple[Dict[str, Set[Cohort]], Dict[str, Set[Cohort]]]:
    """Work out which cohorts each course belongs to, returning two indices.

    The first lists, for each course, the cohorts where it is obligatory; it
    feeds the min-gap metric (1) and the span metric (4). The second lists every
    cohort each course is in, regardless of requirement; it feeds the
    average-gap metric (2). When selected_programs is given, only those programs
    are counted.
    """
    obligatory, any_req, _ = build_metric_indices(
        courses,
        selected_programs,
        selected_index,
    )
    return obligatory, any_req


def build_span_index(
    courses: list,
    slots: Optional[list] = None,
    selected_programs: Optional[list] = None,
    selected_index: Optional[SelectedProgramIndex] = None,
) -> Dict[str, Set[SpanCohort]]:
    """Index for the span metric (4): the (program, year, semester) groups each
    course is obligatory in.

    Semester is part of the key because every semester has its own exam
    period (mirrors ExamSpanChecker.prepare(), which groups by
    (program, year, semester, moed) for the same reason). The moed is added
    later, by the span metric itself, from each exam's own moed.

    Pass real slots so semester correctly participates in the key — production
    callers (ScheduleScorer) must do this. Without slots, every group falls
    back to a single semester=None bucket, which only degrades to "no
    semester split" rather than failing; this fallback exists so existing
    single-semester callers don't need to construct full Slot objects.
    """
    selected_index = selected_index or SelectedProgramIndex(courses, selected_programs, slots)

    if not slots:
        obligatory, _ = build_cohort_index(courses, selected_programs, selected_index)
        return obligatory

    result: Dict[str, Set[SpanCohort]] = {}
    for slot in slots:
        course = slot.course
        for entry in selected_index.entries_for_slot(slot):
            if entry.requirement is not Requirement.OBLIGATORY:
                continue
            result.setdefault(course.courseId, set()).add(
                (entry.programId, entry.year, slot.semester)
            )
    return result


def build_elective_index(
    courses: list,
    selected_programs: Optional[list] = None,
    selected_index: Optional[SelectedProgramIndex] = None,
) -> Dict[str, Set[Cohort]]:
    """Index for the elective-conflict metric (3): the cohorts where each course
    is elective.

    Built once per run so the metric does not have to re-scan the course list on
    every schedule.
    """
    _, _, elective = build_metric_indices(
        courses,
        selected_programs,
        selected_index,
    )
    return elective


def build_elective_program_index(
    courses: list,
    selected_programs: Optional[list] = None,
    selected_index: Optional[SelectedProgramIndex] = None,
) -> Dict[str, Set[str]]:
    """Index for the elective-conflict metric (3): the programs where each
    course is elective, dropping the year.

    Mirrors ElectiveConflictCapChecker.prepare(), which groups by program only
    ("per program", not "per program and year") — years are ignored here on
    purpose so the metric agrees with the checker.
    """
    elective_cohorts = build_elective_index(courses, selected_programs, selected_index)
    return {
        course_id: {program_id for (program_id, _year) in cohorts}
        for course_id, cohorts in elective_cohorts.items()
    }


def build_program_index(
    courses: list,
    selected_programs: Optional[list] = None,
    selected_index: Optional[SelectedProgramIndex] = None,
) -> Dict[str, Set[str]]:
    """Index every course to the programs it belongs to.

    This is kept as a compatibility helper for older comparator and metric
    tests. Current production max-exams-per-day logic is global, but callers
    that still pass this index can continue to do so harmlessly.
    """
    selected_index = selected_index or SelectedProgramIndex(courses, selected_programs)
    result: Dict[str, Set[str]] = {}
    for course in courses:
        for entry in selected_index.entries_for_course(course.courseId):
            result.setdefault(course.courseId, set()).add(entry.programId)
    return result


def build_metric_indices(
    courses: list,
    selected_programs: Optional[list] = None,
    selected_index: Optional[SelectedProgramIndex] = None,
) -> Tuple[
    Dict[str, Set[Cohort]],
    Dict[str, Set[Cohort]],
    Dict[str, Set[Cohort]],
]:
    """Build all metric indices from one selected-program entry scan."""

    selected_index = selected_index or SelectedProgramIndex(courses, selected_programs)
    obligatory: Dict[str, Set[Cohort]] = {}
    any_req: Dict[str, Set[Cohort]] = {}
    elective: Dict[str, Set[Cohort]] = {}

    for course in courses:
        for entry in selected_index.entries_for_course(course.courseId):
            cohort = (entry.programId, entry.year)
            any_req.setdefault(course.courseId, set()).add(cohort)
            if entry.requirement is Requirement.OBLIGATORY:
                obligatory.setdefault(course.courseId, set()).add(cohort)
            elif entry.requirement is Requirement.ELECTIVE:
                elective.setdefault(course.courseId, set()).add(cohort)

    return obligatory, any_req, elective


def _dates_by_cohort(
    schedule,
    cohort_index: Dict[str, Set[Cohort]],
) -> Dict[Cohort, List[date]]:
    """Group this schedule's exam dates by cohort, using the given index.

    Used by the two gap metrics: pass the obligatory index for metric 1, the
    any-requirement index for metric 2.
    """
    by_cohort: Dict[Cohort, List[date]] = {}
    for a in schedule.assignments:
        cohorts = cohort_index.get(a.course.courseId)
        if not cohorts:
            continue
        for cohort in cohorts:
            by_cohort.setdefault(cohort, []).append(a.date)
    return by_cohort


# ── The five metrics ────────────────────────────────────────────────────────

def min_mandatory_gap(schedule, obligatory_cohorts: Dict[str, Set[Cohort]]) -> int:
    """Metric 1: the smallest gap, in days, between two mandatory exams in the
    same cohort. A bigger smallest-gap means more room, so higher is better.

    A cohort with fewer than two mandatory exams has no pair to clash and is
    skipped. If no cohort has a pair at all, the schedule gets a large sentinel
    so it ranks as best here — there is nothing to be cramped by.
    """
    best = None
    for dates in _dates_by_cohort(schedule, obligatory_cohorts).values():
        if len(dates) < 2:
            continue
        ordered = sorted(dates)
        for earlier, later in zip(ordered, ordered[1:]):
            gap = (later - earlier).days
            if best is None or gap < best:
                best = gap
    return best if best is not None else _NO_PAIR_SENTINEL


def avg_all_courses_gap(schedule, any_cohorts: Dict[str, Set[Cohort]]) -> float:
    """Metric 2: the average gap, in days, between back-to-back exams.

    Each cohort's exams are put in date order and the gaps between neighbours
    are measured; all those gaps are pooled into one average. More spacing is
    better, so higher is better. Returns 0.0 if there are no pairs.
    """
    total = 0
    count = 0
    for dates in _dates_by_cohort(schedule, any_cohorts).values():
        if len(dates) < 2:
            continue
        ordered = sorted(dates)
        for earlier, later in zip(ordered, ordered[1:]):
            total += (later - earlier).days
            count += 1
    return (total / count) if count else 0.0


def elective_conflict_pairs(
    schedule,
    elective_programs: Dict[str, Set[str]],
) -> int:
    """Metric 3: the worst per-program elective same-day pair-conflict total.

    For each program and each day, count how many of that program's elective
    exams fall on that day; n electives on one day make n*(n-1)//2 conflict
    pairs. The score is the total pairs for the worst program, summed across
    all its days. Mirrors ElectiveConflictCapChecker's own pair-conflict
    formula and program-only grouping (year is ignored on purpose), so
    filtering and sorting agree. Fewer is better, so callers negate it.

    Pass the index from build_elective_program_index (built once per run).
    """
    counts: Dict[Tuple[str, date], int] = {}
    for a in schedule.assignments:
        programs = elective_programs.get(a.course.courseId)
        if not programs:
            continue
        for program in programs:
            counts[(program, a.date)] = counts.get((program, a.date), 0) + 1

    per_program_total: Dict[str, int] = {}
    for (program, _day), n in counts.items():
        per_program_total[program] = per_program_total.get(program, 0) + n * (n - 1) // 2
    return max(per_program_total.values(), default=0)


def peak_elective_conflict(
    schedule,
    elective_cohorts: Dict[str, Set[Cohort]],
) -> int:
    """Compatibility metric: worst same-day elective pile-up minus one.

    The threshold checker still enforces pair-conflict caps separately. The
    sorting score uses this peak-minus-one metric.
    """
    counts: Dict[Tuple[Cohort, date], int] = {}
    for a in schedule.assignments:
        cohorts = elective_cohorts.get(a.course.courseId)
        if not cohorts:
            continue
        for cohort in cohorts:
            key = (cohort, a.date)
            counts[key] = counts.get(key, 0) + 1
    peak = max(counts.values(), default=1)
    return max(0, peak - 1)


def mandatory_span(schedule, obligatory_span_cohorts: Dict[str, Set[SpanCohort]]) -> int:
    """Metric 4: the widest spread, in days, from the first to the last
    mandatory exam within one (program, year, semester, moed) group.

    Pass the index from build_span_index; the moed of each group is taken
    here from each exam's own moed. Semester is part of the key (mirrors
    ExamSpanChecker) so two different semesters' exams never get merged into
    one span. More spread is better, so higher is better. Returns 0 when no
    group has at least two mandatory exams.
    """
    # The dates of each group's mandatory exams, keyed by (program, year, semester, moed).
    by_group: Dict[Tuple[str, int, object, object], List[date]] = {}
    for a in schedule.assignments:
        cohorts = obligatory_span_cohorts.get(a.course.courseId)
        if not cohorts:
            continue
        for cohort in cohorts:
            if len(cohort) == 2:
                program_id, year = cohort
                semester = None
            else:
                program_id, year, semester = cohort
            by_group.setdefault((program_id, year, semester, a.moed), []).append(a.date)

    best = 0
    for dates in by_group.values():
        if len(dates) < 2:
            continue
        span = (max(dates) - min(dates)).days
        if span > best:
            best = span
    return best


def max_exams_per_day(schedule, program_index: Optional[dict] = None) -> int:
    """Metric 5: the most exams scheduled on any single day, across the whole
    schedule.

    Mirrors MaxExamsPerDayChecker, which counts every exam on a date globally
    with no program grouping — so every assignment counts once toward its
    date, full stop. Fewer is better, so callers negate it.
    """
    counts: Dict[date, int] = {}
    for a in schedule.assignments:
        counts[a.date] = counts.get(a.date, 0) + 1
    return max(counts.values()) if counts else 0

# Sentinel for "no pair exists" in the min-gap metric: a schedule with nothing
# to clash should rank best. Large but finite so it stays a plain sortable number.
_NO_PAIR_SENTINEL = 10_000
