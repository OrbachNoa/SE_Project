""" ProgramSelectorWidget
PyQt5 widget that displays all available study programs and lets the user
select up to 5 of them.
"""

from typing import List

# Unified and cleaned imports for PyQt6 infrastructure
from PyQt6.QtCore import Qt
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

    SELECTED_STYLE = (
        "background-color: #f0fdf4; border: 1px solid #16a34a; "
        "border-radius: 6px; padding: 0px;"
    )
    DEFAULT_STYLE = (
        "background-color: #ffffff; border: 1px solid #f1f5f9; "
        "border-radius: 6px; padding: 0px;"
    )
    HOVER_STYLE = (
        "background-color: #f8fafc; border: 1px solid #e2e8f0; "
        "border-radius: 6px; padding: 0px;"
    )

    def __init__(self, program_id: str, display_name: str, parent=None):
        super().__init__(parent)
        self.program_id = program_id
        self.display_name = display_name
        self._selected = False

        # Single unified horizontal layout for the entire card
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)

        # 1. Program ID Code Block
        self._id_label = QLabel(program_id)
        self._id_label.setFixedWidth(55)
        self._id_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self._id_label.setStyleSheet("color: #64748b; background: transparent;")
        layout.addWidget(self._id_label)

        # 2. Program Name Label
        self._name_label = QLabel(display_name)
        self._name_label.setFont(QFont("Arial", 11, QFont.Weight.Medium if hasattr(QFont.Weight, 'Medium') else QFont.Weight.Normal))
        self._name_label.setStyleSheet("color: #1e293b; background: transparent;")
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._name_label)

        # Setup base container styling
        self.setStyleSheet(self.DEFAULT_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_selected(self, value: bool) -> None:
        """Flips the entire card color scheme contextually upon selection."""
        self._selected = value
        if value:
            self.setStyleSheet(self.SELECTED_STYLE)
            self._id_label.setStyleSheet("color: #16a34a; font-weight: bold; background: transparent;")
            self._name_label.setStyleSheet("color: #14532d; font-weight: bold; background: transparent;")
        else:
            self.setStyleSheet(self.DEFAULT_STYLE)
            self._id_label.setStyleSheet("color: #64748b; background: transparent;")
            self._name_label.setStyleSheet("color: #334155; background: transparent;")

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

        # Title
        title = QLabel("Select Study Programs (up to 5)")
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        root.addWidget(title)

        # Scrollable program list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(180)

        # Modern minimalist scrollbar styling code block
        scroll.setStyleSheet("""
            QScrollArea { 
                border: 1px solid #e2e8f0; 
                border-radius: 8px; 
                background-color: #ffffff;
            }
            
            /* The vertical scrollbar container */
            QScrollBar:vertical {
                border: none;
                background: #f8fafc;
                width: 8px;
                margin: 4px 2px 4px 2px;
                border-radius: 4px;
            }
            
            /* The draggable handle part */
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 20px;
                border-radius: 4px;
            }
            
            /* Handle color when hovering over it */
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            
            /* Remove the mofos top and bottom arrow buttons entirely */
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
                height: 0px;
            }
        """)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(6, 6, 6, 6)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_container)
        root.addWidget(scroll)

        # Counter label
        self._counter_label = QLabel(f"Selected: 0 / {self.MAX_PROGRAMS}")
        self._counter_label.setStyleSheet("color: #64748b; font-size: 11px;")
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

    def _deselect(self, program_id: str) -> None:
        if program_id not in self._selected:
            return
        self._selected.remove(program_id)
        self._rows[program_id].set_selected(False)
        self._refresh_summary()
        self._refresh_counter()

    def _refresh_counter(self) -> None:
        count = len(self._selected)
        self._counter_label.setText(f"Selected: {count} / {self.MAX_PROGRAMS}")
        color = "#dc2626" if count == self.MAX_PROGRAMS else "#64748b"
        self._counter_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _refresh_summary(self) -> None:
        pass

    def _clear_all(self) -> None:
        for prog_id in list(self._selected):
            self._deselect(prog_id)
