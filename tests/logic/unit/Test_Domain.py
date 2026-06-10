from datetime import date
import pytest

from src.models.Enums import EvalType, Semester, Moed, Requirement
from src.models.Domain import (
    Course,
    ProgramEntry,
    ExamPeriod,
    ExamAssignment,
    ExamSchedule,
)


# ---------------------------------------------------------------------------
# Course.hasExam() — TC-DOM-001..003
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-DOM-001: Check that a course with an Exam is marked as a course that needs scheduling.
# ===========================================================================
def test_course_has_exam_returns_true_for_exam_eval(make_course):
    # Arrange
    c = make_course(evaluation=EvalType.EXAM)
    # Act
    result = c.hasExam()
    # Assert
    assert result is True

# ===========================================================================
# TC-DOM-002: A Course whose evaluation is EvalType.PROJECT must report
# hasExam() == False — projects are not scheduled.
# ===========================================================================
def test_course_has_exam_returns_false_for_project_eval(make_course):
    # Arrange
    c = make_course(evaluation=EvalType.PROJECT)
    # Act
    result = c.hasExam()
    # Assert
    assert result is False

# ===========================================================================
# TC-DOM-003: A Course whose evaluation is EvalType.ATTENDANCE must
# report hasExam() == False — attendance-only courses are not scheduled.
# ===========================================================================
def test_course_has_exam_returns_false_for_attendance_eval(make_course):
    # Arrange
    c = make_course(evaluation=EvalType.ATTENDANCE)
    # Act
    result = c.hasExam()
    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# ExamPeriod.availableDates — TC-DOM-004..007
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-DOM-004: For a period with a normal date range and some excluded
# dates, availableDates must return every date in [start, end]
# except the excluded ones.
# ===========================================================================
def test_get_available_dates_excludes_excluded_dates(make_period):
    # Arrange — 5-day period with June 3 excluded.
    period = make_period(
        start=date(2026, 6, 1),
        end=date(2026, 6, 5),
        excluded=[date(2026, 6, 3)],
    )
    # Act
    dates = period.availableDates
    # Assert — exactly four dates, June 3 missing.
    assert dates == [
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 4),
        date(2026, 6, 5),
    ]

# ===========================================================================
# TC-DOM-005: When every date in [start, end] is excluded,
# availableDates must return an empty list.
# ===========================================================================
def test_get_available_dates_returns_empty_when_all_excluded(make_period):
    # Arrange — 2-day period, both days excluded.
    period = make_period(
        start=date(2026, 6, 1),
        end=date(2026, 6, 2),
        excluded=[date(2026, 6, 1), date(2026, 6, 2)],
    )
    # Act
    dates = period.availableDates
    # Assert
    assert dates == []


# ===========================================================================
# TC-DOM-006: A two-day period is the minimum valid range.
# Verify the smallest legal period returns both dates when neither is excluded.
# ===========================================================================
def test_get_available_dates_returns_both_days_for_two_day_period(make_period):
    # Arrange — smallest legal period: start strictly less than end.
    period = make_period(
        start=date(2026, 6, 10),
        end=date(2026, 6, 11),
        excluded=[],
    )
    # Act
    dates = period.availableDates
    # Assert
    assert dates == [date(2026, 6, 10), date(2026, 6, 11)]


# ===========================================================================
# TC-DOM-007: An ExamPeriod whose startDate is NOT strictly less than its endDate must be rejected at construction.
# This covers both start == end and start > end
# ===========================================================================
@pytest.mark.parametrize("start,end", [
    (date(2026, 6, 10), date(2026, 6, 10)),  # start == end (invalid)
    (date(2026, 6, 30), date(2026, 6, 1)),   # start  > end (invalid)
])
def test_exam_period_rejects_non_strict_start_before_end(start, end):
    # Arrange + Act + Assert — constructor must raise.
    with pytest.raises(ValueError):
        ExamPeriod(
            semester=Semester.FALL,
            moed=Moed.ALEPH,
            start_date=start,
            end_date=end,
            excluded_dates=[],
        )


