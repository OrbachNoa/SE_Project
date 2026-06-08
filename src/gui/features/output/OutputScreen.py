"""
Output screen for the exam scheduler.

This screen shows the generated schedules one at a time. It owns two
navigation bars and a calendar area:

    Solution bar : moves between page loads of 10,000 schedules as well as
                   individual schedules inside the page that is currently
                   loaded in memory.
    Calendar     : the area where the currently selected schedule is drawn.

PDF export is handled entirely by SchedulePdfExporter so this file stays
focused on navigation and display logic only.
"""
from __future__ import annotations

from typing import List
from datetime import datetime, timedelta
from gui.common.components.CalendarWidget import CalendarWidget
from gui.common.components.HeaderWidget import HeaderWidget
from gui.common.helpers import create_divider
from gui.features.output.widgets.SchedulePdfExporter import export_schedule_pdf
from gui.features.output.widgets.SolutionBarWidget import SolutionBarWidget
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

from PyQt6.QtWidgets import (
    QLabel, QMessageBox, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
from gui.core.screen import Screen

# Variable for max number of schedules in memory
_PAGE_WINDOW = 10_000


class OutputScreen(Screen):
    """Displays generated schedules with solution and page navigation."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router

        # Index of the schedule shown inside the page that is loaded in memory.
        self._current_index: int = 0

        # Number of schedules held in the page currently loaded in memory.
        self._total: int = 0

        # Pagination state mirrored from the SQLite backed repository.
        self._current_page: int = 0
        self._total_pages: int = 0
        self._total_found: int = 0
        self._sqlite_count: int = 0

        # Contiguous list of loaded period view models
        self._available_periods: List[PeriodEditViewModel] = []
        # Current active period index showing on the calendar
        self._current_period_index: int = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Build the screen top to bottom.
        self._build_header(root)
        self._build_solution_bar(root)
        self._build_calendar_area(root)

        # Show the initial empty state before any schedule is loaded.
        self._refresh_counter()
        # Update page navigation status when new batches are written to disk
        self._controller.total_count_updated.connect(self._on_total_count_updated)

    def _build_header(self, root: QVBoxLayout) -> None:
        """Build the gold branding bar with active output breadcrumb at the top of the screen."""
        header = HeaderWidget(parent=self)
        root.addWidget(header)

    def _build_solution_bar(self, root: QVBoxLayout) -> None:
        """Build the reusable solution navigation bar."""
        self.solution_bar = SolutionBarWidget(self)
        self.solution_bar.back_btn.clicked.connect(self._on_back)
        self.solution_bar.export_btn.clicked.connect(self._on_export_pdf)
        self.solution_bar.prev_btn.clicked.connect(self.on_prev)
        self.solution_bar.next_btn.clicked.connect(self.on_next)
        self.solution_bar.first_page_btn.clicked.connect(self._on_first_page)
        self.solution_bar.prev_page_btn.clicked.connect(self._on_prev_page)
        self.solution_bar.next_page_btn.clicked.connect(self._on_next_page)
        self.solution_bar.last_page_btn.clicked.connect(self._on_last_page)
        root.addWidget(self.solution_bar)
        root.addWidget(create_divider())

    def _build_calendar_area(self, root: QVBoxLayout) -> None:
        """
        Build the scrollable area that holds the calendar widget,
        including a navigation bar for switching between months.
        """
        body = QVBoxLayout()
        body.setContentsMargins(28, 20, 28, 20)
        body.setSpacing(0)

        content_card = QFrame()
        content_card.setObjectName("content-area")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Period Navigation Bar - allows user to navigate between semester periods
        month_nav_frame = QFrame()
        month_nav_frame.setObjectName("month-nav-bar")
        month_nav_layout = QHBoxLayout(month_nav_frame)
        month_nav_layout.setContentsMargins(20, 10, 20, 10)
        
        self.prev_month_btn = QPushButton("← Prev Period")
        self.prev_month_btn.setFixedWidth(130)
        self.prev_month_btn.clicked.connect(self._on_prev_month)
        
        self.month_label = QLabel("")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_month_btn = QPushButton("Next Period →")
        self.next_month_btn.setFixedWidth(130)
        self.next_month_btn.clicked.connect(self._on_next_month)
        
        month_nav_layout.addWidget(self.prev_month_btn)
        month_nav_layout.addWidget(self.month_label, stretch=1)
        month_nav_layout.addWidget(self.next_month_btn)
        content_layout.addWidget(month_nav_frame)

        # A scroll area keeps a long calendar usable on small windows.
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._content_widget = QWidget()
        self._content_widget.setObjectName("calendar-scroll-content")
        content_inner = QVBoxLayout(self._content_widget)
        content_inner.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.calendar_grid = CalendarWidget()
        content_inner.addWidget(self.calendar_grid)

        self._scroll.setWidget(self._content_widget)
        content_layout.addWidget(self._scroll)

        body.addWidget(content_card)
        root.addLayout(body)

    def _refresh_counter(self) -> None:
        """Update the solution counter and refresh the page button states."""
        if self._total == 0:
            self.solution_bar.counter_label.setText("No solutions")
        else:
            self.solution_bar.counter_label.setText(
                f"Solution {self._current_index + 1} / {self._total}"
            )

        # Keep the arrows strictly inside the bounds of the current window.
        self.solution_bar.prev_btn.setEnabled(self._current_index > 0)
        self.solution_bar.next_btn.setEnabled(self._current_index < self._total - 1)

        # Export only makes sense when there is a schedule on screen.
        self.solution_bar.export_btn.setEnabled(self._total > 0)

        self._refresh_page_bar()

    def _refresh_page_bar(self) -> None:
        """Update the page navigation button visibility and enabled states."""
        has_multiple_pages = self._total_pages > 1
        self.solution_bar.pages_group.setVisible(has_multiple_pages)
        if not has_multiple_pages:
            return

        # Refresh the page counter and button states
        self.solution_bar.page_label.setText(f"Page {self._current_page + 1} / {self._total_pages}")
        self.solution_bar.first_page_btn.setEnabled(self._current_page > 0)
        self.solution_bar.prev_page_btn.setEnabled(self._current_page > 0)

        # Check if the next page is ready
        next_page_index = self._current_page + 1
        rows_needed_on_disk = next_page_index * _PAGE_WINDOW
        next_page_is_ready = self._sqlite_count >= rows_needed_on_disk
        
        # Enable/disable the next page buttons based on whether the next page is ready
        has_next = self._current_page < self._total_pages - 1
        self.solution_bar.next_page_btn.setEnabled(has_next and next_page_is_ready)
        self.solution_bar.last_page_btn.setEnabled(has_next and next_page_is_ready)

    def _on_total_count_updated(self, _total: int) -> None:
        """
        Update the total count of solutions and refresh the page bar.
        """
        info = self._controller.get_page_info()
        self._total_found = info["total_count"]
        self._total_pages = info["total_pages"]
        self._sqlite_count = info.get("sqlite_count", 0)

        if self._current_page == 0:
            self._total = info["window_size"]
            self._refresh_counter()
        else:
            self._refresh_page_bar()

    def _on_next_page(self) -> None:
        """Load the next page, reset to its first schedule and redraw."""
        target = self._current_page + 1
        # Check if the next page is within the valid range
        if target >= self._total_pages:
            return
        self._controller.load_page(target)
        self._sync_page_info()
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def _on_prev_page(self) -> None:
        """Load the previous page, reset to its first schedule and redraw."""
        target = self._current_page - 1
        if target < 0:
            return
        self._controller.load_page(target)
        self._sync_page_info()
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def _on_first_page(self) -> None:
        """Load the first page, reset to its first schedule and redraw."""
        if self._current_page == 0:
            return
        self._controller.load_page(0)
        self._sync_page_info()
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def _on_last_page(self) -> None:
        """Load the last page, reset to its first schedule and redraw."""
        target = self._total_pages - 1
        if target < 0 or self._current_page == target:
            return
        self._controller.load_page(target)
        self._sync_page_info()
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def _show_current(self) -> None:
        """
        Draw the schedule at the current index inside the calendar widget.
        """
        if self._total == 0:
            return
            
        # Freeze the screen while the calendar is being rebuilt
        self.setUpdatesEnabled(False)
        try:
            view = self._controller.get_schedule_view(self._current_index)
            
            # Make sure available periods are initialized
            if not hasattr(self, "_available_periods") or not self._available_periods:
                self._available_periods = self._get_available_periods()
                self._current_period_index = 0
                
            # Bounds check current period index
            if self._current_period_index >= len(self._available_periods):
                self._current_period_index = max(0, len(self._available_periods) - 1)
            if self._current_period_index < 0:
                self._current_period_index = 0
                
            if not self._available_periods:
                return
                
            selected_period = self._available_periods[self._current_period_index]
            
            # Update the period label text (e.g. "Semester FALL - Moed ALEPH (1/4)")
            self.month_label.setText(
                f"Semester {selected_period.semester} - Moed {selected_period.moed} "
                f"({self._current_period_index + 1}/{len(self._available_periods)})"
            )
            
            # Update navigation buttons enabled states
            self.prev_month_btn.setEnabled(self._current_period_index > 0)
            self.next_month_btn.setEnabled(self._current_period_index < len(self._available_periods) - 1)
            
            # Generate the dates only for the selected period range
            start = datetime.strptime(selected_period.start_date, "%Y-%m-%d")
            end = datetime.strptime(selected_period.end_date, "%Y-%m-%d")
            
            # Create a list of dates in the selected period range
            date_list = []
            if end >= start:
                delta = end - start
                for i in range(delta.days + 1):
                    day = start + timedelta(days=i)
                    date_list.append(day.strftime("%Y-%m-%d"))
                
            self.calendar_grid.setup_month_grid(date_list, show_month_header=False, show_month_banner=True)
            
            # Paint excluded dates in the output calendar with soft brown shade
            for ex_date in selected_period.excluded_dates:
                self.calendar_grid.set_date_excluded_output_style(ex_date)
            
            # Filter assignments to only show the ones in the selected period date range
            filtered_items = [
                item for item in view.items 
                if item.date and selected_period.start_date <= item.date <= selected_period.end_date
            ]
            self.calendar_grid.display_assignments(filtered_items)
            
        except Exception as error:
            # Show error message if something goes wrong
            QMessageBox.critical(self, "Display Error", f"Failed to paint calendar: {error}")
        finally:
            # Re-enable repaints
            self.setUpdatesEnabled(True)

    def _on_back(self) -> None:
        """
        Return to the input screen using the router history.
        """
        self._router.back()

    def _on_export_pdf(self) -> None:
        """
        Save the schedule that is currently on screen as a PDF.
        """
        # Check if there is a schedule to export
        if self._total == 0:
            QMessageBox.information(self, "Nothing to export", "There is no schedule to export yet.")
            return

        # Read the display data for the schedule currently shown
        try:
            view = self._controller.get_schedule_view(self._current_index)
        except Exception as error:
            QMessageBox.critical(self, "Export error", f"Could not read the current schedule:\n{error}")
            return

        if view.is_empty():
            QMessageBox.information(self, "Nothing to export", "This schedule has no exams to export.")
            return

        # Delegate the file dialog, HTML build, PDF write and result dialog to the exporter.
        export_schedule_pdf(view, self._current_index, parent=self)

    def _sync_page_info(self) -> None:
        """
        Copy the current paging state from the controller into this screen.
        """
        info = self._controller.get_page_info()
        self._current_page = info["current_page"]
        self._total_pages = info["total_pages"]
        self._total = info["window_size"]
        self._total_found = info["total_count"]
        self._sqlite_count = info.get("sqlite_count", 0)

    def _get_available_periods(self) -> List[PeriodEditViewModel]:
        """Get the mapped PeriodEditViewModel instances for all loaded periods."""
        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if mapper and periods:
            return mapper.to_period_edit_vms(periods)
        return []

    def _on_prev_month(self) -> None:
        """Switch calendar view to the previous period."""
        if self._current_period_index > 0:
            self._current_period_index -= 1
            self._show_current()

    def _on_next_month(self) -> None:
        """Switch calendar view to the next period."""
        if self._current_period_index < len(self._available_periods) - 1:
            self._current_period_index += 1
            self._show_current()

    def on_next(self) -> None:
        """Move forward one schedule inside the current page."""
        if self._current_index < self._total - 1:
            self._current_index += 1
            self._show_current()
            self._refresh_counter()

    def on_prev(self) -> None:
        """Move back one schedule inside the current page."""
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current()
            self._refresh_counter()

    def on_enter(self) -> None:
        """
        Prepare the screen each time the router makes it active.
        """
        self._current_index = 0
        self._sync_page_info()
        self._available_periods = self._get_available_periods()
        self._current_period_index = 0
        self._show_current()
        self._refresh_counter()
        self.solution_bar.back_btn.setFocus()

    def on_leave(self) -> None:
        """Called by the router when navigating away from this screen."""
        pass

    @property
    def _prev_btn(self):
        return self.solution_bar.prev_btn

    @property
    def _next_btn(self):
        return self.solution_bar.next_btn

    @property
    def _counter_label(self):
        return self.solution_bar.counter_label