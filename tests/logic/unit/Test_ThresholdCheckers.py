"""
Test_ThresholdCheckers.py — Unit tests for the configurable threshold checkers.

These four checkers are threshold-based. Unlike the "hard" conflict
checkers (ProgramYearConflictChecker, MoedOrderChecker), each of these is driven
by a user-configurable threshold k that is set in the Settings screen, and each
one can be turned on or off independently:

    - MinDaysBetweenExamsChecker  (minimum gap, scoped to obligatory-only or any course)
    - ElectiveConflictCapChecker  (same-day elective pair-conflict cap)
    - ExamSpanChecker             (minimum span across a mandatory exam group)
    - MaxExamsPerDayChecker       (maximum exams on any single day)

They live in a separate file from Test_Checkers.py so that neither file grows
unreasonably large; the split is by checker family (fixed-rule vs. configurable
threshold), not by version. TC-CHK numbering continues from Test_Checkers.py
(which ends at TC-CHK-011) rather than restarting, since both files share one
checker-family identifier covering every IConflictChecker implementation.

Convention shared by every checker: check() returns True when the candidate
placement VIOLATES the rule (a conflict, reject it) and False when the placement
is acceptable.

Conventions:
- Each test carries a unique TC-CHK-NNN identifier in the comment block
  above its definition, grouped under a section divider per checker.
- Each test body is split into Arrange / Act / Assert sections.
- `make_course`, `make_program_entry`, and `make_assignment` come from the
  shared fixtures in tests/conftest.py; the `_make_*_checker()` and
  `_make_slot()` helpers below are local since no conftest fixture models
  a prepared threshold checker or a bare Slot.
"""
from datetime import date

from src.models.Enums import Semester, Moed, Requirement
from src.models.ExamSchedule import ExamSchedule
from src.logic.SlotBuilder import Slot
from src.logic.checkers.MinDaysBetweenExamsChecker import MinDaysBetweenExamsChecker, GapScope
from src.logic.checkers.ElectiveConflictCapChecker import ElectiveConflictCapChecker
from src.logic.checkers.ExamSpanChecker import ExamSpanChecker
from src.logic.checkers.MaxExamsPerDayChecker import MaxExamsPerDayChecker


# ---------------------------------------------------------------------------
# MinDaysBetweenExamsChecker  TC-CHK-012..017
#
# Enforces a minimum number of calendar days between any two exams that share
# the same (program, year) cohort. Two scopes are supported:
#   - OBLIGATORY_ONLY (rule 2.1): only mandatory courses are counted
#   - ANY             (rule 2.2): every course is counted (mandatory + elective)
#
# This checker reads the schedule through its ordinal-date index, so every
# schedule in this section is created with ExamSchedule(use_ordinal_index=True).
# ---------------------------------------------------------------------------

def _make_min_gap_checker(scope, k, courses):
    """Build a MinDaysBetweenExamsChecker and run its one-time prepare() step.

    prepare() must be called before check(); it precomputes which courses
    belong to which cohort. Skipping it would leave the checker with no data
    and every check() call would wrongly return False.
    """
    checker = MinDaysBetweenExamsChecker(scope=scope, k=k)
    checker.prepare(courses, selected_programs=None, slots=None)
    return checker


