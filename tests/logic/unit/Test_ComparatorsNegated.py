"""
Tests for the negated comparators: MaxElectiveConflictsComparator and
MaxExamsPerDayComparator.

Both wrap a lower-is-better metric (peak_elective_conflict,
max_exams_per_day respectively) and expose it as a higher-is-better sort
key by negating it, so a calmer/lighter schedule produces a less negative
key and is ranked first. These cases confirm that negation, stability for
ties, isolation from the sibling metric, and boundary values all hold.

TC-ID family: this file shares the "CMP" prefix with Test_Comparators.py.
That sibling owns TC-CMP-001..012 (MinMandatoryGapComparator,
AvgAllCoursesGapComparator, MandatorySpanComparator); this file continues
the same family with TC-CMP-013..020 for the two negated comparators
above. The shared prefix and continuous numbering are intentional and
should not be renumbered independently.

Test bodies follow the Arrange / Act / Assert structure, marked inline.

Fixtures: uses the shared make_course, make_program_entry, and
make_assignment factory fixtures from tests/conftest.py to build courses
and schedules; no other shared fixtures from conftest.py are used.
"""
from datetime import date
import pytest

from src.models.Enums import Requirement
from src.models.ExamSchedule import ExamSchedule
from src.logic.comparators.Metrics import (
    build_elective_index,
    build_program_index,
    peak_elective_conflict,
    max_exams_per_day,
)
from src.logic.comparators.MaxElectiveConflictsComparator import MaxElectiveConflictsComparator
from src.logic.comparators.MaxExamsPerDayComparator import MaxExamsPerDayComparator


# ---------------------------------------------------------------------------
# MaxElectiveConflictsComparator TC-CMP-013..016
#
# The underlying metric (peak_elective_conflict) is lower-is-better, so the
# comparator negates it. "Less negative" therefore means "better" here.
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CMP-013: MaxElectiveConflictsComparator — a calmer schedule (no
# same-day elective pile-up) ranks ahead of a crowded one, because its less
# negative key is higher.
# ===========================================================================
def test_max_elective_conflicts_comparator_orders_calmer_schedule_first(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C")]
    comparator = MaxElectiveConflictsComparator(courses)

    crowded = ExamSchedule()
    for course in courses:
        crowded.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 5)))

    calm = ExamSchedule()
    calm.addAssignment(make_assignment(course=courses[0], exam_date=date(2026, 6, 1)))
    calm.addAssignment(make_assignment(course=courses[1], exam_date=date(2026, 6, 2)))
    calm.addAssignment(make_assignment(course=courses[2], exam_date=date(2026, 6, 3)))

    # Act
    result = sorted([crowded, calm], key=comparator.key, reverse=True)

    # Assert
    assert result == [calm, crowded]


# ===========================================================================
# TC-CMP-014: MaxElectiveConflictsComparator — two schedules with an equal
# conflict peak keep their original relative order.
# ===========================================================================
def test_max_elective_conflicts_comparator_is_stable_for_equal_peaks(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    comparator = MaxElectiveConflictsComparator([course_a, course_b])

    first = ExamSchedule()
    first.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    first.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))

    second = ExamSchedule()
    second.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    second.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))

    # Act
    original_order = sorted([first, second], key=comparator.key, reverse=True)
    swapped_order = sorted([second, first], key=comparator.key, reverse=True)

    # Assert
    assert original_order == [first, second]
    assert swapped_order == [second, first]


# ===========================================================================
# TC-CMP-015: MaxElectiveConflictsComparator — key() matches
# -peak_elective_conflict directly and ignores same-day obligatory courses,
# proving it counts only electives (not MaxExamsPerDayComparator's job).
# ===========================================================================
def test_max_elective_conflicts_comparator_uses_only_its_own_metric(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe_elective = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    elective_a = make_course(course_id="EA", program_entries=[pe_elective])
    elective_b = make_course(course_id="EB", program_entries=[pe_elective])
    obligatory_a = make_course(course_id="OA", program_entries=[pe_obligatory])
    obligatory_b = make_course(course_id="OB", program_entries=[pe_obligatory])
    courses = [elective_a, elective_b, obligatory_a, obligatory_b]
    comparator = MaxElectiveConflictsComparator(courses)
    elective_index = build_elective_index(courses)

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=elective_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=elective_b, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=obligatory_a, exam_date=date(2026, 6, 5)))
    schedule.addAssignment(make_assignment(course=obligatory_b, exam_date=date(2026, 6, 5)))

    # Act
    result = comparator.key(schedule)

    # Assert
    assert comparator.criterion_id == "ELECTIVE_CONFLICTS"
    assert result == -float(peak_elective_conflict(schedule, elective_index))
    assert result == -1.0


