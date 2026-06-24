from datetime import date
import pytest

from src.models.Enums import Semester, Moed, Requirement
from src.logic.SlotBuilder import Slot, SlotBuilder
from src.logic.ScheduleFeasibilityValidator import ScheduleFeasibilityValidator
from src.logic.feasibility.FeasibilityContext import FeasibilityContext
from src.logic.feasibility.InfeasibleScheduleError import InfeasibleScheduleError
from src.logic.feasibility.NonEmptyDomainRule import NonEmptyDomainRule
from src.logic.feasibility.MoedOrderDomainRule import MoedOrderDomainRule
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig


# ---------------------------------------------------------------------------
# ScheduleFeasibilityValidator — valid setup TC-FEA-001
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FEA-001: a satisfiable setup (two mandatory courses, three available
# days, no config) produces no feasibility errors at all.
# ===========================================================================
def test_validate_returns_no_errors_for_a_satisfiable_setup(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[])
    slots = SlotBuilder([period]).build([course_a, course_b])

    # Act
    errors = ScheduleFeasibilityValidator().validate([course_a, course_b], None, slots, None)

    # Assert
    assert errors == []


# ---------------------------------------------------------------------------
# Infeasible setup raises a descriptive InfeasibleScheduleError TC-FEA-002
#
# ScheduleFeasibilityValidator.validate() itself only ever returns a list of
# strings; it is the caller's responsibility to raise InfeasibleScheduleError
# when that list is non-empty (this is exactly what main.py and
# SchedulingService.py do).
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FEA-002: a course whose only candidate dates are all excluded makes
# validate() return a non-empty error list; raising InfeasibleScheduleError
# from those errors produces a descriptive, prefixed message.
# ===========================================================================
def test_infeasible_setup_raises_descriptive_error(
    make_course, make_program_entry, make_period,
):
    # Arrange — every day in the period is excluded, so the course's slot
    # ends up with an empty domain and no schedule can ever be built.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 2),
        excluded=[date(2026, 6, 1), date(2026, 6, 2)],
    )
    slots = SlotBuilder([period]).build([course])

    # Act
    errors = ScheduleFeasibilityValidator().validate([course], None, slots, None)

    # Assert
    assert errors
    with pytest.raises(InfeasibleScheduleError) as exc_info:
        raise InfeasibleScheduleError(errors)
    assert "No valid schedules possible" in str(exc_info.value)
    assert "no available dates" in str(exc_info.value)


