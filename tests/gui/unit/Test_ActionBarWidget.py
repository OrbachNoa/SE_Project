import pytest
from unittest.mock import MagicMock
from src.gui.features.input.widgets.ActionBarWidget import ActionBarWidget

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-ABW-001: test default initial state of action bar controls.
# ===========================================================================
def test_action_bar_initial_state():
    # Arrange
    widget = ActionBarWidget()
    
    # Assert
    # Buttons exist
    assert widget.courses_load_btn is not None
    assert widget.periods_load_btn is not None
    assert widget.generate_btn is not None
    assert widget.cancel_btn is not None
    assert widget.view_results_btn is not None
    
    # Defaults
    assert widget.mode_replace.isChecked() is True
    assert widget.mode_update.isChecked() is False
    assert widget.generate_btn.isEnabled() is False
    assert widget.cancel_btn.isVisible() is False
    assert widget.view_results_btn.isVisible() is False

# ===========================================================================
# TC-ABW-002: test radio button toggling.
# ===========================================================================
def test_action_bar_mode_toggling():
    # Arrange
    widget = ActionBarWidget()
    
    # Act - switch to update mode
    widget.mode_update.setChecked(True)
    
    # Assert
    assert widget.mode_replace.isChecked() is False
    assert widget.mode_update.isChecked() is True
    
    # Act - switch back to replace mode
    widget.mode_replace.setChecked(True)
    
    # Assert
    assert widget.mode_replace.isChecked() is True
    assert widget.mode_update.isChecked() is False

# ===========================================================================
# TC-ABW-003: test button clicked signals.
# ===========================================================================
def test_action_bar_button_clicks():
    # Arrange
    widget = ActionBarWidget()
    
    mock_courses = MagicMock()
    mock_periods = MagicMock()
    mock_generate = MagicMock()
    mock_cancel = MagicMock()
    mock_view = MagicMock()
    
    widget.courses_load_btn.clicked.connect(mock_courses)
    widget.periods_load_btn.clicked.connect(mock_periods)
    widget.generate_btn.clicked.connect(mock_generate)
    widget.cancel_btn.clicked.connect(mock_cancel)
    widget.view_results_btn.clicked.connect(mock_view)
    
    # Act
    widget.courses_load_btn.click()
    widget.periods_load_btn.click()
    widget.generate_btn.setEnabled(True)
    widget.generate_btn.click()
    widget.cancel_btn.click()
    widget.view_results_btn.click()
    
    # Assert
    assert mock_courses.call_count == 1
    assert mock_periods.call_count == 1
    assert mock_generate.call_count == 1
    assert mock_cancel.call_count == 1
    assert mock_view.call_count == 1

# ===========================================================================
# TC-ABW-004: test that clicking a disabled generate button is rejected.
# ===========================================================================
def test_action_bar_disabled_click_rejection():
    # Arrange
    widget = ActionBarWidget()
    mock_generate = MagicMock()
    widget.generate_btn.clicked.connect(mock_generate)
    
    # Act
    widget.generate_btn.setEnabled(False)
    widget.generate_btn.click()
    
    # Assert
    assert mock_generate.call_count == 0

# ===========================================================================
# TC-ABW-005: test control states when entering running state.
# ===========================================================================
def test_action_bar_enter_running_state():
    # Arrange
    widget = ActionBarWidget()
    
    # Act - Simulate running mode (set by InputScreen)
    widget.generate_btn.setVisible(False)
    widget.cancel_btn.setVisible(True)
    widget.courses_load_btn.setEnabled(False)
    widget.periods_load_btn.setEnabled(False)
    
    # Assert
    assert widget.generate_btn.isHidden() is True
    assert widget.cancel_btn.isHidden() is False
    assert widget.courses_load_btn.isEnabled() is False
    assert widget.periods_load_btn.isEnabled() is False

# ===========================================================================
# TC-ABW-006: test control states when exiting running state.
# ===========================================================================
def test_action_bar_exit_running_state():
    # Arrange
    widget = ActionBarWidget()
    # Start in simulated running state
    widget.generate_btn.setVisible(False)
    widget.cancel_btn.setVisible(True)
    widget.courses_load_btn.setEnabled(False)
    widget.periods_load_btn.setEnabled(False)
    
    # Act - Simulate returning to normal mode
    widget.generate_btn.setVisible(True)
    widget.cancel_btn.setVisible(False)
    widget.courses_load_btn.setEnabled(True)
    widget.periods_load_btn.setEnabled(True)
    
    # Assert
    assert widget.generate_btn.isHidden() is False
    assert widget.cancel_btn.isHidden() is True
    assert widget.courses_load_btn.isEnabled() is True
    assert widget.periods_load_btn.isEnabled() is True
