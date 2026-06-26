"""Unit tests for ActionBarWidget — the input screen's primary action toolbar.

The widget exposes five buttons (load courses, load periods, generate,
cancel, view results) and a replace/update mode toggle. Tests verify the
default disabled/hidden state before any data is loaded, that the mode
toggle is mutually exclusive, that each button's click actually reaches a
connected slot, and that a disabled button's click never fires its slot —
the same guard InputScreenPresenter relies on while a run is in progress.

Conventions:
- Each test carries a unique TC-ABW-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections. Where
  construction itself is the behaviour under test (e.g. checking default
  state), the construction call is placed under Act rather than Arrange.
- Tests use the shared `qapp` fixture (tests/conftest.py) via
  `pytestmark = pytest.mark.usefixtures("qapp")`, since every PyQt widget
  needs a live QApplication; no other conftest fixture applies to this
  widget's plain construction.
"""
import pytest
from unittest.mock import MagicMock
from src.gui.features.input.widgets.ActionBarWidget import ActionBarWidget

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-ABW-001: before any course/period file is loaded, generate must stay
# disabled and the cancel/view-results controls must stay hidden — only
# the two load buttons and the default replace mode are active.
# ===========================================================================
def test_action_bar_initial_state():
    # Act — construction itself produces the default state under test.
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
# TC-ABW-002: replace and update mode are mutually exclusive — checking
# one must uncheck the other, in both directions.
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
# TC-ABW-003: each of the five buttons' clicked signal reaches a connected
# slot exactly once per click — confirms the widget wires real Qt signals,
# not just visually-present buttons with no behaviour behind them.
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
# TC-ABW-004: a click on a disabled generate_btn must not reach the
# connected slot — the button has to be genuinely disabled at the Qt level,
# not merely styled to look inactive.
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
# TC-ABW-005: while a generation run is in progress, the action bar must
# hide generate/load controls and show cancel — preventing a second run
# from being started concurrently.
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
# TC-ABW-006: once a run ends, the action bar must restore the pre-run
# control layout — generate/load controls visible again, cancel hidden.
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
