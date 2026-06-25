"""Compare two families' representatives side by side.

The top panel lists the two archetypes' feature values next to each other and
highlights the rows that differ; the bottom panel shows the two representative
schedules on calendars, side by side, each with its own period navigation so the
two timelines can be paged independently in the same window.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.common.components.HeaderWidget import HeaderWidget
from gui.common.helpers import create_divider
from gui.core.screen import Screen
from gui.features.clusters.ClusterComparePresenter import ClusterComparePresenter
from gui.features.clusters.widgets.ScheduleCalendarView import ScheduleCalendarView

# Background highlight for feature rows that differ between the two archetypes.
_DIFF_STYLE = "background-color: #fff3cd; font-weight: 600; padding: 2px 6px;"
_SAME_STYLE = "color: #555; padding: 2px 6px;"


class ClusterCompareScreen(Screen):
    """Side-by-side comparison of two representatives with differences flagged."""

    def __init__(self, controller, router) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(HeaderWidget(parent=self))
        self._build_toolbar(root)
        root.addWidget(create_divider())
        self._build_feature_table(root)
        self._build_calendars(root)

        self._presenter = ClusterComparePresenter(self, controller, router)
        self._back_btn.clicked.connect(self._presenter.on_back)

    def _build_toolbar(self, root: QVBoxLayout) -> None:
        bar = QFrame()
        bar.setObjectName("nav-bar")
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 8, 20, 8)

        self._back_btn = QPushButton("← Back to clusters")
        self._back_btn.setObjectName("btn-ghost")
        layout.addWidget(self._back_btn)

        self._title = QLabel("<b>Compare representatives</b>")
        self._title.setStyleSheet("font-size: 16px;")
        layout.addWidget(self._title)
        layout.addStretch()
        root.addWidget(bar)

    def _build_feature_table(self, root: QVBoxLayout) -> None:
        self._table_frame = QFrame()
        self._table = QGridLayout(self._table_frame)
        self._table.setContentsMargins(24, 12, 24, 12)
        self._table.setHorizontalSpacing(24)
        self._table.setVerticalSpacing(4)
        root.addWidget(self._table_frame)
        root.addWidget(create_divider())

    def _build_calendars(self, root: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        self._left_view = ScheduleCalendarView()
        self._right_view = ScheduleCalendarView()

        left_wrap = self._wrap_with_caption(self._left_view, "left")
        right_wrap = self._wrap_with_caption(self._right_view, "right")

        row.addWidget(left_wrap, stretch=1)
        row.addWidget(right_wrap, stretch=1)
        root.addLayout(row, stretch=1)
    def _wrap_with_caption(self, view: QWidget, side: str) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        caption = QLabel("")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setStyleSheet("font-weight: 700; color: #0f766e; font-size: 14px;")
        layout.addWidget(caption)

        # Composite widget placeholder container
        composite_container = QWidget()
        composite_container_layout = QVBoxLayout(composite_container)
        composite_container_layout.setContentsMargins(0, 0, 0, 0)
        composite_container_layout.setSpacing(0)
        layout.addWidget(composite_container)

        layout.addWidget(view, stretch=1)

        if side == "left":
            self._left_caption = caption
            self._left_comp_container = composite_container
        else:
            self._right_caption = caption
            self._right_comp_container = composite_container
        return wrap

    def _build_composite_widget(self, container: QWidget, comfort: str, admin: str, faculty: str, spread: str) -> None:
        # Clear existing layout
        layout = container.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # Composite labels container
        composite_widget = QFrame()
        composite_widget.setObjectName("composite-container")
        composite_layout = QGridLayout(composite_widget)
        composite_layout.setContentsMargins(10, 10, 10, 10)
        composite_layout.setHorizontalSpacing(12)
        composite_layout.setVerticalSpacing(8)

        labels_data = [
            ("Student Comfort", comfort),
            ("Admin Load", admin),
            ("Faculty Impact", faculty),
            ("Schedule Spread", spread),
        ]

        for idx, (label_name, label_val) in enumerate(labels_data):
            row = idx // 2
            col = (idx % 2) * 2

            name_lbl = QLabel(f"<b>{label_name}:</b>")
            name_lbl.setObjectName("composite-label-name")
            val_lbl = QLabel(label_val)
            val_lbl.setObjectName("composite-label-value")

            val_lower = label_val.lower()
            val_lbl.setProperty("rating", val_lower)

            composite_layout.addWidget(name_lbl, row, col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            composite_layout.addWidget(val_lbl, row, col + 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(composite_widget)

    # ── view API used by the presenter ───────────────────────────────────────

    def set_periods(self, periods) -> None:
        self._left_view.set_periods(periods)
        self._right_view.set_periods(periods)

    def render_comparison(self, comparison) -> None:
        self._left_caption.setText(comparison.left_title)
        self._right_caption.setText(comparison.right_title)

        # Build composite ratings widgets
        self._build_composite_widget(
            self._left_comp_container,
            comparison.left_student_comfort,
            comparison.left_admin_load,
            comparison.left_faculty_impact,
            comparison.left_schedule_spread
        )
        self._build_composite_widget(
            self._right_comp_container,
            comparison.right_student_comfort,
            comparison.right_admin_load,
            comparison.right_faculty_impact,
            comparison.right_schedule_spread
        )

        # Rebuild the feature comparison table.
        while self._table.count():
            item = self._table.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        header_feature = QLabel("Feature")
        header_left = QLabel(comparison.left_title)
        header_right = QLabel(comparison.right_title)
        for col, lbl in enumerate((header_feature, header_left, header_right)):
            lbl.setStyleSheet("font-weight: 700;")
            self._table.addWidget(lbl, 0, col)

        # Combine composite rows and feature rows
        composite_rows = [
            ("Student Comfort", comparison.left_student_comfort, comparison.right_student_comfort),
            ("Admin Load", comparison.left_admin_load, comparison.right_admin_load),
            ("Faculty Impact", comparison.left_faculty_impact, comparison.right_faculty_impact),
            ("Schedule Spread", comparison.left_schedule_spread, comparison.right_schedule_spread),
        ]

        table_rows = []
        for label, lv, rv in composite_rows:
            table_rows.append((f"★ {label}", lv, rv, lv != rv))

        for label, lv, rv, differs in comparison.feature_rows:
            table_rows.append((label, lv, rv, differs))

        for row, (label, left_val, right_val, differs) in enumerate(table_rows, start=1):
            style = _DIFF_STYLE if differs else _SAME_STYLE
            name = QLabel(label)
            name.setStyleSheet(style)
            lv = QLabel(left_val)
            lv.setStyleSheet(style)
            lv.setAlignment(Qt.AlignmentFlag.AlignRight)
            rv = QLabel(right_val)
            rv.setStyleSheet(style)
            rv.setAlignment(Qt.AlignmentFlag.AlignRight)
            self._table.addWidget(name, row, 0)
            self._table.addWidget(lv, row, 1)
            self._table.addWidget(rv, row, 2)

        self._left_view.show_schedule(comparison.left_schedule)
        self._right_view.show_schedule(comparison.right_schedule)

    def show_message(self, message: str) -> None:
        QMessageBox.information(self, "Compare", message)

    # ── public hook from overview ────────────────────────────────────────────

    def set_pair(self, cluster_a: int, cluster_b: int) -> None:
        self._presenter.set_pair(cluster_a, cluster_b)

    # ── Screen lifecycle ─────────────────────────────────────────────────────

    def on_enter(self) -> None:
        self._presenter.on_enter()

    def on_leave(self) -> None:
        self._presenter.on_leave()
