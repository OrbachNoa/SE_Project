"""Unit tests for PeriodNavigator — cycling through exam periods for editing.

The calendar editor screen lets the user step through one ExamPeriod at a
time (as a PeriodEditViewModel) to set excluded dates. PeriodNavigator owns
the current index and the boundary logic: it must not be possible to move
past either end of the list, the label/date-list must reflect whichever
period is currently selected, and an invalid date range (start after end)
must yield an empty date list rather than raising or looping.

Conventions:
- Each test carries a unique TC-PN-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections. Where
  construction itself is the behaviour under test, the construction call is
  placed under Act rather than Arrange.
- No conftest fixture models PeriodEditViewModel or PeriodNavigator, so
  every test builds them directly; this is a plain Python class with no
  Qt or I/O dependency, so no `qapp` fixture is needed either.
"""
from src.gui.features.output.PeriodNavigator import PeriodNavigator
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

# ===========================================================================
# TC-PN-001: a navigator constructed with no periods must report a safe
# empty state (zero total, no current period, no movement possible) rather
# than raising or leaving attributes uninitialised.
# ===========================================================================
def test_period_navigator_init_empty():
    # Act
    nav = PeriodNavigator()
    
    # Assert
    assert nav.current_index == 0
    assert nav.total == 0
    assert nav.current_period is None
    assert nav.label() == ""
    assert nav.date_list() == []
    assert nav.can_move_previous() is False
    assert nav.can_move_next() is False

# ===========================================================================
# TC-PN-002: constructing with a non-empty list must select the first
# period as current and report the correct total immediately, with no
# separate "load" step required.
# ===========================================================================
def test_period_navigator_init_with_periods():
    # Arrange
    p1 = PeriodEditViewModel(semester="A", moed="A", start_date="2026-06-01", end_date="2026-06-03")
    
    # Act
    nav = PeriodNavigator([p1])
    
    # Assert
    assert nav.total == 1
    assert nav.current_period == p1

# ===========================================================================
# TC-PN-003: reset() must replace the period list and snap the index back
# to the first period — a stale index from the previous list must not
# carry over and point past the new list's bounds.
# ===========================================================================
def test_period_navigator_reset():
    # Arrange
    p1 = PeriodEditViewModel(semester="A", moed="A", start_date="2026-06-01", end_date="2026-06-03")
    p2 = PeriodEditViewModel(semester="A", moed="B", start_date="2026-07-01", end_date="2026-07-03")
    nav = PeriodNavigator([p1])
    
    # Act
    nav.reset([p1, p2])
    
    # Assert
    assert nav.total == 2
    assert nav.current_index == 0
    assert nav.current_period == p1

# ===========================================================================
# TC-PN-004: move_previous() at index 0 must refuse the move (return
# False, index unchanged) instead of wrapping around or going negative.
# ===========================================================================
def test_period_navigator_cannot_move_previous_at_start():
    # Arrange
    p1 = PeriodEditViewModel(semester="A", moed="A", start_date="2026-06-01", end_date="2026-06-03")
    p2 = PeriodEditViewModel(semester="A", moed="B", start_date="2026-07-01", end_date="2026-07-03")
    nav = PeriodNavigator([p1, p2])
    
    # Act
    result = nav.move_previous()
    
    # Assert
    assert result is False
    assert nav.current_index == 0
    assert nav.can_move_previous() is False

# ===========================================================================
# TC-PN-005: move_next() must advance the index, switch current_period to
# the next entry, and flip the boundary flags (can move back, can't move
# further forward) in the same call — not just one of these in isolation.
# ===========================================================================
def test_period_navigator_move_next():
    # Arrange
    p1 = PeriodEditViewModel(semester="A", moed="A", start_date="2026-06-01", end_date="2026-06-03")
    p2 = PeriodEditViewModel(semester="A", moed="B", start_date="2026-07-01", end_date="2026-07-03")
    nav = PeriodNavigator([p1, p2])
    
    # Act
    result = nav.move_next()
    
    # Assert
    assert result is True
    assert nav.current_index == 1
    assert nav.current_period == p2
    assert nav.can_move_previous() is True
    assert nav.can_move_next() is False

