"""Output screen layout and widget wiring."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMessageBox, QFrame, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from gui.common.components.HeaderWidget import HeaderWidget
from gui.common.components.OutputCalendarWidget import OutputCalendarWidget
from gui.common.helpers import create_divider
from gui.core.screen import Screen
from gui.features.output.OutputScreenPresenter import OutputScreenPresenter
from gui.features.output.widgets.SchedulePdfExporter import export_schedule_pdf
from gui.features.output.widgets.SolutionBarWidget import SolutionBarWidget


class OutputScreen(Screen):
    """Displays generated schedules with solution and page navigation."""

    def __init__(self, controller, router) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_header(root)
        self._build_solution_bar(root)
        self._build_calendar_area(root)

        self._presenter = OutputScreenPresenter(self, controller, router)
        self._connect_events()
        self._presenter.refresh_counter()

    # Build the header widget
    def _build_header(self, root: QVBoxLayout) -> None:
        root.addWidget(HeaderWidget(parent=self))

    # Build the solution navigation toolbar
    def _build_solution_bar(self, root: QVBoxLayout) -> None:
        self.solution_bar = SolutionBarWidget(self)
        root.addWidget(self.solution_bar)
        root.addWidget(create_divider())

    # Build the calendar grid area
    def _build_calendar_area(self, root: QVBoxLayout) -> None:
        body = QVBoxLayout()
        body.setContentsMargins(28, 20, 28, 20)
        body.setSpacing(0)

        content_card = QFrame()
        content_card.setObjectName("content-area")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        month_nav_frame = QFrame()
        month_nav_frame.setObjectName("month-nav-bar")
        month_nav_layout = QHBoxLayout(month_nav_frame)
        month_nav_layout.setContentsMargins(20, 10, 20, 10)

        self.prev_month_btn = QPushButton("< Prev Period")
        self.prev_month_btn.setFixedWidth(130)

        self.month_label = QLabel("")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.next_month_btn = QPushButton("Next Period >")
        self.next_month_btn.setFixedWidth(130)

        month_nav_layout.addWidget(self.prev_month_btn)
        month_nav_layout.addWidget(self.month_label, stretch=1)
        month_nav_layout.addWidget(self.next_month_btn)
        content_layout.addWidget(month_nav_frame)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._content_widget = QWidget()
        self._content_widget.setObjectName("calendar-scroll-content")
        content_inner = QVBoxLayout(self._content_widget)
        content_inner.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.calendar_grid = OutputCalendarWidget()
        content_inner.addWidget(self.calendar_grid)

        self._scroll.setWidget(self._content_widget)
        content_layout.addWidget(self._scroll)

        body.addWidget(content_card)
        root.addLayout(body)

    # Connect UI signals to the presenter logic
    def _connect_events(self) -> None:
        self.solution_bar.back_btn.clicked.connect(self._presenter.on_back)
        self.solution_bar.export_btn.clicked.connect(self._presenter.on_export_pdf)
        self.solution_bar.prev_btn.clicked.connect(self._presenter.on_prev_solution)
        self.solution_bar.next_btn.clicked.connect(self._presenter.on_next_solution)
        self.solution_bar.solution_input.returnPressed.connect(self._presenter.on_jump_to_solution)
        self.solution_bar.first_page_btn.clicked.connect(self._presenter.on_first_page)
        self.solution_bar.prev_page_btn.clicked.connect(self._presenter.on_prev_page)
        self.solution_bar.next_page_btn.clicked.connect(self._presenter.on_next_page)
        self.solution_bar.last_page_btn.clicked.connect(self._presenter.on_last_page)
        self.prev_month_btn.clicked.connect(self._presenter.on_prev_period)
        self.next_month_btn.clicked.connect(self._presenter.on_next_period)

    # Refresh the text inside the solution counter
    def set_solution_counter(self, text: str) -> None:
        if "Solution" in text and "/" in text:
            parts = text.split("/")
            solution_num = parts[0].replace("Solution", "").strip()
            if not self.solution_bar.solution_input.hasFocus():
                self.solution_bar.solution_input.setText(solution_num)
        else:
            if not self.solution_bar.solution_input.hasFocus():
                self.solution_bar.solution_input.clear()

    # Update enabled/disabled state of solution navigation buttons
    def set_solution_controls(self, can_prev: bool, can_next: bool, can_export: bool) -> None:
        self.solution_bar.prev_btn.setEnabled(can_prev)
        self.solution_bar.next_btn.setEnabled(can_next)
        self.solution_bar.export_btn.setEnabled(can_export)

    # Show or hide the page navigation bar
    def set_page_bar_visible(self, visible: bool) -> None:
        self.solution_bar.pages_group.setVisible(visible)

    # Configure the state of the page navigation bar
    def set_page_bar(
        self,
        visible: bool,
        label: str,
        can_first: bool,
        can_previous: bool,
        can_next: bool,
        can_last: bool,
    ) -> None:
        self.solution_bar.pages_group.setVisible(visible)
        self.solution_bar.page_label.setText(label)
        self.solution_bar.first_page_btn.setEnabled(can_first)
        self.solution_bar.prev_page_btn.setEnabled(can_previous)
        self.solution_bar.next_page_btn.setEnabled(can_next)
        self.solution_bar.last_page_btn.setEnabled(can_last)

    # Configure period navigation labels and button availability
    def set_period_navigation(self, label: str, can_previous: bool, can_next: bool) -> None:
        self.month_label.setText(label)
        self.prev_month_btn.setEnabled(can_previous)
        self.next_month_btn.setEnabled(can_next)

    # Draw the calendar grid with dates, exclusion styles, and exam assignments
    def render_calendar(self, date_list: list[str], excluded_dates: list[str], assignments: list) -> None:
        self.calendar_grid.setup_month_grid(
            date_list,
            show_month_header=True,
            show_month_banner=False,
        )
        for excluded_date in excluded_dates:
            self.calendar_grid.set_date_excluded_output_style(excluded_date)
        self.calendar_grid.display_assignments(assignments)

    # UI utility to toggle screen updates
    def set_screen_updates(self, enabled: bool) -> None:
        self.setUpdatesEnabled(enabled)

    # Error message dialogs
    def show_display_error(self, message: str) -> None:
        QMessageBox.critical(self, "Display Error", message)

    def show_nothing_to_export(self, message: str) -> None:
        QMessageBox.information(self, "Nothing to export", message)

    def show_export_error(self, message: str) -> None:
        QMessageBox.critical(self, "Export error", message)

    # Export functionality
    def export_schedule_pdf(self, schedule_view, current_index: int) -> None:
        export_schedule_pdf(schedule_view, current_index, parent=self)

    # Helpers for UI focus and input
    def focus_back_button(self) -> None:
        self.solution_bar.back_btn.setFocus()

    def get_jump_to_value(self) -> str:
        return self.solution_bar.solution_input.text()

    def clear_jump_to_input(self) -> None:
        self.solution_bar.solution_input.clear()

    # Presenter helper methods
    def _refresh_counter(self) -> None:
        self._presenter.refresh_counter()

    def _refresh_page_bar(self) -> None:
        self._presenter.refresh_page_bar()

    def _on_total_count_updated(self, total: int) -> None:
        self._presenter.on_total_count_updated(total)

    def _on_next_page(self) -> None:
        self._presenter.on_next_page()

    def _on_prev_page(self) -> None:
        self._presenter.on_prev_page()

    def _on_first_page(self) -> None:
        self._presenter.on_first_page()

    def _on_last_page(self) -> None:
        self._presenter.on_last_page()

    def _show_current(self) -> None:
        self._presenter.show_current()

    def _on_back(self) -> None:
        self._presenter.on_back()

    def _on_export_pdf(self) -> None:
        self._presenter.on_export_pdf()

    def _on_prev_month(self) -> None:
        self._presenter.on_prev_period()

    def _on_next_month(self) -> None:
        self._presenter.on_next_period()

    def on_next(self) -> None:
        self._presenter.on_next_solution()

    def on_prev(self) -> None:
        self._presenter.on_prev_solution()

    def on_enter(self) -> None:
        self._presenter.on_enter()

    def on_leave(self) -> None:
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