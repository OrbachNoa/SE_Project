"""Shared calendar overlay screen for comparing two families.

Overlays two representative schedules on a single calendar using color-coded badges
to highlight differences and similarities.
"""
from __future__ import annotations

from typing import List, Tuple
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.common.components.HeaderWidget import HeaderWidget
from gui.common.helpers import create_divider
from gui.core.screen import Screen
from gui.features.clusters.ClusterCalendarOverlayPresenter import ClusterCalendarOverlayPresenter
from gui.features.clusters.widgets.OverlayCalendarWidget import OverlayCalendarWidget
from gui.features.output.PeriodNavigator import PeriodNavigator
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel
from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel


class ClusterCalendarOverlayScreen(Screen):
    """Unified calendar overlay screen for two representative schedules."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._periods = PeriodNavigator()
        self._period_vms: List[PeriodEditViewModel] = []
        self._merged_items: List[Tuple[ScheduleItemViewModel, str]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Main Header Bar
        root.addWidget(HeaderWidget(parent=self))

        # Toolbar: Back to Stats + Title + Legend
        self._build_toolbar(root)
        root.addWidget(create_divider())

        # Unified Calendar Area with Period Navigation
        self._build_calendar_area(root)

        self._presenter = ClusterCalendarOverlayPresenter(self, controller, router)
        self._back_btn.clicked.connect(self._presenter.on_back)

    def _build_toolbar(self, root: QVBoxLayout) -> None:
        bar = QFrame()
        bar.setObjectName("nav-bar")
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 8, 24, 8)

        # Left: Back to stats
        self._back_btn = QPushButton("← Back to statistics")
        self._back_btn.setObjectName("btn-ghost")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._back_btn)

        # Center: Title
        self._title = QLabel("<b>Calendar Overlay</b>")
        self._title.setObjectName("overlay-title")
        layout.addWidget(self._title)

        layout.addStretch()

        # --- Legend Panel ---
        legend_frame = QFrame()
        legend_frame.setObjectName("legend-panel")
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(16, 4, 16, 4)
        legend_layout.setSpacing(12)

        # Helper function to create standard 12x12px solid color blocks. The
        # swatch color comes from QSS via the object name (see ClusterStyles).
        def create_color_block(object_name: str) -> QLabel:
            block = QLabel()
            block.setFixedSize(12, 12)
            block.setObjectName(object_name)
            return block

        # Family 1
        icon_a = create_color_block("overlay-legend-a")
        self._lbl_a = QLabel("Family 1 only")
        self._lbl_a.setObjectName("overlay-legend-label")

        # Family 2
        icon_b = create_color_block("overlay-legend-b")
        self._lbl_b = QLabel("Family 2 only")
        self._lbl_b.setObjectName("overlay-legend-label")

        # Mutual
        icon_mutual = create_color_block("overlay-legend-mutual")
        lbl_mutual = QLabel("Mutual")
        lbl_mutual.setObjectName("overlay-legend-label")

        # helper to create a vertical divider
        def create_vertical_divider() -> QFrame:
            divider = QFrame()
            divider.setFrameShape(QFrame.Shape.VLine)
            divider.setFrameShadow(QFrame.Shadow.Sunken)
            divider.setFixedWidth(2)
            return divider

        # Add to layout in structured pairs
        legend_layout.addWidget(icon_a)
        legend_layout.addWidget(self._lbl_a)
        
        legend_layout.addWidget(create_vertical_divider())
        legend_layout.addWidget(icon_b)
        legend_layout.addWidget(self._lbl_b)

        legend_layout.addWidget(create_vertical_divider())
        legend_layout.addWidget(icon_mutual)
        legend_layout.addWidget(lbl_mutual)

        layout.addWidget(legend_frame)
        root.addWidget(bar)

    def _build_calendar_area(self, root: QVBoxLayout) -> None:
        calendar_wrap = QWidget()
        layout = QVBoxLayout(calendar_wrap)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Month Navigation Bar styled like the teal month-nav-bar
        nav = QFrame()
        nav.setObjectName("month-nav-bar")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(16, 8, 16, 8)

        self._prev_period_btn = QPushButton("< Prev Period")
        self._prev_period_btn.setFixedWidth(120)
        self._prev_period_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._period_label = QLabel("")
        self._period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._period_label.setObjectName("overlay-period-label")

        self._next_period_btn = QPushButton("Next Period >")
        self._next_period_btn.setFixedWidth(120)
        self._next_period_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self._prev_period_btn.clicked.connect(self._on_prev_period)
        self._next_period_btn.clicked.connect(self._on_next_period)

        nav_layout.addWidget(self._prev_period_btn)
        nav_layout.addWidget(self._period_label, stretch=1)
        nav_layout.addWidget(self._next_period_btn)
        layout.addWidget(nav)

        # Scrollable Overlay Calendar Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        self._calendar = OverlayCalendarWidget()
        content_layout.addWidget(self._calendar)
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        root.addWidget(calendar_wrap, stretch=1)

    # ── view API used by the presenter ───────────────────────────────────────

    def set_periods(self, periods: List[PeriodEditViewModel]) -> None:
        """Set the available periods for navigation."""
        self._period_vms = list(periods or [])
        self._periods.reset(self._period_vms)

    def set_titles(self, left_title: str, right_title: str) -> None:
        """Update the comparison screen titles in header and legend labels."""
        self._title.setText(f"<b>Shared Calendar Overlay: {left_title} vs {right_title}</b>")
        self._lbl_a.setText(f"{left_title} only")
        self._lbl_b.setText(f"{right_title} only")

    def render_overlay(self, merged: List[Tuple[ScheduleItemViewModel, str]]) -> None:
        """Store merged items and render the current active period."""
        self._merged_items = merged
        self._periods.reset(self._period_vms)
        self._render()

    def show_message(self, message: str) -> None:
        QMessageBox.information(self, "Calendar Overlay", message)

    def set_pair(self, cluster_a: int, cluster_b: int) -> None:
        self._presenter.set_pair(cluster_a, cluster_b)

    # ── internals ────────────────────────────────────────────────────────────

    def _on_prev_period(self) -> None:
        if self._periods.move_previous():
            self._render()

    def _on_next_period(self) -> None:
        if self._periods.move_next():
            self._render()

    def _render(self) -> None:
        period = self._periods.current_period
        if period is None:
            self._calendar.setup_month_grid([], show_month_header=False, show_month_banner=False)
            self._period_label.setText("")
            self._prev_period_btn.setEnabled(False)
            self._next_period_btn.setEnabled(False)
            return

        self._period_label.setText(self._periods.label())
        self._prev_period_btn.setEnabled(self._periods.can_move_previous())
        self._next_period_btn.setEnabled(self._periods.can_move_next())

        # Filter items inside current period
        visible = [
            (item, source) for item, source in self._merged_items
            if item.date and period.start_date <= item.date <= period.end_date
        ]

        self._calendar.setup_month_grid(
            self._periods.date_list(), show_month_header=True, show_month_banner=False
        )
        for excluded in period.excluded_dates:
            self._calendar.set_date_excluded_output_style(excluded)

        self._calendar.display_overlay_assignments(visible)

    # ── Screen lifecycle ─────────────────────────────────────────────────────

    def on_enter(self) -> None:
        self._presenter.on_enter()

    def on_leave(self) -> None:
        self._presenter.on_leave()
