"""Interactive exam-period date editor widget."""
from __future__ import annotations

from typing import List

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import QDateEdit, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from gui.common.components.CalendarWidget import CalendarWidget
from gui.common.components.ExclusionModel import ExclusionModel
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel


class CalendarEditorWidget(QWidget):
    """
    UI shell for editing exam-period date exclusions.

    ExclusionModel owns the editable period state. This widget only syncs Qt
    controls to the model and repaints the calendar grid.
    """

    constraints_saved = pyqtSignal(list)

    def __init__(self, view_models: List[PeriodEditViewModel], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = ExclusionModel(view_models)
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("calendar-editor-card")
        outer_layout.addWidget(card)

        self.main_layout = QVBoxLayout(card)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(16, 14, 16, 14)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedSize(20, 20)
        self.prev_btn.setObjectName("btn-calendar-nav")
        self.prev_btn.clicked.connect(self._on_prev_clicked)

        self.period_label = QLabel()
        self.period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.period_label.setObjectName("calendar-period-label")

        self.next_btn = QPushButton(">")
        self.next_btn.setFixedSize(20, 20)
        self.next_btn.setObjectName("btn-calendar-nav")
        self.next_btn.clicked.connect(self._on_next_clicked)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.period_label, stretch=1)
        nav_layout.addWidget(self.next_btn)
        self.main_layout.addLayout(nav_layout)

        dates_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.dateChanged.connect(self._on_dates_changed)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.dateChanged.connect(self._on_dates_changed)

        dates_layout.addWidget(QLabel("<b>Start:</b>"))
        dates_layout.addWidget(self.start_date_edit)
        dates_layout.addSpacing(16)
        dates_layout.addWidget(QLabel("<b>End:</b>"))
        dates_layout.addWidget(self.end_date_edit)
        dates_layout.addStretch()
        self.main_layout.addLayout(dates_layout)

        self.calendar_grid = CalendarWidget()
        self.calendar_grid.date_clicked.connect(self.toggle_date_exclusion)
        self.main_layout.addWidget(self.calendar_grid, stretch=1)

        self.button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Save All Constraints")
        self.apply_btn.setObjectName("btn-apply-constraints")
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.apply_btn)
        self.main_layout.addLayout(self.button_layout)

        self._refresh_ui()

    def _refresh_ui(self) -> None:
        current_period = self._model.current_period

        self.start_date_edit.blockSignals(True)
        self.end_date_edit.blockSignals(True)
        self.start_date_edit.setDate(QDate.fromString(self._model.start_date, Qt.DateFormat.ISODate))
        self.end_date_edit.setDate(QDate.fromString(self._model.end_date, Qt.DateFormat.ISODate))
        self.start_date_edit.blockSignals(False)
        self.end_date_edit.blockSignals(False)

        self.period_label.setText(
            f"Semester {current_period.semester} - Moed {current_period.moed} "
            f"({self._model.current_index + 1}/{self._model.total})"
        )
        self.prev_btn.setEnabled(self._model.can_move_previous())
        self.next_btn.setEnabled(self._model.can_move_next())
        self._render_calendar()

    def _on_prev_clicked(self) -> None:
        self._sync_date_controls_to_model()
        self._model.move_previous()
        self._refresh_ui()

    def _on_next_clicked(self) -> None:
        self._sync_date_controls_to_model()
        self._model.move_next()
        self._refresh_ui()

    def _on_dates_changed(self) -> None:
        self._sync_date_controls_to_model()
        self._render_calendar()

    def _sync_date_controls_to_model(self) -> None:
        self._model.set_date_range(
            self.start_date_edit.date().toString(Qt.DateFormat.ISODate),
            self.end_date_edit.date().toString(Qt.DateFormat.ISODate),
        )

    def _render_calendar(self) -> None:
        date_list = self._model.date_list()
        self.calendar_grid.setup_month_grid(
            date_list,
            show_month_header=True,
            show_month_banner=False,
        )

        for date_str in date_list:
            self.calendar_grid.set_date_excluded_style(date_str, False)

        for excluded_date in self._model.excluded_dates:
            self.calendar_grid.set_date_excluded_style(excluded_date, True)

    def toggle_date_exclusion(self, date_str: str) -> None:
        is_excluded = self._model.toggle(date_str)
        self.calendar_grid.set_date_excluded_style(date_str, is_excluded)

    def _on_apply_clicked(self) -> None:
        self._sync_date_controls_to_model()
        updated_periods = self._model.apply()
        self.constraints_saved.emit(updated_periods)
        QMessageBox.information(
            self,
            "Saved",
            f"Constraints saved successfully for all {self._model.total} periods.",
        )
