"""OutputScreen — displays generated schedule results.

SCRUM-147 : on_enter loads results from controller
SCRUM-93  : year-calendar widget replaces content area (Yuval)
SCRUM-96  : export button (Yuval)
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

from src.gui.screen import Screen


def _divider(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("divider")
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    return f


class OutputScreen(Screen):
    """Output screen: schedule results with navigation."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router

        self._current_index: int = 0
        self._total: int = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(72)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 0, 28, 0)

        title = QLabel("EXAM SCHEDULER")
        title.setObjectName("app-title")
        subtitle = QLabel("Generated schedules")
        subtitle.setObjectName("app-subtitle")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        h_layout.addLayout(title_col)
        h_layout.addStretch()
        root.addWidget(header)

        # ── Navigation bar ────────────────────────────────────────────
        nav_bar = QFrame()
        nav_bar.setObjectName("nav-bar")
        nav_bar.setFixedHeight(52)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(8)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setObjectName("btn-ghost")
        self._back_btn.setShortcut(QKeySequence("Alt+Left"))
        self._back_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._back_btn.setToolTip("Back to input screen (Alt+Left)")
        self._back_btn.setFixedHeight(36)
        self._back_btn.clicked.connect(self._on_back)
        nav_layout.addWidget(self._back_btn)

        nav_layout.addStretch()

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setObjectName("btn-secondary")
        self._prev_btn.setToolTip("Previous solution")
        self._prev_btn.setFixedSize(36, 36)
        self._prev_btn.clicked.connect(self.on_prev)

        self._counter_label = QLabel()
        self._counter_label.setObjectName("counter-label")
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._next_btn = QPushButton("▶")
        self._next_btn.setObjectName("btn-secondary")
        self._next_btn.setToolTip("Next solution")
        self._next_btn.setFixedSize(36, 36)
        self._next_btn.clicked.connect(self.on_next)

        nav_layout.addWidget(self._prev_btn)
        nav_layout.addWidget(self._counter_label)
        nav_layout.addWidget(self._next_btn)

        root.addWidget(nav_bar)
        root.addWidget(_divider())

        # ── Content area ──────────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(28, 20, 28, 20)
        body.setSpacing(0)

        content_card = QFrame()
        content_card.setObjectName("content-area")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area — the calendar widget (SCRUM-93) will live here
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        content_inner = QVBoxLayout(self._content_widget)
        content_inner.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._content_label = QLabel()
        self._content_label.setObjectName("schedule-text")
        self._content_label.setWordWrap(True)
        self._content_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._content_label.setContentsMargins(20, 16, 20, 16)
        content_inner.addWidget(self._content_label)

        self._scroll.setWidget(self._content_widget)
        content_layout.addWidget(self._scroll)

        body.addWidget(content_card)
        root.addLayout(body)

        self._refresh_counter()

    # ── Display helpers ────────────────────────────────────────────────

    def _refresh_counter(self) -> None:
        if self._total == 0:
            self._counter_label.setText("No solutions")
        else:
            self._counter_label.setText(
                f"Solution  {self._current_index + 1} / {self._total}"
            )
        self._prev_btn.setEnabled(self._current_index > 0)
        self._next_btn.setEnabled(self._current_index < self._total - 1)

    def _show_current(self) -> None:
        """Render solution at _current_index. CalendarWidget (SCRUM-93) replaces this."""
        if self._total == 0:
            self._content_label.setText(
                "No solutions to display.\n\n"
                "Go back and adjust your selections."
            )
            return
        try:
            vm = self._controller.get_schedule_view(self._current_index)
            lines = [
                f"Schedule {self._current_index + 1} of {vm.total}\n",
                "─" * 48,
            ]
            for item in vm.items:
                lines.append(f"  {item.date}   {item.title}")
                lines.append(f"             {item.subtitle}\n")
            self._content_label.setText("\n".join(lines))
        except Exception as e:
            self._content_label.setText(f"Error displaying schedule:\n{e}")

    def _on_back(self) -> None:
        self._router.back()

    # ── Navigation ─────────────────────────────────────────────────────

    def on_next(self) -> None:
        if self._current_index < self._total - 1:
            self._current_index += 1
            self._show_current()
            self._refresh_counter()

    def on_prev(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current()
            self._refresh_counter()

    # ── Lifecycle (SCRUM-147) ──────────────────────────────────────────

    def on_enter(self) -> None:
        self._current_index = 0
        try:
            vm = self._controller.get_schedule_view(0)
            self._total = vm.total
        except IndexError:
            self._total = 0
        self._show_current()
        self._refresh_counter()
        self._back_btn.setFocus()

    def on_leave(self) -> None:
        pass