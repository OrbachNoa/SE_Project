from typing import Dict
from PyQt6.QtWidgets import QStackedWidget
from gui.core.screen import Screen

# Routes screen transitions and keeps a back-navigation history.
class ScreenRouter:
    """Manages screen transitions with back-navigation history."""

    # Initialize the screen registry and the back-navigation history.
    def __init__(self, stack: QStackedWidget) -> None:
        self._stack = stack
        self._screens: Dict[str, Screen] = {}
        self._history: list = []

    # Teach the router about a new screen so it knows it exists and can switch to it later
    def register(self, name: str, screen: Screen) -> None:
        """Register a screen with the router."""
        self._screens[name] = screen
        self._stack.addWidget(screen)

    def get_screen(self, name: str) -> Screen | None:
        """Get a registered screen by name."""
        return self._screens.get(name)

    # The main command to jump to a specific screen by its name
    def show(self, name: str, push_history: bool = True) -> None:
        """Show a screen by name.

        When push_history is True the screen being left is recorded for Back
        navigation; pass False (or use replace()) to navigate without adding a
        Back entry. Consecutive duplicate entries are never stored.
        """
        if name not in self._screens:
            raise KeyError(f"Screen '{name}' is not registered.")
        current_name = self._current_name()

        # If we are already on the screen we want to go to, just refresh it and stop here
        if current_name == name:
            self._screens[name].on_enter()
            return

        current = self._current_screen()

        # If we are leaving a screen, trigger its cleanup function and save it to our "back" history
        if current is not None:
            current.on_leave()
            # Skip empty names and consecutive duplicates so Back doesn't stutter.
            if push_history and current_name and (
                not self._history or self._history[-1] != current_name
            ):
                self._history.append(current_name)

        # Actually flip the view to the new screen and trigger its startup function
        target = self._screens[name]
        self._stack.setCurrentWidget(target)
        target.on_enter()

    # Navigate to a screen without recording the current one in Back history.
    def replace(self, name: str) -> None:
        """Switch screens without leaving a Back entry (replace, don't push)."""
        self.show(name, push_history=False)

    # Works exactly like the "Back" button in a web browser, returning to the last visited screen
    def back(self) -> None:
        """Go back to the previous screen."""
        # If there is nowhere to go back to, do nothing
        if not self._history:
            return
            
        # Get the name of the previous screen and remove it from the history list
        previous = self._history.pop()
        target = self._screens[previous]
        current = self._current_screen()
        
        # Tell the current screen we are leaving
        if current:
            current.on_leave()
            
        # Switch the view back to the previous screen
        self._stack.setCurrentWidget(target)
        target.on_enter()

    # Internal helper tool to quickly get the actual Screen object the user is looking at right now
    def _current_screen(self) -> Screen | None:
        """Get the current screen."""
        w = self._stack.currentWidget()
        return w if isinstance(w, Screen) else None

    # Internal helper tool to quickly get the text name of the screen the user is looking at right now
    def _current_name(self) -> str | None:
        """Get the current screen name."""
        current = self._current_screen()
        for name, screen in self._screens.items():
            if screen is current:
                return name
        return None