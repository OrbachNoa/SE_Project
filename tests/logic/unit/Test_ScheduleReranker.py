"""Tests for ScheduleReranker.rerank: ordering ScheduleDTOs by stored scores.

These cases cover single- and multi-criterion sorting, priority reversal,
empty/single-element inputs, negated (fewer-is-better) criteria, sort
stability on ties, an empty priority list, and a missing score key. Each
test is identified by a sequential TC-RNK-NNN tag and follows the
Arrange/Act/Assert structure in its body.

Fixture policy: none of the shared fixtures from tests/conftest.py are
used here. Every ScheduleDTO is built inline through the local _dto()
helper below, since these tests only need a `scores` dict and have no
need for the domain-object factories (make_course, make_period, etc.)
defined in conftest.py.
"""
import pytest

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.application.state.ScheduleReranker import rerank
from src.logic.comparators.ScheduleScorer import (
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
)


def _dto(scores: dict) -> ScheduleDTO:
    """Build a ScheduleDTO carrying only the scores relevant to a test."""
    return ScheduleDTO(scores=scores)


# ---------------------------------------------------------------------------
# Single-criterion sort TC-RNK-001
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-RNK-001: rerank — a single criterion sorts schedules in descending
# order, with the highest score ranked first.
# ===========================================================================
def test_rerank_sorts_single_criterion_descending():
    # Arrange
    low = _dto({MANDATORY_SPAN: 2.0})
    mid = _dto({MANDATORY_SPAN: 4.0})
    high = _dto({MANDATORY_SPAN: 10.0})

    # Act
    result = rerank([low, high, mid], [MANDATORY_SPAN])

    # Assert
    assert result == [high, mid, low]


# ---------------------------------------------------------------------------
# Multi-criterion tie-break TC-RNK-002
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-RNK-002: rerank — when two schedules tie on the primary criterion, the
# second criterion in the priority list breaks the tie.
# ===========================================================================
def test_rerank_uses_second_criterion_as_tiebreaker():
    # Arrange
    tied_low_gap = _dto({MANDATORY_SPAN: 5.0, AVG_ALL_COURSES_GAP: 3.0})
    tied_high_gap = _dto({MANDATORY_SPAN: 5.0, AVG_ALL_COURSES_GAP: 7.0})

    # Act
    result = rerank(
        [tied_low_gap, tied_high_gap],
        [MANDATORY_SPAN, AVG_ALL_COURSES_GAP],
    )

    # Assert
    assert result == [tied_high_gap, tied_low_gap]


# ---------------------------------------------------------------------------
# Priority order reversal TC-RNK-003
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-RNK-003: rerank — swapping which criterion is primary changes which
# schedule is ranked first.
# ===========================================================================
def test_rerank_changes_order_when_priority_is_reversed():
    # Arrange
    span_winner = _dto({MANDATORY_SPAN: 10.0, AVG_ALL_COURSES_GAP: 1.0})
    gap_winner = _dto({MANDATORY_SPAN: 1.0, AVG_ALL_COURSES_GAP: 10.0})
    schedules = [span_winner, gap_winner]

    # Act
    span_first = rerank(schedules, [MANDATORY_SPAN, AVG_ALL_COURSES_GAP])
    gap_first = rerank(schedules, [AVG_ALL_COURSES_GAP, MANDATORY_SPAN])

    # Assert
    assert span_first == [span_winner, gap_winner]
    assert gap_first == [gap_winner, span_winner]


# ---------------------------------------------------------------------------
# Empty and single-element lists TC-RNK-004..005
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-RNK-004: rerank — an empty schedule list returns an empty list
# without raising.
# ===========================================================================
def test_rerank_returns_empty_list_for_empty_input():
    # Arrange
    schedules = []

    # Act
    result = rerank(schedules, [MANDATORY_SPAN])

    # Assert
    assert result == []


# ===========================================================================
# TC-RNK-005: rerank — a single schedule is returned unchanged, regardless
# of the requested priority.
# ===========================================================================
def test_rerank_returns_single_schedule_unchanged():
    # Arrange
    only = _dto({MANDATORY_SPAN: 7.0})

    # Act
    result = rerank([only], [MANDATORY_SPAN])

    # Assert
    assert result == [only]


# ---------------------------------------------------------------------------
# Negated (fewer-is-better) criteria TC-RNK-006..007
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-RNK-006: rerank — for ELECTIVE_CONFLICTS, a less negative stored score
# (fewer conflicts) ranks above a more negative one.
# ===========================================================================
def test_rerank_orders_elective_conflicts_less_negative_first():
    # Arrange
    fewer_conflicts = _dto({ELECTIVE_CONFLICTS: -1.0})
    more_conflicts = _dto({ELECTIVE_CONFLICTS: -3.0})

    # Act
    result = rerank([more_conflicts, fewer_conflicts], [ELECTIVE_CONFLICTS])

    # Assert
    assert result == [fewer_conflicts, more_conflicts]


# ===========================================================================
# TC-RNK-007: rerank — for MAX_EXAMS_PER_DAY, a less negative stored score
# (fewer exams on the busiest day) ranks above a more negative one.
# ===========================================================================
def test_rerank_orders_max_exams_per_day_less_negative_first():
    # Arrange
    lighter_day = _dto({MAX_EXAMS_PER_DAY: -2.0})
    heavier_day = _dto({MAX_EXAMS_PER_DAY: -5.0})

    # Act
    result = rerank([heavier_day, lighter_day], [MAX_EXAMS_PER_DAY])

    # Assert
    assert result == [lighter_day, heavier_day]


# ---------------------------------------------------------------------------
# Sort stability TC-RNK-008
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-RNK-008: rerank — two schedules with identical scores on every
# requested criterion keep their original relative order.
# ===========================================================================
def test_rerank_is_stable_for_equal_scores():
    # Arrange
    first = _dto({MANDATORY_SPAN: 5.0})
    second = _dto({MANDATORY_SPAN: 5.0})

    # Act
    original_order = rerank([first, second], [MANDATORY_SPAN])
    swapped_order = rerank([second, first], [MANDATORY_SPAN])

    # Assert
    assert original_order == [first, second]
    assert swapped_order == [second, first]


# ---------------------------------------------------------------------------
# Documented contract details TC-RNK-009..010
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-RNK-009: rerank — an empty priority list means "no sort": the
# schedules come back in their original order, as a new list.
# ===========================================================================
def test_rerank_with_empty_priority_preserves_original_order():
    # Arrange
    better = _dto({MANDATORY_SPAN: 99.0})
    worse = _dto({MANDATORY_SPAN: 1.0})
    schedules = [better, worse]

    # Act
    result = rerank(schedules, [])

    # Assert — order is untouched even though "worse" has the lower score,
    # and the function returns a new list rather than the same reference.
    assert result == [better, worse]
    assert result is not schedules


# ===========================================================================
# TC-RNK-010: rerank — a schedule missing the requested score key falls
# back to the sentinel and sorts to the bottom instead of raising.
# ===========================================================================
def test_rerank_sorts_missing_score_to_the_bottom():
    # Arrange
    scored = _dto({MANDATORY_SPAN: 1.0})
    unscored = _dto({})

    # Act
    result = rerank([unscored, scored], [MANDATORY_SPAN])

    # Assert
    assert result == [scored, unscored]
