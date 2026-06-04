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

# Maximum number of programs the user may select at once.
MAX_PROGRAMS = 5


class _ProgramCard(QFrame):
    """A single clickable program card with a selected / unselected state."""

    SELECTED_STYLE = (
        "QFrame#prog-card { background-color: #EAF4FA; border: 2px solid #3E89BD;"
        " border-radius: 12px; }"
    )
    DEFAULT_STYLE = (
        "QFrame#prog-card { background-color: #FFFFFF; border: 1px solid #E2E8F0;"
        " border-radius: 12px; }"
        "QFrame#prog-card:hover { border-color: #CBD5E1; }"
    )

    def __init__(self, program_id: str, display_name: str, on_toggle, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("prog-card")
        self.program_id = program_id
        self._selected = False
        self._on_toggle = on_toggle
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self.DEFAULT_STYLE)
        self.setMinimumHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Square check-box indicator on the left, drawn purely with styles.
        self._box = QLabel("")
        self._box.setFixedSize(20, 20)
        self._box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_box_style()
        layout.addWidget(self._box)

        # Program id (small, muted) above the program name.
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        self._id_lbl = QLabel(program_id)
        self._id_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent; border: none;")
        self._name_lbl = QLabel(display_name)
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setStyleSheet("color: #334155; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        text_col.addWidget(self._id_lbl)
        text_col.addWidget(self._name_lbl)
        layout.addLayout(text_col, stretch=1)

    def _apply_box_style(self) -> None:
        """Repaint the square indicator to match the current selection state."""
        if self._selected:
            self._box.setText("✓")
            self._box.setStyleSheet(
                "color: #FFFFFF; background: #3E89BD; border: 2px solid #3E89BD;"
                "border-radius: 6px; font-weight: bold; font-size: 12px;"
            )
        else:
            self._box.setText("")
            self._box.setStyleSheet(
                "background: #FFFFFF; border: 2px solid #CBD5E1; border-radius: 6px;"
            )

    def set_selected(self, value: bool) -> None:
        """Update the visual state of the card (border, background, check box)."""
        self._selected = value
        self.setStyleSheet(self.SELECTED_STYLE if value else self.DEFAULT_STYLE)
        self._apply_box_style()
        if value:
            self._name_lbl.setStyleSheet("color: #143D30; font-size: 13px; font-weight: 700; background: transparent; border: none;")
            self._id_lbl.setStyleSheet("color: #3E89BD; font-size: 11px; font-weight: 600; background: transparent; border: none;")
        else:
            self._name_lbl.setStyleSheet("color: #334155; font-size: 13px; font-weight: 600; background: transparent; border: none;")
            self._id_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent; border: none;")

    def mousePressEvent(self, event) -> None:
        # Delegate the actual toggle decision to the dialog so it can enforce
        # the maximum-selection limit before flipping the card state.
        self._on_toggle(self.program_id)


# Local stylesheet for the dialog chrome (title, buttons, card container).
_DIALOG_STYLE = """
QDialog {
    background-color: #FAFAFA;
}
QFrame#dialog-card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 18px;
}
QLabel#dialog-title {
    color: #143D30;
    font-size: 17px;
    font-weight: 700;
    background: transparent;
}
QLabel#dialog-hint {
    color: #64748B;
    font-size: 12px;
    background: transparent;
}
QLabel#dialog-counter {
    color: #64748B;
    font-size: 12px;
    font-weight: 600;
    background: #F1F5F9;
    border-radius: 11px;
    padding: 4px 12px;
}
QPushButton#dialog-select {
    background-color: #143D30;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 10px 26px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#dialog-select:hover {
    background-color: #0F2D23;
}
QPushButton#dialog-cancel {
    background-color: #FFFFFF;
    color: #64748B;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 13px;
}
QPushButton#dialog-cancel:hover {
    background-color: #F1F5F9;
    border-color: #CBD5E1;
}
"""


class ProgramSelectorDialog(QDialog):
    """Modal popup showing all programs as a clickable grid (no scrolling)."""

    def __init__(self, programs_vm, preselected_ids: List[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Study Programs")
        self.setModal(True)
        self.setMinimumWidth(720)
        self.setStyleSheet(_DIALOG_STYLE)

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