# ---------------------------------------------------------------------------
# ExamSchedule.addAssignment() and getByDate() — TC-DOM-008..010
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-DOM-008: Check that addAssignment() adds an assignment to the schedule.
# ===========================================================================
def test_add_assignment_stores_assignment(empty_schedule, make_assignment):
    # Arrange
    schedule = empty_schedule
    assignment = make_assignment()
    # Act
    schedule.addAssignment(assignment)
    # Assert
    assert len(schedule.assignments) == 1
    assert schedule.assignments[0] is assignment


# ===========================================================================
# TC-DOM-009: getByDate() returns only the assignments whose date matches the requested date.
# ===========================================================================
def test_get_by_date_returns_only_matching_assignments(
    empty_schedule, make_course, make_assignment,
):
    # Arrange — three assignments on three different dates; two share
    # the same target date (June 5).
    schedule = empty_schedule
    target = date(2026, 6, 5)
    schedule.addAssignment(make_assignment(
        course=make_course(course_id="A"), exam_date=target))
    schedule.addAssignment(make_assignment(
        course=make_course(course_id="B"), exam_date=date(2026, 6, 6)))
    schedule.addAssignment(make_assignment(
        course=make_course(course_id="C"), exam_date=target))
    # Act
    result = schedule.getByDate(target)
    # Assert — two assignments, both on the target date.
    assert len(result) == 2
    assert all(a.date == target for a in result)


# ===========================================================================
# TC-DOM-010: getByDate() on an empty schedule must return an empty list
# ===========================================================================
def test_get_by_date_on_empty_schedule_returns_empty_list(empty_schedule):
    # Arrange + Act
    result = empty_schedule.getByDate(date(2026, 6, 1))
    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# ProgramEntry - TC-DOM-011..013
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-DOM-011: A ProgramEntry must accept years 1..4 inclusive.
# ===========================================================================
@pytest.mark.parametrize("good_year", [1, 2, 3, 4])
def test_program_entry_accepts_year_in_range(good_year, make_program_entry):
    # Arrange + Act — should not raise.
    entry = make_program_entry(year=good_year)

    # Assert
    assert entry.year == good_year

# ===========================================================================
# TC-DOM-012: Values outside {1,2,3,4} must be rejected.
# ===========================================================================
@pytest.mark.parametrize("bad_year", [0, 5, -1, 10])
def test_program_entry_rejects_year_out_of_range(bad_year, make_program_entry):
    # Arrange + Act + Assert
    with pytest.raises(ValueError):
        make_program_entry(year=bad_year)


# ===========================================================================
# TC-DOM-013: A ProgramEntry program ID must be a
# 5-digit string. Strings of other lengths or with non-digits must be rejected.
# ===========================================================================
@pytest.mark.parametrize("bad_code", [
    "8310",      # too short
    "831011",    # too long
    "8310A",     # non-digit
    "",          # empty
])
def test_program_entry_rejects_invalid_program_id(bad_code, make_program_entry):
    # Arrange + Act + Assert
    with pytest.raises(ValueError):
        make_program_entry(program_id=bad_code)


# ---------------------------------------------------------------------------
# Semester & Moed & EvalType Enums - TC-DOM-014..016
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-DOM-014: Only FALL, SPRI, SUMM exist; nothing else.
# ===========================================================================
def test_semester_enum_has_exactly_three_members():
    # Arrange + Act
    names = {m.name for m in Semester}

    # Assert
    assert names == {"FALL", "SPRI", "SUMM"}


# ===========================================================================
# TC-DOM-015: Only ALEPH, BET, GIMEL exist.
# ===========================================================================
def test_moed_enum_has_exactly_three_members():
    # Arrange + Act
    names = {m.name for m in Moed}

    # Assert
    assert names == {"ALEPH", "BET", "GIMEL"}


# ===========================================================================
# TC-DOM-016: EvalType must contain exactly EXAM,
# PROJECT, ATTENDANCE — and no others.
# ===========================================================================
def test_eval_type_enum_has_exactly_three_members():
    # Arrange + Act
    names = {m.name for m in EvalType}

    # Assert
    assert names == {"EXAM", "PROJECT", "ATTENDANCE"}