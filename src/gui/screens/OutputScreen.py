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

from gui.widgets.CalendarWidget import CalendarWidget
from gui.widgets.SchedulePdfExporter import export_schedule_pdf

from PyQt6.QtWidgets import (
    QLabel, QMessageBox, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QFont

from gui.screen import Screen

# One SQLite result page holds this many schedules. The same value is used by
# the storage layer, so the two must always match. If they ever differ the page
# navigation will jump to the wrong offsets.
_PAGE_WINDOW = 10_000


# Shared helper create_divider is imported from gui.widgets.Common


class OutputScreen(Screen):
    """Displays generated schedules with solution and page navigation."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router

        # Index of the schedule shown inside the page that is loaded in memory.
        # It is zero based and always stays within the current window.
        self._current_index: int = 0

        # Number of schedules held in the page currently loaded in memory.
        self._total: int = 0

        # Pagination state mirrored from the SQLite backed repository.
        # Page numbers are zero based internally and shown to the user as one
        # based. sqlite_count is the running number of schedules written to disk
        # so far across every page, which is what lets us tell whether the next
        # page is ready to be opened.
        self._current_page: int = 0
        self._total_pages: int = 0
        self._total_found: int = 0
        self._sqlite_count: int = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Build the screen top to bottom.
        self._build_header(root)
        self._build_solution_bar(root)
        self._build_calendar_area(root)

        # Show the initial empty state before any schedule is loaded.
        self._refresh_counter()

        # Stay in sync while the search keeps running in the background.
        # Every time the worker writes a batch of schedules to SQLite the
        # controller emits total_count_updated. We use it to keep the counters
        # and the Next page button state current without asking the user to
        # reload the screen.
        self._controller.total_count_updated.connect(self._on_total_count_updated)

    def _build_header(self, root: QVBoxLayout) -> None:
        """Build the gold branding bar with active output breadcrumb at the top of the screen."""
        header = HeaderWidget(active_step="output", parent=self)
        root.addWidget(header)

    def _build_solution_bar(self, root: QVBoxLayout) -> None:
        """Build the reusable solution navigation bar."""
        from gui.widgets.SolutionBarWidget import SolutionBarWidget
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
        Build the scrollable area that holds the calendar widget.

        The calendar widget is rebuilt for every schedule that is shown. We
        hide its weekday header because the cells are laid out by exam date and
        not by real weekday, so that header never lines up with the cells.
        """
        body = QVBoxLayout()
        body.setContentsMargins(28, 20, 28, 20)
        body.setSpacing(0)

        content_card = QFrame()
        content_card.setObjectName("content-area")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # A scroll area keeps a long calendar usable on small windows.
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        content_inner = QVBoxLayout(self._content_widget)
        content_inner.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.calendar_grid = CalendarWidget()

        # Hide the "Sun Mon Tue ..." header row from here, which keeps the
        # calendar widget itself untouched. The header is misleading because
        # the cells below are ordered by date rather than by weekday.
        if hasattr(self.calendar_grid, "headers_frame"):
            self.calendar_grid.headers_frame.setVisible(False)

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

        self.solution_bar.page_label.setText(f"Page {self._current_page + 1} / {self._total_pages}")
        self.solution_bar.first_page_btn.setEnabled(self._current_page > 0)
        self.solution_bar.prev_page_btn.setEnabled(self._current_page > 0)

        # Work out whether the next page is already fully written to disk.
        next_page_index = self._current_page + 1
        rows_needed_on_disk = next_page_index * _PAGE_WINDOW
        next_page_is_ready = self._sqlite_count >= rows_needed_on_disk
        
        has_next = self._current_page < self._total_pages - 1
        self.solution_bar.next_page_btn.setEnabled(has_next and next_page_is_ready)
        self.solution_bar.last_page_btn.setEnabled(has_next and next_page_is_ready)

    def _on_total_count_updated(self, total: int) -> None:
        """
        React to a new batch being written to disk while the search runs.

        We re-read the authoritative page info from the controller so the local
        state matches the repository exactly, even when several batches landed
        between two repaints. On page 0 the in memory window keeps growing as
        results arrive, so the solution counter is refreshed too. On later pages
        only the page bar changes.
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
        if target >= self._total_pages:
            # Discard clicks that arrived after the state already changed, for
            # example a fast double click on the last enabled page.
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
        """Draw the schedule at the current index inside the calendar widget.

        Repaints are suspended while the grid is torn down and rebuilt so the
        user never sees a flash of empty content. The final result appears in
        one frame once everything is ready.
        """
        if self._total == 0:
            return
        # Freeze the screen while the calendar is being rebuilt. Without this,
        # all the widget deletions and creations happen in full view and the
        # user sees a brief flicker of partially-drawn content.
        self.setUpdatesEnabled(False)
        try:
            view = self._controller.get_schedule_view(self._current_index)
            # Build the empty calendar from the unique exam dates first.
            active_dates = sorted({item.date for item in view.items})
            self.calendar_grid.setup_month_grid(active_dates)
            # Then place the exam tiles into their matching cells.
            self.calendar_grid.display_assignments(view.items)
        except Exception as error:
            QMessageBox.critical(self, "Display Error", f"Failed to paint calendar: {error}")
        finally:
            # Always re-enable repaints, even if an error occurred, otherwise
            # the entire screen would stay frozen.
            self.setUpdatesEnabled(True)

    def _on_back(self) -> None:
        """Return to the input screen using the router history."""
        self._router.back()

    def _on_export_pdf(self) -> None:
        """
        Save the schedule that is currently on screen as a PDF.

        Validation (empty state, empty view) stays here because it needs access
        to self._total and the controller. The actual HTML build and PDF write
        are delegated to SchedulePdfExporter to keep this file focused on
        navigation and display logic.
        """
        if self._total == 0:
            QMessageBox.information(self, "Nothing to export", "There is no schedule to export yet.")
            return

        # Read the display data for the schedule currently shown.
        try:
            view = self._controller.get_schedule_view(self._current_index)
        except Exception as error:
            QMessageBox.critical(self, "Export error", f"Could not read the current schedule:\n{error}")
            return

        if view.is_empty():
            QMessageBox.information(self, "Nothing to export", "This schedule has no exams to export.")
            return

        # Delegate the file dialog, HTML build, PDF write and result dialog to
        # the dedicated exporter module so this file stays lean.
        export_schedule_pdf(view, self._current_index, parent=self)

    def _sync_page_info(self) -> None:
        """Copy the current paging state from the controller into this screen."""
        info = self._controller.get_page_info()
        self._current_page = info["current_page"]
        self._total_pages = info["total_pages"]
        self._total = info["window_size"]
        self._total_found = info["total_count"]
        self._sqlite_count = info.get("sqlite_count", 0)

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

        We reset to the first schedule, refresh the paging state from the
        controller, draw the calendar and put the focus on Back so the Alt+Left
        shortcut works right away.
        """
        self._current_index = 0
        self._sync_page_info()
        self._show_current()
        self._refresh_counter()
        self.solution_bar.back_btn.setFocus()

    def on_leave(self) -> None:
        """Called by the router when the user navigates away from this screen."""
        pass