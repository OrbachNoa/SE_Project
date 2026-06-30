"""
Test suite for MandatorySpanGapRule.

Scope   : Verifies the early-exit branches (no config, no exam_span, no
          mandatory gap), the satisfiable case where two mandatory-exam
          groups can coexist, and the infeasible case where the forced
          earliest/latest dates of two mandatory-exam groups in the same
          (program, year) cohort can never satisfy the minimum gap given the
          required exam span.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-MSG-001, TC-MSG-002, ...
Fixtures: make_course, make_program_entry (shared); Slot and
          FeasibilityContext constructed directly, matching the pattern used
          in tests/logic/integration/Test_FeasibilityValidator.py.
"""
from datetime import date

from src.models.Enums import Semester, Moed, Requirement
from src.logic.SlotBuilder import Slot
from src.logic.feasibility.FeasibilityContext import FeasibilityContext
from src.logic.feasibility.MandatorySpanGapRule import MandatorySpanGapRule
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig


# ---------------------------------------------------------------------------
# Early-exit branches TC-MSG-001..005
# ---------------------------------------------------------------------------

# TC-MSG-001
# With config=None, the rule has no exam_span to enforce and must return an
# empty error list without inspecting any slots.
def test_validate_returns_empty_when_config_is_none():
    # Arrange
    context = FeasibilityContext(selected_programs=None, slots=[], config=None)
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert
    assert errors == []


# TC-MSG-002
# With config.exam_span left at its default of None, the rule must return an
# empty error list -- there is no span requirement to combine with the gap.
def test_validate_returns_empty_when_exam_span_is_none():
    # Arrange
    config = ConstraintsConfig(exam_span=None, min_gap_obligatory=3)
    context = FeasibilityContext(selected_programs=None, slots=[], config=config)
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert
    assert errors == []


# TC-MSG-003
# A non-positive exam_span (<=0) must be treated the same as "no span rule",
# returning an empty error list.
def test_validate_returns_empty_when_exam_span_is_not_positive():
    # Arrange
    config = ConstraintsConfig(exam_span=0, min_gap_obligatory=3)
    context = FeasibilityContext(selected_programs=None, slots=[], config=config)
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert
    assert errors == []


# TC-MSG-004
# With exam_span enabled but neither min_gap_obligatory nor min_gap_any set,
# there is no mandatory gap to combine with the span, so the rule must
# return an empty error list.
def test_validate_returns_empty_when_no_mandatory_gap_is_configured():
    # Arrange
    config = ConstraintsConfig(exam_span=10)
    context = FeasibilityContext(selected_programs=None, slots=[], config=config)
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert
    assert errors == []


# TC-MSG-005
# A non-positive mandatory gap value must also be treated as "no gap rule",
# even when exam_span is enabled.
def test_validate_returns_empty_when_mandatory_gap_is_not_positive(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    slot_a = Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    slot_b = Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 11)])
    config = ConstraintsConfig(exam_span=10, min_gap_obligatory=0)
    context = FeasibilityContext(selected_programs=None, slots=[slot_a, slot_b], config=config)
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert
    assert errors == []


# ---------------------------------------------------------------------------
# Infeasible cross-group scenario TC-MSG-006..007
# ---------------------------------------------------------------------------

