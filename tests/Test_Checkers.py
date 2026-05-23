from datetime import date
import pytest

from src.models.enums import EvalType, Semester, Moed, Requirement
from src.logic.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.ExcludedDatesChecker import ExcludedDatesChecker
from src.logic.ExamPeriodBoundaryChecker import ExamPeriodBoundaryChecker


# ===========================================================================
# ProgramYearConflictChecker TC-CHK-001..005.
# ===========================================================================

# TC-CHK-001: two OBLIGATORY courses from the same program AND same year on the same date must conflict.
def test_program_year_checker_detects_same_program_same_year_same_date_conflict(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.OBLIGATORY,
    )
    existing = make_assignment(
        course=make_course(course_id="A", program_entries=[pe]),
        exam_date=date(2026, 6, 5),
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)

    candidate = make_assignment(
        course=make_course(course_id="B", program_entries=[pe]),
        exam_date=date(2026, 6, 5),
    )
    # Act
    result = ProgramYearConflictChecker().check(candidate, schedule)
    # Assert
    assert result is True


# TC-CHK-002: courses from different programs on the same date do NOT conflict.
def test_program_year_checker_no_conflict_for_different_programs(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe_a = make_program_entry(program_id="83101", year=2)
    pe_b = make_program_entry(program_id="83102", year=2)
    existing = make_assignment(
        course=make_course(course_id="A", program_entries=[pe_a]),
        exam_date=date(2026, 6, 5),
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)
    candidate = make_assignment(
        course=make_course(course_id="B", program_entries=[pe_b]),
        exam_date=date(2026, 6, 5),
    )
    # Act
    result = ProgramYearConflictChecker().check(candidate, schedule)
    # Assert
    assert result is False


# TC-CHK-003: same program, DIFFERENT year, same date — no conflict
def test_program_year_checker_no_conflict_for_different_years(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange — same program 83101, but years 1 and 2.
    pe_year1 = make_program_entry(program_id="83101", year=1)
    pe_year2 = make_program_entry(program_id="83101", year=2)
    existing = make_assignment(
        course=make_course(course_id="A", program_entries=[pe_year1]),
        exam_date=date(2026, 6, 5),
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)
    candidate = make_assignment(
        course=make_course(course_id="B", program_entries=[pe_year2]),
        exam_date=date(2026, 6, 5),
    )
    # Act
    result = ProgramYearConflictChecker().check(candidate, schedule)
    # Assert
    assert result is False


# TC-CHK-004: two ELECTIVE courses in the same program/year on the same date are explicitly ALLOWED.
def test_program_year_checker_no_conflict_between_two_electives(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange — both courses are ELECTIVE under the same program/year.
    pe = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.ELECTIVE,
    )
    existing = make_assignment(
        course=make_course(course_id="A", program_entries=[pe]),
        exam_date=date(2026, 6, 5),
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)
    candidate = make_assignment(
        course=make_course(course_id="B", program_entries=[pe]),
        exam_date=date(2026, 6, 5),
    )
    # Act
    result = ProgramYearConflictChecker().check(candidate, schedule)
    # Assert
    assert result is False


# TC-CHK-005 — ProgramYearChecker: compares by date only
def test_program_year_checker_uses_date_only_not_time(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange — same calendar day for two OBLIGATORY courses,
    # same program/year.
    pe = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.OBLIGATORY,
    )
    existing = make_assignment(
        course=make_course(course_id="A", program_entries=[pe]),
        exam_date=date(2026, 6, 5),
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)

    candidate = make_assignment(
        course=make_course(course_id="B", program_entries=[pe]),
        exam_date=date(2026, 6, 5),
    )

    # Act
    result = ProgramYearConflictChecker().check(candidate, schedule)

    # Assert — date-only comparison must still trigger the conflict.
    assert result is True


# ===========================================================================
# ExcludedDatesChecker — TC-CHK-006..007.
# ===========================================================================

# TC-CHK-006: Check that an exam cannot be scheduled on an excluded date.
def test_excluded_dates_checker_rejects_excluded_date(
    make_course, make_period, make_assignment, empty_schedule,
):
    # Arrange — exam period excludes June 3; candidate is on June 3.
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 30),
        excluded=[date(2026, 6, 3)],
    )
    candidate = make_assignment(
        course=make_course(),
        exam_date=date(2026, 6, 3),
        moed=Moed.ALEPH,
    )
    # accepts either a single period or a list — adjust if needed.
    checker = ExcludedDatesChecker([period])
    # Act
    result = checker.check(candidate, empty_schedule)
    # Assert
    assert result is True


# TC-CHK-007: an assignment on a date NOT in the excluded list is OK.
def test_excluded_dates_checker_accepts_non_excluded_date(
    make_course, make_period, make_assignment, empty_schedule,
):
    # Arrange — exam period excludes June 3; candidate is on June 5.
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 30),
        excluded=[date(2026, 6, 3)],
    )
    candidate = make_assignment(
        course=make_course(),
        exam_date=date(2026, 6, 5),
        moed=Moed.ALEPH,
    )
    checker = ExcludedDatesChecker([period])
    # Act
    result = checker.check(candidate, empty_schedule)
    # Assert
    assert result is False


# ===========================================================================
# ExamPeriodBoundaryChecker — TC-CHK-008..011
# ===========================================================================

# TC-CHK-008: Check that an exam before the exam period start date is marked as a conflict.
def test_period_boundary_checker_rejects_date_before_start(
    make_course, make_period, make_assignment, empty_schedule,
):
    # Arrange
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 30))
    candidate = make_assignment(
        course=make_course(),
        exam_date=date(2026, 5, 31),
        moed=Moed.ALEPH,
    )
    checker = ExamPeriodBoundaryChecker([period])
    # Act
    result = checker.check(candidate, empty_schedule)
    # Assert
    assert result is True


# TC-CHK-009: Check that a date after the exam period ends is rejected.
def test_period_boundary_checker_rejects_date_after_end(
    make_course, make_period, make_assignment, empty_schedule,
):
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 30))
    candidate = make_assignment(
        course=make_course(),
        exam_date=date(2026, 7, 1),
        moed=Moed.ALEPH,
    )
    checker = ExamPeriodBoundaryChecker([period])
    # Act
    result = checker.check(candidate, empty_schedule)
    # Assert
    assert result is True


# TC-CHK-010: The startDate itself is inclusive — a candidate exactly on the start of the period is NOT a conflict.
def test_period_boundary_checker_accepts_start_date_inclusive(
    make_course, make_period, make_assignment, empty_schedule,
):
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 30))
    candidate = make_assignment(
        course=make_course(),
        exam_date=date(2026, 6, 1),
        moed=Moed.ALEPH,
    )
    checker = ExamPeriodBoundaryChecker([period])
    # Act
    result = checker.check(candidate, empty_schedule)
    # Assert
    assert result is False


# TC-CHK-011: The endDate itself is inclusive — a candidate exactly on
# the end of the period is NOT a conflict.
def test_period_boundary_checker_accepts_end_date_inclusive(
    make_course, make_period, make_assignment, empty_schedule,
):
    # Arrange — period 01-06..30-06; candidate 30-06 (end boundary).
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 30))
    candidate = make_assignment(
        course=make_course(),
        exam_date=date(2026, 6, 30),
        moed=Moed.ALEPH,
    )
    checker = ExamPeriodBoundaryChecker([period])
    # Act
    result = checker.check(candidate, empty_schedule)
    # Assert
    assert result is False