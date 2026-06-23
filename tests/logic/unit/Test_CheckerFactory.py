from datetime import date
import pytest

from src.models.Enums import Requirement
from src.logic.checkers.config.CheckerFactory import build_checkers
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.checkers.MoedOrderChecker import MoedOrderChecker
from src.logic.checkers.MinDaysBetweenExamsChecker import MinDaysBetweenExamsChecker, GapScope
from src.logic.checkers.ElectiveConflictCapChecker import ElectiveConflictCapChecker
from src.logic.checkers.ExamSpanChecker import ExamSpanChecker
from src.logic.checkers.MaxExamsPerDayChecker import MaxExamsPerDayChecker


# ---------------------------------------------------------------------------
# All criteria disabled TC-FAC-001..002
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FAC-001: build_checkers — a config with every threshold field at its
# default of None yields only the two base checkers.
# ===========================================================================
def test_build_checkers_returns_only_base_checkers_when_all_disabled():
    # Arrange
    config = ConstraintsConfig()

    # Act
    checkers = build_checkers(config, courses=[])

    # Assert
    assert len(checkers) == 2
    assert isinstance(checkers[0], ProgramYearConflictChecker)
    assert isinstance(checkers[1], MoedOrderChecker)


# ===========================================================================
# TC-FAC-002: build_checkers — passing config=None (no config object at
# all) is equivalent to every field being disabled.
# ===========================================================================
def test_build_checkers_returns_only_base_checkers_when_config_is_none():
    # Arrange
    config = None

    # Act
    checkers = build_checkers(config, courses=[])

    # Assert
    assert len(checkers) == 2
    assert isinstance(checkers[0], ProgramYearConflictChecker)
    assert isinstance(checkers[1], MoedOrderChecker)


# ---------------------------------------------------------------------------
# One criterion enabled — correct checker type, k transmitted, others
# absent TC-FAC-003..007
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FAC-003: build_checkers — only min_gap_obligatory (2.1) set adds
# exactly one MinDaysBetweenExamsChecker, scoped to OBLIGATORY_ONLY, with k
# forwarded unchanged.
# ===========================================================================
def test_build_checkers_adds_only_min_gap_obligatory_checker():
    # Arrange
    config = ConstraintsConfig(min_gap_obligatory=5)

    # Act
    checkers = build_checkers(config, courses=[])

    # Assert — exactly 3 checkers means no other threshold checker was added.
    assert len(checkers) == 3
    assert isinstance(checkers[2], MinDaysBetweenExamsChecker)
    assert checkers[2]._scope is GapScope.OBLIGATORY_ONLY
    assert checkers[2]._k == 5


# ===========================================================================
# TC-FAC-004: build_checkers — only min_gap_any (2.2) set adds exactly one
# MinDaysBetweenExamsChecker, scoped to ANY, with k forwarded unchanged.
# ===========================================================================
def test_build_checkers_adds_only_min_gap_any_checker():
    # Arrange
    config = ConstraintsConfig(min_gap_any=5)

    # Act
    checkers = build_checkers(config, courses=[])

    # Assert
    assert len(checkers) == 3
    assert isinstance(checkers[2], MinDaysBetweenExamsChecker)
    assert checkers[2]._scope is GapScope.ANY
    assert checkers[2]._k == 5


# ===========================================================================
# TC-FAC-005: build_checkers — only elective_conflict_cap (2.3) set adds
# exactly one ElectiveConflictCapChecker, with k forwarded unchanged.
# ===========================================================================
def test_build_checkers_adds_only_elective_conflict_cap_checker():
    # Arrange
    config = ConstraintsConfig(elective_conflict_cap=5)

    # Act
    checkers = build_checkers(config, courses=[])

    # Assert
    assert len(checkers) == 3
    assert isinstance(checkers[2], ElectiveConflictCapChecker)
    assert checkers[2]._k == 5


# ===========================================================================
# TC-FAC-006: build_checkers — only exam_span (2.4) set adds exactly one
# ExamSpanChecker, with k forwarded unchanged.
# ===========================================================================
def test_build_checkers_adds_only_exam_span_checker():
    # Arrange
    config = ConstraintsConfig(exam_span=5)

    # Act
    checkers = build_checkers(config, courses=[])

    # Assert
    assert len(checkers) == 3
    assert isinstance(checkers[2], ExamSpanChecker)
    assert checkers[2]._k == 5


# ===========================================================================
# TC-FAC-007: build_checkers — only max_exams_per_day (2.5) set adds
# exactly one MaxExamsPerDayChecker, with k forwarded unchanged.
# ===========================================================================
def test_build_checkers_adds_only_max_exams_per_day_checker():
    # Arrange
    config = ConstraintsConfig(max_exams_per_day=5)

    # Act
    checkers = build_checkers(config, courses=[])

    # Assert
    assert len(checkers) == 3
    assert isinstance(checkers[2], MaxExamsPerDayChecker)
    assert checkers[2]._k == 5


# ---------------------------------------------------------------------------
# All criteria enabled TC-FAC-008
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FAC-008: build_checkers — with every threshold field set to a distinct
# k, all five threshold checkers are present, each with its own k, and the
# two base checkers still lead the list.
# ===========================================================================
def test_build_checkers_includes_all_threshold_checkers_when_all_enabled():
    # Arrange
    config = ConstraintsConfig(
        min_gap_obligatory=3,
        min_gap_any=4,
        elective_conflict_cap=1,
        exam_span=20,
        max_exams_per_day=6,
    )

    # Act
    checkers = build_checkers(config, courses=[])

    # Assert
    assert len(checkers) == 7
    assert isinstance(checkers[0], ProgramYearConflictChecker)
    assert isinstance(checkers[1], MoedOrderChecker)

    min_gap_checkers = [c for c in checkers if isinstance(c, MinDaysBetweenExamsChecker)]
    assert len(min_gap_checkers) == 2
    k_by_scope = {c._scope: c._k for c in min_gap_checkers}
    assert k_by_scope[GapScope.OBLIGATORY_ONLY] == 3
    assert k_by_scope[GapScope.ANY] == 4

    elective_checker = next(c for c in checkers if isinstance(c, ElectiveConflictCapChecker))
    assert elective_checker._k == 1

    span_checker = next(c for c in checkers if isinstance(c, ExamSpanChecker))
    assert span_checker._k == 20

    max_per_day_checker = next(c for c in checkers if isinstance(c, MaxExamsPerDayChecker))
    assert max_per_day_checker._k == 6


# ---------------------------------------------------------------------------
# Base checkers always present and prepared TC-FAC-009
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-FAC-009: build_checkers — the two base checkers are always present and
# already prepared by the factory, so check() works without the caller
# invoking prepare() manually.
# ===========================================================================
def test_base_checkers_are_already_prepared_by_the_factory(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="A", program_entries=[pe])
    checkers = build_checkers(ConstraintsConfig(), [course])
    schedule = empty_schedule
    candidate = make_assignment(course=course, exam_date=date(2026, 6, 1))

    # Act — call check() directly; the test never calls prepare() itself.
    program_year_result = checkers[0].check(candidate, schedule)
    moed_order_result = checkers[1].check(candidate, schedule)

    # Assert — both base checkers ran without raising and found no conflict.
    assert isinstance(checkers[0], ProgramYearConflictChecker)
    assert isinstance(checkers[1], MoedOrderChecker)
    assert program_year_result is False
    assert moed_order_result is False
