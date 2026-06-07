""" ProgramSelectorWidget
PyQt5 widget that displays all available study programs and lets the user
select up to 5 of them.
"""

from typing import List

# Unified and cleaned imports for PyQt6 infrastructure
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal helper: one row in the program list

class _ProgramRow(QWidget):
    """A single unified clickable card representing one study program."""

    # Bar-Ilan sky-blue selection, neutral default, slate hover
    SELECTED_STYLE = (
        "background-color: #FAF5EC; border: 1px solid #3396ad; "
        "border-radius: 8px; padding: 0px;"
    )
    DEFAULT_STYLE = (
        "background-color: #FFFFFF; border: 1px solid #E2E8F0; "
        "border-radius: 8px; padding: 0px;"
    )
    HOVER_STYLE = (
        "background-color: #F1F5F9; border: 1px solid #CBD5E1; "
        "border-radius: 8px; padding: 0px;"
    )

    def __init__(self, program_id: str, display_name: str, parent=None):
        super().__init__(parent)
        self.program_id = program_id
        self.display_name = display_name
        self._selected = False
        # Fixed height ensures uniform card size across the list
        self.setFixedHeight(48)

        # Single horizontal layout for the card contents
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # Program ID — narrow fixed column, subdued colour
        self._id_label = QLabel(program_id)
        self._id_label.setFixedWidth(48)
        self._id_label.setFont(QFont("Segoe UI", 11))
        self._id_label.setStyleSheet("color: #64748B; background: transparent;")
        layout.addWidget(self._id_label)

        # Program name — expands to fill remaining space
        self._name_label = QLabel(display_name)
        self._name_label.setFont(QFont("Segoe UI", 12))
        self._name_label.setStyleSheet("color: #334155; background: transparent;")
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._name_label)

        # Check mark shown at right edge when the row is selected; hidden by default
        self._check_label = QLabel("")
        self._check_label.setFixedWidth(20)
        self._check_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._check_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._check_label)

        # Setup base container styling
        self.setStyleSheet(self.DEFAULT_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_selected(self, value: bool) -> None:
        """Flips the entire card color scheme and check mark on selection toggle."""
        self._selected = value
        if value:
            self.setStyleSheet(self.SELECTED_STYLE)
            self._id_label.setStyleSheet("color: #3396ad; font-weight: 600; background: transparent;")
            self._name_label.setStyleSheet("color: #3E352F; font-weight: 600; background: transparent;")
            self._check_label.setText("✓")
            self._check_label.setStyleSheet("color: #3396ad; font-weight: bold; background: transparent;")
        else:
            self.setStyleSheet(self.DEFAULT_STYLE)
            self._id_label.setStyleSheet("color: #64748B; background: transparent;")
            self._name_label.setStyleSheet("color: #334155; background: transparent;")
            self._check_label.setText("")
            self._check_label.setStyleSheet("background: transparent;")

    # Keep mouse and hover events exactly as they were below...
    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self._selected:
            self.setStyleSheet(self.HOVER_STYLE)

    def leaveEvent(self, event):
        self.setStyleSheet(self.SELECTED_STYLE if self._selected else self.DEFAULT_STYLE)


# Main widget

class ProgramSelectorWidget(QWidget):
    """
    Displays all available programs in a scrollable list and lets the user
    select up to MAX_PROGRAMS of them.

    Public API
   ------
    render(programs_vm)         Populate / refresh the list.
    get_selected() -> List[str] Return the currently selected program IDs.
    toggle(program_id)          Select or deselect a program by ID.
    """

    # Emitted whenever the selection changes; carries the new selection count.
    selection_changed = pyqtSignal(int)

    MAX_PROGRAMS: int = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        # ordered list of selected IDs
        self._selected: List[str] = []
        # program_id -> _ProgramRow
        self._rows: dict = {}

        self._build_ui()

    # UI construction

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Title is intentionally absent here — the parent card in input_screen.py
        # provides the "📚  Study Programs" heading so it is not duplicated.

        # Scrollable program list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(180)

        # Thin borderless scrollbar that blends into the card background
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { width: 4px; background: transparent; } "
            "QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 2px; } "
            "QScrollBar::handle:vertical:hover { background: #94A3B8; }"
        )

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(6, 6, 6, 6)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_container)
        root.addWidget(scroll)

        # Counter label
        self._counter_label = QLabel(f"Selected: 0 / {self.MAX_PROGRAMS}")
        self._counter_label.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        root.addWidget(self._counter_label)

    # Public API

    def render(self, programs_vm) -> None:
        """
        Populate the widget from a list of ProgramViewModel objects.

        programs_vm: List[ProgramViewModel]
            Each item must have:
              .program_id: str
              .display_name: str
        """
        # Remove all widgets except the trailing stretch
        for row in self._rows.values():
            self._list_layout.removeWidget(row)
            row.deleteLater()
        # Clear existing rows
        self._rows.clear()
        self._selected.clear()

        # Add a row per program
        for vm in programs_vm:
            row = _ProgramRow(vm.program_id, vm.display_name)
            row.mousePressEvent = self._make_click_handler(vm.program_id, row)
            self._rows[vm.program_id] = row
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

        self._refresh_summary()
        self._refresh_counter()

    def get_selected(self) -> List[str]:
        """Return the list of currently selected program IDs (in selection order)."""
        return list(self._selected)

    def toggle(self, program_id: str) -> None:
        """Select or deselect a program by ID. Enforces MAX_PROGRAMS limit."""
        if program_id in self._selected:
            self._deselect(program_id)
        else:
            self._try_select(program_id)

    # Internal helpers

    def _make_click_handler(self, program_id: str, row: _ProgramRow):
        """Return a mousePressEvent function bound to the given program."""

        def handler(event):
            _ProgramRow.mousePressEvent(row, event)
            self.toggle(program_id)

        return handler

    def _try_select(self, program_id: str) -> None:
        if program_id not in self._rows:
            return
        if len(self._selected) >= self.MAX_PROGRAMS:
            QMessageBox.warning(
                self,
                "Selection Limit Reached",
                f"Cannot select more than {self.MAX_PROGRAMS} programs.\n"
                "Please deselect an existing program before adding a new one.",
            )
            return
        self._selected.append(program_id)
        self._rows[program_id].set_selected(True)
        self._refresh_summary()
        self._refresh_counter()
        self.selection_changed.emit(len(self._selected))

    def _deselect(self, program_id: str) -> None:
        if program_id not in self._selected:
            return
        self._selected.remove(program_id)
        self._rows[program_id].set_selected(False)
        self._refresh_summary()
        self._refresh_counter()
        self.selection_changed.emit(len(self._selected))

    def _refresh_counter(self) -> None:
        count = len(self._selected)
        self._counter_label.setText(f"Selected: {count} / {self.MAX_PROGRAMS}")
        color = "#dc2626" if count == self.MAX_PROGRAMS else "#64748B"
        self._counter_label.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

    def _refresh_summary(self) -> None:
        pass

    def _clear_all(self) -> None:
        for prog_id in list(self._selected):
            self._deselect(prog_id)