# ---------------------------------------------------------------------------
# NonEmptyDomainRule TC-FEA-003..004
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FEA-003: NonEmptyDomainRule — a slot with an empty candidateDates list
# is reported as a violation.
# ===========================================================================
def test_non_empty_domain_rule_flags_a_slot_with_no_candidate_dates(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    slot = Slot(course=course, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[])
    context = FeasibilityContext(selected_programs=None, slots=[slot], config=None)

    # Act
    errors = NonEmptyDomainRule().validate(context)

    # Assert
    assert len(errors) == 1
    assert "no available dates" in errors[0]


# ===========================================================================
# TC-FEA-004: NonEmptyDomainRule — a slot with at least one candidate date
# is not a violation.
# ===========================================================================
def test_non_empty_domain_rule_passes_when_every_slot_has_dates(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    slot = Slot(course=course, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    context = FeasibilityContext(selected_programs=None, slots=[slot], config=None)

    # Act
    errors = NonEmptyDomainRule().validate(context)

    # Assert
    assert errors == []


# ---------------------------------------------------------------------------
# MoedOrderDomainRule TC-FEA-005..008
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FEA-005: MoedOrderDomainRule — two ALEPH slots for the same course can
# never satisfy moed order, so this is reported as a violation.
# ===========================================================================
def test_moed_order_rule_flags_duplicate_moed_slots_for_the_same_course(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    slot_one = Slot(course=course, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    slot_two = Slot(course=course, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 5)])
    context = FeasibilityContext(selected_programs=None, slots=[slot_one, slot_two], config=None)

    # Act
    errors = MoedOrderDomainRule().validate(context)

    # Assert
    assert len(errors) == 1
    assert "more than one" in errors[0]


# ===========================================================================
# TC-FEA-006: MoedOrderDomainRule — when ALEPH's only candidate date falls
# after BET's only candidate date, no increasing sequence exists.
# ===========================================================================
def test_moed_order_rule_flags_when_no_increasing_date_sequence_exists(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    aleph_slot = Slot(course=course, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 10)])
    bet_slot = Slot(course=course, semester=Semester.FALL, moed=Moed.BET, candidateDates=[date(2026, 6, 1)])
    context = FeasibilityContext(selected_programs=None, slots=[aleph_slot, bet_slot], config=None)

    # Act
    errors = MoedOrderDomainRule().validate(context)

    # Assert
    assert len(errors) == 1
    assert "no possible date sequence" in errors[0]


# ===========================================================================
# TC-FEA-007: MoedOrderDomainRule — ALEPH before BET is a valid increasing
# sequence, so it is not a violation.
# ===========================================================================
def test_moed_order_rule_passes_for_a_valid_increasing_sequence(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    aleph_slot = Slot(course=course, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    bet_slot = Slot(course=course, semester=Semester.FALL, moed=Moed.BET, candidateDates=[date(2026, 6, 10)])
    context = FeasibilityContext(selected_programs=None, slots=[aleph_slot, bet_slot], config=None)

    # Act
    errors = MoedOrderDomainRule().validate(context)

    # Assert
    assert errors == []


# ===========================================================================
# TC-FEA-008: MoedOrderDomainRule — a course with one empty-domain slot is
# skipped entirely, deferring that report to NonEmptyDomainRule instead of
# raising its own (less informative) error.
# ===========================================================================
def test_moed_order_rule_skips_a_course_with_an_empty_domain_slot(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    aleph_slot = Slot(course=course, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    bet_slot = Slot(course=course, semester=Semester.FALL, moed=Moed.BET, candidateDates=[])
    context = FeasibilityContext(selected_programs=None, slots=[aleph_slot, bet_slot], config=None)

    # Act
    errors = MoedOrderDomainRule().validate(context)

    # Assert
    assert errors == []


# ---------------------------------------------------------------------------
# Disabled config accepts what an active threshold would reject TC-FEA-009..010
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FEA-009: with config=None, build_checkers adds no threshold checker, so
# three exams forced onto the same single day raises no feasibility error.
# ===========================================================================
def test_validate_ignores_threshold_violations_when_config_is_none(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C")]
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 2), excluded=[date(2026, 6, 2)])
    slots = SlotBuilder([period]).build(courses)

    # Act
    errors = ScheduleFeasibilityValidator().validate(courses, None, slots, None)

    # Assert
    assert errors == []


# ===========================================================================
# TC-FEA-010: the same setup, but with max_exams_per_day=1 enabled, is now
# reported as infeasible: the day cap cannot be met.
# ===========================================================================
def test_validate_flags_threshold_violation_when_config_enables_it(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C")]
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 2), excluded=[date(2026, 6, 2)])
    slots = SlotBuilder([period]).build(courses)
    config = ConstraintsConfig(max_exams_per_day=1)

    # Act
    errors = ScheduleFeasibilityValidator().validate(courses, None, slots, config)

    # Assert
    assert len(errors) == 1
    assert "Max exams per day" in errors[0]


# ---------------------------------------------------------------------------
# Multiple violated rules accumulate TC-FEA-011
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FEA-011: a structural violation (course A has no available dates) and a
# threshold violation (B and C cannot fit under max_exams_per_day=1) fire
# together; validate() returns both, not just the first one found.
# ===========================================================================
def test_validate_accumulates_errors_from_every_violated_rule(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 2), excluded=[date(2026, 6, 2)])
    slots = SlotBuilder([period]).build([course_b, course_c])
    empty_slot = Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[])
    slots = slots + [empty_slot]
    config = ConstraintsConfig(max_exams_per_day=1)

    # Act
    errors = ScheduleFeasibilityValidator().validate(
        [course_a, course_b, course_c], None, slots, config,
    )

    # Assert — both the structural rule and the threshold checker contributed.
    assert len(errors) == 2
    assert any("no available dates" in e for e in errors)
    assert any("Max exams per day" in e for e in errors)


# ---------------------------------------------------------------------------
# Threshold checkers' feasibility_bound() — imports added for this section.
# ---------------------------------------------------------------------------
from src.logic.checkers.ElectiveConflictCapChecker import ElectiveConflictCapChecker
from src.logic.checkers.ExamSpanChecker import ExamSpanChecker
from src.logic.checkers.MinDaysBetweenExamsChecker import MinDaysBetweenExamsChecker, GapScope


# ===========================================================================
# TC-FEA-012: ElectiveConflictCapChecker.feasibility_bound — three electives
# crammed onto a single shared date can never satisfy a k=0 cap (at most 1
# elective per day), but the same 3 electives spread over 3 distinct dates
# fit comfortably under k=2.
# ===========================================================================
def test_elective_conflict_cap_feasibility_bound_flags_an_overcrowded_day(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    electives = [make_course(course_id=cid, program_entries=[pe]) for cid in ("E1", "E2", "E3")]
    overcrowded_slots = [
        Slot(course=c, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
        for c in electives
    ]
    spread_slots = [
        Slot(
            course=c, semester=Semester.FALL, moed=Moed.ALEPH,
            candidateDates=[date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)],
        )
        for c in electives
    ]
    overcrowded_context = FeasibilityContext(selected_programs=None, slots=overcrowded_slots, config=None)
    spread_context = FeasibilityContext(selected_programs=None, slots=spread_slots, config=None)

    # Act
    overcrowded_errors = ElectiveConflictCapChecker(k=0).feasibility_bound(overcrowded_context)
    spread_errors = ElectiveConflictCapChecker(k=2).feasibility_bound(spread_context)

    # Assert
    assert len(overcrowded_errors) == 1
    assert "Elective conflict cap 0" in overcrowded_errors[0]
    assert "83101" in overcrowded_errors[0]
    assert spread_errors == []


# ===========================================================================
# TC-FEA-013: ExamSpanChecker.feasibility_bound — when the union of two
# mandatory exams' candidate dates can span at most 1 day, a required span
# of 10 days is provably unreachable; a 10-day-wide window is feasible.
# ===========================================================================
def test_exam_span_feasibility_bound_flags_a_window_too_narrow_for_the_span(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    narrow_slots = [
        Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1), date(2026, 6, 2)]),
        Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1), date(2026, 6, 2)]),
    ]
    wide_slots = [
        Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)]),
        Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 11)]),
    ]
    narrow_context = FeasibilityContext(selected_programs=None, slots=narrow_slots, config=None)
    wide_context = FeasibilityContext(selected_programs=None, slots=wide_slots, config=None)

    # Act
    narrow_errors = ExamSpanChecker(k=10).feasibility_bound(narrow_context)
    wide_errors = ExamSpanChecker(k=10).feasibility_bound(wide_context)

    # Assert
    assert len(narrow_errors) == 1
    assert "requires 10 days" in narrow_errors[0]
    assert "at most 1 days" in narrow_errors[0]
    assert wide_errors == []


