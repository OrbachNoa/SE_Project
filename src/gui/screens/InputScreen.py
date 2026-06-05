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

from gui.widgets.ProgramSelectorWidget import ProgramSelectorWidget
from gui.widgets.ProgramSelectorDialog import ProgramSelectorDialog
from gui.widgets.CourseListWidget import CourseListWidget
from src.application.viewmodels.ProgramViewModel import ProgramViewModel
from data.programs import programs_data

from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QFileDialog,
    QMessageBox, QProgressBar, QSizePolicy, QWidget,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from gui.screen import Screen
from src.application.ImportBoundary import ImportMode

# Name used by the router to identify the output screen.
SCREEN_OUTPUT = "output"

# Maximum number of programs the user may select (mirrors the widget limit).
MAX_PROGRAMS = 5


def _card(parent=None) -> QFrame:
    """Return a styled card frame (white background, rounded border)."""
    f = QFrame(parent)
    f.setObjectName("card")
    f.setFrameShape(QFrame.Shape.NoFrame)
    return f


def _divider(parent=None) -> QFrame:
    """Return a 1-pixel horizontal separator line."""
    f = QFrame(parent)
    f.setObjectName("divider")
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    return f


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

        # Committed program selection. The popup works on a copy and only
        # writes back here when the user presses "Select", so closing the
        # popup without confirming never loses the previous choice.
        self._selected_program_ids: List[str] = []

        # Built once from the static programs dictionary and reused every time
        # the popup opens, so we never rebuild view models on each click.
        self._program_view_models = [
            ProgramViewModel(program_id=p_id, display_name=p_name, course_count=0)
            for p_id, p_name in programs_data.items()
        ]

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        # Green branding bar: icon + title on the left, breadcrumb on the right.
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(70)
        header.setStyleSheet("QFrame#header { background: #143D30; }")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 0, 28, 0)
        h_layout.setSpacing(12)

        # Rounded-square icon with "S" initial — placeholder for a logo asset.
        icon_frame = QFrame()
        icon_frame.setFixedSize(34, 34)
        icon_frame.setStyleSheet("background: #3E89BD; border-radius: 8px;")
        icon_inner = QHBoxLayout(icon_frame)
        icon_inner.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("S")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: white; font-weight: bold; font-size: 16px; background: transparent;"
        )
        icon_inner.addWidget(icon_lbl)

        title = QLabel("Exam Scheduler")
        title.setObjectName("app-title")
        title.setFont(QFont("Segoe UI", 15))
        subtitle = QLabel("Schedule generation for academic institutions")
        subtitle.setObjectName("app-subtitle")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.6); background: transparent;")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        h_layout.addWidget(icon_frame)
        h_layout.addLayout(title_col)
        h_layout.addStretch()

        # Breadcrumb: active step in blue, next step dimmed.
        bc_input = QLabel("Input")
        bc_input.setStyleSheet("color: #5BA4D4; font-weight: 600; background: transparent;")
        bc_sep = QLabel("›")
        bc_sep.setStyleSheet("color: #475569; background: transparent;")
        bc_output = QLabel("Output")
        bc_output.setStyleSheet("color: #475569; background: transparent;")
        bc_output.setEnabled(False)

        h_layout.addWidget(bc_input)
        h_layout.addWidget(bc_sep)
        h_layout.addWidget(bc_output)

        root.addWidget(header)

        # ── Action bar ─────────────────────────────────────────────────────
        # File-load triggers on the left, import mode in the middle, the
        # generate / cancel pair on the right. Stays pinned below the header.
        action_bar = QFrame()
        action_bar.setFixedHeight(56)
        action_bar.setStyleSheet(
            "QFrame { background: white; border-bottom: 1px solid #E2E8F0; }"
        )
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(20, 0, 20, 0)
        ab_layout.setSpacing(10)

        self._courses_load_btn = QPushButton("📂  Load Courses")
        self._courses_load_btn.setObjectName("btn-secondary")
        self._courses_load_btn.setFixedHeight(36)
        self._courses_load_btn.clicked.connect(self._on_load_courses_clicked)

        self._periods_load_btn = QPushButton("📅  Load Periods")
        self._periods_load_btn.setObjectName("btn-secondary")
        self._periods_load_btn.setFixedHeight(36)
        self._periods_load_btn.clicked.connect(self._on_load_periods_clicked)

        ab_layout.addWidget(self._courses_load_btn)
        ab_layout.addWidget(self._periods_load_btn)

        # Vertical divider between load buttons and the mode selector.
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.Shape.VLine)
        v_sep.setFixedHeight(24)
        v_sep.setStyleSheet("color: #E2E8F0;")
        ab_layout.addWidget(v_sep)

        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("color: #64748B; background: transparent;")
        self._mode_replace = QRadioButton("Replace")
        self._mode_replace.setChecked(True)
        self._mode_update = QRadioButton("Update")
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_replace)
        self._mode_group.addButton(self._mode_update)

        ab_layout.addWidget(mode_label)
        ab_layout.addWidget(self._mode_replace)
        ab_layout.addWidget(self._mode_update)
        ab_layout.addStretch()

        self._generate_btn = QPushButton("▶  Generate Schedule")
        self._generate_btn.setObjectName("btn-primary")
        self._generate_btn.setEnabled(False)
        self._generate_btn.setFixedHeight(40)
        self._generate_btn.clicked.connect(self._on_generate_clicked)

        self._cancel_btn = QPushButton("✕  Cancel")
        self._cancel_btn.setObjectName("btn-danger")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.setFixedHeight(40)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

        ab_layout.addWidget(self._generate_btn)
        ab_layout.addWidget(self._cancel_btn)

        root.addWidget(action_bar)

        # Hidden status badges kept so _mark_file_loaded / _set_running_mode can
        # update load state without depending on the visible layout structure.
        self._courses_status_badge = QLabel("Not loaded")
        self._courses_status_badge.setVisible(False)
        _periods_count_lbl = QLabel("Not loaded")
        _periods_count_lbl.setVisible(False)

        self._courses_row = {
            "count_lbl": self._courses_status_badge,
            "load_btn": self._courses_load_btn,
        }
        self._periods_row = {
            "count_lbl": _periods_count_lbl,
            "load_btn": self._periods_load_btn,
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
        left_col.addWidget(self._build_program_selector_card())
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

        self._refresh_program_summary()
        self._refresh_generate_button()

    # ── Body builders ───────────────────────────────────────────────────

    def _build_program_selector_card(self) -> QFrame:
        """Build the clickable program-selector line.

        Shows a placeholder when nothing is chosen and a row of program chips
        once the user has selected programs. Clicking anywhere on the card
        opens the selection popup. The card grows vertically as chips wrap.
        """
        card = _card()
        card.setObjectName("selector-card")
        # Local rounded style + pointer cursor to signal it is clickable.
        card.setStyleSheet(
            "QFrame#selector-card {"
            "  background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;"
            "}"
            "QFrame#selector-card:hover { border-color: #3E89BD; }"
        )
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header row: icon + title on the left, count badge + chevron on the right.
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        prog_title = QLabel("📚  Study Programs")
        prog_title.setObjectName("card-title")
        header_row.addWidget(prog_title)
        header_row.addStretch()

        self._programs_count_badge = QLabel(f"0 / {MAX_PROGRAMS}")
        self._programs_count_badge.setStyleSheet(
            "color: #64748B; background: #F1F5F9; border-radius: 10px;"
            "padding: 2px 10px; font-size: 11px;"
        )
        header_row.addWidget(self._programs_count_badge)

        chevron = QLabel("▾")
        chevron.setStyleSheet("color: #94A3B8; background: transparent; font-size: 13px;")
        header_row.addWidget(chevron)
        layout.addLayout(header_row)

        # Summary area: rebuilt by _refresh_program_summary (placeholder or chips).
        self._summary_container = QWidget()
        self._summary_container.setStyleSheet("background: transparent;")
        self._summary_layout = QVBoxLayout(self._summary_container)
        self._summary_layout.setContentsMargins(0, 0, 0, 0)
        self._summary_layout.setSpacing(6)
        layout.addWidget(self._summary_container)

        # Make the whole card open the popup, no matter where the user clicks.
        card.mousePressEvent = self._on_selector_card_clicked
        return card

    def _build_courses_card(self) -> QFrame:
        """Build the card holding the loaded-course catalogue widget."""
        card = _card()
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
        layout.addWidget(_divider())

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

    # ── Program selection popup ───────────────────────────────────────────

    def _on_selector_card_clicked(self, event) -> None:
        """Open the program selection popup when the selector card is clicked."""
        self._open_program_dialog()

    def _open_program_dialog(self) -> None:
        """Show the modal popup and commit the new selection only on accept."""
        dialog = ProgramSelectorDialog(
            self._program_view_models,
            preselected_ids=self._selected_program_ids,
            parent=self,
        )
        if dialog.exec():
            # Accepted ("Select" pressed) — commit the new selection.
            self._selected_program_ids = dialog.selected_ids()
            self._refresh_program_summary()
            self._refresh_generate_button()

    def _refresh_program_summary(self) -> None:
        """Rebuild the selector summary: placeholder when empty, chips otherwise."""
        # Remove any previously rendered summary widgets.
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        count = len(self._selected_program_ids)
        self._programs_count_badge.setText(f"{count} / {MAX_PROGRAMS}")

        if count == 0:
            placeholder = QLabel("Click to select programs")
            placeholder.setStyleSheet(
                "color: #94A3B8; font-size: 13px; background: transparent;"
            )
            self._summary_layout.addWidget(placeholder)
            return

        # Map program IDs back to display names for nicer chip labels.
        name_by_id = {vm.program_id: vm.display_name for vm in self._program_view_models}

        # Lay chips out in rows of up to three so the card grows gracefully.
        row = None
        for i, pid in enumerate(self._selected_program_ids):
            if i % 3 == 0:
                row = QHBoxLayout()
                row.setSpacing(6)
                row.setAlignment(Qt.AlignmentFlag.AlignLeft)
                row_holder = QWidget()
                row_holder.setStyleSheet("background: transparent;")
                row_holder.setLayout(row)
                self._summary_layout.addWidget(row_holder)

            label = name_by_id.get(pid, pid)
            chip = QLabel(f"{pid} · {label}")
            chip.setStyleSheet(
                "color: #143D30; background: #E5F0EB; border: 1px solid #14633F;"
                "border-radius: 11px; padding: 3px 10px; font-size: 11px;"
            )
            row.addWidget(chip)
        if row is not None:
            row.addStretch()

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

        self._generate_btn.setEnabled(len(missing) == 0)

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
        self._generate_btn.setVisible(not running)
        self._cancel_btn.setVisible(running)
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
        return ImportMode.REPLACE if self._mode_replace.isChecked() else ImportMode.UPDATE

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
        path, _ = QFileDialog.getOpenFileName(self, "Select courses file", "", "All files (*)")
        if not path:
            return
        result = self._controller.load_file(path, "courses", mode)
        self._handle_import_result(result, "courses")
        if result.success:
            self._courses_loaded = True
            self._mark_file_loaded(self._courses_row, result.loaded_count, "courses")
            self._courses_visible_badge.setText(f"✓  {result.loaded_count} courses")
            self._courses_visible_badge.setStyleSheet(
                "color: #14633F; background: #E5F0EB; border-radius: 10px;"
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
        path, _ = QFileDialog.getOpenFileName(self, "Select periods file", "", "All files (*)")
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
        return list(self._selected_program_ids)

    # ── Screen lifecycle ───────────────────────────────────────────────

    def on_enter(self) -> None:
        """Called by the router when this screen becomes active."""
        self._refresh_generate_button()

    def on_leave(self) -> None:
        """Called by the router when navigating away from this screen."""
        pass
