"""InputScreen — file loading + schedule generation trigger.

Layout overview:
  - Header      : green branding bar with breadcrumb (Input › Output)
  - Action bar  : Load Courses / Load Periods, import mode, Generate / Cancel
  - Body        : two columns
        left    -> program selector line (opens a popup) + loaded course list
        right   -> reserved placeholder for a future calendar date editor
  - Footer      : validation message + progress bar
"""
from __future__ import annotations

from typing import List

from gui.widgets.ProgramSelectorCardWidget import ProgramSelectorCardWidget
from gui.widgets.CourseListWidget import CourseListWidget

from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QRadioButton, QButtonGroup, QFrame,
    QMessageBox, QProgressBar, QSizePolicy, QWidget,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from gui.widgets.HeaderWidget import HeaderWidget
from gui.widgets.Common import create_divider, create_card, prompt_open_file
from gui.widgets.ActionBarWidget import ActionBarWidget

from gui.screen import Screen
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

        # Guards against navigating to the output screen twice: once when
        # early_results_ready fires (first SQLite page ready) and again when
        # search_finished fires at the end of the full search. Reset before
        # each new run.
        self._already_navigated = False

        # Reusable program selector card widget
        self.program_selector_card = ProgramSelectorCardWidget(MAX_PROGRAMS, self)
        self.program_selector_card.selection_changed.connect(self._refresh_generate_button)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        # Reusable gold header branding bar
        header = HeaderWidget(active_step="input", parent=self)
        root.addWidget(header)

        # ── Action bar ─────────────────────────────────────────────────────
        self.action_bar = ActionBarWidget(self)
        self.action_bar.courses_load_btn.clicked.connect(self._on_load_courses_clicked)
        self.action_bar.periods_load_btn.clicked.connect(self._on_load_periods_clicked)
        self.action_bar.generate_btn.clicked.connect(self._on_generate_clicked)
        self.action_bar.cancel_btn.clicked.connect(self._on_cancel_clicked)
        root.addWidget(self.action_bar)

        # Hidden status badges kept so _mark_file_loaded / _set_running_mode can
        # update load state without depending on the visible layout structure.
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

        # ── Body — two columns ─────────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(20, 20, 20, 20)
        body.setSpacing(16)

        two_col_layout = QHBoxLayout()
        two_col_layout.setSpacing(16)

        # Left column: program selector line + loaded course list.
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        left_col.addWidget(self.program_selector_card)
        left_col.addWidget(self._build_courses_card(), stretch=1)

        # Right column: reserved calendar editor placeholder.
        self.right_col = QVBoxLayout()
        self._placeholder = self._build_calendar_placeholder()
        self.right_col.addWidget(self._placeholder, stretch=1)

        two_col_layout.addLayout(left_col, stretch=1)
        two_col_layout.addLayout(self.right_col, stretch=1)
        body.addLayout(two_col_layout)

        root.addLayout(body)

        # ── Footer — validation + progress ─────────────────────────────────
        self._validation_label = QLabel("")
        self._validation_label.setObjectName("status-error")
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

        # ── Connect controller signals ─────────────────────────────────────
        # progress_updated    — running count (may not fire with the SQL engine)
        # search_finished     — full background search completed
        # error_occurred      — fatal scheduler error
        # early_results_ready — first SQLite page is ready; jump to output now
        #                       without waiting for the whole search to finish.
        self._controller.schedule_found.connect(self._on_schedule_found)
        self._controller.progress_updated.connect(self._on_progress_updated)
        self._controller.search_finished.connect(self._on_search_finished)
        self._controller.error_occurred.connect(self._on_error_occurred)
        self._controller.early_results_ready.connect(self._on_early_results_ready)

        self._refresh_generate_button()

    # ── Body builders ───────────────────────────────────────────────────



    def _build_courses_card(self) -> QFrame:
        """Build the card holding the loaded-course catalogue widget."""
        card = create_card()
        card.setStyleSheet(
            "QFrame#card { background: #FFFFFF; border: 1px solid #E2E8F0;"
            " border-radius: 14px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        courses_title = QLabel("📋  Courses")
        courses_title.setObjectName("card-title")
        header_row.addWidget(courses_title)
        header_row.addStretch()
        # Visible badge showing how many courses were loaded.
        self._courses_visible_badge = QLabel("Not loaded")
        self._courses_visible_badge.setStyleSheet(
            "color: #94A3B8; background: #F1F5F9; border-radius: 10px;"
            "padding: 2px 10px; font-size: 11px;"
        )
        header_row.addWidget(self._courses_visible_badge)
        layout.addLayout(header_row)
        layout.addWidget(create_divider())

        self._course_list_widget = CourseListWidget()
        layout.addWidget(self._course_list_widget, stretch=1)
        return card

    def _build_calendar_placeholder(self) -> QFrame:
        """Build the reserved (non-interactive) placeholder for the date editor.

        The exam-period calendar editor is owned by another part of the team;
        here we only reserve the space with a rounded dashed frame so the layout
        already reflects where it will live.
        """
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame {"
            "  border: 2px dashed #CBD5E1; border-radius: 16px;"
            "  background: #FFFFFF;"
            "}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        layout.addStretch()

        icon = QLabel("🗓")
        icon.setStyleSheet("font-size: 30px; background: transparent; border: none;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Calendar editor")
        title.setStyleSheet(
            "color: #94A3B8; font-size: 14px; font-weight: 600;"
            " background: transparent; border: none;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Reserved — exam date selection coming soon")
        sub.setStyleSheet(
            "color: #B6C0CC; font-size: 11px; background: transparent; border: none;"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addStretch()
        return frame



    # ── File row state helpers ────────────────────────────────────────────

    def _mark_file_loaded(self, row: dict, count: int, label: str) -> None:
        """Record a successful file load on the (hidden) status badge."""
        row["count_lbl"].setText(f"✓  {count} {label}")

    # ── Validation ─────────────────────────────────────────────────────

    def _refresh_generate_button(self) -> None:
        """Enable Generate only when both files are loaded; warn otherwise."""
        missing = []
        if not self._courses_loaded:
            missing.append("courses file")
        if not self._periods_loaded:
            missing.append("periods file")

        self.action_bar.generate_btn.setEnabled(len(missing) == 0)

        if missing:
            self._validation_label.setObjectName("status-error")
            self._validation_label.setStyleSheet("color:#dc2626; background:transparent;")
            self._validation_label.setText(
                "⚠  Please load: " + " and ".join(missing) + " to continue."
            )
        else:
            self._validation_label.setText("")

    # ── Running state ──────────────────────────────────────────────────

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

    # ── Event handlers ─────────────────────────────────────────────────

    def _selected_mode(self) -> ImportMode:
        """Return the import mode currently selected in the radio buttons."""
        return ImportMode.REPLACE if self.action_bar.mode_replace.isChecked() else ImportMode.UPDATE

    def _on_load_courses_clicked(self) -> None:
        self.on_load_courses(self._selected_mode())

    def _on_load_periods_clicked(self) -> None:
        self.on_load_periods(self._selected_mode())

    def _on_generate_clicked(self) -> None:
        """Validate the program selection, then launch the scheduler."""
        program_ids = self._collect_selected_program_ids()
        if not program_ids:
            self._validation_label.setStyleSheet("color:#d97706; background:transparent;")
            self._validation_label.setText(
                "ℹ  Please select at least one study program before generating."
            )
            return
        # Reset the navigation guard so this run can switch to the output screen.
        self._already_navigated = False
        self._set_running_mode(True)
        self._controller.generate_schedules(program_ids)

    def _on_cancel_clicked(self) -> None:
        """Stop the running scheduler and restore the idle UI."""
        self._controller.cancel_scheduling()
        self._set_running_mode(False)
        self._progress_label.setText("")

    def _on_constraints_saved(self, updated_vms: list) -> None:
        """Triggered when the user saves constraints in the calendar editor."""
        # Push the edited periods into the model so generation uses them.
        self._controller.update_exam_periods(updated_vms)
        self._refresh_generate_button()
        
        # Debug print to verify it works:
        print(f"InputScreen received {len(updated_vms)} updated periods from calendar.")

    # ── Controller signal handlers ─────────────────────────────────────

    def _on_schedule_found(self, dto) -> None:
        # Per-result notifications are not used here; the output screen reads
        # results on demand once it becomes active.
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
        self._router.show(SCREEN_OUTPUT)

    def _result_count(self) -> int:
        """Return the authoritative number of schedules found.

        The SQL engine reports progress as batches written to SQLite rather
        than via progress_updated, so _last_count can stay at 0 even when
        results exist. We therefore ask the controller for the real count and
        fall back to _last_count only if that lookup is unavailable.
        """
        try:
            info = self._controller.get_page_info()
            return int(info.get("total_count", 0))
        except Exception:
            return self._last_count

    def _on_early_results_ready(self) -> None:
        """First SQLite page is ready — open the output screen immediately.

        This is what makes pressing "Generate" jump straight to the results
        without waiting for the entire search to complete.
        """
        self._navigate_to_output()

    def _on_search_finished(self) -> None:
        """Navigate to the output screen if results exist, else warn the user.

        If early_results_ready already switched screens, this is a no-op.
        Uses the real result count (not _last_count) so navigation works even
        when the engine never emits progress_updated.
        """
        self._set_running_mode(False)
        if self._already_navigated:
            return
        if self._result_count() > 0:
            self._navigate_to_output()
        else:
            self._validation_label.setStyleSheet("color:#d97706; background:transparent;")
            self._validation_label.setText(
                "⚠  No valid schedules found. Try adjusting programs or exam dates."
            )

    def _on_error_occurred(self, message: str) -> None:
        """Show a critical error dialog and restore the idle UI."""
        self._set_running_mode(False)
        QMessageBox.critical(self, "Scheduler error", message)

    # ── File loading ───────────────────────────────────────────────────

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
            self._courses_visible_badge.setStyleSheet(
                "color: #16A34A; background: #E8F5E9; border-radius: 10px;"
                "padding: 2px 10px; font-size: 11px; font-weight: 600;"
            )
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

            # --- Inject the dynamic calendar editor ---
            periods = self._get_loaded_periods()
            mapper = self._get_mapper()
            if periods and mapper:
                period_vms = mapper.to_period_edit_vms(periods)
                if period_vms:
                    # Remove the static placeholder UI
                    if self._placeholder:
                        self._placeholder.deleteLater()
                        self._placeholder = None
                    
                    # Insert the interactive calendar editor with all loaded periods
                    from src.gui.widgets.CalendarEditorWidget import CalendarEditorWidget
                    self._editor_widget = CalendarEditorWidget(period_vms)
                    self._editor_widget.constraints_saved.connect(self._on_constraints_saved)
                    self.right_col.insertWidget(0, self._editor_widget, stretch=1)

    # ── Program selection ──────────────────────────────────────────────

    def _collect_selected_program_ids(self) -> List[str]:
        """Return the program IDs the user has committed via the popup."""
        return self.program_selector_card.selected_program_ids()

    # ── Screen lifecycle ───────────────────────────────────────────────

    def on_enter(self) -> None:
        """Called by the router when this screen becomes active."""
        self._refresh_generate_button()

    def on_leave(self) -> None:
        """Called by the router when navigating away from this screen."""
        pass
