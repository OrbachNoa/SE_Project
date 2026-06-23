from datetime import date
import pytest

from src.models.Enums import Requirement, Moed
from src.logic.comparators.Metrics import (
    build_cohort_index,
    build_span_index,
    build_program_index,
    build_elective_index,
    min_mandatory_gap,
    avg_all_courses_gap,
    peak_elective_conflict,
    mandatory_span,
    max_exams_per_day,
)


# ---------------------------------------------------------------------------
# build_cohort_index TC-MET-001..003
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-001: build_cohort_index — an obligatory course appears in the
# obligatory index AND the any-requirement index for its cohort.
# ===========================================================================
def test_build_cohort_index_obligatory_course_in_both_indices(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])

    # Act
    obligatory, any_req = build_cohort_index([course])

    # Assert
    assert obligatory["A"] == {("83101", 2)}
    assert any_req["A"] == {("83101", 2)}


# ===========================================================================
# TC-MET-002: build_cohort_index — an elective course appears in the
# any-requirement index but is absent from the obligatory index.
# ===========================================================================
def test_build_cohort_index_elective_course_excluded_from_obligatory(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course = make_course(course_id="A", program_entries=[pe])

    # Act
    obligatory, any_req = build_cohort_index([course])

    # Assert
    assert "A" not in obligatory
    assert any_req["A"] == {("83101", 2)}


# ===========================================================================
# TC-MET-003: build_cohort_index — a program absent from selected_programs
# is ignored in both the obligatory and any-requirement indices.
# ===========================================================================
def test_build_cohort_index_ignores_unselected_program(
    make_course, make_program_entry,
):
    # Arrange
    pe_selected = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_unselected = make_program_entry(program_id="83102", year=3, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe_selected, pe_unselected])

    # Act
    obligatory, any_req = build_cohort_index([course], selected_programs=["83101"])

    # Assert
    assert obligatory["A"] == {("83101", 2)}
    assert any_req["A"] == {("83101", 2)}


# ---------------------------------------------------------------------------
# build_span_index TC-MET-004
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-004: build_span_index — returns the same obligatory cohorts as the
# first element of build_cohort_index, with no elective entries mixed in.
# ===========================================================================
def test_build_span_index_returns_only_obligatory_cohorts(
    make_course, make_program_entry,
):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=3, requirement=Requirement.ELECTIVE)
    obligatory_course = make_course(course_id="A", program_entries=[pe_obligatory])
    elective_course = make_course(course_id="B", program_entries=[pe_elective])
    courses = [obligatory_course, elective_course]

    # Act
    expected_obligatory, _ = build_cohort_index(courses)
    span_index = build_span_index(courses)

    # Assert
    assert span_index == expected_obligatory


# ---------------------------------------------------------------------------
# build_program_index TC-MET-005
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-005: build_program_index — a course taught under two different
# programs appears for both programs in the index.
# ===========================================================================
def test_build_program_index_course_in_two_programs(
    make_course, make_program_entry,
):
    # Arrange
    pe_a = make_program_entry(program_id="83101", year=2)
    pe_b = make_program_entry(program_id="83102", year=2)
    course = make_course(course_id="A", program_entries=[pe_a, pe_b])

    # Act
    index = build_program_index([course])

    # Assert
    assert index["A"] == {"83101", "83102"}


# ---------------------------------------------------------------------------
# build_elective_index TC-MET-006
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-006: build_elective_index — an obligatory course is absent from
# the index, while an elective course is present with its cohort.
# ===========================================================================
def test_build_elective_index_includes_only_elective_entries(
    make_course, make_program_entry,
):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    obligatory_course = make_course(course_id="A", program_entries=[pe_obligatory])
    elective_course = make_course(course_id="B", program_entries=[pe_elective])

    # Act
    index = build_elective_index([obligatory_course, elective_course])

    # Assert
    assert "A" not in index
    assert index["B"] == {("83101", 2)}


