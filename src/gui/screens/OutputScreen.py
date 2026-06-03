"""OutputScreen — displays generated schedule results.

SCRUM-147 : on_enter loads results from controller
SCRUM-93  : year-calendar widget replaces content area (Yuval)
SCRUM-96  : export button (Yuval)
"""
from __future__ import annotations

# Import your custom calendar view component safely
from gui.widgets.CalendarWidget import CalendarWidget

from PyQt6.QtWidgets import (
    QLabel, QMessageBox, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

from gui.Screen import Screen


def _divider(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("divider")
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    return f


class OutputScreen(Screen):
    """Output screen: schedule results with navigation."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router

        self._current_index: int = 0
        self._total: int = 0
        self._current_page: int = 0
        self._total_pages: int = 0
        self._total_found: int = 0
        self._sqlite_count: int = 0   # items written to SQLite so far

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
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

        # ── Navigation bar ────────────────────────────────────────────
        nav_bar = QFrame()
        nav_bar.setObjectName("nav-bar")
        nav_bar.setFixedHeight(52)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(8)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setObjectName("btn-ghost")
        self._back_btn.setShortcut(QKeySequence("Alt+Left"))
        self._back_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._back_btn.setToolTip("Back to input screen (Alt+Left)")
        self._back_btn.setFixedHeight(36)
        self._back_btn.clicked.connect(self._on_back)
        nav_layout.addWidget(self._back_btn)

        nav_layout.addStretch()

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setObjectName("btn-secondary")
        self._prev_btn.setToolTip("Previous solution")
        self._prev_btn.setFixedSize(36, 36)
        self._prev_btn.clicked.connect(self.on_prev)

        self._counter_label = QLabel()
        self._counter_label.setObjectName("counter-label")
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        self._page_bar.setVisible(False)   # hidden until there are multiple pages
        root.addWidget(self._page_bar)
        root.addWidget(_divider())

        # ── Content area ──────────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(28, 20, 28, 20)
        body.setSpacing(0)

        content_card = QFrame()
        content_card.setObjectName("content-area")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area — the calendar widget (SCRUM-93) will live here
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        content_inner = QVBoxLayout(self._content_widget)
        content_inner.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.calendar_grid = CalendarWidget()
        content_inner.addWidget(self.calendar_grid)

        self._scroll.setWidget(self._content_widget)
        content_layout.addWidget(self._scroll)

        body.addWidget(content_card)
        root.addLayout(body)

        self._refresh_counter()
        # Live update: while the search continues in the background, keep the
        # page-bar counter current so the user knows more results are arriving.
        self._controller.total_count_updated.connect(self._on_total_count_updated)

    # ── Display helpers ────────────────────────────────────────────────

    def _refresh_counter(self) -> None:
        """Update the solution counter and page bar to reflect current state."""
        if self._total == 0:
            self._counter_label.setText("No solutions")
        else:
            self._counter_label.setText(
                f"Solution  {self._current_index + 1} / {self._total}"
            )
        self._prev_btn.setEnabled(self._current_index > 0)
        self._next_btn.setEnabled(self._current_index < self._total - 1)
        self._refresh_page_bar()

    def _refresh_page_bar(self) -> None:
        """Show/hide page bar and update its label + button states."""
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

        # "Next Page →" is only enabled when the target page has a FULL 10 K of
        # data written to SQLite.  Navigating into a partially-written page causes
        # a freeze (SQLite read while writes are pending) and a crash (empty page
        # → IndexError in get_schedule).  The button grays out while that page
        # fills up and re-enables automatically once it is ready.
        _WINDOW       = 10_000
        next_page_idx = self._current_page + 1          # 0-based
        sqlite_needed = next_page_idx * _WINDOW         # items SQLite must hold
        next_ready    = self._sqlite_count >= sqlite_needed
        self._next_page_btn.setEnabled(
            self._current_page < self._total_pages - 1 and next_ready
        )

    def _on_total_count_updated(self, total: int) -> None:
        """Fired each batch while the search is running — keep UI in sync."""
        info               = self._controller.get_page_info()
        self._total_found  = info["total_count"]
        self._total_pages  = info["total_pages"]
        self._sqlite_count = info.get("sqlite_count", 0)
        # On page 0 the memory window grows live — keep the solution counter current.
        if self._current_page == 0:
            self._total = info["window_size"]
            self._refresh_counter()
        else:
            self._refresh_page_bar()

    def _on_next_page(self) -> None:
        target = self._current_page + 1
        if target >= self._total_pages:
            return   # safety: discard queued clicks that arrived after state changed
        self._controller.load_page(target)
        self._sync_page_info()
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def _on_prev_page(self) -> None:
        target = self._current_page - 1
        if target < 0:
            return   # safety guard
        self._controller.load_page(target)
        self._sync_page_info()
        self._current_index = 0
        self._show_current()
        self._refresh_counter()

    def _show_current(self) -> None:
        """Render solution at _current_index via the CalendarWidget."""
        if self._total == 0:
            return
        try:
            vm = self._controller.get_schedule_view(self._current_index)
            active_dates = sorted(list({item.date for item in vm.items}))
            self.calendar_grid.setup_month_grid(active_dates)
            self.calendar_grid.display_assignments(vm.items)
        except Exception as e:
            QMessageBox.critical(self, "Display Error", f"Failed to paint calendar: {str(e)})")

    def _on_back(self) -> None:
        self._router.back()

    # ── Page navigation ────────────────────────────────────────────────

    def _sync_page_info(self) -> None:
        """Pull current paging state from the controller."""
        info = self._controller.get_page_info()
        self._current_page  = info["current_page"]
        self._total_pages   = info["total_pages"]
        self._total         = info["window_size"]
        self._total_found   = info["total_count"]
        self._sqlite_count  = info.get("sqlite_count", 0)

    # ── Navigation ─────────────────────────────────────────────────────

    def on_next(self) -> None:
        if self._current_index < self._total - 1:
            self._current_index += 1
            self._show_current()
            self._refresh_counter()

    def on_prev(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current()
            self._refresh_counter()

    # ── Lifecycle (SCRUM-147) ──────────────────────────────────────────

    def on_enter(self) -> None:
        self._current_index = 0
        self._sync_page_info()
        self._show_current()
        self._refresh_counter()
        self._back_btn.setFocus()

    def on_leave(self) -> None:
        pass