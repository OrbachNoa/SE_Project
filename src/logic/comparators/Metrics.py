"""Domain-layer metric functions for ranking complete exam schedules.

Each function takes a finished schedule plus the course list and returns one
number saying how good that schedule is on a single sort criterion. Which exams
count, and how they are grouped, follows the same rules as the threshold
checkers, so filtering and sorting always agree.

A "cohort" is one (program, year). Whether a course is obligatory or elective
is decided per program-entry.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from src.models.Enums import Requirement

# One (program, year).
Cohort = Tuple[str, int]
# One (program, year, moed).
MoedCohort = Tuple[str, int, object]


# ── Cohort eligibility (same rule the checkers use in prepare()) ────────────

def build_cohort_index(
    courses: list,
    selected_programs: Optional[list] = None,
) -> Tuple[Dict[str, Set[Cohort]], Dict[str, Set[Cohort]]]:
    """Work out which cohorts each course belongs to, returning two indices.

    The first lists, for each course, the cohorts where it is obligatory; it
    feeds the min-gap metric (1) and the span metric (4). The second lists every
    cohort each course is in, regardless of requirement; it feeds the
    average-gap metric (2). When selected_programs is given, only those programs
    are counted.
    """
    # Only these programs count; None means all of them.
    selected = set(selected_programs) if selected_programs else None
    obligatory: Dict[str, Set[Cohort]] = {}
    any_req: Dict[str, Set[Cohort]] = {}
    for course in courses:
        for entry in course.programEntries:
            if selected and entry.programId not in selected:
                continue
            cohort = (entry.programId, entry.year)
            any_req.setdefault(course.courseId, set()).add(cohort)
            if entry.requirement is Requirement.OBLIGATORY:
                obligatory.setdefault(course.courseId, set()).add(cohort)
    return obligatory, any_req


def build_span_index(
    courses: list,
    selected_programs: Optional[list] = None,
) -> Dict[str, Set[Cohort]]:
    """Index for the span metric (4): the obligatory cohorts each course is in.

    It only knows (program, year). The moed is added later, by the span metric
    itself, from each exam's own moed.
    """
    obligatory, _ = build_cohort_index(courses, selected_programs)
    return obligatory


def build_program_index(
    courses: list,
    selected_programs: Optional[list] = None,
) -> Dict[str, Set[str]]:
    """Index for the exams-per-day metric (5): the programs each course is in.

    Grouped by program, across all years and any requirement.
    """
    # Only these programs count; None means all of them.
    selected = set(selected_programs) if selected_programs else None
    course_programs: Dict[str, Set[str]] = {}
    for course in courses:
        programs = {
            entry.programId for entry in course.programEntries
            if not selected or entry.programId in selected
        }
        if programs:
            course_programs[course.courseId] = programs
    return course_programs


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


def peak_elective_conflict(
    schedule,
    courses: list,
    selected_programs: Optional[list] = None,
) -> int:
    """Metric 3: the worst single-day elective crowding, counted as the number
    of electives beyond the first.

    For each cohort and each day, count how many of that cohort's elective exams
    fall on that day; the score is the worst such pile-up anywhere, minus one.
    So one day with 4 electives (score 3) is rated worse than two days of 2
    (score 1) — the worst pile-up matters, not the total. Fewer is better, so
    callers negate it. Returns 0 when no day has more than one elective.
    """
    # Only these programs count; None means all of them.
    selected = set(selected_programs) if selected_programs else None
    # The cohorts where each course is elective, using the checker's rule.
    course_cohorts: Dict[str, Set[Cohort]] = {}
    for course in courses:
        for entry in course.programEntries:
            if selected and entry.programId not in selected:
                continue
            if entry.requirement is not Requirement.ELECTIVE:
                continue
            course_cohorts.setdefault(course.courseId, set()).add(
                (entry.programId, entry.year)
            )

    # How many of a cohort's electives fall on each day.
    crowding: Dict[Tuple[Cohort, date], int] = {}
    for a in schedule.assignments:
        cohorts = course_cohorts.get(a.course.courseId)
        if not cohorts:
            continue
        for cohort in cohorts:
            crowding[(cohort, a.date)] = crowding.get((cohort, a.date), 0) + 1

    peak = max(crowding.values(), default=0)
    return max(0, peak - 1)


def mandatory_span(schedule, obligatory_cohorts: Dict[str, Set[Cohort]]) -> int:
    """Metric 4: the widest spread, in days, from the first to the last
    mandatory exam within one (program, year, moed) group.

    Pass the obligatory index from build_span_index; the moed of each group is
    taken here from each exam's own moed. More spread is better, so higher is
    better. Returns 0 when no group has at least two mandatory exams.
    """
    # The dates of each group's mandatory exams, keyed by (program, year, moed).
    by_group: Dict[MoedCohort, List[date]] = {}
    for a in schedule.assignments:
        cohorts = obligatory_cohorts.get(a.course.courseId)
        if not cohorts:
            continue
        for (program_id, year) in cohorts:
            by_group.setdefault((program_id, year, a.moed), []).append(a.date)

    best = 0
    for dates in by_group.values():
        if len(dates) < 2:
            continue
        span = (max(dates) - min(dates)).days
        if span > best:
            best = span
    return best


def max_exams_per_day(schedule, course_programs: Dict[str, Set[str]]) -> int:
    """Metric 5: the most exams any single program has on any single day.

    Counted per program, across all years, one exam per course per day. Pass the
    index from build_program_index. Fewer is better, so callers negate it.
    """
    counts: Dict[Tuple[str, date], int] = {}
    for a in schedule.assignments:
        programs = course_programs.get(a.course.courseId)
        if not programs:
            continue
        for program in programs:
            counts[(program, a.date)] = counts.get((program, a.date), 0) + 1
    return max(counts.values()) if counts else 0

# Sentinel for "no pair exists" in the min-gap metric: a schedule with nothing
# to clash should rank best. Large but finite so it stays a plain sortable number.
_NO_PAIR_SENTINEL = 10_000