# ===========================================================================
# TC-CHK-012: a gap strictly smaller than k days between two obligatory exams
# is a violation. With k=5 and exams 3 days apart, check() must return True.
# ===========================================================================
def test_min_gap_checker_rejects_gap_below_k(make_course, make_program_entry, make_assignment):
    # Arrange — two obligatory courses in the same program and year.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])

    # The first exam is already placed on June 1.
    schedule = ExamSchedule(use_ordinal_index=True)
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))

    # The candidate sits on June 4: only a 3-day gap, which is below k=5.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 4))
    checker = _make_min_gap_checker(GapScope.OBLIGATORY_ONLY, k=5, courses=[course_a, course_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — gap of 3 < k=5, so the placement is a conflict.
    assert result is True


# ===========================================================================
# TC-CHK-013: a gap exactly equal to k days is allowed (boundary case).
# With k=5 and exams exactly 5 days apart, check() must return False.
# ===========================================================================
def test_min_gap_checker_accepts_gap_exactly_k(make_course, make_program_entry, make_assignment):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])

    schedule = ExamSchedule(use_ordinal_index=True)
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))

    # June 1 to June 6 is exactly a 5-day gap, right on the threshold.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 6))
    checker = _make_min_gap_checker(GapScope.OBLIGATORY_ONLY, k=5, courses=[course_a, course_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — gap of 5 == k=5 is acceptable, so no conflict.
    assert result is False


# ===========================================================================
# TC-CHK-014: a gap strictly greater than k days is allowed.
# With k=5 and exams 10 days apart, check() must return False.
# ===========================================================================
def test_min_gap_checker_accepts_gap_above_k(make_course, make_program_entry, make_assignment):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])

    schedule = ExamSchedule(use_ordinal_index=True)
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))

    # June 1 to June 11 is a 10-day gap, comfortably above k=5.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 11))
    checker = _make_min_gap_checker(GapScope.OBLIGATORY_ONLY, k=5, courses=[course_a, course_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — gap of 10 > k=5, no conflict.
    assert result is False


# ===========================================================================
# TC-CHK-015: under OBLIGATORY_ONLY scope, elective courses are ignored.
# Two electives one day apart with k=5 must NOT be rejected, because rule 2.1
# only constrains mandatory courses.
# ===========================================================================
def test_min_gap_checker_obligatory_scope_ignores_electives(
    make_course, make_program_entry, make_assignment
):
    # Arrange — both courses are ELECTIVE in the same program and year.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])

    schedule = ExamSchedule(use_ordinal_index=True)
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))

    # Only one day apart: this would be a conflict if electives were counted.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 2))
    checker = _make_min_gap_checker(GapScope.OBLIGATORY_ONLY, k=5, courses=[course_a, course_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — OBLIGATORY_ONLY scope never looks at electives, so no conflict.
    assert result is False


# ===========================================================================
# TC-CHK-016: under ANY scope, elective courses are counted (rule 2.2).
# The same two electives one day apart with k=5 must now be rejected.
# ===========================================================================
def test_min_gap_checker_any_scope_counts_electives(
    make_course, make_program_entry, make_assignment
):
    # Arrange — both courses are ELECTIVE in the same program and year.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])

    schedule = ExamSchedule(use_ordinal_index=True)
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))

    # One day apart, and ANY scope counts every course type.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 2))
    checker = _make_min_gap_checker(GapScope.ANY, k=5, courses=[course_a, course_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — gap of 1 < k=5 with electives counted, so this is a conflict.
    assert result is True


# ===========================================================================
# TC-CHK-017: k=0 disables the rule entirely. Even two obligatory exams on the
# exact same day must be accepted, because a non-positive k short-circuits the
# check to "no conflict".
# ===========================================================================
def test_min_gap_checker_disabled_when_k_is_zero(
    make_course, make_program_entry, make_assignment
):
    # Arrange — two obligatory courses scheduled on the very same day.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])

    schedule = ExamSchedule(use_ordinal_index=True)
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))

    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 1))
    checker = _make_min_gap_checker(GapScope.OBLIGATORY_ONLY, k=0, courses=[course_a, course_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — k=0 means the gap rule is off, so nothing is ever a conflict.
    assert result is False


# ---------------------------------------------------------------------------
# ElectiveConflictCapChecker  TC-CHK-018..021
#
# Caps how many same-day elective pair-conflicts are allowed per program.
# n elective exams on one day produce n*(n-1)/2 distinct pairs; k is the largest
# number of pairs tolerated. Years are deliberately ignored: every elective in a
# program contributes to that program's single conflict count.
# ---------------------------------------------------------------------------

def _make_elective_cap_checker(k, courses):
    """Build an ElectiveConflictCapChecker and run its prepare() step.

    prepare() records, per program, which course IDs are elective so that
    check() can count same-day clashes in O(1) per course.
    """
    checker = ElectiveConflictCapChecker(k=k)
    checker.prepare(courses, selected_programs=None, slots=None)
    return checker


# ===========================================================================
# TC-CHK-018: placing a course that pushes the pair-count above k is rejected.
# Three electives on one day make 3 pairs; with k=2 the third placement must
# return True (conflict).
# ===========================================================================
def test_elective_cap_checker_rejects_when_conflicts_exceed_k(
    make_course, make_program_entry, make_assignment
):
    # Arrange — three elective courses in the same program.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])

    # A and B already share June 1: that is 1 pair so far, within k=2.
    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))

    # Adding C to the same day raises the total to 3 pairs, exceeding k=2.
    candidate = make_assignment(course=course_c, exam_date=date(2026, 6, 1))
    checker = _make_elective_cap_checker(k=2, courses=[course_a, course_b, course_c])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — 3 pairs > k=2, so the placement is a conflict.
    assert result is True


