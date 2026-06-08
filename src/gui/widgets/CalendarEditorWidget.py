"""
CalendarEditorWidget — interactive exam-period date editor.

Displays one exam period at a time (semester + moed) with a navigable
calendar grid. The user can click any date cell to toggle it between
included (green) and excluded (red). On save, the updated constraints
are emitted via the constraints_saved signal so the input screen can
forward them to the application layer.
"""
from datetime import datetime, timedelta
from typing import List

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
                             QMessageBox, QLabel, QDateEdit, QFrame)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

from src.gui.widgets.CalendarWidget import CalendarWidget
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel


class CalendarEditorWidget(QWidget):
    """Widget that lets the user inspect and edit the dates of an exam period.

    Wraps a CalendarWidget grid and adds period navigation (prev/next),
    date-range pickers and a save button. Excluded dates are shown in red;
    included dates in green. Emits constraints_saved with the full updated
    list of view models when the user saves.
    """

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
        """Load the currently selected period's data into working state."""
        self._current_vm = self._view_models[self._current_index]
        self._excluded_dates = set(self._current_vm.excluded_dates)

    def _save_current_state(self) -> None:
        """Write the working state back into the current view model."""
        self._current_vm.start_date = self.start_date_edit.date().toString(Qt.DateFormat.ISODate)
        self._current_vm.end_date = self.end_date_edit.date().toString(Qt.DateFormat.ISODate)
        self._current_vm.excluded_dates = list(self._excluded_dates)

    def _init_ui(self) -> None:
        """Build and arrange all child widgets inside a styled card frame."""
        # Outer layout holds a card frame so the whole editor has the same
        # white background and rounded border as the other cards on the input
        # screen (program selector, course list). Margins are zero here so the
        # card fills the space allocated by the parent layout.
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(
            "QFrame {"
            "  background: #FFFFFF;"
            "  border: 1px solid #E2E8F0;"
            "  border-radius: 14px;"
            "}"
        )
        outer_layout.addWidget(card)

        # All inner content lives inside the card with comfortable padding.
        self.main_layout = QVBoxLayout(card)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(16, 14, 16, 14)

        # --- Navigation Bar ---
        btn_style = "background-color: #3396ad; color: #FDFBF7; border-radius: 4px; padding: 5px; font-weight: bold; border: none;"
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(20, 20)
        self.prev_btn.setStyleSheet(btn_style)
        self.prev_btn.clicked.connect(self._on_prev_clicked)

        self.period_label = QLabel()
        self.period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.period_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #3E352F;")
        
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(20, 20)
        self.next_btn.setStyleSheet(btn_style)
        self.next_btn.clicked.connect(self._on_next_clicked)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.period_label, stretch=1)
        nav_layout.addWidget(self.next_btn)
        self.main_layout.addLayout(nav_layout)

        # Date pickers for the period start and end dates.
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

        # Calendar grid: clicking a cell toggles that date's inclusion.
        self.calendar_grid = CalendarWidget()
        self.calendar_grid.date_clicked.connect(self.toggle_date_exclusion)

        # Hide the weekday header row (Sun Mon Tue ...). In this editor the
        # cells are laid out by exam date order, not by real weekday column, so
        # the header is misleading and wastes vertical space. We hide it here
        # without touching CalendarWidget's own file.
        if hasattr(self.calendar_grid, "headers_frame"):
            self.calendar_grid.headers_frame.setVisible(False)

        self.main_layout.addWidget(self.calendar_grid, stretch=1)

        # Save button at the bottom right of the card.
        self.button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Save All Constraints")
        self.apply_btn.setStyleSheet("background-color: #3396ad; color: #FDFBF7; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.apply_btn)
        self.main_layout.addLayout(self.button_layout)

        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Update all controls to reflect the currently loaded period."""
        # Temporarily block signals to prevent triggering UI updates while
        # setting the initial dates programmatically.
        self.start_date_edit.blockSignals(True)
        self.end_date_edit.blockSignals(True)

        self.start_date_edit.setDate(QDate.fromString(self._current_vm.start_date, Qt.DateFormat.ISODate))
        self.end_date_edit.setDate(QDate.fromString(self._current_vm.end_date, Qt.DateFormat.ISODate))

        self.start_date_edit.blockSignals(False)
        self.end_date_edit.blockSignals(False)

        # Update navigation label and button states.
        self.period_label.setText(
            f"{self._current_vm.semester} Semester - Moed {self._current_vm.moed} "
            f"({self._current_index + 1}/{len(self._view_models)})"
        )
        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(self._current_index < len(self._view_models) - 1)

        self._render_calendar()

    def _on_prev_clicked(self) -> None:
        """Save the current period's state and move to the previous one."""
        self._save_current_state()
        self._current_index -= 1
        self._load_current_state()
        self._refresh_ui()

    def _on_next_clicked(self) -> None:
        """Save the current period's state and move to the next one."""
        self._save_current_state()
        self._current_index += 1
        self._load_current_state()
        self._refresh_ui()

    def _on_dates_changed(self) -> None:
        """Redraw the calendar whenever the start or end date picker changes."""
        self._render_calendar()

    def _render_calendar(self) -> None:
        """Rebuild the calendar grid from the current start/end date range.

        Every cell starts green (included). Excluded dates are then painted
        red on top. This avoids changing CalendarWidget's neutral default
        style, which must stay white for the output screen.
        """
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

        # Paint every cell green first — all dates start as included.
        for date_str in date_list:
            self.calendar_grid.set_date_excluded_style(date_str, False)

        # Then paint the already-excluded dates red on top of the green base.
        for ex_date in self._excluded_dates:
            self.calendar_grid.set_date_excluded_style(ex_date, True)

    def toggle_date_exclusion(self, date_str: str) -> None:
        """Toggle a date between included (green) and excluded (red).

        Called when the user clicks a cell. Updates the internal exclusion
        set and immediately repaints the cell to give visual feedback.
        """
        if date_str in self._excluded_dates:
            self._excluded_dates.remove(date_str)
            # Date is back in — restore green to show it is included again.
            self.calendar_grid.set_date_excluded_style(date_str, False)
        else:
            self._excluded_dates.add(date_str)
            # Date is excluded — turn red to show it has been removed.
            self.calendar_grid.set_date_excluded_style(date_str, True)

    def _on_apply_clicked(self) -> None:
        """Save all periods and emit the constraints_saved signal."""
        self._save_current_state()
        self.constraints_saved.emit(self._view_models)
        QMessageBox.information(
            self, "Saved",
            f"Constraints saved successfully for all {len(self._view_models)} periods."
        )