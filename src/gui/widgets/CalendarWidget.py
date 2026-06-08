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

        # Container frame managing days-of-week descriptor rows
        self.headers_frame = QFrame()
        self.headers_layout = QGridLayout(self.headers_frame)
        self.headers_layout.setContentsMargins(0, 0, 0, 0)
        
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        
        # Draw text labels systematically for columns header trackers
        for column_idx, name in enumerate(days):
            lbl = QLabel(name)

            # Text alignment conversion adjusted to strictly obey PyQt6 enums
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Slate-500 text with comfortable vertical padding matching card min-height rhythm
            lbl.setStyleSheet("font-weight: 600; color: #64748B; padding: 8px 4px;")
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

    def setup_month_grid(self, date_list: List[str]) -> None:
        """Flushes viewport matrix structures and maps date squares with month headers."""
        # Wipe past container allocations securely
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        self._day_layouts.clear()
        self._day_frames.clear()

        # Give every weekday column the same share of horizontal space. Without
        # this, columns that have no content collapse and the filled columns
        # stretch unevenly, making the grid look lopsided.
        for c in range(7):
            self.grid_layout.setColumnStretch(c, 1)

        if not date_list:
            return

        current_month = None
        row = 0
        col = 0

        for date_str in date_list:
            qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
            month_str = qdate.toString("MMMM yyyy")

            # Handle month change and print month header
            if month_str != current_month:
                if current_month is not None:
                    # Move to a new row for the new month to avoid overlapping
                    row += 1 
                
                month_lbl = QLabel(month_str)
                month_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #008080; padding: 12px 0 6px 0;")
                month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Span the header across all 7 columns
                self.grid_layout.addWidget(month_lbl, row, 0, 1, 7)
                
                row += 1
                current_month = month_str
                
                # Start from the leftmost column. The weekday-based offset was
                # designed for the day-of-week header row, which is no longer
                # visible, so placing cells by weekday only creates empty gaps
                # on the left side of the grid.
                col = 0

            # Generate bounding square shells contextually
            cell_frame = QFrame()
            cell_frame.setFrameShape(QFrame.Shape.StyledPanel)
            # Off-white background for visual depth; min-height ensures usable cell area
            cell_frame.setStyleSheet("QFrame { background-color: #FAFAFA; border: 1px solid #E2E8F0; border-radius: 8px; min-height: 60px; }")
            # Turning the cell to pressable and passing the date
            cell_frame.mousePressEvent = lambda event, d=date_str: self.date_clicked.emit(d)
            
            cell_layout = QVBoxLayout(cell_frame)
            cell_layout.setContentsMargins(6, 4, 6, 4)
            cell_layout.setSpacing(4)

            # Draw upper text marker tracking the explicit calendar month offset element
            day_num = date_str.split("-")[-1]
            day_lbl = QLabel(day_num)
            day_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; background: transparent;")
            
            # Target left side placement for numerical indexing alignment bounds
            day_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            
            cell_layout.addWidget(day_lbl)
            self.grid_layout.addWidget(cell_frame, row, col)
            self._day_layouts[date_str] = cell_layout
            self._day_frames[date_str] = cell_frame

            col += 1

            # Step down down into subsequent grid levels whenever completing a weekly block
            if col > 6:
                col = 0
                row += 1

    def display_assignments(self, items: List[ScheduleItemViewModel]) -> None:
        """Place exam tiles into the matching day cells on the calendar grid.

        Each cell shows the course name and its subtitle (course id, programs,
        obligatory/elective). The subtitle may contain HTML markup produced by
        the mapper, so we convert it to plain text before displaying: line break
        tags become real newlines and any remaining tags are stripped out. The
        full unabridged detail is also available in the tooltip on hover.
        """
        for item in items:
            target_date = item.date

            if target_date in self._day_layouts:
                container_layout = self._day_layouts[target_date]

                # Convert the subtitle from HTML to plain text. The mapper uses
                # <br> for line breaks and <span> for coloring, which show up as
                # raw tags when a QLabel is in plain text mode. We turn <br> into
                # real newlines and strip every other tag so the cell is readable.
                clean_subtitle = item.subtitle.replace("<br>", "\n")
                clean_subtitle = re.sub(r"<[^>]+>", "", clean_subtitle)
                # Drop the "ID: " prefix — the number alone is clear enough.
                clean_subtitle = clean_subtitle.replace("ID: ", "")

                exam_lbl = QLabel(f"{item.title}\n{clean_subtitle}")
                exam_lbl.setWordWrap(True)
                exam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                # The tooltip keeps the complete detail for quick reference.
                exam_lbl.setToolTip(item.tooltip)

                # Bar-Ilan light green tile with dark green text.
                exam_lbl.setStyleSheet(
                    "QLabel { background-color: #E5F0EB; color: #143D30; "
                    "border: 1px solid #B7D4C5; font-size: 11px; border-radius: 4px; padding: 4px; }"
                )
                container_layout.addWidget(exam_lbl)

    def set_date_excluded_style(self, date_str: str, is_excluded: bool) -> None:
        """Switch a cell between the included (green) and excluded (red) style.

        This method is called by CalendarEditorWidget to colour its cells.
        The output screen never calls this method, so changing these colours
        here only affects the editor and never touches the output calendar.
        Green signals the day is part of the exam period; red signals the user
        has manually removed it.
        """
        if date_str in self._day_frames:
            frame = self._day_frames[date_str]
            if is_excluded:
                # Vivid red — this day has been removed from the exam period.
                frame.setStyleSheet(
                    "QFrame { background-color: #FEE2E2; border: 1px solid #FCA5A5;"
                    " border-radius: 8px; min-height: 60px; }"
                )
            else:
                # Vivid green — this day is included in the exam period.
                frame.setStyleSheet(
                    "QFrame { background-color: #D1FAE5; border: 1px solid #6EE7B7;"
                    " border-radius: 8px; min-height: 60px; }"
                )