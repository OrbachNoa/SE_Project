import pytest
from unittest.mock import MagicMock
from src.gui.screens.InputScreen import InputScreen
from src.application.ImportBoundary import ImportMode

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-UI-IN-001: test courses upload button.
# ===========================================================================
def test_courses_upload_button_exists(mock_controller, mock_router):
    # Act
    screen = InputScreen(mock_controller, mock_router)
    
    # Assert
    assert screen._courses_load_btn is not None
    assert "Load Courses" in screen._courses_load_btn.text()

# ===========================================================================
# TC-UI-IN-002: test periods upload button.
# ===========================================================================
def test_periods_upload_button_exists(mock_controller, mock_router):
    # Act
    screen = InputScreen(mock_controller, mock_router)
    
    # Assert
    assert screen._periods_load_btn is not None
    assert "Load Periods" in screen._periods_load_btn.text()

# ===========================================================================
# TC-UI-IN-003: test replace mode is default selected.
# ===========================================================================
def test_replace_mode_default_selected(mock_controller, mock_router):
    # Act
    screen = InputScreen(mock_controller, mock_router)
    
    # Assert
    assert screen._mode_replace.isChecked() is True
    assert screen._mode_update.isChecked() is False

# ===========================================================================
# TC-UI-IN-004: test that the program selection updates the view.
# ===========================================================================
def test_program_selection_updates_view(mock_controller, mock_router):
    # Arrange
    screen = InputScreen(mock_controller, mock_router)
    
    # Act
    screen._selected_program_ids = ["83101", "83102"]
    screen._refresh_program_summary()
    
    # Assert
    assert screen._programs_count_badge.text() == "2 / 5"
