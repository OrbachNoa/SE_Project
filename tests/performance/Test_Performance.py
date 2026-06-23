from datetime import date, timedelta
import time
import pytest

from src.models.Enums import EvalType, Semester, Moed, Requirement
from src.logic.Scheduler import Scheduler
from src.logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.checkers.MoedOrderChecker import MoedOrderChecker
from src.logic.SlotBuilder import SlotBuilder
from src.logic.observers.CollectingScheduleObserver import CollectingScheduleObserver

# ---------------------------------------------------------------------------
# Helper functions and constants used in the tests.
# ---------------------------------------------------------------------------

# The maximum time allowed to run the algorithm (30 seconds).
MAX_EXECUTION_SECONDS = 30.0

# ===========================================================================
# Helper: Create the standard checkers and give them the exam dates.
# ===========================================================================
def _default_checkers(periods, courses):
    py_checker = ProgramYearConflictChecker()
    py_checker.precompute_conflicts(courses)
    return [
        py_checker,
        MoedOrderChecker(),
    ]


# ===========================================================================
# Functions to build fake data for the tests.
# ===========================================================================
def _build_courses(
    make_course, make_program_entry,
    *, num_programs, courses_per_program,
):
    """
    Creates a list of courses for testing. It mixes mandatory and 
    elective courses across different years to simulate a real university load.
    """
    # Valid program codes we use for testing.
    program_codes = ["83101", "83102", "83103", "83104", "83105"][:num_programs]

    courses = []
    course_id_counter = 10000
    for code in program_codes:
        for i in range(courses_per_program):
            # Alternate year and requirement to spread the load.
            year = (i % 2) + 1                              # year 1 or 2
            requirement = (
                Requirement.OBLIGATORY if i % 3 != 0
                else Requirement.ELECTIVE
            )
            pe = make_program_entry(
                program_id=code,
                year=year,
                semester=Semester.FALL,
                requirement=requirement,
            )
            courses.append(make_course(
                course_id=str(course_id_counter),
                name=f"Course {course_id_counter}",
                instructor=f"Dr. Instructor {course_id_counter}",
                evaluation=EvalType.EXAM,
                program_entries=[pe],
            ))
            course_id_counter += 1
    return courses


