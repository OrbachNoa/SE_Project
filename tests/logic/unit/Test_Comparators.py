"""Unit tests for the non-negated scoring criteria used to rank and sort exam
schedules: MIN_MANDATORY_GAP, AVG_ALL_COURSES_GAP, and MANDATORY_SPAN. These
criteria used to be implemented as standalone comparator classes
(MinMandatoryGapComparator, AvgAllCoursesGapComparator,
MandatorySpanComparator), each exposing a `key()` used by `sorted()`. That
layer was merged into `ScheduleScorer`, which now computes every criterion in
one pass and returns a `{criterion_id: float}` dict from `score()`. These
tests check the same things the old comparators were responsible for —
ordering direction, sort stability on ties, agreement with the underlying
Metrics function, and the sentinel/zero value returned when a schedule has no
qualifying pair of exams to measure — but read the value straight out of
`ScheduleScorer.score()` instead of through a per-criterion object.

TC-ID family: shares the "CMP" prefix with Test_ComparatorsNegated.py — this
file owns TC-CMP-001..012 (the direct criteria above), and the sibling
file continues the same family with TC-CMP-013..020 (the negated/inverted
criteria). Numbering is intentionally split across the two files and must
stay contiguous between them.

Test bodies follow Arrange/Act/Assert. Fixtures come from tests/conftest.py:
make_course, make_program_entry, and make_assignment are used to build the
courses and assignments under test; ExamSchedule instances are constructed
directly in each test rather than via the empty_schedule fixture.
"""

from datetime import date
import pytest

from src.models.Enums import Requirement
from src.models.ExamSchedule import ExamSchedule
from src.logic.comparators.Metrics import (
    build_cohort_index,
    build_span_index,
    min_mandatory_gap,
    avg_all_courses_gap,
    mandatory_span,
)
from src.logic.comparators.ScheduleScorer import (
    ScheduleScorer,
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    MANDATORY_SPAN,
)


# ---------------------------------------------------------------------------
# MinMandatoryGapComparator TC-CMP-001..004
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CMP-001: MinMandatoryGapComparator — a wider mandatory gap ranks ahead
# of a narrower one (descending key, higher is better).
# ===========================================================================
def test_min_mandatory_gap_comparator_orders_wider_gap_first(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])

    narrow = ExamSchedule()
    narrow.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    narrow.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 3)))

    wide = ExamSchedule()
    wide.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    wide.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 11)))

    # Act
    result = sorted([narrow, wide], key=lambda s: scorer.score(s)[MIN_MANDATORY_GAP], reverse=True)

    # Assert
    assert result == [wide, narrow]


# ===========================================================================
# TC-CMP-002: MinMandatoryGapComparator — two schedules with an equal
# mandatory gap keep their original relative order (stable sort).
# ===========================================================================
def test_min_mandatory_gap_comparator_is_stable_for_equal_gaps(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])

    first = ExamSchedule()
    first.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    first.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 6)))

    second = ExamSchedule()
    second.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    second.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 6)))

    # Act
    original_order = sorted([first, second], key=lambda s: scorer.score(s)[MIN_MANDATORY_GAP], reverse=True)
    swapped_order = sorted([second, first], key=lambda s: scorer.score(s)[MIN_MANDATORY_GAP], reverse=True)

    # Assert
    assert original_order == [first, second]
    assert swapped_order == [second, first]


# ===========================================================================
# TC-CMP-003: MinMandatoryGapComparator — key() matches Metrics.min_mandatory_gap
# directly and ignores a nearby elective exam, proving it uses only its own
# metric (not the any-requirement average gap).
# ===========================================================================
def test_min_mandatory_gap_comparator_uses_only_its_own_metric(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe_obligatory])
    course_b = make_course(course_id="B", program_entries=[pe_obligatory])
    course_c = make_course(course_id="C", program_entries=[pe_elective])
    obligatory_cohorts, _ = build_cohort_index([course_a, course_b, course_c])
    scorer = ScheduleScorer([course_a, course_b, course_c])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 3)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 11)))

    # Act
    result = scorer.score(schedule)[MIN_MANDATORY_GAP]

    # Assert
    assert result == min_mandatory_gap(schedule, obligatory_cohorts)
    assert result == 10.0


# ===========================================================================
# TC-CMP-004: MinMandatoryGapComparator — a schedule with no mandatory pair
# falls back to the 10_000.0 sentinel.
# ===========================================================================
def test_min_mandatory_gap_comparator_returns_sentinel_when_no_pair(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    scorer = ScheduleScorer([course])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    # Act
    result = scorer.score(schedule)[MIN_MANDATORY_GAP]

    # Assert
    assert result == 10_000.0


# ---------------------------------------------------------------------------
# AvgAllCoursesGapComparator TC-CMP-005..008
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CMP-005: AvgAllCoursesGapComparator — a wider average gap ranks ahead
# of a narrower one.
# ===========================================================================
def test_avg_all_courses_gap_comparator_orders_wider_gap_first(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])

    narrow = ExamSchedule()
    narrow.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    narrow.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 3)))

    wide = ExamSchedule()
    wide.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    wide.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 11)))

    # Act
    result = sorted([narrow, wide], key=lambda s: scorer.score(s)[AVG_ALL_COURSES_GAP], reverse=True)

    # Assert
    assert result == [wide, narrow]


