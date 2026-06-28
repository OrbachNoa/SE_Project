"""Compare two families' representatives side by side.

Redesigned View 1: Main Statistics Comparison Screen containing a top toolbar,
two side-by-side archetype overview header cards with composite ratings,
and a scrollable core comparison body featuring a unified metrics table with
better-value highlights and delta arrows.
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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.common.components.HeaderWidget import HeaderWidget
from gui.common.helpers import create_divider
from gui.core.screen import Screen
from gui.features.clusters.ClusterComparePresenter import ClusterComparePresenter


class ClusterCompareScreen(Screen):
    """Redesigned side-by-side statistics comparison of two representatives."""

    def __init__(self, controller, router) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Main header widget
        root.addWidget(HeaderWidget(parent=self))
        
        # Toolbar navigation and button
        self._build_toolbar(root)
        root.addWidget(create_divider())

        # Archetype Overview Header
        self._build_archetype_header(root)
        root.addWidget(create_divider())

        # Core Comparison Body (Scrollable Table)
        self._build_scrollable_table_area(root)

        self._presenter = ClusterComparePresenter(self, controller, router)
        self._back_btn.clicked.connect(self._presenter.on_back)
        self._view_calendar_btn.clicked.connect(self._presenter.on_view_calendar)

    def _build_toolbar(self, root: QVBoxLayout) -> None:
        bar = QFrame()
        bar.setObjectName("nav-bar")
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 8, 20, 8)

        # Back link widget
        self._back_btn = QPushButton("← Back to cluster overview")
        self._back_btn.setObjectName("btn-ghost")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._back_btn)

        # Center/Left: Title
        self._title = QLabel("<b>Compare Representatives</b>")
        self._title.setObjectName("compare-title")
        layout.addWidget(self._title)
        layout.addStretch()

        # View calendar comparison
        self._view_calendar_btn = QPushButton("View Comparison on Calendar")
        self._view_calendar_btn.setObjectName("btn-calendar-overlay")
        self._view_calendar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._view_calendar_btn)

        root.addWidget(bar)

    def _build_archetype_header(self, root: QVBoxLayout) -> None:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(24)

        # Left Panel (Family A)
        self._left_panel = QFrame()
        self._left_panel.setObjectName("compare-archetype-panel")
        self._left_layout = QVBoxLayout(self._left_panel)
        self._left_layout.setContentsMargins(16, 16, 16, 16)
        self._left_layout.setSpacing(12)

        # Right Panel (Family B)
        self._right_panel = QFrame()
        self._right_panel.setObjectName("compare-archetype-panel")
        self._right_layout = QVBoxLayout(self._right_panel)
        self._right_layout.setContentsMargins(16, 16, 16, 16)
        self._right_layout.setSpacing(12)

        layout.addWidget(self._left_panel, stretch=1)
        layout.addWidget(self._right_panel, stretch=1)

        root.addWidget(container)

    def _populate_archetype_panel(
        self,
        layout: QVBoxLayout,
        title: str,
        comfort: str,
        admin: str,
        faculty: str,
        spread: str,
    ) -> None:
        # Clear layout first
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Title
        title_lbl = QLabel(f"<b>{title}</b>")
        title_lbl.setObjectName("archetype-title")
        layout.addWidget(title_lbl)

        # Divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setObjectName("compare-divider")
        layout.addWidget(divider)

        # 2x2 grid of composite ratings
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        ratings_data = [
            ("Student Comfort", comfort),
            ("Administrative Load", admin),
            ("Faculty Impact", faculty),
            ("Schedule Spread", spread),
        ]

        for idx, (label_name, val) in enumerate(ratings_data):
            row = idx // 2
            col = (idx % 2) * 2

            name_lbl = QLabel(label_name)
            name_lbl.setObjectName("compare-composite-name")

            val_lbl = QLabel(val)
            val_lbl.setObjectName("composite-label-value")
            val_lbl.setProperty("rating", val.lower())
            
            # Force stylesheet refresh on property change
            val_lbl.style().unpolish(val_lbl)
            val_lbl.style().polish(val_lbl)

            grid.addWidget(name_lbl, row, col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(val_lbl, row, col + 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(grid_widget)

    def _build_scrollable_table_area(self, root: QVBoxLayout) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("compare-scroll")

        self._table_frame = QFrame()
        self._table_frame.setObjectName("compare-table-frame")
        self._table = QGridLayout(self._table_frame)
        self._table.setContentsMargins(24, 16, 24, 16)
        self._table.setHorizontalSpacing(36)
        self._table.setVerticalSpacing(8)

        scroll.setWidget(self._table_frame)
        root.addWidget(scroll, stretch=1)

    def _get_arrow(self, crit_id: str) -> str:
        from src.logic.clustering.CriterionDisplay import is_lower_better
        return "↓" if is_lower_better(crit_id) else "↑"

    def _winning_value_container(self, value_lbl: QLabel, crit_id: str) -> QWidget:
        """Wrap the better side's value label with a directional delta arrow."""
        value_lbl.setObjectName("compare-metric-better")
        value_lbl.style().unpolish(value_lbl)
        value_lbl.style().polish(value_lbl)

        arrow = QLabel(self._get_arrow(crit_id))
        arrow.setObjectName("delta-indicator")

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addStretch()
        layout.addWidget(value_lbl)
        layout.addWidget(arrow)
        return container

    # ── view API used by the presenter ───────────────────────────────────────

    def render_comparison(self, comparison) -> None:
        self._title.setText(f"<b>Compare Representatives: {comparison.left_title} vs {comparison.right_title}</b>")

        # Build archetype overview cards
        self._populate_archetype_panel(
            self._left_layout,
            comparison.left_title,
            comparison.left_student_comfort,
            comparison.left_admin_load,
            comparison.left_faculty_impact,
            comparison.left_schedule_spread,
        )
        self._populate_archetype_panel(
            self._right_layout,
            comparison.right_title,
            comparison.right_student_comfort,
            comparison.right_admin_load,
            comparison.right_faculty_impact,
            comparison.right_schedule_spread,
        )

        # Rebuild the metrics comparison table
        while self._table.count():
            item = self._table.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        header_feature = QLabel("Metric")
        header_left = QLabel(comparison.left_title)
        header_right = QLabel(comparison.right_title)
        for col, lbl in enumerate((header_feature, header_left, header_right)):
            lbl.setObjectName("compare-table-header")
            if col > 0:
                lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.addWidget(lbl, 0, col)

        # Render feature rows
        for row, (crit_id, label, left_val, right_val, differs) in enumerate(comparison.feature_rows, start=1):
            name_lbl = QLabel(label)
            name_lbl.setObjectName("compare-row-name")

            left_lbl = QLabel(left_val)
            left_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            left_lbl.setObjectName("compare-row-value")

            right_lbl = QLabel(right_val)
            right_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            right_lbl.setObjectName("compare-row-value")

            # Which side wins is precomputed from raw numeric scores in the
            # view-model (no parsing of the display strings here).
            winner = comparison.better_by_criterion.get(crit_id, "") if differs else ""

            self._table.addWidget(name_lbl, row, 0)
            if winner == "left":
                self._table.addWidget(self._winning_value_container(left_lbl, crit_id), row, 1)
                self._table.addWidget(right_lbl, row, 2)
            elif winner == "right":
                self._table.addWidget(left_lbl, row, 1)
                self._table.addWidget(self._winning_value_container(right_lbl, crit_id), row, 2)
            else:
                self._table.addWidget(left_lbl, row, 1)
                self._table.addWidget(right_lbl, row, 2)

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