# ===========================================================================
# TC-CHK-019: a pair-count exactly equal to k is allowed (boundary case).
# Three electives on one day make 3 pairs; with k=3 the third placement must
# return False.
# ===========================================================================
def test_elective_cap_checker_accepts_when_conflicts_equal_k(
    make_course, make_program_entry, make_assignment
):
    # Arrange — three elective courses in the same program.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))

    # Adding C makes exactly 3 pairs, which equals k=3 and is still allowed.
    candidate = make_assignment(course=course_c, exam_date=date(2026, 6, 1))
    checker = _make_elective_cap_checker(k=3, courses=[course_a, course_b, course_c])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — 3 pairs == k=3, the boundary is inclusive, so no conflict.
    assert result is False


# ===========================================================================
# TC-CHK-020: with k=0 no same-day elective clash is tolerated at all.
# Two electives on one day make a single pair, which already exceeds k=0.
# ===========================================================================
def test_elective_cap_checker_rejects_any_conflict_when_k_is_zero(
    make_course, make_program_entry, make_assignment
):
    # Arrange — two elective courses in the same program.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))

    # Adding B to the same day creates 1 pair, already over the k=0 cap.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 1))
    checker = _make_elective_cap_checker(k=0, courses=[course_a, course_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — 1 pair > k=0, so even a single clash is a conflict.
    assert result is True


# ===========================================================================
# TC-CHK-021: obligatory courses are invisible to this checker.
# Two obligatory courses on the same day create no elective pair, so the
# placement is accepted even with the strictest cap of k=0.
# ===========================================================================
def test_elective_cap_checker_ignores_obligatory_courses(
    make_course, make_program_entry, make_assignment
):
    # Arrange — both courses are OBLIGATORY, not elective.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))

    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 1))
    checker = _make_elective_cap_checker(k=0, courses=[course_a, course_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — no elective courses involved, so this checker sees no conflict.
    assert result is False


# ===========================================================================
# TC-CHK-021b: the cap counts pair-conflicts across the WHOLE schedule for a
# program, not just on the candidate's own day. With k=1, a conflict already
# committed on one day (A & B on June 1) plus a second, separate conflict
# being completed on another day (C already on June 2, D about to join it)
# pushes the running total to 2, which must be rejected even though neither
# day individually exceeds the per-day cap.
# ===========================================================================
def test_elective_cap_checker_totals_conflicts_across_separate_days(
    make_course, make_program_entry, make_assignment
):
    # Arrange — four elective courses in the same program.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    course_d = make_course(course_id="D", program_entries=[pe])

    # June 1 already holds one committed conflict (A & B).
    # June 2 holds a single, conflict-free exam (C) so far.
    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_c, exam_date=date(2026, 6, 2)))

    # Placing D on June 2 creates a second, separate conflict. The running
    # total across the schedule becomes 2, which exceeds k=1.
    candidate = make_assignment(course=course_d, exam_date=date(2026, 6, 2))
    checker = _make_elective_cap_checker(k=1, courses=[course_a, course_b, course_c, course_d])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — total of 2 pair-conflicts across the schedule > k=1, rejected.
    assert result is True


# ===========================================================================
# TC-CHK-021c: a single conflict elsewhere in the schedule must not block an
# unrelated, conflict-free placement. With k=1, the committed conflict on
# June 1 (A & B) leaves room for one exam (E) to be placed alone on June 3.
# ===========================================================================
def test_elective_cap_checker_allows_unrelated_conflict_free_placement(
    make_course, make_program_entry, make_assignment
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_e = make_course(course_id="E", program_entries=[pe])

    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 1)))

    # E lands alone on a brand-new day: it adds zero new pairs.
    candidate = make_assignment(course=course_e, exam_date=date(2026, 6, 3))
    checker = _make_elective_cap_checker(k=1, courses=[course_a, course_b, course_e])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — total stays at 1 (the existing A/B pair), still within k=1.
    assert result is False


# ---------------------------------------------------------------------------
# ExamSpanChecker  TC-CHK-022..025
#
# Per (program, year, moed), requires the span in days between the first and
# last OBLIGATORY exam to be at least k. Because the span can only grow while a
# group is still being filled, the rule is evaluated only once every obligatory
# exam in that group has been placed. The expected group size is derived from
# the slots passed to prepare().
# ---------------------------------------------------------------------------

def _make_span_checker(k, courses, slots):
    """Build an ExamSpanChecker and run its prepare() step.

    prepare() needs the slots so it can learn the full membership (and therefore
    the expected size) of every obligatory (program, year, moed) group.
    """
    checker = ExamSpanChecker(k=k)
    checker.prepare(courses, selected_programs=None, slots=slots)
    return checker


