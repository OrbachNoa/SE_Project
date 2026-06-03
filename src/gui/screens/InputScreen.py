"""InputScreen — file loading + schedule generation trigger.

SCRUM-89  : file loading
SCRUM-144 : Generate button + UI selections
SCRUM-145 : input validation
SCRUM-148 : empty-state message
SCRUM-149 : error-handling UI
"""
from __future__ import annotations

from typing import List

from gui.widgets.ProgramSelectorWidget import ProgramSelectorWidget
from application.viewmodels.ProgramViewModel import ProgramViewModel
from data.programs import programs_data

from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QFileDialog,
    QMessageBox, QProgressBar, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from src.gui.Screen import Screen
from application.ImportMode import ImportMode

SCREEN_OUTPUT = "output"


def _card(parent=None) -> QFrame:
    """Return a styled card frame."""
    f = QFrame(parent)
    f.setObjectName("card")
    f.setFrameShape(QFrame.Shape.NoFrame)
    return f


def _divider(parent=None) -> QFrame:
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
        # Prevents _on_search_finished from switching screens a second time when
        # early_results_ready has already done so (e.g. for searches > 10 K results).
        self._already_navigated_to_output = False

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
        subtitle = QLabel("Schedule generation for academic institutions")
        subtitle.setObjectName("app-subtitle")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        badge = QLabel("v2.0")
        badge.setStyleSheet(
            "color:#475569; background:#1e293b; border-radius:4px;"
            "padding:2px 8px; font-size:11px; font-weight:600;"
        )
        badge.setFixedHeight(22)

        h_layout.addLayout(title_col)
        h_layout.addStretch()
        h_layout.addWidget(badge)
        root.addWidget(header)

        # ── Scrollable body ───────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(28, 24, 28, 24)
        body.setSpacing(16)

        # ── Data files card ───────────────────────────────────────────
        files_card = _card()
        files_layout = QVBoxLayout(files_card)
        files_layout.setContentsMargins(20, 16, 20, 16)
        files_layout.setSpacing(12)

        card_header = QHBoxLayout()
        card_title = QLabel("Data Files")
        card_title.setObjectName("card-title")
        card_header.addWidget(card_title)
        card_header.addStretch()

        mode_label = QLabel("Import mode:")
        mode_label.setStyleSheet("color:#64748b; font-size:12px; background:transparent;")
        self._mode_replace = QRadioButton("Replace")
        self._mode_replace.setChecked(True)
        self._mode_update = QRadioButton("Update")
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_replace)
        self._mode_group.addButton(self._mode_update)
        card_header.addWidget(mode_label)
        card_header.addWidget(self._mode_replace)
        card_header.addWidget(self._mode_update)
        files_layout.addLayout(card_header)

        files_layout.addWidget(_divider())

        # Courses row
        self._courses_row = self._build_file_row(
            "Courses", "Course catalogue with programs and exam types",
            self._on_load_courses_clicked
        )
        files_layout.addLayout(self._courses_row["layout"])

        files_layout.addWidget(_divider())

        # Periods row
        self._periods_row = self._build_file_row(
            "Exam Periods", "Exam windows with start/end dates and exclusions",
            self._on_load_periods_clicked
        )
        files_layout.addLayout(self._periods_row["layout"])

        body.addWidget(files_card)

        # ── Study Programs Real Selection Widget (SCRUM-90) ───────────
        self.program_selector = ProgramSelectorWidget()
        body.addWidget(self.program_selector)

        # Convert the raw dictionary items into structured ProgramViewModel tokens
        view_models_list = [
            ProgramViewModel(program_id=p_id, display_name=p_name, course_count=0)
            for p_id, p_name in programs_data.items()
        ]
        
        # Populate and paint your selector widget framework instantly with the live models
        self.program_selector.render(view_models_list)

        body.addStretch()

        # ── Validation label ──────────────────────────────────────────
        self._validation_label = QLabel("")
        self._validation_label.setObjectName("status-error")
        self._validation_label.setWordWrap(True)
        self._validation_label.setContentsMargins(4, 0, 0, 0)
        body.addWidget(self._validation_label)

        # ── Generate / Cancel / Progress ──────────────────────────────
        action_card = _card()
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(20, 16, 20, 16)
        action_layout.setSpacing(10)

        btn_row = QHBoxLayout()

        self._generate_btn = QPushButton("▶  Generate Schedule")
        self._generate_btn.setObjectName("btn-primary")
        self._generate_btn.setEnabled(False)
        self._generate_btn.setFixedHeight(44)
        self._generate_btn.clicked.connect(self._on_generate_clicked)
        btn_row.addWidget(self._generate_btn)

        self._cancel_btn = QPushButton("✕  Cancel")
        self._cancel_btn.setObjectName("btn-danger")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.setFixedHeight(44)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self._cancel_btn)

        action_layout.addLayout(btn_row)

        # Progress bar + label (hidden when idle)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)   # indeterminate pulsing
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(False)
        action_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("status-ok")
        self._progress_label.setVisible(False)
        action_layout.addWidget(self._progress_label)

        body.addWidget(action_card)

        root.addLayout(body)

        # ── Connect signals ───────────────────────────────────────────
        self._controller.schedule_found.connect(self._on_schedule_found)
        self._controller.progress_updated.connect(self._on_progress_updated)
        self._controller.search_finished.connect(self._on_search_finished)
        self._controller.error_occurred.connect(self._on_error_occurred)
        self._controller.early_results_ready.connect(self._on_early_results_ready)

        self._refresh_generate_button()

    # ── File row builder ───────────────────────────────────────────────

    def _build_file_row(self, label: str, hint: str, slot) -> dict:
        """Build a labelled file-load row and return refs to its dynamic widgets."""
        row = QHBoxLayout()
        row.setSpacing(12)

        # Status dot
        status_dot = QLabel("○")
        status_dot.setObjectName("status-pending")
        status_dot.setFixedWidth(16)
        status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Labels
        col = QVBoxLayout()
        col.setSpacing(1)
        name_lbl = QLabel(label)
        name_lbl.setStyleSheet("font-weight:600; color:#1e293b; background:transparent;")
        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("card-hint")
        col.addWidget(name_lbl)
        col.addWidget(hint_lbl)

        # Count badge
        count_lbl = QLabel("Not loaded")
        count_lbl.setObjectName("status-pending")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        count_lbl.setMinimumWidth(100)

        # Load button
        load_btn = QPushButton("Load ↑")
        load_btn.setObjectName("btn-secondary")
        load_btn.setFixedSize(80, 32)
        load_btn.clicked.connect(slot)

        row.addWidget(status_dot)
        row.addLayout(col, stretch=1)
        row.addWidget(count_lbl)
        row.addWidget(load_btn)

        return {
            "layout": row,
            "dot": status_dot,
            "count_lbl": count_lbl,
            "load_btn": load_btn,
        }

    def _mark_file_loaded(self, row: dict, count: int, label: str) -> None:
        """Update a file row to show the loaded state."""
        row["dot"].setText("●")
        row["dot"].setObjectName("status-ok")
        row["dot"].setStyleSheet("color:#16a34a; background:transparent; font-size:12px;")
        row["count_lbl"].setText(f"✓  {count} {label}")
        row["count_lbl"].setObjectName("status-ok")
        row["count_lbl"].setStyleSheet("color:#16a34a; font-weight:600; background:transparent;")

    # ── Validation ─────────────────────────────────────────────────────

    def _refresh_generate_button(self) -> None:
        missing = []
        if not self._courses_loaded:
            missing.append("courses file")
        if not self._periods_loaded:
            missing.append("periods file")

        ready = len(missing) == 0
        self._generate_btn.setEnabled(ready)

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
        self._generate_btn.setVisible(not running)
        self._cancel_btn.setVisible(running)
        self._progress_bar.setVisible(running)
        self._progress_label.setVisible(running)
        self._courses_row["load_btn"].setEnabled(not running)
        self._periods_row["load_btn"].setEnabled(not running)
        if running:
            self._last_count = 0
            self._progress_label.setText("Initialising scheduler…")

    # ── Handlers ───────────────────────────────────────────────────────

    def _selected_mode(self) -> ImportMode:
        return ImportMode.REPLACE if self._mode_replace.isChecked() else ImportMode.UPDATE

    def _on_load_courses_clicked(self) -> None:
        self.on_load_courses(self._selected_mode())

    def _on_load_periods_clicked(self) -> None:
        self.on_load_periods(self._selected_mode())

    def _on_generate_clicked(self) -> None:
        program_ids = self._collect_selected_program_ids()
        if not program_ids:
            self._validation_label.setStyleSheet("color:#d97706; background:transparent;")
            self._validation_label.setText(
                "ℹ  Program selection coming in SCRUM-90."
            )
            return
        self._already_navigated_to_output = False
        self._set_running_mode(True)
        self._controller.generate_schedules(program_ids)

    def _on_cancel_clicked(self) -> None:
        self._controller.cancel_scheduling()
        self._set_running_mode(False)
        self._progress_label.setText("")

    # ── Controller signal handlers ─────────────────────────────────────

    def _on_schedule_found(self, dto) -> None:
        pass

    def _on_progress_updated(self, count: int) -> None:
        self._last_count = count
        self._progress_label.setText(
            f"Found {count} schedule{'s' if count != 1 else ''} so far…"
        )

    def _on_early_results_ready(self) -> None:
        """First window (10 K) is ready — switch screens without waiting for full search."""
        self._already_navigated_to_output = True
        self._router.show(SCREEN_OUTPUT)

    def _on_search_finished(self) -> None:
        self._set_running_mode(False)
        if self._already_navigated_to_output:
            # early_results_ready already handled the screen switch; nothing to do.
            return
        if self._last_count > 0:
            self._router.show(SCREEN_OUTPUT)
        else:
            self._validation_label.setStyleSheet("color:#d97706; background:transparent;")
            self._validation_label.setText(
                "⚠  No valid schedules found. Try adjusting programs or exam dates."
            )

    def _on_error_occurred(self, message: str) -> None:
        self._set_running_mode(False)
        QMessageBox.critical(self, "Scheduler error", message)

    # ── File loading ───────────────────────────────────────────────────

    def _handle_import_result(self, result, data_label: str) -> None:
        if not result.success:
            detail = "\n".join(result.errors) if result.errors else "Unknown error."
            QMessageBox.critical(self, "Import error", f"Failed to load {data_label}:\n{detail}")

    def on_load_courses(self, mode: ImportMode) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select courses file", "", "All files (*)")
        if not path:
            return
        result = self._controller.load_file(path, "courses", mode)
        self._handle_import_result(result, "courses")
        if result.success:
            self._courses_loaded = True
            self._mark_file_loaded(self._courses_row, result.loaded_count, "courses")
            self._refresh_generate_button()

    def on_load_periods(self, mode: ImportMode) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select periods file", "", "All files (*)")
        if not path:
            return
        result = self._controller.load_file(path, "periods", mode)
        self._handle_import_result(result, "periods")
        if result.success:
            self._periods_loaded = True
            self._mark_file_loaded(self._periods_row, result.loaded_count, "periods")
            self._refresh_generate_button()

    # ── Placeholder ────────────────────────────────────────────────────

    def _collect_selected_program_ids(self) -> List[str]:
        """Fetch the active checked program IDs directly from Shira's custom widget."""
        return self.program_selector.get_selected()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def on_enter(self) -> None:
        self._refresh_generate_button()

    def on_leave(self) -> None:
        pass