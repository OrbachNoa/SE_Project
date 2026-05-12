from datetime import date, timedelta
import time
import pytest

from exam_scheduler.enums import EvalType, Semester, Moed, Requirement
from exam_scheduler.scheduler import Scheduler
from exam_scheduler.checkers import (
    ProgramYearConflictChecker,
    ExcludedDatesChecker,
    ExamPeriodBoundaryChecker,
)


# The maximum time allowed to run the algorithm (30 seconds).
MAX_EXECUTION_SECONDS = 30.0


# Helper: Create the standard checkers and give them the exam dates.
def _default_checkers(periods):
    return [
        ProgramYearConflictChecker(),
        ExcludedDatesChecker(periods),
        ExamPeriodBoundaryChecker(periods),
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
# ===========================================================================

# TC-PER-001: # Test that the system finishes in under 30 seconds for a normal amount of courses.
@pytest.mark.performance
def test_per_001_typical_load_under_30_seconds(make_course, make_program_entry,
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
    scheduler = Scheduler(
        courses=courses,
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )

    # Act — Run the scheduler and measure how much time it takes.
    start_time = time.perf_counter()
    schedules = scheduler.generateAllSchedules()
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
# ===========================================================================

# TC-PER-002: Verify performance under maximum expected load.
@pytest.mark.performance
def test_per_002_maximum_load_under_30_seconds(make_course, make_program_entry,
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
    scheduler = Scheduler(
        courses=courses,
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )

    # Act — Run the scheduler and measure how much time it takes.
    start_time = time.perf_counter()
    schedules = scheduler.generateAllSchedules()
    elapsed = time.perf_counter() - start_time

    # Assert — Check that it took less than 30 seconds. If it fails, the code needs to be faster.
    assert elapsed < MAX_EXECUTION_SECONDS, (
        f"Maximum load (5 programs × 20 courses, 60-day period, "
        f"10 excluded dates) took {elapsed:.2f}s, exceeding the "
        f"{MAX_EXECUTION_SECONDS}s SRS §5.1 performance budget. "
        f"Optimisation required — see SCRUM-45."
    )
    assert schedules is not None