def _make_slot(course, moed=Moed.ALEPH, candidate_dates=None):
    """Create a minimal Slot for prepare(). Only course and moed matter to the
    span checker's grouping; candidateDates just needs to be a non-empty list.
    """
    if candidate_dates is None:
        candidate_dates = [date(2026, 6, 1)]
    return Slot(course=course, semester=Semester.FALL, moed=moed, candidateDates=candidate_dates)


# ===========================================================================
# TC-CHK-022: once the group is complete, a span below k is a violation.
# Two obligatory exams on June 1 and June 5 give a 4-day span; with k=10 the
# completing placement must return True.
# ===========================================================================
def test_exam_span_checker_rejects_when_span_below_k(
    make_course, make_program_entry, make_assignment
):
    # Arrange — two obligatory courses sharing one (program, year, moed) group.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    slots = [_make_slot(course_a), _make_slot(course_b)]

    # Course A sits on June 1; the group still needs B to be complete.
    schedule = ExamSchedule()
    schedule.addAssignment(
        make_assignment(course=course_a, exam_date=date(2026, 6, 1), moed=Moed.ALEPH)
    )

    # Placing B on June 5 completes the group with a span of only 4 days.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 5), moed=Moed.ALEPH)
    checker = _make_span_checker(k=10, courses=[course_a, course_b], slots=slots)

    # Act
    result = checker.check(candidate, schedule)

    # Assert — span of 4 < k=10, so the completed group violates the rule.
    assert result is True


# ===========================================================================
# TC-CHK-023: a span exactly equal to k is allowed (boundary case).
# June 1 to June 11 is a 10-day span; with k=10 the completing placement must
# return False.
# ===========================================================================
def test_exam_span_checker_accepts_when_span_equals_k(
    make_course, make_program_entry, make_assignment
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    slots = [_make_slot(course_a), _make_slot(course_b)]

    schedule = ExamSchedule()
    schedule.addAssignment(
        make_assignment(course=course_a, exam_date=date(2026, 6, 1), moed=Moed.ALEPH)
    )

    # June 1 to June 11 is exactly a 10-day span, right on the threshold.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 11), moed=Moed.ALEPH)
    checker = _make_span_checker(k=10, courses=[course_a, course_b], slots=slots)

    # Act
    result = checker.check(candidate, schedule)

    # Assert — span of 10 == k=10 is acceptable, so no conflict.
    assert result is False


# ===========================================================================
# TC-CHK-024: while the group is still incomplete the checker defers judgment.
# Three courses form the group but only one is placed; adding a second (a 1-day
# span so far) must not be flagged, because the third exam can still widen it.
# ===========================================================================
def test_exam_span_checker_defers_when_group_incomplete(
    make_course, make_program_entry, make_assignment
):
    # Arrange — three obligatory courses in one (program, year, moed) group.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    slots = [_make_slot(c) for c in (course_a, course_b, course_c)]

    # Only course A is placed so far, so the group is incomplete.
    schedule = ExamSchedule()
    schedule.addAssignment(
        make_assignment(course=course_a, exam_date=date(2026, 6, 1), moed=Moed.ALEPH)
    )

    # Placing B one day later looks tight, but C is still unplaced.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 6, 2), moed=Moed.ALEPH)
    checker = _make_span_checker(k=10, courses=[course_a, course_b, course_c], slots=slots)

    # Act
    result = checker.check(candidate, schedule)

    # Assert — the group is not complete yet, so judgment is deferred (no conflict).
    assert result is False


# ===========================================================================
# TC-CHK-025: a single-course group can never violate a span rule.
# With only one obligatory exam there is no pair to measure a span between, so
# the placement is always accepted.
# ===========================================================================
def test_exam_span_checker_accepts_single_course_group(
    make_course, make_program_entry, make_assignment
):
    # Arrange — exactly one obligatory course in this (program, year, moed) group.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    slots = [_make_slot(course_a)]

    schedule = ExamSchedule()
    candidate = make_assignment(course=course_a, exam_date=date(2026, 6, 1), moed=Moed.ALEPH)
    checker = _make_span_checker(k=10, courses=[course_a], slots=slots)

    # Act
    result = checker.check(candidate, schedule)

    # Assert — a group of one has no span to check, so no conflict.
    assert result is False


# ===========================================================================
# TC-CHK-025b: groups are scoped per semester, not just per (program, year,
# moed). Two obligatory courses share a program/year/moed but belong to
# different semesters (FALL vs SPRING), which are unrelated exam periods that
# can be months apart. Each forms its own group of size 1, so neither can
# ever violate the span rule, even when scheduled one day apart.
# ===========================================================================
def test_exam_span_checker_keeps_different_semesters_in_separate_groups(
    make_course, make_assignment, make_program_entry
):
    # Arrange — same program/year/moed, but course A is a FALL obligation and
    # course B is a SPRING obligation.
    pe_fall = make_program_entry(
        program_id="83101", year=2, semester=Semester.FALL, requirement=Requirement.OBLIGATORY
    )
    pe_spring = make_program_entry(
        program_id="83101", year=2, semester=Semester.SPRI, requirement=Requirement.OBLIGATORY
    )
    course_a = make_course(course_id="A", program_entries=[pe_fall])
    course_b = make_course(course_id="B", program_entries=[pe_spring])
    slot_a = Slot(course=course_a, semester=Semester.FALL, moed=Moed.ALEPH,
                  candidateDates=[date(2026, 1, 1)])
    slot_b = Slot(course=course_b, semester=Semester.SPRI, moed=Moed.ALEPH,
                  candidateDates=[date(2026, 6, 1)])

    schedule = ExamSchedule()
    schedule.addAssignment(
        make_assignment(course=course_a, exam_date=date(2026, 1, 1), moed=Moed.ALEPH)
    )

    # Placing B one day after A would be a 1-day span — a violation if the two
    # semesters were wrongly merged into one group, given a strict k=10.
    candidate = make_assignment(course=course_b, exam_date=date(2026, 1, 2), moed=Moed.ALEPH)
    checker = _make_span_checker(k=10, courses=[course_a, course_b], slots=[slot_a, slot_b])

    # Act
    result = checker.check(candidate, schedule)

    # Assert — each semester's group has only one member, so no span is ever
    # measured and the placement is accepted.
    assert result is False


# ---------------------------------------------------------------------------
# MaxExamsPerDayChecker  TC-CHK-026..028
#
# Caps the total number of exams placed on any single calendar day, counted
# across all programs, at k. This checker needs no prepare() step: it simply
# reads how many courses already sit on the candidate's date.
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CHK-026: placing the (k+1)-th exam on a day is a violation.
# With k=3 and three exams already on June 1, the fourth must return True.
# ===========================================================================
def test_max_per_day_checker_rejects_when_count_exceeds_k(
    make_course, make_program_entry, make_assignment
):
    # Arrange — three exams already occupy June 1 (the daily limit is k=3).
    pe = make_program_entry(program_id="83101", year=2)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])
    course_d = make_course(course_id="D", program_entries=[pe])

    schedule = ExamSchedule()
    for course in (course_a, course_b, course_c):
        schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    # The candidate would be the fourth exam on June 1, exceeding k=3.
    candidate = make_assignment(course=course_d, exam_date=date(2026, 6, 1))
    checker = MaxExamsPerDayChecker(k=3)

    # Act
    result = checker.check(candidate, schedule)

    # Assert — 4 exams > k=3, so the placement is a conflict.
    assert result is True


