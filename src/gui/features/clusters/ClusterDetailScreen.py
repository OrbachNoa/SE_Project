"""Cluster detail screen — browse the schedules inside one family.

Navigation between schedules within the family mirrors browsing solutions on the
output screen; rendering reuses ``ScheduleCalendarView``.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QMenu
)

from gui.common.components.HeaderWidget import HeaderWidget
from gui.common.helpers import create_divider, prompt_save_file
from gui.core.screen import Screen
from gui.features.clusters.ClusterDetailPresenter import ClusterDetailPresenter
from gui.features.clusters.widgets.ScheduleCalendarView import ScheduleCalendarView


class ClusterDetailScreen(Screen):
    """Shows one schedule of a family at a time with prev/next and export."""

    def __init__(self, controller, router) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(HeaderWidget(parent=self))
        self._build_toolbar(root)
        root.addWidget(create_divider())

        self._calendar_view = ScheduleCalendarView()
        root.addWidget(self._calendar_view, stretch=1)

        self._presenter = ClusterDetailPresenter(self, controller, router)
        self._connect_events()

    def _build_toolbar(self, root: QVBoxLayout) -> None:
        bar = QFrame()
        bar.setObjectName("nav-bar")
        bar.setFixedHeight(70)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(12)

        self._back_btn = QPushButton("← Back to clusters")
        self._back_btn.setObjectName("btn-ghost")
        layout.addWidget(self._back_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setObjectName("btn-export")
        self._export_btn.setToolTip("Export the current schedule as PDF or TXT")
        self._export_btn.setFixedHeight(36)
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._export_btn)

        layout.addStretch()

        self._prev_btn = QPushButton("◀ Prev")
        self._prev_btn.setObjectName("btn-secondary")
        self._title = QLabel("")
        self._title.setStyleSheet("font-weight: 600;")
        self._next_btn = QPushButton("Next ▶")
        self._next_btn.setObjectName("btn-secondary")

        layout.addWidget(self._prev_btn)
        layout.addWidget(self._title)
        layout.addWidget(self._next_btn)

        root.addWidget(bar)

    def _connect_events(self) -> None:
        self._back_btn.clicked.connect(self._presenter.on_back)

        export_menu = QMenu(self)
        pdf_action = export_menu.addAction("Export as PDF")
        txt_action = export_menu.addAction("Export as TXT")
        excel_action = export_menu.addAction("Export as Excel")
        self._export_btn.setMenu(export_menu)

        pdf_action.triggered.connect(self._presenter.on_export_pdf)
        txt_action.triggered.connect(self._presenter.on_export_txt)
        excel_action.triggered.connect(self._presenter.on_export_excel)

        self._prev_btn.clicked.connect(self._presenter.on_prev)
        self._next_btn.clicked.connect(self._presenter.on_next)

    # ── API called by the overview screen ────────────────────────────────────

    def enter_cluster(self, cluster_id: int) -> None:
        self._presenter.set_cluster(cluster_id)

    # ── view API used by the presenter ───────────────────────────────────────

    def set_periods(self, periods) -> None:
        self._calendar_view.set_periods(periods)

    def show_schedule(self, schedule_vm) -> None:
        self._calendar_view.show_schedule(schedule_vm)

    def clear_calendar(self) -> None:
        self._calendar_view.clear()

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_nav_state(self, can_prev: bool, can_next: bool) -> None:
        self._prev_btn.setEnabled(can_prev)
        self._next_btn.setEnabled(can_next)

    def ask_save_path(self, default_name: str) -> str:
        return prompt_save_file(self, "Save schedule", default_name, "Text files (*.txt)")
    
    def ask_save_path_excel(self, default_name: str) -> str:
        return prompt_save_file(self, "Save schedule as Excel", default_name, "Excel files (*.xlsx)")

    def show_message(self, message: str) -> None:
        QMessageBox.information(self, "Cluster", message)

    def export_schedule_pdf(self, schedule_view, current_index: int) -> None:
        from gui.features.output.widgets.SchedulePdfExporter import export_schedule_pdf
        export_schedule_pdf(schedule_view, current_index, parent=self)

    # ── Screen lifecycle ─────────────────────────────────────────────────────

    def on_enter(self) -> None:
        self._presenter.on_enter()

    def on_leave(self) -> None:
        self._presenter.on_leave()
