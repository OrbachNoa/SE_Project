"""Integration tests for ScreenRouter's registration, transitions, and history.

Confirms that ScreenRouter actually swaps the visible screen in the
QStackedWidget and tracks navigation history correctly: showing a screen
the first time records nothing to go back to, navigating to a second
screen pushes the previous one onto history, and back() both returns to
the previous screen and pops the history entry — it doesn't just flip
visibility without the bookkeeping that "back" depends on.

Conventions:
- This file uses a single TC-GUI-INT-NNN identifier scheme, independent of
  the TC-GUI-E2E- scheme used by Test_GUI.py.
- The test body is one Arrange section followed by three Act/Assert pairs,
  one per navigation step — appropriate here since each step's expected
  outcome depends on the screen state left by the previous step.
- `mock_controller` comes from the shared fixture in tests/conftest.py;
  InputScreen/OutputScreen need a live QApplication, provided via the
  shared `qapp` fixture (`pytestmark = pytest.mark.usefixtures("qapp")`).
"""
import pytest
from PyQt6.QtWidgets import QStackedWidget
from src.gui.core.ScreenRouter import ScreenRouter
from src.gui.features.input.InputScreen import InputScreen
from src.gui.features.output.OutputScreen import OutputScreen

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-GUI-INT-001: ScreenRouter must track history correctly across a
# forward-forward-back navigation sequence — showing the first screen
# records no history, showing a second pushes the first onto history, and
# back() both returns to it and pops that history entry.
# ===========================================================================
def test_gui_integration_screen_transitions(mock_controller):
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)

    input_screen = InputScreen(mock_controller, router)
    output_screen = OutputScreen(mock_controller, router)

    router.register("input", input_screen)
    router.register("output", output_screen)

    # Act — show the input screen first (nothing to go back to yet)
    router.show("input")
    # Assert
    assert router._current_name() == "input"

    # Act — navigate forward to the output screen
    router.show("output")
    # Assert — the input screen is now recorded in history
    assert router._current_name() == "output"
    assert router._history == ["input"]

    # Act — navigate back
    router.back()
    # Assert — back returns to input and consumes the history entry
    assert router._current_name() == "input"
    assert len(router._history) == 0