# ===========================================================================
# TC-CHK-027: placing exactly the k-th exam on a day is allowed (boundary).
# With k=3 and two exams already on June 1, the third must return False.
# ===========================================================================
def test_max_per_day_checker_accepts_when_count_equals_k(
    make_course, make_program_entry, make_assignment
):
    # Arrange — two exams occupy June 1, leaving room for one more under k=3.
    pe = make_program_entry(program_id="83101", year=2)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    course_c = make_course(course_id="C", program_entries=[pe])

    schedule = ExamSchedule()
    for course in (course_a, course_b):
        schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    # The candidate is the third exam on June 1, exactly hitting k=3.
    candidate = make_assignment(course=course_c, exam_date=date(2026, 6, 1))
    checker = MaxExamsPerDayChecker(k=3)

    # Act
    result = checker.check(candidate, schedule)

    # Assert — 3 exams == k=3 is acceptable, so no conflict.
    assert result is False


# ===========================================================================
# TC-CHK-028: k=0 disables the rule. Even a crowded day produces no conflict,
# because a non-positive k short-circuits check() to False.
# ===========================================================================
def test_max_per_day_checker_disabled_when_k_is_zero(
    make_course, make_program_entry, make_assignment
):
    # Arrange — four exams already crowd June 1.
    pe = make_program_entry(program_id="83101", year=2)
    courses = [make_course(course_id=str(i), program_entries=[pe]) for i in range(5)]

    schedule = ExamSchedule()
    for course in courses[:4]:
        schedule.addAssignment(make_assignment(course=course, exam_date=date(2026, 6, 1)))

    # A fifth exam on the same day would normally break any sane limit.
    candidate = make_assignment(course=courses[4], exam_date=date(2026, 6, 1))
    checker = MaxExamsPerDayChecker(k=0)

    # Act
    result = checker.check(candidate, schedule)

    # Assert — k=0 turns the rule off, so nothing is ever a conflict.
    assert result is False