# ===========================================================================
# TC-CMP-016: MaxElectiveConflictsComparator — boundary values: a lone
# elective scores 0.0, while three same-day electives score -2.0.
# ===========================================================================
def test_max_elective_conflicts_comparator_boundary_values(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C")]
    comparator = MaxElectiveConflictsComparator(courses)

    crowded = ExamSchedule()
    for course in courses:
        crowded.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 5)))

    lone = ExamSchedule()
    lone.addAssignment(make_assignment(course=courses[0], exam_date=date(2026, 6, 1)))

    # Act
    crowded_score = comparator.key(crowded)
    lone_score = comparator.key(lone)

    # Assert
    assert crowded_score == -2.0
    assert lone_score == 0.0


# ---------------------------------------------------------------------------
# MaxExamsPerDayComparator TC-CMP-017..020
#
# The underlying metric (max_exams_per_day) is lower-is-better, so the
# comparator negates it. "Less negative" therefore means "better" here.
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CMP-017: MaxExamsPerDayComparator — a lighter day ranks ahead of a
# crowded one, because its less negative key is higher.
# ===========================================================================
def test_max_exams_per_day_comparator_orders_lighter_day_first(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C", "D")]
    program_index = build_program_index(courses)
    comparator = MaxExamsPerDayComparator(program_index)

    crowded = ExamSchedule()
    for course in courses[:3]:
        crowded.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    light = ExamSchedule()
    light.addAssignment(make_assignment(course=courses[3], exam_date=date(2026, 6, 1)))

    # Act
    result = sorted([crowded, light], key=comparator.key, reverse=True)

    # Assert
    assert result == [light, crowded]


# ===========================================================================
# TC-CMP-018: MaxExamsPerDayComparator — two schedules with an equal
# busiest-day count keep their original relative order.
# ===========================================================================
def test_max_exams_per_day_comparator_is_stable_for_equal_counts(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    program_index = build_program_index([course_a, course_b])
    comparator = MaxExamsPerDayComparator(program_index)

    first = ExamSchedule()
    first.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    first.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))

    second = ExamSchedule()
    second.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    second.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))

    # Act
    original_order = sorted([first, second], key=comparator.key, reverse=True)
    swapped_order = sorted([second, first], key=comparator.key, reverse=True)

    # Assert
    assert original_order == [first, second]
    assert swapped_order == [second, first]


# ===========================================================================
# TC-CMP-019: MaxExamsPerDayComparator — key() matches -max_exams_per_day
# directly and counts every course on a program's busiest day regardless of
# requirement, proving it does not use the elective-only metric.
# ===========================================================================
def test_max_exams_per_day_comparator_uses_only_its_own_metric(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=3, requirement=Requirement.ELECTIVE)
    obligatory_course = make_course(course_id="A", program_entries=[pe_obligatory])
    elective_course = make_course(course_id="B", program_entries=[pe_elective])
    courses = [obligatory_course, elective_course]
    program_index = build_program_index(courses)
    comparator = MaxExamsPerDayComparator(program_index)

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=obligatory_course, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=elective_course, exam_date=date(2026, 6, 1)))

    # Act
    result = comparator.key(schedule)

    # Assert
    assert comparator.criterion_id == "MAX_EXAMS_PER_DAY"
    assert result == -float(max_exams_per_day(schedule, program_index))
    assert result == -2.0


# ===========================================================================
# TC-CMP-020: MaxExamsPerDayComparator — boundary values: an empty schedule
# scores 0.0, while three same-day same-program exams score -3.0.
# ===========================================================================
def test_max_exams_per_day_comparator_boundary_values(
    make_course, make_program_entry, make_assignment,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C")]
    program_index = build_program_index(courses)
    comparator = MaxExamsPerDayComparator(program_index)

    crowded = ExamSchedule()
    for course in courses:
        crowded.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    empty = ExamSchedule()

    # Act
    crowded_score = comparator.key(crowded)
    empty_score = comparator.key(empty)

    # Assert
    assert crowded_score == -3.0
    assert empty_score == 0.0
