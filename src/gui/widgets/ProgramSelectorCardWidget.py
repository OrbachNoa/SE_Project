"""Program selector card widget for selecting study programs on the input screen."""
from __future__ import annotations

from typing import List
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal

from gui.widgets.ProgramSelectorDialog import ProgramSelectorDialog
from src.application.viewmodels.ProgramViewModel import ProgramViewModel
from data.programs import programs_data


class ProgramSelectorCardWidget(QFrame):
    """Clickable card displaying selected study programs and launching the selector dialog."""

    selection_changed = pyqtSignal()

    def __init__(self, max_programs: int = 5, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.max_programs = max_programs
        self._selected_program_ids: List[str] = []

        # Build view models once from the static programs dictionary
        self._program_view_models = [
            ProgramViewModel(program_id=p_id, display_name=p_name, course_count=0)
            for p_id, p_name in programs_data.items()
        ]

        self.setObjectName("selector-card")
        self.setStyleSheet(
            "QFrame#selector-card {"
            "  background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;"
            "}"
            "QFrame#selector-card:hover { border-color: #3E89BD; }"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header row: icon + title on the left, count badge + chevron on the right.
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        prog_title = QLabel("📚  Study Programs")
        prog_title.setObjectName("card-title")
        header_row.addWidget(prog_title)
        header_row.addStretch()

        self._programs_count_badge = QLabel(f"0 / {self.max_programs}")
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

        self._refresh_program_summary()

    def mousePressEvent(self, event) -> None:
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
            self.selection_changed.emit()

    def _refresh_program_summary(self) -> None:
        """Rebuild the selector summary: placeholder when empty, chips otherwise."""
        # Remove any previously rendered summary widgets.
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        count = len(self._selected_program_ids)
        self._programs_count_badge.setText(f"{count} / {self.max_programs}")

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
                "color: #3E352F; background: #FAF5EC; border: 1px solid #3396ad;"
                "border-radius: 11px; padding: 3px 10px; font-size: 11px;"
            )
            row.addWidget(chip)
        if row is not None:
            row.addStretch()

    def selected_program_ids(self) -> List[str]:
        """Return the program IDs the user has committed via the popup."""
        return list(self._selected_program_ids)
