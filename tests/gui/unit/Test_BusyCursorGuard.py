"""
Test suite for BusyCursorGuard.

Scope   : Validates that the application wait cursor is properly set and restored,
          and that reference counting handles nested calls securely.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-BCG-001..002
"""
from unittest.mock import patch

from src.gui.common.BusyCursorGuard import BusyCursorGuard
import pytest

@pytest.fixture(autouse=True)
def reset_busy_cursor_depth():
    BusyCursorGuard._depth = 0
    yield
    BusyCursorGuard._depth = 0
# ===========================================================================
# TC-BCG-001: Context manager sets and restores override cursor securely
# ===========================================================================
@patch("PyQt6.QtGui.QGuiApplication.setOverrideCursor")
@patch("PyQt6.QtGui.QGuiApplication.restoreOverrideCursor")
def test_busy_cursor_guard_context_manager(mock_restore, mock_set, qapp):
    # Arrange
    # (Depth is reset by fixture)
    # Act
    with BusyCursorGuard():
        # Assert - inside context
        assert BusyCursorGuard._depth == 1
        mock_set.assert_called_once()
        mock_restore.assert_not_called()

    # Assert - outside context
    assert BusyCursorGuard._depth == 0
    mock_restore.assert_called_once()


# ===========================================================================
# TC-BCG-002: Nested push/pop calls maintain reference counts properly
# ===========================================================================
@patch("PyQt6.QtGui.QGuiApplication.setOverrideCursor")
@patch("PyQt6.QtGui.QGuiApplication.restoreOverrideCursor")
def test_busy_cursor_guard_nesting(mock_restore, mock_set, qapp):
    # Arrange
    # (Depth is reset by fixture)
    # Act
    BusyCursorGuard.push()
    BusyCursorGuard.push()

    # Assert 1
    assert BusyCursorGuard._depth == 2
    mock_set.assert_called_once()

    # Act 2
    BusyCursorGuard.pop()

    # Assert 2
    assert BusyCursorGuard._depth == 1
    mock_restore.assert_not_called()

    # Act 3
    BusyCursorGuard.pop()

    # Assert 3
    assert BusyCursorGuard._depth == 0
    mock_restore.assert_called_once()