def _build_period(
    make_period,
    *, start, end, num_excluded,
):
    """
    Creates one exam period with specific start and end dates, 
    and adds some excluded dates (days with no exams) evenly inside it.
    """
    total_days = (end - start).days + 1
    excluded = []
    if num_excluded > 0:
        # Spread the empty days evenly, but keep the first and last day available.
        stride = max(1, (total_days - 2) // num_excluded)
        for i in range(num_excluded):
            offset = (i + 1) * stride
            if offset < total_days - 1:
                excluded.append(start + timedelta(days=offset))
    return make_period(
        semester=Semester.FALL,
        moed=Moed.ALEPH,
        start=start,
        end=end,
        excluded=excluded,
    )


# ===========================================================================
# TC-PER-001 — Normal load: 5 programs, 10 courses each, 30 days.
# Test that the system finishes in under 30 seconds for a normal amount of courses.
# ===========================================================================
@pytest.mark.performance
def test_typical_load_under_30_seconds(make_course, make_program_entry,
                                                make_period):
    # Arrange — Create 50 exam courses and a 30-day test period.
    courses = _build_courses(
        make_course, make_program_entry,
        num_programs=5, courses_per_program=10,
    )
    period = _build_period(
        make_period,
        start=date(2026, 6, 1), end=date(2026, 6, 30),
        num_excluded=0,
    )
    slots = SlotBuilder([period]).build(courses)
    scheduler = Scheduler(_default_checkers([period], courses))
    observer = CollectingScheduleObserver()

    # Act — Run the scheduler and measure how much time it takes.
    start_time = time.perf_counter()
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    elapsed = time.perf_counter() - start_time

    # Assert — Check that it took less than 30 seconds.
    assert elapsed < MAX_EXECUTION_SECONDS, (
        f"Typical load (5 programs × 10 courses, 30-day period) took "
        f"{elapsed:.2f}s, exceeding the {MAX_EXECUTION_SECONDS}s SRS §5.1 "
        f"performance budget."
    )
    # Sanity check — the run actually produced something (not just
    # returning early on an unrelated error).
    assert schedules is not None


# ===========================================================================
# TC-PER-002 — Heavy load: 5 programs, 20 courses each, 60 days, 10 excluded dates.
# Test that the system finishes in under 30 seconds for a heavy amount of courses.
# ===========================================================================
@pytest.mark.performance
def test_maximum_load_under_30_seconds(make_course, make_program_entry,
                                                make_period):
    # Arrange — Create 100 exam courses and a 60-day period with 10 empty days.
    courses = _build_courses(
        make_course, make_program_entry,
        num_programs=5, courses_per_program=20,
    )
    period = _build_period(
        make_period,
        start=date(2026, 6, 1), end=date(2026, 7, 30),
        num_excluded=10,
    )
    slots = SlotBuilder([period]).build(courses)
    scheduler = Scheduler(_default_checkers([period], courses))
    observer = CollectingScheduleObserver()

    # Act — Run the scheduler and measure how much time it takes.
    start_time = time.perf_counter()
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    elapsed = time.perf_counter() - start_time

    # Assert — Check that it took less than 30 seconds. If it fails, the code needs to be faster.
    assert elapsed < MAX_EXECUTION_SECONDS, (
        f"Maximum load (5 programs × 20 courses, 60-day period, "
        f"10 excluded dates) took {elapsed:.2f}s, exceeding the "
        f"{MAX_EXECUTION_SECONDS}s SRS §5.1 performance budget. "
        f"Optimisation required — see SCRUM-45."
    )
    assert schedules is not None


# ---------------------------------------------------------------------------
# Threshold checkers performance scenarios — imports added for this section only.
# ---------------------------------------------------------------------------
import random

from src.models.ExamSchedule import ExamSchedule, ExamAssignment
from src.logic.checkers.config.CheckerFactory import build_checkers
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.comparators.ScheduleScorer import (
    ScheduleScorer,
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
)
from src.application.dto.ScheduleDTO import ScheduleDTO
from src.application.state.ScheduleReranker import rerank
from src.logic.clustering.ClusteringService import ClusteringService
from src.logic.clustering.ClusterConfig import ClusterConfig


# ===========================================================================
# TC-PER-003 — Scoring 1000 schedules with ScheduleScorer must stay under
# 2 seconds, since score() runs once per generated schedule in the real
# worker (potentially up to a million times per run).
# ===========================================================================
@pytest.mark.performance
def test_schedule_scorer_scores_1000_schedules_under_2_seconds(
    make_course, make_program_entry,
):
    # Arrange — 10 courses across 2 programs, shared by every schedule below.
    # ScheduleScorer caches its course index by object identity, so the same
    # course objects must be reused, not rebuilt, for each schedule.
    courses = _build_courses(
        make_course, make_program_entry,
        num_programs=2, courses_per_program=5,
    )
    scorer = ScheduleScorer(courses)
    schedules = []
    for i in range(1000):
        schedule = ExamSchedule()
        for j, course in enumerate(courses):
            exam_date = date(2026, 6, 1) + timedelta(days=(i + j) % 28)
            schedule.addAssignment(
                ExamAssignment(course=course, date=exam_date, moed=Moed.ALEPH, semester=Semester.FALL)
            )
        schedules.append(schedule)

    # Act — measure only the scoring loop, not the schedule setup above.
    start_time = time.perf_counter()
    for schedule in schedules:
        scorer.score(schedule)
    elapsed = time.perf_counter() - start_time

    # Assert
    assert elapsed < 2.0, (
        f"Scoring 1000 schedules took {elapsed:.2f}s, exceeding the 2.0s "
        f"budget for ScheduleScorer.score()."
    )


# ===========================================================================
# TC-PER-004 — Reranking 10000 already-scored schedules must stay under
# 1 second: ScheduleReranker only ever sorts numbers already computed at
# generation time, with no metric recomputation involved.
# ===========================================================================
@pytest.mark.performance
def test_reranker_sorts_10000_schedules_under_1_second():
    # Arrange — 10,000 pre-scored DTOs with varying values on two criteria.
    schedules = [
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: float(i % 50),
            MANDATORY_SPAN: float((i * 7) % 100),
        })
        for i in range(10_000)
    ]

    # Act
    start_time = time.perf_counter()
    result = rerank(schedules, [MIN_MANDATORY_GAP, MANDATORY_SPAN])
    elapsed = time.perf_counter() - start_time

    # Assert
    assert elapsed < 1.0, (
        f"Reranking 10000 schedules took {elapsed:.2f}s, exceeding the "
        f"1.0s budget for ScheduleReranker.rerank()."
    )
    assert len(result) == 10_000


