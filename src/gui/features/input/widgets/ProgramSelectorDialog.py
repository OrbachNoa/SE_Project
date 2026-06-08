"""ProgramSelectorDialog — modal popup for choosing study programs.

Shows every available program at once as a grid of clickable cards (no
scrolling). Clicking a card selects it; clicking again deselects it. The
dialog keeps its own selection state and enforces the maximum-selection
limit, so the parent screen only learns the result via selected_ids() once
the user presses "Select". Closing or cancelling leaves the previous
selection untouched.
"""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QWidget, QMessageBox, QSizePolicy,
)
from gui.core.styles.Theme import APP_STYLESHEET
from gui.core.styles.DialogStyles import DIALOG_STYLESHEET

# Maximum number of programs the user may select at once.
MAX_PROGRAMS = 5


class _ProgramCard(QFrame):
    """A single clickable program card with a selected / unselected state."""

    def __init__(self, program_id: str, display_name: str, on_toggle, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("prog-card")
        self.program_id = program_id
        self._selected = False
        self._on_toggle = on_toggle
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Square check-box indicator on the left, drawn purely with styles.
        self._box = QLabel("")
        self._box.setObjectName("prog-card-box")
        self._box.setFixedSize(20, 20)
        self._box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._box)

        # Program id (small, muted) above the program name.
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        self._id_lbl = QLabel(program_id)
        self._id_lbl.setObjectName("prog-card-id")
        self._name_lbl = QLabel(display_name)
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setObjectName("prog-card-name")
        text_col.addWidget(self._id_lbl)
        text_col.addWidget(self._name_lbl)
        layout.addLayout(text_col, stretch=1)

        self._apply_styles()

    def _apply_styles(self) -> None:
        """Apply dynamic property for styling and force repaint."""
        val_str = "true" if self._selected else "false"
        self.setProperty("selected", val_str)
        self._box.setProperty("selected", val_str)
        self._id_lbl.setProperty("selected", val_str)
        self._name_lbl.setProperty("selected", val_str)

        # For check-box indicator text
        if self._selected:
            self._box.setText("✓")
        else:
            self._box.setText("")

        self.style().unpolish(self)
        self.style().polish(self)
        self._box.style().unpolish(self._box)
        self._box.style().polish(self._box)
        self._id_lbl.style().unpolish(self._id_lbl)
        self._id_lbl.style().polish(self._id_lbl)
        self._name_lbl.style().unpolish(self._name_lbl)
        self._name_lbl.style().polish(self._name_lbl)

    def set_selected(self, value: bool) -> None:
        """Update the selection state and refresh styles."""
        self._selected = value
        self._apply_styles()

    def mousePressEvent(self, event) -> None:
        """Delegate the actual toggle decision to the dialog so it can enforce the maximum-selection limit before flipping the card state."""
        self._on_toggle(self.program_id)


# Modal popup showing all programs as a clickable grid (no scrolling)
class ProgramSelectorDialog(QDialog):

    def __init__(self, programs_vm, preselected_ids: List[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Study Programs")
        self.setModal(True)
        self.setMinimumWidth(720)
        self.setStyleSheet(APP_STYLESHEET + DIALOG_STYLESHEET)

        # Selection state owned by the dialog. Start from the caller's choice.
        self._selected: List[str] = list(preselected_ids)
        self._cards: Dict[str, _ProgramCard] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("dialog-card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(16)

        # ── Header: title + hint on the left, live counter on the right ──
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Study Programs")
        title.setObjectName("dialog-title")
        hint = QLabel(f"Tap a card to select. You can pick up to {MAX_PROGRAMS} programs.")
        hint.setObjectName("dialog-hint")
        title_col.addWidget(title)
        title_col.addWidget(hint)
        header_row.addLayout(title_col)
        header_row.addStretch()

        self._counter = QLabel()
        self._counter.setObjectName("dialog-counter")
        header_row.addWidget(self._counter, alignment=Qt.AlignmentFlag.AlignTop)
        card_layout.addLayout(header_row)

        # ── Program grid: two columns, every program visible at once ──────
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        columns = 2
        for index, vm in enumerate(programs_vm):
            prog_card = _ProgramCard(vm.program_id, vm.display_name, self._toggle)
            prog_card.set_selected(vm.program_id in self._selected)
            self._cards[vm.program_id] = prog_card
            row = index // columns
            col = index % columns
            grid.addWidget(prog_card, row, col)
        card_layout.addLayout(grid)

        # ── Button row: Cancel + Select, bottom-right ─────────────────────
        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dialog-cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        select_btn = QPushButton("Select")
        select_btn.setObjectName("dialog-select")
        select_btn.clicked.connect(self.accept)
        button_row.addWidget(select_btn)

        card_layout.addLayout(button_row)
        outer.addWidget(card)

        self._refresh_counter()

    # ── Selection logic ─────────────────────────────────────────────────

    def _toggle(self, program_id: str) -> None:
        """Select or deselect a program, enforcing the maximum-selection limit."""
        if program_id in self._selected:
            self._selected.remove(program_id)
            self._cards[program_id].set_selected(False)
        else:
            if len(self._selected) >= MAX_PROGRAMS:
                QMessageBox.warning(
                    self,
                    "Selection Limit Reached",
                    f"You can select at most {MAX_PROGRAMS} programs.\n"
                    "Deselect one before adding another.",
                )
                return
            self._selected.append(program_id)
            self._cards[program_id].set_selected(True)
        self._refresh_counter()

    def _refresh_counter(self) -> None:
        """Update the "N / MAX" counter pill in the header."""
        self._counter.setText(f"{len(self._selected)} / {MAX_PROGRAMS} selected")

    def selected_ids(self) -> List[str]:
        """Return the program IDs currently selected in the dialog."""
        return list(self._selected)