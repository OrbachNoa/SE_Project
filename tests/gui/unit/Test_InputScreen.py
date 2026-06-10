import pytest
from unittest.mock import MagicMock, patch
from src.gui.features.input.InputScreen import InputScreen
from src.application.ImportBoundary import ImportMode

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-IN-UI-001: test courses upload button.
# ===========================================================================
def test_courses_upload_button_exists(mock_controller, mock_router):
    # Act
    screen = InputScreen(mock_controller, mock_router)
    
    # Assert
    assert screen._courses_load_btn is not None
    assert "Load Courses" in screen._courses_load_btn.text()

# ===========================================================================
# TC-IN-UI-002: test periods upload button.
# ===========================================================================
def test_periods_upload_button_exists(mock_controller, mock_router):
    # Act
    screen = InputScreen(mock_controller, mock_router)
    
    # Assert
    assert screen._periods_load_btn is not None
    assert "Load Periods" in screen._periods_load_btn.text()

# ===========================================================================
# TC-IN-UI-003: test replace mode is default selected.
# ===========================================================================
def test_replace_mode_default_selected(mock_controller, mock_router):
    # Act
    screen = InputScreen(mock_controller, mock_router)
    
    # Assert
    assert screen._mode_replace.isChecked() is True
    assert screen._mode_update.isChecked() is False

# ===========================================================================
# TC-IN-UI-004: test that the program selection updates the view.
# ===========================================================================
def test_program_selection_updates_view(mock_controller, mock_router):
    # Arrange
    screen = InputScreen(mock_controller, mock_router)
    
    # Act
    screen._selected_program_ids = ["83101", "83102"]
    screen._refresh_program_summary()
    
    # Assert
    assert screen._programs_count_badge.text() == "2 / 5"

# ===========================================================================
# TC-IN-UI-005: test that clicking the generate button starts scheduling.
# ===========================================================================
def test_generate_schedules_button_clicks(mock_controller, mock_router):
    # Arrange
    screen = InputScreen(mock_controller, mock_router)
    
    # Select programs and enable generate button
    screen._selected_program_ids = ["83101"]
    screen._refresh_program_summary()
    screen._presenter._courses_loaded = True
    screen._presenter._periods_loaded = True
    screen.action_bar.generate_btn.setEnabled(True)
    
    # Act
    screen.action_bar.generate_btn.click()
    
    # Assert
    assert mock_controller.generate_schedules.call_count == 1
    assert mock_controller.generate_schedules.call_args[0][0] == ["83101"]

# ===========================================================================
# TC-IN-UI-006: test that generation is rejected if no study programs are selected.
# ===========================================================================
def test_generate_schedules_rejected_if_no_programs_selected(mock_controller, mock_router):
    # Arrange
    screen = InputScreen(mock_controller, mock_router)
    
    # Enable generate button but keep programs list empty
    screen._presenter._courses_loaded = True
    screen._presenter._periods_loaded = True
    screen.action_bar.generate_btn.setEnabled(True)
    screen._selected_program_ids = []
    screen._refresh_program_summary()
    
    # Act
    screen.action_bar.generate_btn.click()
    
    # Assert
    # 1. Controller should NOT have been called
    assert mock_controller.generate_schedules.call_count == 0
    # 2. Error label should be visible and show error message
    assert not screen.program_error_label.isHidden()
    assert screen.program_error_label.text() == "Please select at least one study program."

# ===========================================================================
# TC-IN-UI-007: test that failing file import shows a critical message box.
# ===========================================================================
def test_load_courses_failure_shows_error_box(mock_controller, mock_router):
    # Arrange
    from src.application.ImportBoundary import ImportResult
    
    screen = InputScreen(mock_controller, mock_router)
    screen.prompt_for_file = MagicMock(return_value="invalid_courses.csv")
    
    # Mock critical box
    with patch("src.gui.features.input.InputScreen.QMessageBox.critical") as mock_critical:
        mock_controller.load_file.return_value = ImportResult(
            success=False,
            loaded_count=0,
            errors=["Column mismatch error", "Missing courseId header"]
        )
        
        # Act
        screen.action_bar.courses_load_btn.click()
        
        # Assert
        # 1. QMessageBox.critical should have been called with the error details
        assert mock_critical.call_count == 1
        message = mock_critical.call_args[0][2]
        assert "courses" in message
        assert "Column mismatch error" in message
        assert "Missing courseId header" in message
        
        # 2. Courses loaded state remains False
        assert screen._presenter._courses_loaded is False

# ===========================================================================
# TC-IN-UI-008: test that failing periods file import shows a critical message box.
# ===========================================================================
def test_load_periods_failure_shows_error_box(mock_controller, mock_router):
    # Arrange
    from src.application.ImportBoundary import ImportResult
    
    screen = InputScreen(mock_controller, mock_router)
    screen.prompt_for_file = MagicMock(return_value="invalid_periods.csv")
    
    # Mock critical box
    with patch("src.gui.features.input.InputScreen.QMessageBox.critical") as mock_critical:
        mock_controller.load_file.return_value = ImportResult(
            success=False,
            loaded_count=0,
            errors=["Invalid date format", "Missing start date"]
        )
        
        # Act
        screen.action_bar.periods_load_btn.click()
        
        # Assert
        # 1. QMessageBox.critical should have been called with the error details
        assert mock_critical.call_count == 1
        message = mock_critical.call_args[0][2]
        assert "periods" in message
        assert "Invalid date format" in message
        assert "Missing start date" in message
        
        # 2. Periods loaded state remains False
        assert screen._presenter._periods_loaded is False

