"""InputScreen — file loading + schedule generation trigger.

Layout overview:
  - Header      : green branding bar with breadcrumb (Input › Output)
  - Action bar  : Load Courses / Load Periods, import mode, Generate / Cancel / View Results
  - Body        : two columns
        left    -> program selector line (opens a popup) + loaded course list
        right   -> reserved placeholder for a future calendar date editor
  - Footer      : validation message + progress bar
"""
from __future__ import annotations

from typing import List
from gui.features.input.widgets.ProgramSelectorCardWidget import ProgramSelectorCardWidget
from gui.common.components.CourseListWidget import CourseListWidget
from gui.common.components.CalendarEditorWidget import CalendarEditorWidget

from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QRadioButton, QButtonGroup, QFrame,
    QMessageBox, QProgressBar, QWidget,
)
from PyQt6.QtCore import Qt

from gui.common.components.HeaderWidget import HeaderWidget
from gui.common.helpers import create_divider, create_card, prompt_open_file, create_scaled_pixmap
from gui.features.input.widgets.ActionBarWidget import ActionBarWidget

from gui.core.screen import Screen
from src.application.ImportBoundary import ImportMode

# Name used by the router to identify the output screen.
SCREEN_OUTPUT = "output"

# Maximum number of programs the user may select (mirrors the widget limit).
MAX_PROGRAMS = 5

