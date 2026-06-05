from datetime import date
import pytest

from src.models.Enums import EvalType, Semester, Moed, Requirement
from src.logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.checkers.MoedOrderChecker import MoedOrderChecker


# ---------------------------------------------------------------------------
# ProgramYearConflictChecker TC-CHK-001..005
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CHK-001: two OBLIGATORY courses from the same program AND same year on the same date must conflict.
# ===========================================================================
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
    checker = ProgramYearConflictChecker()
    checker.precompute_conflicts([existing.course, candidate.course])
    result = checker.check(candidate, schedule)
    # Assert
    assert result is True


# ===========================================================================
# TC-CHK-002: courses from different programs on the same date do NOT conflict.
# ===========================================================================
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
    checker = ProgramYearConflictChecker()
    checker.precompute_conflicts([existing.course, candidate.course])
    result = checker.check(candidate, schedule)
    # Assert
    assert result is False


# ===========================================================================
# TC-CHK-003: same program, DIFFERENT year, same date — no conflict
# ===========================================================================
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
    checker = ProgramYearConflictChecker()
    checker.precompute_conflicts([existing.course, candidate.course])
    result = checker.check(candidate, schedule)
    # Assert
    assert result is False


# ===========================================================================
# TC-CHK-004: two ELECTIVE courses in the same program/year on the same date are explicitly ALLOWED.
# ===========================================================================
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
    checker = ProgramYearConflictChecker()
    checker.precompute_conflicts([existing.course, candidate.course])
    result = checker.check(candidate, schedule)
    # Assert
    assert result is False


# ===========================================================================
# TC-CHK-005 — ProgramYearChecker: compares by date only
# ===========================================================================
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
    checker = ProgramYearConflictChecker()
    checker.precompute_conflicts([existing.course, candidate.course])
    result = checker.check(candidate, schedule)

    # Assert — date-only comparison must still trigger the conflict.
    assert result is True


# ---------------------------------------------------------------------------
# MoedOrderChecker TC-CHK-006..011
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CHK-006: a course with no existing assignments in the schedule does not conflict.
# ===========================================================================
def test_moed_order_checker_no_conflict_when_no_existing_assignment(
    make_course, make_assignment, empty_schedule
):
    # Arrange
    candidate = make_assignment(
        course=make_course(course_id="A"),
        exam_date=date(2026, 6, 10),
        moed=Moed.ALEPH
    )
    # Act
    result = MoedOrderChecker().check(candidate, empty_schedule)
    # Assert
    assert result is False


# ===========================================================================
# TC-CHK-007: assignments for other courses do not trigger a moed order conflict.
# ===========================================================================
def test_moed_order_checker_no_conflict_for_different_courses(
    make_course, make_assignment, empty_schedule
):
    # Arrange
    existing = make_assignment(
        course=make_course(course_id="A"),
        exam_date=date(2026, 6, 10),
        moed=Moed.ALEPH
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)

    candidate = make_assignment(
        course=make_course(course_id="B"),
        exam_date=date(2026, 6, 5),
        moed=Moed.BET
    )
    # Act
    result = MoedOrderChecker().check(candidate, schedule)
    # Assert
    assert result is False


# ===========================================================================
# TC-CHK-008: a course cannot be scheduled for the same Moed twice.
# ===========================================================================
def test_moed_order_checker_rejects_duplicate_moed(
    make_course, make_assignment, empty_schedule
):
    # Arrange
    course = make_course(course_id="A")
    existing = make_assignment(
        course=course,
        exam_date=date(2026, 6, 5),
        moed=Moed.ALEPH
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)

    candidate = make_assignment(
        course=course,
        exam_date=date(2026, 6, 10),
        moed=Moed.ALEPH
    )
    # Act
    result = MoedOrderChecker().check(candidate, schedule)
    # Assert
    assert result is True


# ===========================================================================
# TC-CHK-009: scheduling earlier moed before later moed is conflict-free (e.g. ALEPH then BET).
# ===========================================================================
def test_moed_order_checker_enforces_chronological_order(
    make_course, make_assignment, empty_schedule
):
    # Arrange
    course = make_course(course_id="A")
    existing = make_assignment(
        course=course,
        exam_date=date(2026, 6, 5),
        moed=Moed.ALEPH
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)

    candidate = make_assignment(
        course=course,
        exam_date=date(2026, 6, 10),
        moed=Moed.BET
    )
    # Act
    result = MoedOrderChecker().check(candidate, schedule)
    # Assert
    assert result is False


# ===========================================================================
# TC-CHK-010: a later moed scheduled on or before an earlier moed is a conflict.
# ===========================================================================
def test_moed_order_checker_rejects_reversed_moed_order(
    make_course, make_assignment, empty_schedule
):
    # Arrange
    course = make_course(course_id="A")
    existing = make_assignment(
        course=course,
        exam_date=date(2026, 6, 10),
        moed=Moed.ALEPH
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)

    candidate = make_assignment(
        course=course,
        exam_date=date(2026, 6, 5),
        moed=Moed.BET
    )
    # Act
    result = MoedOrderChecker().check(candidate, schedule)
    # Assert
    assert result is True


# ===========================================================================
# TC-CHK-011: different moeds for the same course on the exact same date is a conflict.
# ===========================================================================
def test_moed_order_checker_rejects_same_date_different_moed(
    make_course, make_assignment, empty_schedule
):
    # Arrange
    course = make_course(course_id="A")
    existing = make_assignment(
        course=course,
        exam_date=date(2026, 6, 5),
        moed=Moed.ALEPH
    )
    schedule = empty_schedule
    schedule.addAssignment(existing)

    candidate = make_assignment(
        course=course,
        exam_date=date(2026, 6, 5),
        moed=Moed.BET
    )
    # Act
    result = MoedOrderChecker().check(candidate, schedule)
    # Assert
    assert result is True
