"""
Test suite for App (the main window composition root).

Scope   : Lightweight smoke tests for src/gui/core/app.py — constructing
          App with a heavily mocked controller wires the expected window
          title, registers every screen with the router, starts on the
          input screen, and closeEvent() notifies the controller before
          accepting the close.

          App is a composition root: it directly instantiates the entire
          screen graph (InputScreen, OutputScreen, and four cluster
          screens). It is still practical to smoke-test in isolation
          because every one of those screens only needs (controller,
          router) at construction time, and the shared mock_controller
          fixture already provides every attribute/signal they touch
          during __init__ — confirmed by the fact that this same
          mock_controller is already used to construct real InputScreen/
          OutputScreen instances in tests/gui/integration/Test_GuiIntegration.py.
          This file therefore favors a few structural assertions over no
          coverage at all, rather than treating composition roots as
          inherently untestable.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004
Fixtures: qapp, mock_controller (tests/conftest.py)
"""
import pytest
from PyQt6.QtGui import QCloseEvent

from src.gui.core.app import (
    App,
    SCREEN_CLUSTER_CALENDAR_OVERLAY,
    SCREEN_CLUSTER_COMPARE,
    SCREEN_CLUSTER_DETAIL,
    SCREEN_CLUSTERS,
    SCREEN_INPUT,
    SCREEN_OUTPUT,
)

pytestmark = pytest.mark.usefixtures("qapp")


# TC-APP-001
# Constructing App must set the expected window title and a sane initial
# size, confirming the composition root actually finished building without
# raising.
def test_app_construction_sets_window_title(mock_controller):
    # Act
    window = App(mock_controller)

    # Assert
    assert window.windowTitle() == "Exam Scheduler v3.1"
    assert window.minimumWidth() == 800
    assert window.minimumHeight() == 560


# TC-APP-002
# Constructing App must register all six screens with the router, under
# the exact names the rest of the app depends on for navigation.
def test_app_construction_registers_all_screens(mock_controller):
    # Act
    window = App(mock_controller)

    # Assert
    registered = window._router._screens.keys()
    for name in (
        SCREEN_INPUT,
        SCREEN_OUTPUT,
        SCREEN_CLUSTERS,
        SCREEN_CLUSTER_DETAIL,
        SCREEN_CLUSTER_COMPARE,
        SCREEN_CLUSTER_CALENDAR_OVERLAY,
    ):
        assert name in registered


# TC-APP-003
# Constructing App must leave the router showing the input screen first,
# since that's the very first thing a user should see on launch.
def test_app_construction_starts_on_input_screen(mock_controller):
    # Act
    window = App(mock_controller)

    # Assert
    assert window._router._current_name() == SCREEN_INPUT


# TC-APP-004
# closeEvent must notify the controller via on_app_closing() and accept the
# close event, so the window doesn't linger or fail to release background
# resources when the user clicks the close button.
def test_app_close_event_notifies_controller_and_accepts(mock_controller):
    # Arrange
    window = App(mock_controller)
    event = QCloseEvent()

    # Act
    window.closeEvent(event)

    # Assert
    mock_controller.on_app_closing.assert_called_once()
    assert event.isAccepted() is True