# ===========================================================================
# TC-PER-005 — A realistic load (5 programs x 10 courses, 30-day period)
# with every threshold checker active must still respond in under
# 5 seconds, capped at a production-sized result window (max_results) —
# the same cap SchedulingService uses to keep the UI responsive.
# ===========================================================================
@pytest.mark.performance
def test_scheduler_with_all_threshold_checkers_under_5_seconds(
    make_course, make_program_entry, make_period,
):
    # Arrange — same scale as TC-PER-001, but with every threshold checker
    # turned on via build_checkers (min gap, elective cap, span, day cap).
    courses = _build_courses(
        make_course, make_program_entry,
        num_programs=5, courses_per_program=10,
    )
    period = _build_period(
        make_period,
        start=date(2026, 6, 1), end=date(2026, 6, 30),
        num_excluded=0,
    )
    slots = SlotBuilder([period]).build(courses)
    config = ConstraintsConfig(
        min_gap_obligatory=1,
        min_gap_any=1,
        elective_conflict_cap=5,
        exam_span=1,
        max_exams_per_day=10,
    )
    checkers = build_checkers(config, courses, None, slots)
    scheduler = Scheduler(checkers)
    observer = CollectingScheduleObserver()

    # Act
    start_time = time.perf_counter()
    scheduler.generateSchedules(slots, observer, max_results=2000)
    elapsed = time.perf_counter() - start_time

    # Assert
    assert elapsed < 5.0, (
        f"Scheduler with all threshold checkers active took {elapsed:.2f}s for "
        f"2000 results, exceeding the 5.0s budget."
    )
    assert len(observer.schedules) > 0


# ===========================================================================
# TC-PER-006 — The complete clustering pipeline (fit + cluster, including
# automatic K selection) on 500 schedules must stay under 3 seconds.
# ===========================================================================
@pytest.mark.performance
def test_clustering_service_pipeline_on_500_schedules_under_3_seconds():
    # Arrange — 500 schedules with randomized but realistic-range scores.
    rng = random.Random(42)
    schedules = [
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: float(rng.randint(0, 30)),
            AVG_ALL_COURSES_GAP: float(rng.randint(0, 20)),
            ELECTIVE_CONFLICTS: float(-rng.randint(0, 5)),
            MANDATORY_SPAN: float(rng.randint(0, 60)),
            MAX_EXAMS_PER_DAY: float(-rng.randint(1, 6)),
        })
        for _ in range(500)
    ]
    service = ClusteringService(ClusterConfig.default())

    # Act
    start_time = time.perf_counter()
    service.fit(schedules)
    result = service.cluster()
    elapsed = time.perf_counter() - start_time

    # Assert
    assert elapsed < 3.0, (
        f"Clustering 500 schedules (fit + cluster) took {elapsed:.2f}s, "
        f"exceeding the 3.0s budget."
    )
    assert result.k > 0
    assert len(result.clusters) > 0