from datetime import datetime, timedelta
from typing import List

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QHBoxLayout, 
                             QMessageBox, QLabel, QDateEdit)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

from src.gui.widgets.CalendarWidget import CalendarWidget
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel
from src.application.viewmodels.PeriodEditRequest import PeriodEditRequest

class CalendarEditorWidget(QWidget):
    constraints_saved = pyqtSignal(list)

    def __init__(self, view_models: List[PeriodEditViewModel], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Holds the list of all exam periods.
        self._view_models = view_models
        self._current_index = 0
        
        # Initialize the widget with the first period's data.
        self._load_current_state()
        self._init_ui()

    def _load_current_state(self) -> None:
        """Loads the currently selected period's data into the widget."""
        self._current_vm = self._view_models[self._current_index]
        self._excluded_dates = set(self._current_vm.excluded_dates)

    def _save_current_state(self) -> None:
        """Saves the widget's current state back into the view model."""
        self._current_vm.start_date = self.start_date_edit.date().toString(Qt.DateFormat.ISODate)
        self._current_vm.end_date = self.end_date_edit.date().toString(Qt.DateFormat.ISODate)
        self._current_vm.excluded_dates = list(self._excluded_dates)

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Navigation Bar ---
        style = "background-color: #3396ad; color: #FDFBF7; border-radius: 4px; padding: 5px; font-weight: bold; border: none;"
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(20, 20)
        self.prev_btn.setStyleSheet(style)
        self.prev_btn.clicked.connect(self._on_prev_clicked)
        
        self.period_label = QLabel()
        self.period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.period_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #3E352F;")
        
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(20, 20)
        self.next_btn.setStyleSheet(style)
        self.next_btn.clicked.connect(self._on_next_clicked)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.period_label, stretch=1)
        nav_layout.addWidget(self.next_btn)
        self.main_layout.addLayout(nav_layout)

        # --- Date Pickers ---
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

        # --- Calendar Grid ---
        self.calendar_grid = CalendarWidget()
        self.calendar_grid.date_clicked.connect(self.toggle_date_exclusion)
        self.main_layout.addWidget(self.calendar_grid, stretch=1)

        # --- Bottom Bar ---
        self.button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Save All Constraints")
        self.apply_btn.setStyleSheet("background-color: #3396ad; color: #FDFBF7; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.apply_btn)
        self.main_layout.addLayout(self.button_layout)

        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Updates the UI to match the currently loaded period."""
        # Temporarily block signals to prevent triggering UI updates while setting the initial dates.
        self.start_date_edit.blockSignals(True)
        self.end_date_edit.blockSignals(True)
        
        self.start_date_edit.setDate(QDate.fromString(self._current_vm.start_date, Qt.DateFormat.ISODate))
        self.end_date_edit.setDate(QDate.fromString(self._current_vm.end_date, Qt.DateFormat.ISODate))
        
        self.start_date_edit.blockSignals(False)
        self.end_date_edit.blockSignals(False)

        # Update navigation label and button states.
        self.period_label.setText(f"{self._current_vm.semester} Semester - Moed {self._current_vm.moed} "
                                  f"({self._current_index + 1}/{len(self._view_models)})")
        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(self._current_index < len(self._view_models) - 1)

        self._render_calendar()

    def _on_prev_clicked(self) -> None:
        self._save_current_state()
        self._current_index -= 1
        self._load_current_state()
        self._refresh_ui()

    def _on_next_clicked(self) -> None:
        self._save_current_state()
        self._current_index += 1
        self._load_current_state()
        self._refresh_ui()

    def _on_dates_changed(self) -> None:
        self._render_calendar()

    def _render_calendar(self) -> None:
        """Draws the calendar grid based on the selected start and end dates."""
        start_str = self.start_date_edit.date().toString(Qt.DateFormat.ISODate)
        end_str = self.end_date_edit.date().toString(Qt.DateFormat.ISODate)
        
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        
        date_list = []
        if end >= start:
            delta = end - start
            for i in range(delta.days + 1):
                day = start + timedelta(days=i)
                date_list.append(day.strftime("%Y-%m-%d"))
                
        self.calendar_grid.setup_month_grid(date_list)
        
        # Re-apply the grey style to dates that were already excluded.
        for ex_date in self._excluded_dates:
            self.calendar_grid.set_date_excluded_style(ex_date, True)

    def toggle_date_exclusion(self, date_str: str) -> None:
        """Adds or removes a date from the excluded list and updates its color."""
        if date_str in self._excluded_dates:
            self._excluded_dates.remove(date_str)
            self.calendar_grid.set_date_excluded_style(date_str, False)
        else:
            self._excluded_dates.add(date_str)
            self.calendar_grid.set_date_excluded_style(date_str, True)

    def _on_apply_clicked(self) -> None:
        """Saves the state and notifies the user."""
        self._save_current_state()
        self.constraints_saved.emit(self._view_models)
        QMessageBox.information(self, "Saved", f"Constraints saved successfully for all {len(self._view_models)} periods.")