# Shared helpers create_card and create_divider are imported from gui.widgets.Common
class InputScreen(Screen):
    """Input screen: file loading + schedule generation trigger."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router

        self._courses_loaded = False
        self._periods_loaded = False
        self._last_count = 0

        # Guards against navigating to the output screen twice
        self._already_navigated = False

        # Reference to the active calendar editor
        self._editor_widget = None

        # Reusable program selector card widget
        self.program_selector_card = ProgramSelectorCardWidget(MAX_PROGRAMS, self)
        self.program_selector_card.selection_changed.connect(self._refresh_generate_button)

        # Committed program selection. The popup works on a copy and only
        # writes back here when the user presses "Select", so closing the
        # popup without confirming never loses the previous choice.
        #self._selected_program_ids: List[str] = []

        # Built once from the static programs dictionary and reused every time
        # the popup opens, so we never rebuild view models on each click.
        # self._program_view_models = [
        #     ProgramViewModel(program_id=p_id, display_name=p_name, course_count=0)
        #     for p_id, p_name in programs_data.items()
        # ]

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        header = HeaderWidget(parent=self)
        root.addWidget(header)

        # ── Action bar ─────────────────────────────────────────────────────
        self.action_bar = ActionBarWidget(self)
        self.action_bar.courses_load_btn.clicked.connect(self._on_load_courses_clicked)
        self.action_bar.periods_load_btn.clicked.connect(self._on_load_periods_clicked)
        self.action_bar.generate_btn.clicked.connect(self._on_generate_clicked)
        self.action_bar.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._view_results_btn = self.action_bar.view_results_btn
        self._view_results_btn.clicked.connect(self._on_view_results_clicked)
        root.addWidget(self.action_bar)

        # Hidden status badges
        self._courses_status_badge = QLabel("Not loaded")
        self._courses_status_badge.setVisible(False)
        _periods_count_lbl = QLabel("Not loaded")
        _periods_count_lbl.setVisible(False)

        self._courses_row = {
            "count_lbl": self._courses_status_badge,
            "load_btn": self.action_bar.courses_load_btn,
        }
        self._periods_row = {
            "count_lbl": _periods_count_lbl,
            "load_btn": self.action_bar.periods_load_btn,
        }

        # Error label for program selection validation
        self.program_error_label = QLabel("")
        self.program_error_label.setObjectName("status-error")
        self.program_error_label.setWordWrap(True)
        self.program_error_label.setVisible(False)

        # Body: two-column layout.
        body = QVBoxLayout()
        body.setContentsMargins(20, 20, 20, 20)
        body.setSpacing(16)

        two_col_layout = QHBoxLayout()
        two_col_layout.setSpacing(16)

        # Left column: program selector line + loaded course list.
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # Sub-layout with tighter spacing (6px) to keep the error message close to the selector card.
        prog_group_layout = QVBoxLayout()
        prog_group_layout.setSpacing(6)
        prog_group_layout.addWidget(self.program_error_label)
        prog_group_layout.addWidget(self.program_selector_card)

        left_col.addLayout(prog_group_layout)
        left_col.addWidget(self._build_courses_card(), stretch=1)

        # Right column: reserved calendar editor placeholder.
        self.right_col = QVBoxLayout()
        self._placeholder = self._build_calendar_placeholder()
        self.right_col.addWidget(self._placeholder, stretch=1)

        two_col_layout.addLayout(left_col, stretch=1)
        two_col_layout.addLayout(self.right_col, stretch=1)
        body.addLayout(two_col_layout)

        root.addLayout(body)

        # Footer: validation label + indeterminate progress bar + running counter.
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

        # Connect controller signals to methods
        self._controller.schedule_found.connect(self._on_schedule_found)
        self._controller.progress_updated.connect(self._on_progress_updated)
        self._controller.search_finished.connect(self._on_search_finished)
        self._controller.error_occurred.connect(self._on_error_occurred)
        self._controller.early_results_ready.connect(self._on_early_results_ready)

        self._refresh_generate_button()

    def _build_courses_card(self) -> QFrame:
        """Build the card holding the loaded-course catalogue widget."""
        card = create_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setObjectName("card-icon")
        try:
            icon_pix = create_scaled_pixmap(self, "data/assets/courseIcon.png", 18)
            icon_lbl.setPixmap(icon_pix)
        except Exception:
            icon_lbl.setText("📋")
            icon_lbl.setObjectName("card-icon")

        courses_title = QLabel("Courses")
        courses_title.setObjectName("card-title")

        header_row.addWidget(icon_lbl)
        header_row.addWidget(courses_title)
        header_row.addStretch()
        # Visible badge showing how many courses were loaded.
        self._courses_visible_badge = QLabel("Not loaded")
        self._courses_visible_badge.setObjectName("badge")
        header_row.addWidget(self._courses_visible_badge)
        layout.addLayout(header_row)
        layout.addWidget(create_divider())

        self._course_list_widget = CourseListWidget()
        layout.addWidget(self._course_list_widget, stretch=1)
        return card

    def _build_calendar_placeholder(self) -> QFrame:
        """Build the placeholder for the date editor."""
        frame = QFrame()
        frame.setObjectName("calendar-placeholder")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        layout.addStretch()

        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            icon_pix = create_scaled_pixmap(self, "data/assets/periodIcon.png", 36)
            icon.setPixmap(icon_pix)
            icon.setObjectName("calendar-placeholder-icon")
        except Exception:
            icon.setText("🗓")
            icon.setObjectName("calendar-placeholder-icon")

        title = QLabel("Calendar editor")
        title.setObjectName("calendar-placeholder-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Reserved — exam date selection coming soon")
        sub.setObjectName("calendar-placeholder-subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addStretch()
        return frame

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

    def _refresh_program_summary(self) -> None:
        self.program_selector_card._refresh_program_summary()

    @property
    def _programs_count_badge(self):
        return self.program_selector_card._programs_count_badge

    def _mark_file_loaded(self, row: dict, count: int, label: str) -> None:
        """Record a successful file load on the status badge."""
        row["count_lbl"].setText(f"✓  {count} {label}")

    def _refresh_generate_button(self) -> None:
        """Enable Generate only when both files are loaded; warn otherwise."""
        missing = []
        if not self._courses_loaded:
            missing.append("courses file")
        if not self._periods_loaded:
            missing.append("periods file")

        self.action_bar.generate_btn.setEnabled(len(missing) == 0)

        if missing:
            self.action_bar.generate_btn.setToolTip(
                "⚠  Please load: " + " and ".join(missing) + " to continue."
            )
        else:
            self.action_bar.generate_btn.setToolTip("")

        self._validation_label.setText("")
        self._validate_programs()

    def _set_running_mode(self, running: bool) -> None:
        """Toggle the UI between idle and running states."""
        self.action_bar.generate_btn.setVisible(not running)
        self.action_bar.cancel_btn.setVisible(running)
        self._progress_bar.setVisible(running)
        self._progress_label.setVisible(running)
        self._courses_row["load_btn"].setEnabled(not running)
        self._periods_row["load_btn"].setEnabled(not running)
        if running:
            self._last_count = 0
            self._progress_label.setText("Initialising scheduler…")
            # Hide "View Results" while a new run is in progress so the user cannot jump to stale results from a previous generation.
            self._view_results_btn.setVisible(False)

    def _selected_mode(self) -> ImportMode:
        """Return the import mode currently selected in the radio buttons."""
        return ImportMode.REPLACE if self.action_bar.mode_replace.isChecked() else ImportMode.UPDATE

    def _on_load_courses_clicked(self) -> None:
        """Relay the load-courses button click using the currently selected import mode."""
        self.on_load_courses(self._selected_mode())

    def _on_load_periods_clicked(self) -> None:
        """Relay the load-periods button click using the currently selected import mode."""
        self.on_load_periods(self._selected_mode())

    def _on_generate_clicked(self) -> None:
        """Validate the program selection, then launch the scheduler."""
        if not self._validate_programs():
            return
        program_ids = self._collect_selected_program_ids()
        # Reset the navigation guard so this run can switch to the output screen.
        self._already_navigated = False
        self._set_running_mode(True)
        self._controller.generate_schedules(program_ids)

    def _on_cancel_clicked(self) -> None:
        """Stop the running scheduler and restore the idle UI."""
        self._controller.cancel_scheduling()
        self._set_running_mode(False)
        self._progress_label.setText("")

    def _on_view_results_clicked(self) -> None:
        """Jump back to the output screen without re-running the scheduler."""
        self._router.show(SCREEN_OUTPUT)

    def _on_constraints_saved(self, updated_vms: list) -> None:
        """Triggered when the user saves constraints in the calendar editor."""
        # Push the edited periods into the model so generation uses them.
        self._controller.update_exam_periods(updated_vms)
        self._refresh_generate_button()

    def _on_schedule_found(self, dto) -> None:
        """Receive per-result notifications from the scheduler. Not used here."""
        pass

    def _on_progress_updated(self, count: int) -> None:
        """Update the running counter as new schedules are found."""
        self._last_count = count
        self._progress_label.setText(
            f"Found {count} schedule{'s' if count != 1 else ''} so far…"
        )

    def _navigate_to_output(self) -> None:
        """Switch to the output screen exactly once per run."""
        if self._already_navigated:
            return
        self._already_navigated = True
        # Show the button now that results exist and the output screen is active.
        self._view_results_btn.setVisible(True)
        self._router.show(SCREEN_OUTPUT)

    def _result_count(self) -> int:
        """Return the authoritative number of schedules found."""
        try:
            info = self._controller.get_page_info()
            return int(info.get("total_count", 0))
        except Exception:
            return self._last_count

    def _on_early_results_ready(self) -> None:
        """Open output screen once first sqlite page is ready."""
        self._navigate_to_output()

    def _on_search_finished(self) -> None:
        """Navigate to the output screen if results exist, else warn the user."""
        self._set_running_mode(False)
        if self._already_navigated:
            return
        if self._result_count() > 0:
            self._navigate_to_output()
        else:
            self._validation_label.setText(
                "⚠  No valid schedules found. Try adjusting programs or exam dates."
            )

    def _on_error_occurred(self, message: str) -> None:
        """Show a critical error dialog and restore the idle UI."""
        self._set_running_mode(False)
        QMessageBox.critical(self, "Scheduler error", message)

    def _get_loaded_courses(self) -> list:
        """Return the list of currently loaded courses."""
        return self._controller.get_loaded_courses()

    def _get_loaded_periods(self) -> list:
        """Return the list of currently loaded exam periods."""
        return self._controller.get_loaded_periods()

    def _get_mapper(self):
        """Return the mapper instance for converting domain objects to view models."""
        return self._controller.get_mapper()

    def _handle_import_result(self, result, data_label: str) -> None:
        """Show an error dialog if the import failed."""
        if not result.success:
            detail = "\n".join(result.errors) if result.errors else "Unknown error."
            QMessageBox.critical(self, "Import error", f"Failed to load {data_label}:\n{detail}")

    def on_load_courses(self, mode: ImportMode) -> None:
        """Import a courses file and populate the course catalogue widget."""
        path = prompt_open_file(self, "Select courses file", "All files (*)")
        if not path:
            return
        result = self._controller.load_file(path, "courses", mode)
        self._handle_import_result(result, "courses")
        if result.success:
            self._courses_loaded = True
            self._mark_file_loaded(self._courses_row, result.loaded_count, "courses")
            self._courses_visible_badge.setText(f"✓  {result.loaded_count} courses")
            self._courses_visible_badge.setObjectName("badge-ok")
            self._courses_visible_badge.style().unpolish(self._courses_visible_badge)
            self._courses_visible_badge.style().polish(self._courses_visible_badge)
            self._refresh_generate_button()

            # Read the imported courses back and render them grouped by program.
            courses = self._get_loaded_courses()
            mapper = self._get_mapper()
            if courses and mapper is not None:
                programs_vm = mapper.to_program_courses_vm(courses)
                self._course_list_widget.render(programs_vm)

    def on_load_periods(self, mode: ImportMode) -> None:
        """Import a periods file and update the load state."""
        path = prompt_open_file(self, "Select periods file", "All files (*)")
        if not path:
            return
        result = self._controller.load_file(path, "periods", mode)
        self._handle_import_result(result, "periods")
        if result.success:
            self._periods_loaded = True
            self._mark_file_loaded(self._periods_row, result.loaded_count, "periods")
            self._refresh_generate_button()

            periods = self._get_loaded_periods()
            mapper = self._get_mapper()
            # Insert the real editor once we have periods and the mapper.
            if periods and mapper:
                period_vms = mapper.to_period_edit_vms(periods)
                if period_vms:
                    # Remove the static placeholder before inserting the real editor.
                    if self._placeholder:
                        self._placeholder.deleteLater()
                        self._placeholder = None

                    if self._editor_widget is not None:
                        try:
                            self._editor_widget.constraints_saved.disconnect(
                                self._on_constraints_saved
                            )
                        except RuntimeError:
                            pass

                    self._editor_widget = CalendarEditorWidget(period_vms)
                    self._editor_widget.constraints_saved.connect(self._on_constraints_saved)
                    self.right_col.insertWidget(0, self._editor_widget, stretch=1)

    def _collect_selected_program_ids(self) -> List[str]:
        """Return the program IDs the user has committed via the popup."""
        return self.program_selector_card.selected_program_ids()

    def _validate_programs(self) -> bool:
        """Validate the program selection and update the error label above the selector."""
        program_ids = self._collect_selected_program_ids()
        if not program_ids:
            self.program_error_label.setText("⚠ Please select at least one study program.")
            self.program_error_label.setVisible(True)
            return False
        else:
            self.program_error_label.setText("")
            self.program_error_label.setVisible(False)
            return True

    def on_enter(self) -> None:
        """Called by the router when this screen becomes active."""
        self._refresh_generate_button()

    def on_leave(self) -> None:
        """Called by the router when navigating away from this screen."""
        pass