# TC-MSG-006
# Two mandatory-exam groups (FALL/ALEPH and FALL/BET) in the same
# (program, year) cohort are each pinned to two single-candidate-date slots
# exactly span days apart. Given the configured exam_span (10) and minimum
# gap (5), every possible pairing between the two groups' forced extreme
# dates is closer than the gap, so the rule must report exactly one
# infeasibility error naming the program and year.
def test_validate_flags_infeasible_combination_of_span_and_gap(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    course_d = make_course(course_id="D", program_entries=[pe])

    # Group 1 (ALEPH): forced to June 1 and June 11 -- span exactly 10.
    slot_a = Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    slot_b = Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 11)])
    # Group 2 (BET): forced to June 2 and June 12 -- span exactly 10, but
    # only 1 day away from group 1's matching extremes.
    slot_c = Slot(course=course_c, semester=Semester.FALL, moed=Moed.BET, candidateDates=[date(2026, 6, 2)])
    slot_d = Slot(course=course_d, semester=Semester.FALL, moed=Moed.BET, candidateDates=[date(2026, 6, 12)])

    config = ConstraintsConfig(exam_span=10, min_gap_obligatory=5)
    context = FeasibilityContext(
        selected_programs=None, slots=[slot_a, slot_b, slot_c, slot_d], config=config,
    )
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert
    assert len(errors) == 1
    assert "83101" in errors[0]
    assert "year 2" in errors[0]
    assert "Exam span 10 days" in errors[0]
    assert "minimum gap 5 days" in errors[0]


# TC-MSG-007
# The same exam_span and gap requirement applied to two groups that are far
# apart in time (a full month between them) must be satisfiable: at least
# one pairing of forced extremes is farther apart than the required gap, so
# the rule reports no error.
def test_validate_returns_empty_for_satisfiable_combination_of_span_and_gap(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    course_d = make_course(course_id="D", program_entries=[pe])

    slot_a = Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    slot_b = Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 11)])
    # Group 2 starts a full month later -- comfortably clear of the gap.
    slot_c = Slot(course=course_c, semester=Semester.FALL, moed=Moed.BET, candidateDates=[date(2026, 7, 1)])
    slot_d = Slot(course=course_d, semester=Semester.FALL, moed=Moed.BET, candidateDates=[date(2026, 7, 11)])

    config = ConstraintsConfig(exam_span=10, min_gap_obligatory=5)
    context = FeasibilityContext(
        selected_programs=None, slots=[slot_a, slot_b, slot_c, slot_d], config=config,
    )
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert
    assert errors == []


# ---------------------------------------------------------------------------
# Groups that do not participate in the cross-group comparison TC-MSG-008..009
# ---------------------------------------------------------------------------

# TC-MSG-008
# With only a single mandatory-exam group in the cohort (no second group to
# compare against), the rule must return no errors -- there is nothing to
# combine across groups.
def test_validate_returns_empty_with_only_one_mandatory_group(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    slot_a = Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    slot_b = Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 11)])

    config = ConstraintsConfig(exam_span=10, min_gap_obligatory=5)
    context = FeasibilityContext(selected_programs=None, slots=[slot_a, slot_b], config=config)
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert
    assert errors == []


# TC-MSG-009
# A group with a slot that has an empty candidateDates list must be skipped
# entirely from the span-extremes calculation (deferred to NonEmptyDomainRule
# instead), so it cannot trigger a false infeasibility report here.
def test_validate_skips_group_with_an_empty_domain_slot(
    make_course, make_program_entry,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    course_d = make_course(course_id="D", program_entries=[pe])

    # Group 1 is fully specified.
    slot_a = Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 1)])
    slot_b = Slot(course=course_b, semester=Semester.FALL, moed=Moed.ALEPH, candidateDates=[date(2026, 6, 11)])
    # Group 2 has one slot with no candidate dates at all.
    slot_c = Slot(course=course_c, semester=Semester.FALL, moed=Moed.BET, candidateDates=[date(2026, 6, 2)])
    slot_d = Slot(course=course_d, semester=Semester.FALL, moed=Moed.BET, candidateDates=[])

    config = ConstraintsConfig(exam_span=10, min_gap_obligatory=5)
    context = FeasibilityContext(
        selected_programs=None, slots=[slot_a, slot_b, slot_c, slot_d], config=config,
    )
    rule = MandatorySpanGapRule()

    # Act
    errors = rule.validate(context)

    # Assert -- group 2 is excluded from the comparison, leaving only one
    # comparable group, so no cross-group error can be produced.
    assert errors == []
