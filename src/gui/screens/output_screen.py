"""OutputScreen — displays generated schedule results.

Shows one schedule at a time inside a year-calendar widget, with two
navigation bars:
  - Solution bar : move between individual schedules inside the current page
  - Page bar     : move between 10 000-result SQLite pages (only visible when
                   the full result set spans more than one page)

While the background scheduler is still running, the UI listens to
total_count_updated to keep the counters and button states in sync with
the SQLite write progress.
"""
from __future__ import annotations

from src.gui.widgets.calendar_widget import CalendarWidget

from PyQt6.QtWidgets import (
    QLabel, QMessageBox, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

from src.gui.screen import Screen

# Size of one SQLite result page. Must stay in sync with the backend window
# size; changing only one of the two creates off-by-page navigation bugs.
_PAGE_WINDOW = 10_000


def _divider(parent=None) -> QFrame:
    """Return a 1-pixel horizontal separator line."""
    f = QFrame(parent)
    f.setObjectName("divider")
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    return f


class OutputScreen(Screen):
    """Output screen: schedule results with solution + page navigation."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router

        # Index of the schedule currently shown inside the active page (0-based).
        self._current_index: int = 0
        # Number of schedules in the currently-loaded page (window size).
        self._total: int = 0

        # Pagination state — driven by the SQLite-backed repository on the
        # controller side. Page numbers are 0-based internally and displayed
        # as 1-based to the user. sqlite_count reflects how many schedules
        # have been written to disk so far across all pages.
        self._current_page: int = 0
        self._total_pages: int = 0
        self._total_found: int = 0
        self._sqlite_count: int = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        # Same visual style as the input screen for a consistent chrome.
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(72)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 0, 28, 0)

        title = QLabel("EXAM SCHEDULER")
        title.setObjectName("app-title")
        subtitle = QLabel("Generated schedules")
        subtitle.setObjectName("app-subtitle")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        h_layout.addLayout(title_col)
        h_layout.addStretch()
        root.addWidget(header)

        # ── Solution navigation bar ───────────────────────────────────
        # Back button on the left, Prev / counter / Next on the right.
        # Moves between schedules WITHIN the currently-loaded SQLite page.
        nav_bar = QFrame()
        nav_bar.setObjectName("nav-bar")
        nav_bar.setFixedHeight(52)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(8)

        # Back button — uses the router's history stack to return to the input screen.
        # Alt+Left makes it reachable from the keyboard without taking focus.
        self._back_btn = QPushButton("← Back")
        self._back_btn.setObjectName("btn-ghost")
        self._back_btn.setShortcut(QKeySequence("Alt+Left"))
        self._back_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._back_btn.setToolTip("Back to input screen (Alt+Left)")
        self._back_btn.setFixedHeight(36)
        self._back_btn.clicked.connect(self._on_back)
        nav_layout.addWidget(self._back_btn)

        nav_layout.addStretch()

        # Previous solution within the current page. Strictly bounded
        # at index 0 so it can never wrap to a negative index.
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setObjectName("btn-secondary")
        self._prev_btn.setToolTip("Previous solution")
        self._prev_btn.setFixedSize(36, 36)
        self._prev_btn.clicked.connect(self.on_prev)

        # Displays "Solution N / Total" or "No solutions" when empty.
        self._counter_label = QLabel()
        self._counter_label.setObjectName("counter-label")
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Next solution within the current page. Disabled at the last index.
        self._next_btn = QPushButton("▶")
        self._next_btn.setObjectName("btn-secondary")
        self._next_btn.setToolTip("Next solution")
        self._next_btn.setFixedSize(36, 36)
        self._next_btn.clicked.connect(self.on_next)

        nav_layout.addWidget(self._prev_btn)
        nav_layout.addWidget(self._counter_label)
        nav_layout.addWidget(self._next_btn)

        root.addWidget(nav_bar)
        root.addWidget(_divider())

        # ── Page navigation bar ───────────────────────────────────────
        # Hidden when results fit into a single page. Becomes visible
        # only when the SQLite-backed repository reports total_pages > 1.
        self._page_bar = QFrame()
        self._page_bar.setObjectName("nav-bar")
        self._page_bar.setFixedHeight(44)
        page_layout = QHBoxLayout(self._page_bar)
        page_layout.setContentsMargins(20, 0, 20, 0)
        page_layout.setSpacing(8)

        self._prev_page_btn = QPushButton("← Prev 10K")
        self._prev_page_btn.setObjectName("btn-ghost")
        self._prev_page_btn.setFixedHeight(30)
        self._prev_page_btn.clicked.connect(self._on_prev_page)
        page_layout.addWidget(self._prev_page_btn)

        page_layout.addStretch()

        # "Page X / Y · NNN total"
        self._page_label = QLabel()
        self._page_label.setObjectName("counter-label")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_layout.addWidget(self._page_label)

        page_layout.addStretch()

        self._next_page_btn = QPushButton("Next 10K →")
        self._next_page_btn.setObjectName("btn-ghost")
        self._next_page_btn.setFixedHeight(30)
        self._next_page_btn.clicked.connect(self._on_next_page)
        page_layout.addWidget(self._next_page_btn)

        # Initially hidden — _refresh_page_bar shows it when total_pages > 1.
        self._page_bar.setVisible(False)
        root.addWidget(self._page_bar)
        root.addWidget(_divider())

        # ── Content area ──────────────────────────────────────────────
        # Card-style container holding a scroll area with the calendar widget.
        body = QVBoxLayout()
        body.setContentsMargins(28, 20, 28, 20)
        body.setSpacing(0)

        content_card = QFrame()
        content_card.setObjectName("content-area")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area lets the year-long calendar overflow gracefully.
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        content_inner = QVBoxLayout(self._content_widget)
        content_inner.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Year-calendar widget — rebuilt for each shown solution.
        self.calendar_grid = CalendarWidget()
        content_inner.addWidget(self.calendar_grid)

        self._scroll.setWidget(self._content_widget)
        content_layout.addWidget(self._scroll)

        body.addWidget(content_card)
        root.addLayout(body)

        self._refresh_counter()

        # Live updates: every time the worker writes a batch of schedules to
        # SQLite, the controller emits total_count_updated. We use it to keep
        # the page counter and Next-Page button state current without forcing
        # the user to reload the screen manually.
        self._controller.total_count_updated.connect(self._on_total_count_updated)

    # ── Display helpers ────────────────────────────────────────────────

    def _refresh_counter(self) -> None:
        """Update the solution counter and refresh the page bar to match."""
        if self._total == 0:
            self._counter_label.setText("No solutions")
        else:
            self._counter_label.setText(
                f"Solution  {self._current_index + 1} / {self._total}"
            )
        # Strict bounds: never < 0, never beyond the last index in the window.
        self._prev_btn.setEnabled(self._current_index > 0)
        self._next_btn.setEnabled(self._current_index < self._total - 1)
        self._refresh_page_bar()

    def _refresh_page_bar(self) -> None:
        """Show or hide the page bar and update its label and button states.

        The Next-Page button is only enabled once the target page has a FULL
        10 000 schedules persisted to SQLite. Reading from a partially-written
        page produces a freeze (the SQLite read waits for the pending write
        to finish) and an IndexError when the window is still empty. Keeping
        the button disabled while the page fills avoids both crashes; it
        re-enables itself automatically when total_count_updated fires
        again with a higher sqlite_count.
        """
        has_pages = self._total_pages > 1
        self._page_bar.setVisible(has_pages)
        if not has_pages:
            return

        total_str = f"{self._total_found:,}"
        self._page_label.setText(
            f"Page {self._current_page + 1} / {self._total_pages}"
            f"  ·  {total_str} total"
        )
        self._prev_page_btn.setEnabled(self._current_page > 0)

        # Is the next page already fully on disk?
        next_page_idx = self._current_page + 1                  # 0-based
        sqlite_needed = next_page_idx * _PAGE_WINDOW            # rows required
        next_ready    = self._sqlite_count >= sqlite_needed
        self._next_page_btn.setEnabled(
            self._current_page < self._total_pages - 1 and next_ready
        )

    def _on_total_count_updated(self, total: int) -> None:
        """Refresh counters after each background batch write.

        We re-query the controller for the authoritative page-info dict so
        local state mirrors the repository exactly, even if multiple batches
        landed between two UI repaints. While the user is on page 0, the
        active window keeps growing as more results arrive, so we update
        the solution counter as well; on later pages only the page bar
        changes.
        """
        info               = self._controller.get_page_info()
        self._total_found  = info["total_count"]
        self._total_pages  = info["total_pages"]
        self._sqlite_count = info.get("sqlite_count", 0)

        if self._current_page == 0:
            self._total = info["window_size"]
            self._refresh_counter()
        else:
            self._refresh_page_bar()

    def _on_next_page(self) -> None:
        """Ask the controller to load the next 10 K-result page, then redraw."""
        target = self._current_page + 1
        if target >= self._total_pages:
            # Safety guard: discard queued clicks that arrived after the state
            # changed (e.g. a fast double-click on the last enabled page).
            return
        self._controller.load_page(target)
        self._sync_page_info()
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def _on_prev_page(self) -> None:
        """Ask the controller to load the previous 10 K-result page, then redraw."""
        target = self._current_page - 1
        if target < 0:
            return
        self._controller.load_page(target)
        self._sync_page_info()
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def _show_current(self) -> None:
        """Render the schedule at _current_index inside the calendar widget."""
        if self._total == 0:
            return
        try:
            vm = self._controller.get_schedule_view(self._current_index)
            # Build the calendar skeleton from the unique exam dates in this schedule.
            active_dates = sorted(list({item.date for item in vm.items}))
            self.calendar_grid.setup_month_grid(active_dates)
            # Then drop the exam tiles into their cells.
            self.calendar_grid.display_assignments(vm.items)
        except Exception as e:
            QMessageBox.critical(self, "Display Error", f"Failed to paint calendar: {str(e)}")

    def _on_back(self) -> None:
        """Return to the input screen via the router's history stack."""
        self._router.back()

    # ── Page navigation helpers ────────────────────────────────────────

    def _sync_page_info(self) -> None:
        """Pull current paging state from the controller into local variables."""
        info = self._controller.get_page_info()
        self._current_page  = info["current_page"]
        self._total_pages   = info["total_pages"]
        self._total         = info["window_size"]
        self._total_found   = info["total_count"]
        self._sqlite_count  = info.get("sqlite_count", 0)

    # ── Solution navigation ────────────────────────────────────────────

    def on_next(self) -> None:
        """Move forward one schedule inside the current page."""
        if self._current_index < self._total - 1:
            self._current_index += 1
            self._show_current()
            self._refresh_counter()

    def on_prev(self) -> None:
        """Move backward one schedule inside the current page."""
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current()
            self._refresh_counter()

    # ── Screen lifecycle ───────────────────────────────────────────────

    def on_enter(self) -> None:
        """Initialise the screen each time it becomes active.

        Resets the in-page index to 0, refreshes paging state from the
        controller, repaints the calendar, and focuses the Back button
        so Alt+Left works immediately.
        """
        self._current_index = 0
        self._sync_page_info()
        self._show_current()
        self._refresh_counter()
        self._back_btn.setFocus()

    def on_leave(self) -> None:
        """Called by the router when navigating away from this screen."""
        pass