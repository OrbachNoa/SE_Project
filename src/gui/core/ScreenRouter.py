from typing import Dict
from PyQt6.QtWidgets import QStackedWidget
from gui.core.screen import Screen

class ScreenRouter:
    """Manages screen transitions with back-navigation history."""

    def __init__(self, stack: QStackedWidget) -> None:
        self._stack = stack
        self._screens: Dict[str, Screen] = {}
        self._history: list = []

    def register(self, name: str, screen: Screen) -> None:
        """Register a screen with the router."""
        self._screens[name] = screen
        self._stack.addWidget(screen)

    def show(self, name: str) -> None:
        """Show a screen by name."""
        if name not in self._screens:
            raise KeyError(f"Screen '{name}' is not registered.")
        current_name = self._current_name()
        if current_name == name:
            self._screens[name].on_enter()
            return
        current = self._current_screen()
        if current is not None:
            current.on_leave()
            if current_name:
                self._history.append(current_name)
        target = self._screens[name]
        self._stack.setCurrentWidget(target)
        target.on_enter()

    def back(self) -> None:
        """Go back to the previous screen."""
        if not self._history:
            return
        previous = self._history.pop()
        target = self._screens[previous]
        current = self._current_screen()
        if current:
            current.on_leave()
        self._stack.setCurrentWidget(target)
        target.on_enter()

    def _current_screen(self) -> Screen | None:
        """Get the current screen."""
        w = self._stack.currentWidget()
        return w if isinstance(w, Screen) else None

    def _current_name(self) -> str | None:
        """Get the current screen name."""
        current = self._current_screen()
        for name, screen in self._screens.items():
            if screen is current:
                return name
        return None