# ---------------------------------------------------------------------------
# min_mandatory_gap TC-MET-007..009
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-007: min_mandatory_gap — with three mandatory exams in the same
# cohort spaced 5 and 10 days apart, the smaller of the two gaps wins.
# ===========================================================================
def test_min_mandatory_gap_returns_smallest_gap_among_three_exams(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    obligatory_cohorts, _ = build_cohort_index([course_a, course_b, course_c])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 6)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 16)))

    # Act
    result = min_mandatory_gap(schedule, obligatory_cohorts)

    # Assert
    assert result == 5


# ===========================================================================
# TC-MET-008: min_mandatory_gap — with no pair of mandatory exams in any
# cohort, the function returns the no-pair sentinel (10_000).
# ===========================================================================
def test_min_mandatory_gap_returns_sentinel_when_no_pair_exists(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    obligatory_cohorts, _ = build_cohort_index([course])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    # Act
    result = min_mandatory_gap(schedule, obligatory_cohorts)

    # Assert
    assert result == 10_000


# ===========================================================================
# TC-MET-009: min_mandatory_gap — an elective exam scheduled between two
# mandatory exams does not shrink the computed gap.
# ===========================================================================
def test_min_mandatory_gap_ignores_elective_exams(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe_obligatory])
    course_b = make_course(course_id="B", program_entries=[pe_elective])
    course_c = make_course(course_id="C", program_entries=[pe_obligatory])
    obligatory_cohorts, _ = build_cohort_index([course_a, course_b, course_c])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 3)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 11)))

    # Act
    result = min_mandatory_gap(schedule, obligatory_cohorts)

    # Assert — the elective exam on June 3 is excluded, so the only gap
    # considered is between the two mandatory exams (10 days), not 2.
    assert result == 10


# ---------------------------------------------------------------------------
# avg_all_courses_gap TC-MET-010..012
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-010: avg_all_courses_gap — two consecutive gaps of 4 and 6 days
# average to 5.0.
# ===========================================================================
def test_avg_all_courses_gap_returns_average_of_two_gaps(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    _, any_cohorts = build_cohort_index([course_a, course_b, course_c])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 11)))

    # Act
    result = avg_all_courses_gap(schedule, any_cohorts)

    # Assert
    assert result == 5.0


# ===========================================================================
# TC-MET-011: avg_all_courses_gap — with no pair of exams to compare, the
# function returns 0.0.
# ===========================================================================
def test_avg_all_courses_gap_returns_zero_when_no_pair_exists(empty_schedule):
    # Arrange
    _, any_cohorts = build_cohort_index([])
    schedule = empty_schedule

    # Act
    result = avg_all_courses_gap(schedule, any_cohorts)

    # Assert
    assert result == 0.0


# ===========================================================================
# TC-MET-012: avg_all_courses_gap — unlike min_mandatory_gap, an elective
# exam is included in the gap calculation.
# ===========================================================================
def test_avg_all_courses_gap_includes_elective_courses(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe_obligatory])
    course_b = make_course(course_id="B", program_entries=[pe_elective])
    _, any_cohorts = build_cohort_index([course_a, course_b])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))

    # Act
    result = avg_all_courses_gap(schedule, any_cohorts)

    # Assert — if the elective exam were excluded, course A would have no
    # pair and the result would be 0.0 instead of 4.0.
    assert result == 4.0


# ---------------------------------------------------------------------------
# peak_elective_conflict TC-MET-013..015
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-013: peak_elective_conflict — four electives piled on the same day
# score 3 (the peak minus one), not the number of conflicting pairs.
# ===========================================================================
def test_peak_elective_conflict_returns_peak_minus_one_for_four_same_day(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C", "D")]
    elective_cohorts = build_elective_index(courses)

    schedule = empty_schedule
    for course in courses:
        schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 5)))

    # Act
    result = peak_elective_conflict(schedule, elective_cohorts)

    # Assert
    assert result == 3


# ===========================================================================
# TC-MET-014: peak_elective_conflict — electives spread over distinct days
# never pile up, so the score is 0.
# ===========================================================================
def test_peak_elective_conflict_returns_zero_when_electives_on_different_days(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    elective_cohorts = build_elective_index([course_a, course_b, course_c])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 2)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 3)))

    # Act
    result = peak_elective_conflict(schedule, elective_cohorts)

    # Assert
    assert result == 0


