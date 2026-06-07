"""Widget for rendering the structural grid layouts of exam results."""
from __future__ import annotations

from typing import List, Dict
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
                month_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #3396ad; padding: 12px 0 6px 0;")
                month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Span the header across all 7 columns
                self.grid_layout.addWidget(month_lbl, row, 0, 1, 7)
                
                row += 1
                current_month = month_str
                
                # Recalculate column offset for the first day of the new month
                col = qdate.dayOfWeek() % 7

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
        """Maps pre-composed presentation model details inside matched layout placeholders."""
        for item in items:
            target_date = item.date
            
            # Validate if target exam placement calendar keys exist within the active viewport
            if target_date in self._day_layouts:
                container_layout = self._day_layouts[target_date]
                
                exam_lbl = QLabel(f"{item.title}\n{item.subtitle}")
                exam_lbl.setWordWrap(True)
                
                # Apply explicit centralized texts alignments rules matching PyQt6 specifications
                exam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Tooltip configuration using string streams prepared inside business mappers
                exam_lbl.setToolTip(item.tooltip)
                
                # Bar-Ilan light green background with dark green text replaces the blue palette
                exam_lbl.setStyleSheet(
                    "QLabel { background-color: #FAF5EC; color: #3E352F; "
                    "border: 1px solid #3396ad; font-size: 11px; border-radius: 4px; padding: 2px; }"
                )
                container_layout.addWidget(exam_lbl)

    def set_date_excluded_style(self, date_str: str, is_excluded: bool) -> None:
        """Grey out the cell if excluded, else normal."""
        if date_str in self._day_frames:
            frame = self._day_frames[date_str]
            if is_excluded:
                # Grey out the date so we don't have exams on our days off
                frame.setStyleSheet("QFrame { background-color: #E2E8F0; border: 1px solid #CBD5E1; border-radius: 8px; min-height: 60px; }")
            else:
                # Revert to normal
                frame.setStyleSheet("QFrame { background-color: #FAFAFA; border: 1px solid #E2E8F0; border-radius: 8px; min-height: 60px; }")
