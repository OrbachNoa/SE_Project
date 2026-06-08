"""Widget for rendering the structural grid layouts of exam results."""
from __future__ import annotations

from typing import List, Dict
import re
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QVBoxLayout, QFrame, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QDate

from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel


class CalendarWidget(QWidget):
    """Visual day-matrix rendering engine displaying pre-composed schedule items."""
    
    # Custom signal to yell at the editor when a date is clicked
    date_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        
        # Track live calendar cells layout pointers using ISO strings as keys
        self._day_layouts: Dict[str, QVBoxLayout] = {}
        # Need to keep track of the frames so we can style them later
        self._day_frames: Dict[str, QFrame] = {} 
        self._init_ui()

    def _init_ui(self) -> None:
        """Sets up container bounds and structural parameters."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        # Month banner label shown at the top of the calendar widget
        self.month_lbl = QLabel("")
        self.month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_lbl.setObjectName("calendar-month-banner")
        self.month_lbl.setVisible(False)
        self.main_layout.addWidget(self.month_lbl)

        # Container frame managing days-of-week descriptor rows
        self.headers_frame = QFrame()
        self.headers_layout = QGridLayout(self.headers_frame)
        self.headers_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add day names in the header
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        
        # Draw text labels systematically for columns header trackers
        for column_idx, name in enumerate(days):
            lbl = QLabel(name)

            # Align text to the center
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl.setObjectName("calendar-header-day")
            self.headers_layout.addWidget(lbl, 0, column_idx)
            
        self.main_layout.addWidget(self.headers_frame)

        # Scroll area to handle multiple months without squishing the cells
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Primary operational bounding viewport layout matrix for active month cells
        self.grid_frame = QFrame()
        self.grid_layout = QGridLayout(self.grid_frame)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Align top prevents cells from stretching vertically when space is available
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.grid_frame)
        self.main_layout.addWidget(self.scroll_area)

    def setup_month_grid(self, date_list: List[str], show_month_header: bool = True, show_month_banner: bool = True) -> None:
        """Flushes viewport matrix structures and maps date squares with month headers."""
        # Update/show top month banner if requested
        if show_month_banner and date_list:
            # Get unique months in the date list
            unique_months = []
            # Iterate through the date list
            for date_str in date_list:
                qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
                m_str = qdate.toString("MMMM yyyy")
                if m_str not in unique_months:
                    unique_months.append(m_str)
            # Set the month banner text if there are any unique months
            if unique_months:
                self.month_lbl.setText(" - ".join(unique_months))
                self.month_lbl.setVisible(True)
            else:
                self.month_lbl.setVisible(False)
        else:
            self.month_lbl.setVisible(False)

        # Wipe past container allocations securely
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        self._day_layouts.clear()
        self._day_frames.clear()

        # Give every weekday column the same share of horizontal space.
        for c in range(7):
            self.grid_layout.setColumnStretch(c, 1)

        # If there are no dates, return
        if not date_list:
            return

        # Show month headers if requested
        if show_month_header:
            current_month = None
            month_start_row = 0
            max_row_in_month = 0

            # Iterate through the date list
            for date_str in date_list:
                qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
                month_str = qdate.toString("MMMM yyyy")

                # Handle month change and print month header
                if month_str != current_month:
                    if current_month is not None:
                        # Move to a new row for the new month to avoid overlapping
                        month_start_row = month_start_row + max_row_in_month + 1
                    
                    month_lbl = QLabel(month_str)
                    month_lbl.setObjectName("calendar-month-header")
                    month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Span the header across all 7 columns
                    self.grid_layout.addWidget(month_lbl, month_start_row, 0, 1, 7)
                    month_start_row += 1
                    
                    current_month = month_str
                    max_row_in_month = 0
                    
                    # Find the starting weekday column for the 1st of this month
                    first_day_of_month = QDate(qdate.year(), qdate.month(), 1)
                    first_col = first_day_of_month.dayOfWeek() % 7

                # Compute row and col for this date based on first_col and day of month
                day_num = qdate.day()
                total_days_offset = first_col + day_num - 1
                col = total_days_offset % 7
                row_offset = total_days_offset // 7
                # Update the maximum row in the month
                if row_offset > max_row_in_month:
                    max_row_in_month = row_offset
                actual_row = month_start_row + row_offset
                # Create the cell widget
                self._create_cell_widget(date_str, qdate, actual_row, col)
        else:
            # Get the first date
            first_qdate = QDate.fromString(date_list[0], Qt.DateFormat.ISODate)
            # Get the starting column
            start_col = first_qdate.dayOfWeek() % 7
            
            # Iterate through the date list
            for i, date_str in enumerate(date_list):
                qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
                total_days_offset = start_col + i
                col = total_days_offset % 7
                actual_row = total_days_offset // 7
                self._create_cell_widget(date_str, qdate, actual_row, col)

    def _create_cell_widget(self, date_str: str, qdate: QDate, row: int, col: int) -> None:
        """Create a single date cell widget and place it in the grid."""
        cell_frame = QFrame()
        cell_frame.setFrameShape(QFrame.Shape.StyledPanel)
        cell_frame.setObjectName("calendar-cell-frame")
        cell_frame.mousePressEvent = lambda event, d=date_str: self.date_clicked.emit(d)
        
        cell_layout = QVBoxLayout(cell_frame)
        cell_layout.setContentsMargins(6, 4, 6, 4)
        cell_layout.setSpacing(4)

        day_lbl = QLabel(str(qdate.day()))
        day_lbl.setObjectName("calendar-day-lbl")
        day_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        cell_layout.addWidget(day_lbl)
        self.grid_layout.addWidget(cell_frame, row, col)
        self._day_layouts[date_str] = cell_layout
        self._day_frames[date_str] = cell_frame

    def display_assignments(self, items: List[ScheduleItemViewModel]) -> None:
        """
        Place exam tiles into the matching day cells on the calendar grid.

        Each cell shows the course name and its subtitle (course id, programs,
        obligatory/elective).
        """
        # Iterate through the items
        for item in items:
            target_date = item.date

            # Check if the target date is in the day layouts
            if target_date in self._day_layouts:
                # Get the container layout
                container_layout = self._day_layouts[target_date]

                # Convert the subtitle from HTML to plain text.
                clean_subtitle = item.subtitle.replace("<br>", "\n")
                clean_subtitle = re.sub(r"<[^>]+>", "", clean_subtitle)
                # Remove "ID: " prefix
                clean_subtitle = clean_subtitle.replace("ID: ", "")
                # Create the exam label with the course name and subtitle
                exam_lbl = QLabel(f"{item.title}\n{clean_subtitle}")
                exam_lbl.setWordWrap(True)
                exam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                # The tooltip keeps the complete detail for quick reference.
                exam_lbl.setToolTip(item.tooltip)
                # Bar-Ilan light green tile with dark green text.
                exam_lbl.setObjectName("calendar-exam-badge")
                container_layout.addWidget(exam_lbl)

    def set_date_excluded_style(self, date_str: str, is_excluded: bool) -> None:
        """
        Switch a cell between the included (soft teal) and excluded (dark charcoal) style.
        """
        # Check if the target date is in the day frames
        if date_str in self._day_frames:
            frame = self._day_frames[date_str]
            # Check if the date is excluded
            if is_excluded:
                # Dark charcoal — this day has been removed from the exam period.
                frame.setObjectName("calendar-cell-excluded")
            else:
                # Soft teal — this day is included in the exam period.
                frame.setObjectName("calendar-cell-included")
            frame.style().unpolish(frame)
            frame.style().polish(frame)

    def set_date_excluded_output_style(self, date_str: str) -> None:
        """Style an excluded date cell in the output calendar with a soft brown/muted shade."""
        if date_str in self._day_frames:
            frame = self._day_frames[date_str]
            frame.setObjectName("calendar-cell-excluded-output")
            frame.style().unpolish(frame)
            frame.style().polish(frame)
