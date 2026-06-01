import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QStackedWidget
from src.gui.screen import Screen
from src.gui.screen_router import ScreenRouter

# ------------------------------------------------------------------------
# Helper : Mock Screen class to avoid NotImplementedError
# ------------------------------------------------------------------------
class MockScreen(Screen):
    """Subclass of Screen that mocks on_enter and on_leave to avoid NotImplementedError."""
    def __init__(self):
        super().__init__()
        self.enter_called = 0
        self.leave_called = 0

    def on_enter(self) -> None:
        self.enter_called += 1

    def on_leave(self) -> None:
        self.leave_called += 1


# ===========================================================================
# TC-SR-001: Test screen router registration
# Verify that ScreenRouter registers screens and adds them to QStackedWidget.
# ===========================================================================
def test_screen_router_registration():
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    s1 = MockScreen()
    s2 = MockScreen()
    
    # Act
    router.register("screen1", s1)
    router.register("screen2", s2)
    
    # Assert
    assert router._screens["screen1"] == s1
    assert router._screens["screen2"] == s2
    assert stack.indexOf(s1) != -1
    assert stack.indexOf(s2) != -1

# ===========================================================================
# TC-SR-002: Test that showing a registered screen makes it active.
# ===========================================================================
def test_screen_router_navigation_initial():
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    s1 = MockScreen()
    router.register("screen1", s1)
    
    # Act
    router.show("screen1")
    
    # Assert
    assert stack.currentWidget() == s1
    assert s1.enter_called == 1
    assert s1.leave_called == 0
    assert router._history == []


# ===========================================================================
# TC-SR-003: Test that navigating to a second screen pushes the first screen to history.
# ===========================================================================
def test_screen_router_navigation_swap():
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    s1 = MockScreen()
    s2 = MockScreen()
    router.register("screen1", s1)
    router.register("screen2", s2)
    router.show("screen1")
    
    # Act
    router.show("screen2")
    
    # Assert
    assert stack.currentWidget() == s2
    assert s1.leave_called == 1
    assert s2.enter_called == 1
    assert router._history == ["screen1"]


# ===========================================================================
# TC-SR-004: Test that back navigation pops history and shows previous screen.
# ===========================================================================
def test_screen_router_back_navigation_success():
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    s1 = MockScreen()
    s2 = MockScreen()
    router.register("screen1", s1)
    router.register("screen2", s2)
    router.show("screen1")
    router.show("screen2")
    
    # Act
    router.back()
    
    # Assert
    assert stack.currentWidget() == s1
    assert s2.leave_called == 1
    assert s1.enter_called == 2
    assert router._history == []


# ===========================================================================
# TC-SR-005: Test that back navigation is a safe no-op when history is empty.
# ===========================================================================
def test_screen_router_back_navigation_empty_history():
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    s1 = MockScreen()
    router.register("screen1", s1)
    router.show("screen1")
    
    # Act
    router.back()
    
    # Assert
    assert stack.currentWidget() == s1
    assert s1.enter_called == 1
    assert s1.leave_called == 0
    assert router._history == []


# ===========================================================================
# TC-SR-006: Test that showing an unregistered screen raises KeyError.
# ===========================================================================
def test_screen_router_show_unregistered():
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    
    # Act & Assert
    with pytest.raises(KeyError):
        router.show("unregistered")
