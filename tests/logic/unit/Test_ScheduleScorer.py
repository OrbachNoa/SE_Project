from datetime import date
import pytest

from src.models.Enums import Requirement, Moed
from src.logic.comparators.ScheduleScorer import (
    ScheduleScorer,
    _IncrementalScoreState,
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
)


# ---------------------------------------------------------------------------
# ScheduleScorer.score TC-SCO-001..007
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-SCO-001: ScheduleScorer.score — an empty schedule yields the default
# value for every one of the five criteria.
# ===========================================================================
def test_score_returns_defaults_for_empty_schedule(empty_schedule):
    # Arrange
    scorer = ScheduleScorer([])

    # Act
    result = scorer.score(empty_schedule)

    # Assert
    assert result == {
        MIN_MANDATORY_GAP: 10_000.0,
        AVG_ALL_COURSES_GAP: 0.0,
        ELECTIVE_CONFLICTS: 0.0,
        MANDATORY_SPAN: 0.0,
        MAX_EXAMS_PER_DAY: 0.0,
    }


# ===========================================================================
# TC-SCO-002: ScheduleScorer.score — two mandatory exams from the same
# program 5 days apart score MIN_MANDATORY_GAP = 5.0.
# ===========================================================================
def test_score_min_mandatory_gap_for_two_mandatory_exams(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 6)))

    # Act
    result = scorer.score(schedule)

    # Assert
    assert result[MIN_MANDATORY_GAP] == 5.0


# ===========================================================================
# TC-SCO-003: ScheduleScorer.score — gaps of 4 and 6 days within the same
# cohort average to AVG_ALL_COURSES_GAP = 5.0.
# ===========================================================================
def test_score_avg_all_courses_gap_for_three_exams(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b, course_c])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 11)))

    # Act
    result = scorer.score(schedule)

    # Assert
    assert result[AVG_ALL_COURSES_GAP] == 5.0


# ===========================================================================
# TC-SCO-004: ScheduleScorer.score — three electives piled on the same day
# score ELECTIVE_CONFLICTS = -2.0 (peak 3, minus one, negated).
# ===========================================================================
def test_score_elective_conflicts_for_three_electives_same_day(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C")]
    scorer = ScheduleScorer(courses)

    schedule = empty_schedule
    for course in courses:
        schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 5)))

    # Act
    result = scorer.score(schedule)

    # Assert
    assert result[ELECTIVE_CONFLICTS] == -2.0


# ===========================================================================
# TC-SCO-005: ScheduleScorer.score — two mandatory exams in the same
# (program, year, moed) group from June 1 to June 11 score
# MANDATORY_SPAN = 10.0.
# ===========================================================================
def test_score_mandatory_span_for_two_exams_in_same_group(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1), moed=Moed.ALEPH))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 11), moed=Moed.ALEPH))

    # Act
    result = scorer.score(schedule)

    # Assert
    assert result[MANDATORY_SPAN] == 10.0


# ===========================================================================
# TC-SCO-006: ScheduleScorer.score — three exams from the same program on
# the same day score MAX_EXAMS_PER_DAY = -3.0 (negated count).
# ===========================================================================
def test_score_max_exams_per_day_for_three_same_program_same_day(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    course_a = make_course(course_id="A", program_entries=[make_program_entry(program_id="83101", year=2)])
    course_b = make_course(course_id="B", program_entries=[make_program_entry(program_id="83101", year=3)])
    course_c = make_course(course_id="C", program_entries=[make_program_entry(program_id="83101", year=4)])
    scorer = ScheduleScorer([course_a, course_b, course_c])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 5)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 5)))

    # Act
    result = scorer.score(schedule)

    # Assert
    assert result[MAX_EXAMS_PER_DAY] == -3.0


# ===========================================================================
# TC-SCO-007: ScheduleScorer.score — a realistic schedule mixing two
# programs with mandatory and elective courses keeps every criterion on
# its documented side of zero.
# ===========================================================================
def test_score_signs_are_correct_for_realistic_mixed_schedule(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe_mandatory_p1 = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective_p1 = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    pe_mandatory_p2 = make_program_entry(program_id="83102", year=3, requirement=Requirement.OBLIGATORY)

    mandatory_1 = make_course(course_id="M1", program_entries=[pe_mandatory_p1])
    mandatory_2 = make_course(course_id="M2", program_entries=[pe_mandatory_p1])
    elective_1 = make_course(course_id="E1", program_entries=[pe_elective_p1])
    elective_2 = make_course(course_id="E2", program_entries=[pe_elective_p1])
    mandatory_3 = make_course(course_id="M3", program_entries=[pe_mandatory_p2])
    courses = [mandatory_1, mandatory_2, elective_1, elective_2, mandatory_3]
    scorer = ScheduleScorer(courses)

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=mandatory_1, exam_date=date(2026, 6, 1), moed=Moed.ALEPH))
    schedule.addAssignment(make_assignment(course=mandatory_2, exam_date=date(2026, 6, 5), moed=Moed.ALEPH))
    schedule.addAssignment(make_assignment(course=elective_1, exam_date=date(2026, 6, 2), moed=Moed.ALEPH))
    schedule.addAssignment(make_assignment(course=elective_2, exam_date=date(2026, 6, 2), moed=Moed.ALEPH))
    schedule.addAssignment(make_assignment(course=mandatory_3, exam_date=date(2026, 6, 1), moed=Moed.ALEPH))

    # Act
    result = scorer.score(schedule)

    # Assert — higher-is-better criteria stay non-negative, the two
    # negated (fewer-is-better) criteria stay non-positive.
    assert result[MIN_MANDATORY_GAP] > 0
    assert result[AVG_ALL_COURSES_GAP] > 0
    assert result[ELECTIVE_CONFLICTS] <= 0
    assert result[MANDATORY_SPAN] >= 0
    assert result[MAX_EXAMS_PER_DAY] <= 0


