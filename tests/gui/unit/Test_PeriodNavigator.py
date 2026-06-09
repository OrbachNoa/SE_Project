import pytest
from src.gui.features.output.PeriodNavigator import PeriodNavigator
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

# ===========================================================================
# TC-PN-001: test constructor and empty state.
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
# TC-PN-002: test initialization with periods list.
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
# TC-PN-003: test reset method updates periods.
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
# TC-PN-004: test that the period navigator cannot move previous at the beginning.
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
# TC-PN-005: test that the period navigator can move next and updates current index and period.
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
# TC-PN-006: test that the period navigator cannot move next at the end.
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
# TC-PN-007: test that the period navigator can move previous and updates current index and period.
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
# TC-PN-008: test initial period label generation.
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
# TC-PN-009: test period label generation after navigation.
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
# TC-PN-010: test date list generation.
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
# TC-PN-011: test that the date list is empty for invalid date range (start > end).
# ===========================================================================
def test_period_navigator_invalid_date_range_reject():
    # Arrange
    p1 = PeriodEditViewModel(semester="FALL", moed="ALEPH", start_date="2026-06-10", end_date="2026-06-03")
    nav = PeriodNavigator([p1])
    
    # Act
    dates = nav.date_list()
    
    # Assert
    assert dates == []
