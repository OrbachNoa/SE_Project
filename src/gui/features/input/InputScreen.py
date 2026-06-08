"""Input screen layout and widget wiring."""
from __future__ import annotations

from typing import Callable, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMessageBox, QFrame, QHBoxLayout, QProgressBar, QVBoxLayout

from gui.common.components.CalendarEditorWidget import CalendarEditorWidget
from gui.common.components.CourseListWidget import CourseListWidget
from gui.common.components.HeaderWidget import HeaderWidget
from gui.common.helpers import create_card, create_divider, create_scaled_pixmap, prompt_open_file
from gui.core.screen import Screen
from gui.features.input.InputScreenPresenter import InputScreenPresenter
from gui.features.input.widgets.ActionBarWidget import ActionBarWidget
from gui.features.input.widgets.ProgramSelectorCardWidget import ProgramSelectorCardWidget
from src.application.ImportBoundary import ImportMode


SCREEN_OUTPUT = "output"
MAX_PROGRAMS = 5


class InputScreen(Screen):
    """Input screen shell for loading files and starting schedule generation."""

    def __init__(self, controller, router) -> None:
        super().__init__()

        self._editor_widget: CalendarEditorWidget | None = None
        self.program_selector_card = ProgramSelectorCardWidget(MAX_PROGRAMS, self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(HeaderWidget(parent=self))

        self.action_bar = ActionBarWidget(self)
        self._view_results_btn = self.action_bar.view_results_btn
        root.addWidget(self.action_bar)

        self._courses_status_badge = QLabel("Not loaded")
        self._courses_status_badge.setVisible(False)
        self._periods_status_badge = QLabel("Not loaded")
        self._periods_status_badge.setVisible(False)
        self._courses_row = {
            "count_lbl": self._courses_status_badge,
            "load_btn": self.action_bar.courses_load_btn,
        }
        self._periods_row = {
            "count_lbl": self._periods_status_badge,
            "load_btn": self.action_bar.periods_load_btn,
        }

        self.program_error_label = QLabel("")
        self.program_error_label.setObjectName("status-error")
        self.program_error_label.setWordWrap(True)
        self.program_error_label.setVisible(False)

        body = QVBoxLayout()
        body.setContentsMargins(20, 20, 20, 20)
        body.setSpacing(16)

        two_col_layout = QHBoxLayout()
        two_col_layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        prog_group_layout = QVBoxLayout()
        prog_group_layout.setSpacing(6)
        prog_group_layout.addWidget(self.program_error_label)
        prog_group_layout.addWidget(self.program_selector_card)
        left_col.addLayout(prog_group_layout)
        left_col.addWidget(self._build_courses_card(), stretch=1)

        self.right_col = QVBoxLayout()
        self._placeholder = self._build_calendar_placeholder()
        self.right_col.addWidget(self._placeholder, stretch=1)

        two_col_layout.addLayout(left_col, stretch=1)
        two_col_layout.addLayout(self.right_col, stretch=1)
        body.addLayout(two_col_layout)
        root.addLayout(body)

        self._validation_label = QLabel("")
        self._validation_label.setObjectName("status-warning")
        self._validation_label.setWordWrap(True)
        self._validation_label.setContentsMargins(24, 4, 24, 0)
        root.addWidget(self._validation_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(False)
        root.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("status-ok")
        self._progress_label.setVisible(False)
        self._progress_label.setContentsMargins(24, 0, 24, 8)
        root.addWidget(self._progress_label)

        self._presenter = InputScreenPresenter(self, controller, router, SCREEN_OUTPUT)
        self._connect_events()
        self._presenter.refresh_generate_button()

    def _connect_events(self) -> None:
        self.program_selector_card.selection_changed.connect(self._presenter.refresh_generate_button)
        self.action_bar.courses_load_btn.clicked.connect(self._presenter.on_load_courses_clicked)
        self.action_bar.periods_load_btn.clicked.connect(self._presenter.on_load_periods_clicked)
        self.action_bar.generate_btn.clicked.connect(self._presenter.on_generate_clicked)
        self.action_bar.cancel_btn.clicked.connect(self._presenter.on_cancel_clicked)
        self.action_bar.view_results_btn.clicked.connect(self._presenter.on_view_results_clicked)

    def _build_courses_card(self) -> QFrame:
        card = create_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setObjectName("card-icon")
        try:
            icon_lbl.setPixmap(create_scaled_pixmap(self, "data/assets/courseIcon.png", 18))
        except Exception:
            icon_lbl.setText("Courses")

        courses_title = QLabel("Courses")
        courses_title.setObjectName("card-title")
        header_row.addWidget(icon_lbl)
        header_row.addWidget(courses_title)
        header_row.addStretch()

        self._courses_visible_badge = QLabel("Not loaded")
        self._courses_visible_badge.setObjectName("badge")
        header_row.addWidget(self._courses_visible_badge)
        layout.addLayout(header_row)
        layout.addWidget(create_divider())

        self._course_list_widget = CourseListWidget()
        layout.addWidget(self._course_list_widget, stretch=1)
        return card

    def _build_calendar_placeholder(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("calendar-placeholder")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        layout.addStretch()

        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            icon.setPixmap(create_scaled_pixmap(self, "data/assets/periodIcon.png", 36))
            icon.setObjectName("calendar-placeholder-icon")
        except Exception:
            icon.setText("Calendar")
            icon.setObjectName("calendar-placeholder-icon")

        title = QLabel("Calendar editor")
        title.setObjectName("calendar-placeholder-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Load periods to edit exam date constraints")
        sub.setObjectName("calendar-placeholder-subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addStretch()
        return frame

    def is_replace_mode_selected(self) -> bool:
        return self.action_bar.mode_replace.isChecked()

    def selected_program_ids(self) -> List[str]:
        return self.program_selector_card.selected_program_ids()

    def prompt_for_file(self, title: str, file_filter: str) -> str:
        return prompt_open_file(self, title, file_filter)

    def set_generate_button_state(self, enabled: bool, tooltip: str) -> None:
        self.action_bar.generate_btn.setEnabled(enabled)
        self.action_bar.generate_btn.setToolTip(tooltip)

    def set_validation_message(self, message: str) -> None:
        self._validation_label.setText(message)

    def set_program_error(self, message: str) -> None:
        self.program_error_label.setText(message)
        self.program_error_label.setVisible(bool(message))

    def set_running_mode(self, running: bool, progress_text: str) -> None:
        self.action_bar.generate_btn.setVisible(not running)
        self.action_bar.cancel_btn.setVisible(running)
        self._progress_bar.setVisible(running)
        self._progress_label.setVisible(running)
        self._courses_row["load_btn"].setEnabled(not running)
        self._periods_row["load_btn"].setEnabled(not running)
        if progress_text:
            self._progress_label.setText(progress_text)

    def set_progress_text(self, text: str) -> None:
        self._progress_label.setText(text)

    def set_view_results_visible(self, visible: bool) -> None:
        self._view_results_btn.setVisible(visible)

    def mark_courses_loaded(self, count: int) -> None:
        self._mark_file_loaded(self._courses_row, count, "courses")
        self._courses_visible_badge.setText(f"{count} courses")
        self._courses_visible_badge.setObjectName("badge-ok")
        self._refresh_widget_style(self._courses_visible_badge)

    def mark_periods_loaded(self, count: int) -> None:
        self._mark_file_loaded(self._periods_row, count, "periods")

    def render_courses(self, programs_vm) -> None:
        self._course_list_widget.render(programs_vm)

    def show_period_editor(self, period_vms: list, save_callback: Callable[[list], None]) -> None:
        if self._placeholder is not None:
            self.right_col.removeWidget(self._placeholder)
            self._placeholder.deleteLater()
            self._placeholder = None

        if self._editor_widget is not None:
            try:
                self._editor_widget.constraints_saved.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.right_col.removeWidget(self._editor_widget)
            self._editor_widget.deleteLater()

        self._editor_widget = CalendarEditorWidget(period_vms)
        self._editor_widget.constraints_saved.connect(save_callback)
        self.right_col.insertWidget(0, self._editor_widget, stretch=1)

    def show_import_error(self, data_label: str, detail: str) -> None:
        QMessageBox.critical(self, "Import error", f"Failed to load {data_label}:\n{detail}")

    def show_scheduler_error(self, message: str) -> None:
        QMessageBox.critical(self, "Scheduler error", message)

    def _mark_file_loaded(self, row: dict, count: int, label: str) -> None:
        row["count_lbl"].setText(f"{count} {label}")

    def _refresh_widget_style(self, widget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    @property
    def _courses_load_btn(self):
        return self.action_bar.courses_load_btn

    @property
    def _periods_load_btn(self):
        return self.action_bar.periods_load_btn

    @property
    def _mode_replace(self):
        return self.action_bar.mode_replace

    @property
    def _mode_update(self):
        return self.action_bar.mode_update

    @property
    def _selected_program_ids(self) -> List[str]:
        return self.program_selector_card.selected_program_ids()

    @_selected_program_ids.setter
    def _selected_program_ids(self, val: List[str]) -> None:
        self.program_selector_card._selected_program_ids = val

    @property
    def _programs_count_badge(self):
        return self.program_selector_card._programs_count_badge

    def _refresh_program_summary(self) -> None:
        self.program_selector_card._refresh_program_summary()

    def _selected_mode(self) -> ImportMode:
        return self._presenter.selected_mode()

    def _refresh_generate_button(self) -> None:
        self._presenter.refresh_generate_button()

    def _on_load_courses_clicked(self) -> None:
        self._presenter.on_load_courses_clicked()

    def _on_load_periods_clicked(self) -> None:
        self._presenter.on_load_periods_clicked()

    def _on_generate_clicked(self) -> None:
        self._presenter.on_generate_clicked()

    def _on_cancel_clicked(self) -> None:
        self._presenter.on_cancel_clicked()

    def _on_view_results_clicked(self) -> None:
        self._presenter.on_view_results_clicked()

    def _on_constraints_saved(self, updated_vms: list) -> None:
        self._presenter.on_constraints_saved(updated_vms)

    def on_load_courses(self, mode: ImportMode) -> None:
        self._presenter.on_load_courses(mode)

    def on_load_periods(self, mode: ImportMode) -> None:
        self._presenter.on_load_periods(mode)

    def _validate_programs(self) -> bool:
        return self._presenter.validate_programs()

    def on_enter(self) -> None:
        self._presenter.on_enter()

    def on_leave(self) -> None:
        pass
