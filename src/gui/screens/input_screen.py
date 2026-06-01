from __future__ import annotations

from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QRadioButton, QButtonGroup, QGroupBox, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt

from src.gui.screen import Screen
from src.application.import_mode import ImportMode


class InputScreen(Screen):
    """Input screen — file loading (SCRUM-89); full UI built in SCRUM-136."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(8)

        # Placeholder — will be replaced/surrounded by:
        #   program_selector_widget (SCRUM-90), course_list_widget (SCRUM-91),
        #   calendar_editor_widget (SCRUM-92), calendar_widget (SCRUM-93)
        placeholder = QLabel("Input Screen — SCRUM-136")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(placeholder)

        # Vertical space claimed by future content widgets
        root_layout.addStretch()

        # --- File import section (SCRUM-89) ---
        import_group = QGroupBox("File Import")
        import_layout = QVBoxLayout(import_group)

        # Import mode selector
        mode_row = QHBoxLayout()
        mode_label = QLabel("Import mode:")
        self._mode_replace = QRadioButton("Replace")
        self._mode_replace.setChecked(True)
        self._mode_update = QRadioButton("Update")
        # Keep a reference so the group is not garbage-collected
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_replace)
        self._mode_group.addButton(self._mode_update)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self._mode_replace)
        mode_row.addWidget(self._mode_update)
        mode_row.addStretch()
        import_layout.addLayout(mode_row)

        # Load buttons
        btn_row = QHBoxLayout()
        load_courses_btn = QPushButton("Load Courses")
        load_courses_btn.setToolTip("Select a courses file (CSV / JSON)")
        load_courses_btn.clicked.connect(self._on_load_courses_clicked)
        load_periods_btn = QPushButton("Load Periods")
        load_periods_btn.setToolTip("Select a periods file (CSV / JSON)")
        load_periods_btn.clicked.connect(self._on_load_periods_clicked)
        btn_row.addWidget(load_courses_btn)
        btn_row.addWidget(load_periods_btn)
        btn_row.addStretch()
        import_layout.addLayout(btn_row)

        # Status label — updated after each successful import
        self._status_label = QLabel("")
        import_layout.addWidget(self._status_label)

        root_layout.addWidget(import_group)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _selected_mode(self) -> ImportMode:
        """Return the import mode currently selected in the radio group."""
        return ImportMode.REPLACE if self._mode_replace.isChecked() else ImportMode.UPDATE

    def _on_load_courses_clicked(self) -> None:
        self.on_load_courses(self._selected_mode())

    def _on_load_periods_clicked(self) -> None:
        self.on_load_periods(self._selected_mode())

    def _handle_import_result(self, result, data_label: str) -> None:
        """Show a status message or an error dialog depending on the import result."""
        if result.success:
            self._status_label.setText(f"Loaded {result.loaded_count} {data_label}.")
        else:
            self._status_label.setText("")
            detail = "\n".join(result.errors) if result.errors else "Unknown error."
            QMessageBox.critical(
                self,
                "Import error",
                f"Failed to load {data_label}:\n{detail}",
            )

    # ------------------------------------------------------------------
    # Public handlers (called by buttons; also testable directly)
    # ------------------------------------------------------------------

    def on_load_courses(self, mode: ImportMode) -> None:
        """Open a file dialog and delegate course loading to the controller."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select courses file", "",
            "All files (*)",
        )
        if not path:
            return
        if not hasattr(self._controller, "load_courses_file"):
            QMessageBox.warning(self, "Backend not ready", "Backend not wired yet (SCRUM-135)")
            return
        result = self._controller.load_courses_file(path, mode)
        self._handle_import_result(result, "courses")

    def on_load_periods(self, mode: ImportMode) -> None:
        """Open a file dialog and delegate period loading to the controller."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select periods file", "",
            "All files (*)",
        )
        if not path:
            return
        if not hasattr(self._controller, "load_periods_file"):
            QMessageBox.warning(self, "Backend not ready", "Backend not wired yet (SCRUM-135)")
            return
        result = self._controller.load_periods_file(path, mode)
        self._handle_import_result(result, "periods")

    # ------------------------------------------------------------------
    # Screen lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        # Nothing to restore — persistent widget state is retained between navigations.
        pass

    def on_leave(self) -> None:
        # Nothing to tear down — the controller owns loaded data, not this screen.
        pass
