from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from src.gui.screen import Screen


class OutputScreen(Screen):
    """Output screen: shows a schedule solution with back and solution navigation."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router

        # Navigation state
        self._current_index: int = 0
        self._total: int = 0

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)

        # Top bar: back button on the left, solution navigator on the right
        top_bar = QHBoxLayout()

        self._back_btn = QPushButton("← Back")
        self._back_btn.setShortcut(QKeySequence("Alt+Left"))
        self._back_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._back_btn.setToolTip("Back to input screen (Alt+Left)")
        self._back_btn.clicked.connect(self._on_back)
        top_bar.addWidget(self._back_btn)

        top_bar.addStretch()

        # Solution navigator
        self._prev_btn = QPushButton("◀ Prev")
        self._prev_btn.setToolTip("Go to previous solution")
        self._prev_btn.clicked.connect(self.on_prev)

        self._counter_label = QLabel()
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._next_btn = QPushButton("Next ▶")
        self._next_btn.setToolTip("Go to next solution")
        self._next_btn.clicked.connect(self.on_next)

        top_bar.addWidget(self._prev_btn)
        top_bar.addWidget(self._counter_label)
        top_bar.addWidget(self._next_btn)

        root_layout.addLayout(top_bar)

        # Placeholder content area; will be replaced by the calendar widget.
        content = QWidget()
        content_layout = QVBoxLayout(content)
        self._content_label = QLabel("Output Screen — SCRUM-137")
        self._content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self._content_label)
        root_layout.addWidget(content, stretch=1)

        self._refresh_counter()

    # ------------------------------------------------------------------
    # Internal display helpers
    # ------------------------------------------------------------------

    def _refresh_counter(self) -> None:
        """Update the counter label and nav button states."""
        if self._total == 0:
            self._counter_label.setText("No solutions")
        else:
            self._counter_label.setText(
                f"Solution {self._current_index + 1} / {self._total}"
            )
        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        """Grey out Prev/Next at the boundaries."""
        self._prev_btn.setEnabled(self._current_index > 0)
        self._next_btn.setEnabled(self._current_index < self._total - 1)

    def _show_current(self) -> None:
        """Render the solution at _current_index into the content area.

        Delegates to controller.get_schedule_view(index) when available.
        Falls back to a text placeholder until calendar_widget (SCRUM-93) is wired.
        """
        if self._total == 0:
            self._content_label.setText("No solutions to display.")
            return
        if hasattr(self._controller, "get_schedule_view"):
            view_model = self._controller.get_schedule_view(self._current_index)
            self._content_label.setText(str(view_model))
        else:
            # Controller method not yet implemented — show a text fallback
            self._content_label.setText(f"Solution {self._current_index + 1}")

    def _on_back(self) -> None:
        """Navigate back to the previous screen via the router history."""
        self._router.back()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def show_schedules(self, total: int) -> None:
        """Set the number of available solutions and display the first one."""
        self._total = total
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def on_next(self) -> None:
        """Advance to the next solution if one exists."""
        if self._current_index < self._total - 1:
            self._current_index += 1
            self._show_current()
            self._refresh_counter()

    def on_prev(self) -> None:
        """Go back to the previous solution if one exists."""
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current()
            self._refresh_counter()

    # ------------------------------------------------------------------
    # Screen lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        # No state to restore — InputScreen object is persistent and retains its own selections.
        self._back_btn.setFocus()

    def on_leave(self) -> None:
        # No teardown needed — output data lives in the controller, not in this widget.
        pass
