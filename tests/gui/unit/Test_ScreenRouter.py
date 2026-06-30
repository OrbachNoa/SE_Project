"""
Test suite for ScreenRouter.

Scope   : Verifies core navigation logic (history pushing, popping, preventing duplicates).
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-RTR-001..004
"""
import pytest
from unittest.mock import MagicMock
from src.gui.core.ScreenRouter import ScreenRouter
from gui.core.screen import Screen

pytestmark = pytest.mark.usefixtures("qapp")

class DummyScreen(Screen):
    """A dummy screen for testing router transitions."""
    def __init__(self):
        super().__init__()
        self.entered = 0
        self.left = 0

    def on_enter(self) -> None:
        self.entered += 1

    def on_leave(self) -> None:
        self.left += 1

class MockStack:
    def __init__(self):
        self._current = None

    def addWidget(self, widget):
        if self._current is None:
            self._current = widget

    def setCurrentWidget(self, widget):
        self._current = widget

    def currentWidget(self):
        return self._current

# TC-GUI-RTR-001
def test_router_basic_navigation():
    # Arrange
    stack = MockStack()
    router = ScreenRouter(stack)
    
    screen_a = DummyScreen()
    screen_b = DummyScreen()
    
    router.register("A", screen_a)
    router.register("B", screen_b)
    
    # Act
    router.show("A")
    router.show("B")
    
    # Assert
    assert router.get_screen("B") == screen_b
    assert screen_a.entered == 1
    assert screen_a.left == 1
    assert screen_b.entered == 1

# TC-GUI-RTR-002
def test_router_back_history():
    # Arrange
    stack = MockStack()
    router = ScreenRouter(stack)
    
    screen_a = DummyScreen()
    screen_b = DummyScreen()
    screen_c = DummyScreen()
    
    router.register("A", screen_a)
    router.register("B", screen_b)
    router.register("C", screen_c)
    
    # Act
    router.show("A")
    router.show("B")
    router.show("C")
    router.back()
    
    # Assert
    assert router._current_name() == "B"
    assert screen_b.entered == 2
    assert screen_c.left == 1

# TC-GUI-RTR-003
def test_router_replace_history():
    # Arrange
    stack = MockStack()
    router = ScreenRouter(stack)
    
    screen_a = DummyScreen()
    screen_b = DummyScreen()
    
    router.register("A", screen_a)
    router.register("B", screen_b)
    
    # Act
    router.show("A")
    router.replace("B")
    
    # Assert
    assert router._history == []  # 'A' was NOT pushed because of replace
    
    # Act (attempting to go back should do nothing)
    router.back()
    
    # Assert
    assert router._current_name() == "B"

# TC-GUI-RTR-004
def test_router_prevents_duplicate_history():
    # Arrange
    stack = MockStack()
    router = ScreenRouter(stack)
    
    screen_a = DummyScreen()
    router.register("A", screen_a)
    
    # Act
    router.show("A")
    router.show("A")
    router.show("A")
    
    # Assert
    assert router._history == []  # Transitioning to the same screen doesn't push