# ===========================================================================
# TC-FEA-014: MinDaysBetweenExamsChecker.feasibility_bound — two mandatory
# exams that need a 5-day gap but only have 2 candidate dates 3 days apart
# cannot both be spaced out; the same 2 exams with dates 9 days apart are
# feasible.
# ===========================================================================
def test_min_days_between_exams_feasibility_bound_flags_an_insufficient_gap(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    close_dates = [date(2026, 6, 1), date(2026, 6, 4)]
    close_slots = [
        Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=list(close_dates)),
        Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=list(close_dates)),
    ]
    spaced_dates = [date(2026, 6, 1), date(2026, 6, 10)]
    spaced_slots = [
        Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=list(spaced_dates)),
        Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=list(spaced_dates)),
    ]
    close_context = FeasibilityContext(selected_programs=None, slots=close_slots, config=None)
    spaced_context = FeasibilityContext(selected_programs=None, slots=spaced_slots, config=None)

    # Act
    close_errors = MinDaysBetweenExamsChecker(scope=GapScope.OBLIGATORY_ONLY, k=5).feasibility_bound(close_context)
    spaced_errors = MinDaysBetweenExamsChecker(scope=GapScope.OBLIGATORY_ONLY, k=5).feasibility_bound(spaced_context)

    # Assert — with only 2 dates 3 days apart, at most 1 of the 2 required
    # exams can be placed with a 5-day gap from the other; 9 days apart
    # gives both exams room to satisfy the gap.
    assert len(close_errors) == 1
    assert "requires 2 exams" in close_errors[0]
    assert "only 1 dates can fit with a 5-day gap" in close_errors[0]
    assert spaced_errors == []


# ===========================================================================
# TC-FEA-015: FeasibilityContext.selected_set converts a program list into
# a plain Python set with the same members, and is None when no programs
# were selected at all.
# ===========================================================================
def test_feasibility_context_selected_set_reflects_selected_programs():
    # Arrange
    with_programs = FeasibilityContext(selected_programs=["83101", "83102"], slots=[], config=None)
    without_programs = FeasibilityContext(selected_programs=None, slots=[], config=None)

    # Act
    selected_set_with_programs = with_programs.selected_set
    selected_set_without_programs = without_programs.selected_set

    # Assert
    assert selected_set_with_programs == {"83101", "83102"}
    assert isinstance(selected_set_with_programs, set)
    assert selected_set_without_programs is None
