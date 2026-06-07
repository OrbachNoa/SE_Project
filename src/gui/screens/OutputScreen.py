"""
Output screen for the exam scheduler.

This screen shows the generated schedules one at a time. It owns two
navigation bars and a calendar area:

    Solution bar : moves between page loads of 10,000 schedules as well as
                   individual schedules inside the page that is currently
                   loaded in memory.
    Calendar     : the area where the currently selected schedule is drawn.

The screen also lets the user save the schedule that is currently on screen to
a PDF file. The PDF is built here, in the view layer, directly from the display
view model. No scheduling logic and no application service is involved, so this
stays a pure presentation feature.
"""
from __future__ import annotations

import html
import os

from gui.widgets.CalendarWidget import CalendarWidget

from PyQt6.QtWidgets import (
    QLabel, QMessageBox, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QTextDocument, QFont

from gui.widgets.HeaderWidget import HeaderWidget
from gui.widgets.Common import create_divider, prompt_save_file
from gui.widgets.SolutionBarWidget import SolutionBarWidget

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

        """
        Pagination state mirrored from the SQLite backed repository.

        Page numbers are zero based internally and shown to the user as one
        based. sqlite_count is the running number of schedules written to disk
        so far across every page, which is what lets us tell whether the next
        page is ready to be opened.
        """
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

        """
        Stay in sync while the search keeps running in the background.

        Every time the worker writes a batch of schedules to SQLite the
        controller emits total_count_updated. We use it to keep the counters
        and the Next page button state current without asking the user to
        reload the screen.
        """
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
        """Draw the schedule at the current index inside the calendar widget."""
        if self._total == 0:
            return
        try:
            view = self._controller.get_schedule_view(self._current_index)
            # Build the empty calendar from the unique exam dates first.
            active_dates = sorted({item.date for item in view.items})
            self.calendar_grid.setup_month_grid(active_dates)
            # Then place the exam tiles into their matching cells.
            self.calendar_grid.display_assignments(view.items)
        except Exception as error:
            QMessageBox.critical(self, "Display Error", f"Failed to paint calendar: {error}")

    def _on_back(self) -> None:
        """Return to the input screen using the router history."""
        self._router.back()

    def _on_export_pdf(self) -> None:
        """
        Save the schedule that is currently on screen as a PDF.

        Every step here lives in the view layer. We read the same view model
        that paints the calendar, ask the user where to save, build an HTML
        table from that view model and let Qt render it to a PDF. No scheduling
        logic or application service is touched.
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

        # Ask the user where to save, suggesting a readable default file name.
        default_name = f"exam_schedule_solution_{self._current_index + 1}.pdf"
        path = prompt_save_file(self, "Save schedule as PDF", default_name, "PDF files (*.pdf)")
        if not path:
            # The user closed the dialog without choosing a file.
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        # Build the HTML and render it to the chosen file.
        try:
            document_html = self._build_schedule_html(view)
            self._write_html_to_pdf(document_html, path)
        except Exception as error:
            QMessageBox.critical(self, "Export error", f"Failed to create the PDF:\n{error}")
            return

        QMessageBox.information(
            self, "Export complete", f"Schedule saved to:\n{os.path.abspath(path)}"
        )

    def _build_schedule_html(self, view) -> str:
        """
        Build a printable HTML table from a schedule view model.

        QTextDocument only understands a small subset of HTML and ignores most
        CSS written through class selectors. To get clean columns we therefore
        use the classic table model it does support: a fixed table width, an
        explicit width on every cell, cellpadding for the spacing between
        columns and inline styles for the colors. Every dynamic value is escaped
        so the markup always stays valid.

        The four columns are Date, Course, Details and Programs. The Programs
        text is taken from the lines of the tooltip that describe the program
        and whether the course is obligatory or elective.
        """
        # Column widths, declared once so the header and the body always agree.
        width_date = "15%"
        width_course = "30%"
        width_details = "31%"
        width_programs = "24%"

        rows_html = []
        for row_index, item in enumerate(sorted(view.items, key=lambda it: it.date)):
            date_text = html.escape(str(item.date))
            course_text = html.escape(str(item.title))
            details_text = html.escape(str(item.subtitle))

            # The tooltip carries one "Program <id>: <Requirement>" line per
            # program the course belongs to. We keep only those lines for the
            # Programs column and drop the name and date lines.
            program_lines = [
                line.strip()
                for line in str(item.tooltip).split("\n")
                if line.strip().lower().startswith("program ")
            ]
            if program_lines:
                programs_text = "<br>".join(html.escape(line) for line in program_lines)
            else:
                programs_text = "<span style='color:#94A3B8;'>\u2014</span>"

            # Alternate the row background so long tables stay easy to read.
            row_background = "#FFFFFF" if row_index % 2 == 0 else "#F4F7F9"

            rows_html.append(
                f"<tr bgcolor='{row_background}'>"
                f"<td width='{width_date}' style='color:#3E352F; font-weight:bold;'>{date_text}</td>"
                f"<td width='{width_course}' style='font-weight:bold;'>{course_text}</td>"
                f"<td width='{width_details}' style='color:#64748B;'>{details_text}</td>"
                f"<td width='{width_programs}' style='color:#334155;'>{programs_text}</td>"
                "</tr>"
            )

        solution_line = html.escape(f"Solution {view.current_index + 1} of {view.total}")
        exam_count = len(view.items)

        # The header row uses the dark green brand color with white text. The
        # body rows follow with the data assembled above.
        return (
            "<html><body>"
            "<h1 style='color:#3E352F; margin:0 0 2pt 0;'>Exam Schedule</h1>"
            f"<p style='color:#64748B; margin:0 0 14pt 0;'>{solution_line} &nbsp;\u00b7&nbsp; {exam_count} exams</p>"
            "<table width='100%' cellspacing='0' cellpadding='7'>"
            "<tr bgcolor='#d4b483'>"
            f"<td width='{width_date}' style='color:#3E352F; font-weight:bold;'>Date</td>"
            f"<td width='{width_course}' style='color:#3E352F; font-weight:bold;'>Course</td>"
            f"<td width='{width_details}' style='color:#3E352F; font-weight:bold;'>Details</td>"
            f"<td width='{width_programs}' style='color:#3E352F; font-weight:bold;'>Programs</td>"
            "</tr>"
            f"{''.join(rows_html)}"
            "</table>"
            "</body></html>"
        )

    def _write_html_to_pdf(self, document_html: str, path: str) -> None:
        """
        Render an HTML string to a PDF file using Qt printing support.

        The print module is imported here, not at the top of the file, so the
        rest of the screen still loads on a Qt build without print support. Any
        problem then only shows up when the user actually clicks Export.

        We print in screen resolution, which is 96 dots per inch. That matches
        the resolution QTextDocument lays the content out at, so there is no
        scale mismatch between the document and the page. Setting a high
        resolution device size by hand is what made earlier output render as an
        unreadable speck. The text is stored as vectors in the PDF, so it stays
        sharp at any zoom level.
        """
        from PyQt6.QtPrintSupport import QPrinter
        from PyQt6.QtGui import QPageSize

        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        try:
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        except Exception:
            # A4 is the default page size, so a binding mismatch is harmless.
            pass

        document = QTextDocument()
        # A comfortable base font size for the whole document. Headings grow
        # from this automatically.
        document.setDefaultFont(QFont("Arial", 11))
        document.setHtml(document_html)

        # PyQt6 names the method "print"; fall back to "print_" for safety.
        print_method = getattr(document, "print", None) or getattr(document, "print_")
        print_method(printer)

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