# ===========================================================================
# TC-CMP-006: AvgAllCoursesGapComparator — two schedules with an equal
# average gap keep their original relative order.
# ===========================================================================
def test_avg_all_courses_gap_comparator_is_stable_for_equal_gaps(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])

    first = ExamSchedule()
    first.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    first.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))

    second = ExamSchedule()
    second.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    second.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))

    # Act
    original_order = sorted([first, second], key=lambda s: scorer.score(s)[AVG_ALL_COURSES_GAP], reverse=True)
    swapped_order = sorted([second, first], key=lambda s: scorer.score(s)[AVG_ALL_COURSES_GAP], reverse=True)

    # Assert
    assert original_order == [first, second]
    assert swapped_order == [second, first]


# ===========================================================================
# TC-CMP-007: AvgAllCoursesGapComparator — key() matches
# Metrics.avg_all_courses_gap directly and, unlike MinMandatoryGapComparator,
# includes an elective exam in the average.
# ===========================================================================
def test_avg_all_courses_gap_comparator_uses_only_its_own_metric(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe_obligatory])
    course_b = make_course(course_id="B", program_entries=[pe_elective])
    _, any_cohorts = build_cohort_index([course_a, course_b])
    scorer = ScheduleScorer([course_a, course_b])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))

    # Act
    result = scorer.score(schedule)[AVG_ALL_COURSES_GAP]

    # Assert
    assert result == avg_all_courses_gap(schedule, any_cohorts)
    assert result == 4.0


# ===========================================================================
# TC-CMP-008: AvgAllCoursesGapComparator — a schedule with no pair of exams
# scores 0.0.
# ===========================================================================
def test_avg_all_courses_gap_comparator_returns_zero_when_no_pair(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    scorer = ScheduleScorer([course])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    # Act
    result = scorer.score(schedule)[AVG_ALL_COURSES_GAP]

    # Assert
    assert result == 0.0


# ---------------------------------------------------------------------------
# MandatorySpanComparator TC-CMP-009..012
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CMP-009: MandatorySpanComparator — a wider mandatory-exam span ranks
# ahead of a narrower one.
# ===========================================================================
def test_mandatory_span_comparator_orders_wider_span_first(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])

    narrow = ExamSchedule()
    narrow.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    narrow.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 3)))

    wide = ExamSchedule()
    wide.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    wide.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 11)))

    # Act
    result = sorted([narrow, wide], key=lambda s: scorer.score(s)[MANDATORY_SPAN], reverse=True)

    # Assert
    assert result == [wide, narrow]


# ===========================================================================
# TC-CMP-010: MandatorySpanComparator — two schedules with an equal span
# keep their original relative order.
# ===========================================================================
def test_mandatory_span_comparator_is_stable_for_equal_spans(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    scorer = ScheduleScorer([course_a, course_b])

    first = ExamSchedule()
    first.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    first.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))

    second = ExamSchedule()
    second.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    second.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))

    # Act
    original_order = sorted([first, second], key=lambda s: scorer.score(s)[MANDATORY_SPAN], reverse=True)
    swapped_order = sorted([second, first], key=lambda s: scorer.score(s)[MANDATORY_SPAN], reverse=True)

    # Assert
    assert original_order == [first, second]
    assert swapped_order == [second, first]


# ===========================================================================
# TC-CMP-011: MandatorySpanComparator — key() matches Metrics.mandatory_span
# directly and ignores a nearby elective exam.
# ===========================================================================
def test_mandatory_span_comparator_uses_only_its_own_metric(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe_obligatory])
    course_b = make_course(course_id="B", program_entries=[pe_obligatory])
    course_c = make_course(course_id="C", program_entries=[pe_elective])
    span_index = build_span_index([course_a, course_b, course_c])
    scorer = ScheduleScorer([course_a, course_b, course_c])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 2)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 11)))

    # Act
    result = scorer.score(schedule)[MANDATORY_SPAN]

    # Assert
    assert result == mandatory_span(schedule, span_index)
    assert result == 10.0


# ===========================================================================
# TC-CMP-012: MandatorySpanComparator — a single mandatory exam in the
# group has no span to measure, so the score is 0.0.
# ===========================================================================
def test_mandatory_span_comparator_returns_zero_for_single_exam(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    scorer = ScheduleScorer([course])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    # Act
    result = scorer.score(schedule)[MANDATORY_SPAN]

    # Assert
    assert result == 0.0
