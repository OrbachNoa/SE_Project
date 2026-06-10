import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QStackedWidget
from src.gui.core.ScreenRouter import ScreenRouter
from src.gui.features.input.InputScreen import InputScreen
from src.gui.features.output.OutputScreen import OutputScreen

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-GUI-INT-001: test that the AppRouter transitions between screens correctly.
# ===========================================================================
def test_gui_integration_screen_transitions(mock_controller):
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    
    input_screen = InputScreen(mock_controller, router)
    output_screen = OutputScreen(mock_controller, router)
    
    router.register("input", input_screen)
    router.register("output", output_screen)

    # Act - Show input screen
    router.show("input")
    assert router._current_name() == "input"

    # Navigate to output screen
    router.show("output")
    assert router._current_name() == "output"
    assert router._history == ["input"]

    # Navigate back
    router.back()
    assert router._current_name() == "input"
    assert len(router._history) == 0
