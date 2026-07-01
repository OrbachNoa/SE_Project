"""
Test suite for PeriodNavigator.

Scope   : Verifies the UI navigation logic for exam periods.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-PER-NAV-001..003
Fixtures: None
"""
from src.gui.features.output.PeriodNavigator import PeriodNavigator
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

# TC-PER-NAV-001
# PeriodNavigator must handle an empty period list gracefully,
# returning empty strings or lists instead of crashing.
def test_period_navigator_empty_state():
    # Arrange
    nav = PeriodNavigator()

    # Act / Assert
    assert nav.current_period is None
    assert nav.total == 0
    assert nav.can_move_previous() is False
    assert nav.can_move_next() is False
    assert nav.label() == ""
    assert nav.date_list() == []


# TC-PER-NAV-002
# PeriodNavigator must format the UI display label correctly based
# on the currently selected period index and total count.
def test_period_navigator_label_formatting():
    # Arrange
    p1 = PeriodEditViewModel("1", "A", "01-01-2023", "05-01-2023")
    p2 = PeriodEditViewModel("2", "B", "10-01-2023", "15-01-2023")
    nav = PeriodNavigator([p1, p2])

    # Act / Assert
    # At index 0 (first period)
    assert nav.label() == "Semester 1 - Moed A (1/2)"

    # Move to next
    nav.move_next()
    # At index 1 (second period)
    assert nav.label() == "Semester 2 - Moed B (2/2)"


# TC-PER-NAV-003
# PeriodNavigator must respect upper and lower boundaries when
# determining if navigation actions are allowed.
def test_period_navigator_boundaries():
    # Arrange
    p1 = PeriodEditViewModel("1", "A", "01-01-2023", "05-01-2023")
    p2 = PeriodEditViewModel("1", "B", "10-01-2023", "15-01-2023")
    nav = PeriodNavigator([p1, p2])

    # Act / Assert
    # Boundary: Start
    assert nav.can_move_previous() is False
    assert nav.can_move_next() is True

    # Attempt to move out of bounds (backward)
    assert nav.move_previous() is False

    # Move forward
    assert nav.move_next() is True

    # Boundary: End
    assert nav.can_move_previous() is True
    assert nav.can_move_next() is False

    # Attempt to move out of bounds (forward)
    assert nav.move_next() is False
