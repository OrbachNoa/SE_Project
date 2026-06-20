"""A reusable calendar view that renders one ScheduleViewModel across periods.

Both the cluster detail screen (browsing schedules in a family) and the cluster
comparison screen (two representatives side by side) need to draw a single
schedule on the calendar, with per-period navigation. This widget packages that
rendering — reusing ``OutputCalendarWidget`` and ``PeriodNavigator`` — so the
logic that filters assignments by the visible period lives in exactly one place.
Each instance keeps its own period position, so the two compare panels can be
paged independently.
"""
from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.common.components.OutputCalendarWidget import OutputCalendarWidget
from gui.features.output.PeriodNavigator import PeriodNavigator
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel


class ScheduleCalendarView(QWidget):
    """Draws a schedule on the calendar with previous/next period controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._periods = PeriodNavigator()
        self._period_vms: List[PeriodEditViewModel] = []
        self._schedule: ScheduleViewModel | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Period navigation bar.
        nav = QFrame()
        nav.setObjectName("month-nav-bar")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(16, 8, 16, 8)

        self._prev_period_btn = QPushButton("< Prev Period")
        self._prev_period_btn.setFixedWidth(120)
        self._period_label = QLabel("")
        self._period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._next_period_btn = QPushButton("Next Period >")
        self._next_period_btn.setFixedWidth(120)

        self._prev_period_btn.clicked.connect(self._on_prev_period)
        self._next_period_btn.clicked.connect(self._on_next_period)

        nav_layout.addWidget(self._prev_period_btn)
        nav_layout.addWidget(self._period_label, stretch=1)
        nav_layout.addWidget(self._next_period_btn)
        root.addWidget(nav)

        # Scrollable calendar grid.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._calendar = OutputCalendarWidget()
        content_layout.addWidget(self._calendar)
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

    # ── public API ───────────────────────────────────────────────────────────

    def set_periods(self, periods: List[PeriodEditViewModel]) -> None:
        """Provide the exam periods used to page the calendar."""
        self._period_vms = list(periods or [])
        self._periods.reset(self._period_vms)

    def show_schedule(self, schedule: ScheduleViewModel) -> None:
        """Render the given schedule, starting from the first period."""
        self._schedule = schedule
        # Reset back to the first period for the newly shown schedule.
        self._periods.reset(self._period_vms)
        self._render()

    def clear(self) -> None:
        self._schedule = None
        self._calendar.setup_month_grid([], show_month_header=False, show_month_banner=False)
        self._period_label.setText("")

    # ── internals ────────────────────────────────────────────────────────────

    def _on_prev_period(self) -> None:
        if self._periods.move_previous():
            self._render()

    def _on_next_period(self) -> None:
        if self._periods.move_next():
            self._render()

    def _render(self) -> None:
        period = self._periods.current_period
        if period is None or self._schedule is None:
            self._calendar.setup_month_grid([], show_month_header=False, show_month_banner=False)
            self._period_label.setText("")
            self._prev_period_btn.setEnabled(False)
            self._next_period_btn.setEnabled(False)
            return

        self._period_label.setText(self._periods.label())
        self._prev_period_btn.setEnabled(self._periods.can_move_previous())
        self._next_period_btn.setEnabled(self._periods.can_move_next())

        # Only the exams that fall inside the visible period (ISO strings compare).
        visible = [
            item for item in self._schedule.items
            if item.date and period.start_date <= item.date <= period.end_date
        ]
        self._calendar.setup_month_grid(
            self._periods.date_list(), show_month_header=True, show_month_banner=False
        )
        for excluded in period.excluded_dates:
            self._calendar.set_date_excluded_output_style(excluded)
        self._calendar.display_assignments(visible)