# ===========================================================================
# TC-PN-006: move_next() at the last index must refuse the move (return
# False, index unchanged) instead of running past the end of the list.
# ===========================================================================
def test_period_navigator_cannot_move_next_at_end():
    # Arrange
    p1 = PeriodEditViewModel(semester="A", moed="A", start_date="2026-06-01", end_date="2026-06-03")
    p2 = PeriodEditViewModel(semester="A", moed="B", start_date="2026-07-01", end_date="2026-07-03")
    nav = PeriodNavigator([p1, p2])
    nav.move_next()
    
    # Act
    result = nav.move_next()
    
    # Assert
    assert result is False
    assert nav.current_index == 1
    assert nav.can_move_next() is False

# ===========================================================================
# TC-PN-007: move_previous() must mirror move_next() — stepping back from
# index 1 returns to index 0 and restores the first period as current.
# ===========================================================================
def test_period_navigator_move_previous():
    # Arrange
    p1 = PeriodEditViewModel(semester="A", moed="A", start_date="2026-06-01", end_date="2026-06-03")
    p2 = PeriodEditViewModel(semester="A", moed="B", start_date="2026-07-01", end_date="2026-07-03")
    nav = PeriodNavigator([p1, p2])
    nav.move_next()
    
    # Act
    result = nav.move_previous()
    
    # Assert
    assert result is True
    assert nav.current_index == 0
    assert nav.current_period == p1

# ===========================================================================
# TC-PN-008: label() must combine semester, moed, and a 1-based
# "(position/total)" counter into one human-readable string for the
# editor's header — not just expose the raw semester/moed values.
# ===========================================================================
def test_period_navigator_label():
    # Arrange
    p1 = PeriodEditViewModel(semester="FALL", moed="ALEPH", start_date="2026-06-01", end_date="2026-06-03")
    p2 = PeriodEditViewModel(semester="SPRING", moed="BET", start_date="2026-07-01", end_date="2026-07-03")
    nav = PeriodNavigator([p1, p2])
    
    # Act
    lbl = nav.label()
    
    # Assert
    assert lbl == "Semester FALL - Moed ALEPH (1/2)"

# ===========================================================================
# TC-PN-009: label() must update after move_next() — it has to read the
# navigator's *current* state, not be cached from construction time.
# ===========================================================================
def test_period_navigator_label_after_navigation():
    # Arrange
    p1 = PeriodEditViewModel(semester="FALL", moed="ALEPH", start_date="2026-06-01", end_date="2026-06-03")
    p2 = PeriodEditViewModel(semester="SPRING", moed="BET", start_date="2026-07-01", end_date="2026-07-03")
    nav = PeriodNavigator([p1, p2])
    nav.move_next()
    
    # Act
    lbl = nav.label()
    
    # Assert
    assert lbl == "Semester SPRING - Moed BET (2/2)"

# ===========================================================================
# TC-PN-010: date_list() must enumerate every calendar date from start to
# end inclusive, in order — the editor grid needs one cell per date.
# ===========================================================================
def test_period_navigator_date_list():
    # Arrange
    p1 = PeriodEditViewModel(semester="FALL", moed="ALEPH", start_date="2026-06-01", end_date="2026-06-03")
    nav = PeriodNavigator([p1])
    
    # Act
    dates = nav.date_list()
    
    # Assert
    assert dates == ["2026-06-01", "2026-06-02", "2026-06-03"]

# ===========================================================================
# TC-PN-011: an inverted date range (start after end) must produce an
# empty date_list rather than raising or silently iterating backwards —
# the calendar grid would otherwise render with the wrong day count.
# ===========================================================================
def test_period_navigator_invalid_date_range_reject():
    # Arrange
    p1 = PeriodEditViewModel(semester="FALL", moed="ALEPH", start_date="2026-06-10", end_date="2026-06-03")
    nav = PeriodNavigator([p1])
    
    # Act
    dates = nav.date_list()
    
    # Assert
    assert dates == []
