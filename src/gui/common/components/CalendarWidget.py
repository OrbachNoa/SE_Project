"""Widget for rendering structural calendar grids."""
from __future__ import annotations

import re
from typing import Dict, List

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel


class CalendarWidget(QWidget):
    """Visual day-matrix rendering engine displaying pre-composed schedule items."""

    date_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._day_layouts: Dict[str, QVBoxLayout] = {}
        self._day_frames: Dict[str, QFrame] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        self.month_lbl = QLabel("")
        self.month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_lbl.setObjectName("calendar-month-banner")
        self.month_lbl.setVisible(False)
        self.main_layout.addWidget(self.month_lbl)

        self.headers_frame = QFrame()
        self.headers_layout = QGridLayout(self.headers_frame)
        self.headers_layout.setContentsMargins(0, 0, 0, 0)

        for column_idx, name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName("calendar-header-day")
            self.headers_layout.addWidget(label, 0, column_idx)

        self.main_layout.addWidget(self.headers_frame)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.grid_frame = QFrame()
        self.grid_layout = QGridLayout(self.grid_frame)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.grid_frame)
        self.main_layout.addWidget(self.scroll_area)

    def setup_month_grid(
        self,
        date_list: List[str],
        show_month_header: bool = True,
        show_month_banner: bool = True,
    ) -> None:
        """Clear the calendar grid and create one cell for each ISO date."""
        self._refresh_month_banner(date_list, show_month_banner)
        self._clear_grid()

        for column in range(7):
            self.grid_layout.setColumnStretch(column, 1)

        if not date_list:
            return

        if show_month_header:
            self._build_grid_with_month_headers(date_list)
        else:
            self._build_contiguous_grid(date_list)

    def _refresh_month_banner(self, date_list: List[str], show_month_banner: bool) -> None:
        if not show_month_banner or not date_list:
            self.month_lbl.setVisible(False)
            return

        unique_months: list[str] = []
        for date_str in date_list:
            qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
            month_text = qdate.toString("MMMM yyyy")
            if month_text not in unique_months:
                unique_months.append(month_text)

        if unique_months:
            self.month_lbl.setText(" - ".join(unique_months))
            self.month_lbl.setVisible(True)
        else:
            self.month_lbl.setVisible(False)

    def _clear_grid(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._day_layouts.clear()
        self._day_frames.clear()

    def _build_grid_with_month_headers(self, date_list: List[str]) -> None:
        current_month = None
        month_start_row = 0
        max_row_in_month = 0
        first_col = 0

        for date_str in date_list:
            qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
            month_text = qdate.toString("MMMM yyyy")

            if month_text != current_month:
                if current_month is not None:
                    month_start_row = month_start_row + max_row_in_month + 1

                month_label = QLabel(month_text)
                month_label.setObjectName("calendar-month-header")
                month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.grid_layout.addWidget(month_label, month_start_row, 0, 1, 7)
                month_start_row += 1

                current_month = month_text
                max_row_in_month = 0
                first_day_of_month = QDate(qdate.year(), qdate.month(), 1)
                first_col = first_day_of_month.dayOfWeek() % 7

            total_days_offset = first_col + qdate.day() - 1
            col = total_days_offset % 7
            row_offset = total_days_offset // 7
            max_row_in_month = max(max_row_in_month, row_offset)
            self._create_cell_widget(date_str, qdate, month_start_row + row_offset, col)

    def _build_contiguous_grid(self, date_list: List[str]) -> None:
        first_qdate = QDate.fromString(date_list[0], Qt.DateFormat.ISODate)
        start_col = first_qdate.dayOfWeek() % 7

        for offset, date_str in enumerate(date_list):
            qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
            total_days_offset = start_col + offset
            self._create_cell_widget(
                date_str,
                qdate,
                total_days_offset // 7,
                total_days_offset % 7,
            )

    def _create_cell_widget(self, date_str: str, qdate: QDate, row: int, col: int) -> None:
        cell_frame = QFrame()
        cell_frame.setFrameShape(QFrame.Shape.StyledPanel)
        cell_frame.setObjectName("calendar-cell-frame")
        cell_frame.mousePressEvent = lambda event, date=date_str: self.date_clicked.emit(date)

        cell_layout = QVBoxLayout(cell_frame)
        cell_layout.setContentsMargins(6, 4, 6, 4)
        cell_layout.setSpacing(4)

        day_label = QLabel(str(qdate.day()))
        day_label.setObjectName("calendar-day-lbl")
        day_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        cell_layout.addWidget(day_label)

        self.grid_layout.addWidget(cell_frame, row, col)
        self._day_layouts[date_str] = cell_layout
        self._day_frames[date_str] = cell_frame

    def display_assignments(self, items: List[ScheduleItemViewModel]) -> None:
        """Place exam tiles into the matching day cells on the calendar grid."""
        for item in items:
            target_date = item.date
            if target_date not in self._day_layouts:
                continue

            clean_subtitle = item.subtitle.replace("<br>", "\n")
            clean_subtitle = re.sub(r"<[^>]+>", "", clean_subtitle)
            clean_subtitle = clean_subtitle.replace("ID: ", "")

            exam_label = QLabel(f"{item.title}\n{clean_subtitle}")
            exam_label.setWordWrap(True)
            exam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            exam_label.setToolTip(item.tooltip)
            exam_label.setObjectName("calendar-exam-badge")
            self._day_layouts[target_date].addWidget(exam_label)

    def set_date_excluded_style(self, date_str: str, is_excluded: bool) -> None:
        object_name = "calendar-cell-excluded" if is_excluded else "calendar-cell-included"
        self._set_date_object_name(date_str, object_name)

    def _set_date_object_name(self, date_str: str, object_name: str) -> None:
        if date_str not in self._day_frames:
            return

        frame = self._day_frames[date_str]
        frame.setObjectName(object_name)
        frame.style().unpolish(frame)
        frame.style().polish(frame)