# ===========================================================================
# TC-MET-015: peak_elective_conflict — two days with 3 electives each score
# 2 (the worst single-day pile-up), not the total of 6 electives.
# ===========================================================================
def test_peak_elective_conflict_returns_worst_peak_not_total(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    day_one_courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C")]
    day_two_courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("D", "E", "F")]
    elective_cohorts = build_elective_index(day_one_courses + day_two_courses)

    schedule = empty_schedule
    for course in day_one_courses:
        schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))
    for course in day_two_courses:
        schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 2)))

    # Act
    result = peak_elective_conflict(schedule, elective_cohorts)

    # Assert
    assert result == 2


# ---------------------------------------------------------------------------
# mandatory_span TC-MET-016..018
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-016: mandatory_span — mandatory exams from June 1 to June 11 in the
# same (program, year, moed) group span 10 days.
# ===========================================================================
def test_mandatory_span_returns_ten_days_for_first_to_eleventh_june(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    obligatory_cohorts = build_span_index([course_a, course_b])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1), moed=Moed.ALEPH))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 11), moed=Moed.ALEPH))

    # Act
    result = mandatory_span(schedule, obligatory_cohorts)

    # Assert
    assert result == 10


# ===========================================================================
# TC-MET-017: mandatory_span — a single mandatory exam in the group has no
# second date to span, so the result is 0.
# ===========================================================================
def test_mandatory_span_returns_zero_for_single_exam(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    obligatory_cohorts = build_span_index([course])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1), moed=Moed.ALEPH))

    # Act
    result = mandatory_span(schedule, obligatory_cohorts)

    # Assert
    assert result == 0


# ===========================================================================
# TC-MET-018: mandatory_span — two groups in the same program/year but
# different moeds (ALEPH vs BET) have their spans computed independently.
# ===========================================================================
def test_mandatory_span_computes_independently_per_moed_group(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    course_d = make_course(course_id="D", program_entries=[pe])
    obligatory_cohorts = build_span_index([course_a, course_b, course_c, course_d])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1), moed=Moed.ALEPH))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 3), moed=Moed.ALEPH))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 10), moed=Moed.BET))
    schedule.addAssignment(make_assignment(course=course_d, exam_date=date(2026, 6, 12), moed=Moed.BET))

    # Act
    result = mandatory_span(schedule, obligatory_cohorts)

    # Assert — both groups span 2 days; if the moed split were ignored, the
    # combined span from June 1 to June 12 would be 11.
    assert result == 2


# ---------------------------------------------------------------------------
# max_exams_per_day TC-MET-019..021
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-MET-019: max_exams_per_day — three exams from the same program on the
# same day count as 3.
# ===========================================================================
def test_max_exams_per_day_returns_three_for_same_day_same_program(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    course_a = make_course(course_id="A", program_entries=[make_program_entry(program_id="83101", year=2)])
    course_b = make_course(course_id="B", program_entries=[make_program_entry(program_id="83101", year=3)])
    course_c = make_course(course_id="C", program_entries=[make_program_entry(program_id="83101", year=4)])
    program_index = build_program_index([course_a, course_b, course_c])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 5)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 5)))

    # Act
    result = max_exams_per_day(schedule, program_index)

    # Assert
    assert result == 3


# ===========================================================================
# TC-MET-020: max_exams_per_day — with exams spread across several days,
# the result is the busiest day's count, not the overall total.
# ===========================================================================
def test_max_exams_per_day_returns_peak_day_across_multiple_days(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    course_d = make_course(course_id="D", program_entries=[pe])
    program_index = build_program_index([course_a, course_b, course_c, course_d])

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 2)))
    schedule.addAssignment(make_assignment(course=course_d, exam_date=date(2026, 6, 3)))

    # Act
    result = max_exams_per_day(schedule, program_index)

    # Assert
    assert result == 2


# ===========================================================================
# TC-MET-021: max_exams_per_day — an empty schedule has no busiest day, so
# the result is 0.
# ===========================================================================
def test_max_exams_per_day_returns_zero_for_empty_schedule(empty_schedule):
    # Arrange
    program_index = build_program_index([])
    schedule = empty_schedule

    # Act
    result = max_exams_per_day(schedule, program_index)

    # Assert
    assert result == 0