# ---------------------------------------------------------------------------
# _IncrementalScoreState TC-SCO-008..012
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-SCO-008: _IncrementalScoreState.score — building the same two
# mandatory exams incrementally yields MIN_MANDATORY_GAP = 5.0, matching
# ScheduleScorer.score() on the equivalent schedule.
# ===========================================================================
def test_incremental_state_min_mandatory_gap_matches_batch_score(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])
    assignment_a = make_assignment(course=course_a, exam_date=date(2026, 6, 1))
    assignment_b = make_assignment(course=course_b, exam_date=date(2026, 6, 6))

    schedule = empty_schedule
    schedule.addAssignment(assignment_a)
    schedule.addAssignment(assignment_b)
    expected = scorer.score(schedule)

    # Act
    state = scorer.create_state()
    state.add_assignment(assignment_a)
    state.add_assignment(assignment_b)
    result = state.score()

    # Assert
    assert result[MIN_MANDATORY_GAP] == 5.0
    assert result == expected


# ===========================================================================
# TC-SCO-009: _IncrementalScoreState — adding then popping one assignment
# restores the exact pre-add score (sentinel gap, everything else zero).
# ===========================================================================
def test_incremental_state_pop_assignment_restores_previous_score(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    scorer = ScheduleScorer([course])
    state = scorer.create_state()
    baseline = state.score()
    assignment = make_assignment(course=course, exam_date=date(2026, 6, 1))

    # Act
    state.add_assignment(assignment)
    state.pop_assignment()
    result = state.score()

    # Assert
    assert result == baseline
    assert result == {
        MIN_MANDATORY_GAP: 10_000.0,
        AVG_ALL_COURSES_GAP: 0.0,
        ELECTIVE_CONFLICTS: 0.0,
        MANDATORY_SPAN: 0.0,
        MAX_EXAMS_PER_DAY: 0.0,
    }


# ===========================================================================
# TC-SCO-010: _IncrementalScoreState — three add_assignment calls followed
# by three pop_assignment calls fully unwind the undo stack back to the
# initial empty score.
# ===========================================================================
def test_incremental_state_three_adds_and_pops_restore_initial_score(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b, course_c])
    state = scorer.create_state()
    baseline = state.score()

    assignment_a = make_assignment(course=course_a, exam_date=date(2026, 6, 1), moed=Moed.ALEPH)
    assignment_b = make_assignment(course=course_b, exam_date=date(2026, 6, 6), moed=Moed.ALEPH)
    assignment_c = make_assignment(course=course_c, exam_date=date(2026, 6, 16), moed=Moed.BET)

    # Act
    state.add_assignment(assignment_a)
    state.add_assignment(assignment_b)
    state.add_assignment(assignment_c)
    state.pop_assignment()
    state.pop_assignment()
    state.pop_assignment()
    result = state.score()

    # Assert
    assert result == baseline


# ===========================================================================
# TC-SCO-011: _IncrementalScoreState — placing three mandatory exams one at
# a time updates MIN_MANDATORY_GAP to the smallest gap seen so far after
# each addition.
# ===========================================================================
def test_incremental_state_min_mandatory_gap_updates_after_each_add(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b, course_c])
    state = scorer.create_state()
    assignment_a = make_assignment(course=course_a, exam_date=date(2026, 6, 1))
    assignment_b = make_assignment(course=course_b, exam_date=date(2026, 6, 6))
    assignment_c = make_assignment(course=course_c, exam_date=date(2026, 6, 16))

    # Act — the first exam has no peer yet, so the gap is still the sentinel.
    state.add_assignment(assignment_a)
    # Assert
    assert state.score()[MIN_MANDATORY_GAP] == 10_000.0

    # Act — the second exam forms a 5-day gap with the first.
    state.add_assignment(assignment_b)
    # Assert
    assert state.score()[MIN_MANDATORY_GAP] == 5.0

    # Act — the third exam forms a wider 10-day gap, so the minimum stays 5.
    state.add_assignment(assignment_c)
    # Assert
    assert state.score()[MIN_MANDATORY_GAP] == 5.0


# ===========================================================================
# TC-SCO-012: _IncrementalScoreState — a state populated with electives
# only has no mandatory cohort, so MIN_MANDATORY_GAP stays at the sentinel
# and MANDATORY_SPAN stays at 0.0.
# ===========================================================================
def test_incremental_state_electives_only_has_no_mandatory_score(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])
    state = scorer.create_state()

    # Act
    state.add_assignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    state.add_assignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))
    result = state.score()

    # Assert
    assert result[MIN_MANDATORY_GAP] == 10_000.0
    assert result[MANDATORY_SPAN] == 0.0
