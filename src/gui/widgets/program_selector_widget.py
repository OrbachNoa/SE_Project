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
    """A single clickable row representing one study program."""

    SELECTED_STYLE = (
        "background-color: #dbeafe; border: 2px solid #2563eb; "
        "border-radius: 6px; padding: 4px;"
    )
    DEFAULT_STYLE = (
        "background-color: #f8fafc; border: 2px solid #e2e8f0; "
        "border-radius: 6px; padding: 4px;"
    )
    HOVER_STYLE = (
        "background-color: #eff6ff; border: 2px solid #93c5fd; "
        "border-radius: 6px; padding: 4px;"
    )

    def __init__(self, program_id: str, display_name: str, parent=None):
        super().__init__(parent)
        self.program_id = program_id
        self.display_name = display_name
        self._selected = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        # Checkbox indicator
        self._check_label = QLabel("☐")
        self._check_label.setFixedWidth(24)
        self._check_label.setFont(QFont("Arial", 14))
        layout.addWidget(self._check_label)

        # ID label
        id_label = QLabel(program_id)
        id_label.setFixedWidth(64)
        id_label.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        id_label.setStyleSheet("color: #475569;")
        layout.addWidget(id_label)

        # Name label
        self._name_label = QLabel(display_name)
        self._name_label.setFont(QFont("Arial", 11))
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._name_label)

        self.setStyleSheet(self.DEFAULT_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # Selection state

    @property
    def selected(self) -> bool:
        return self._selected

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self._check_label.setText("☑" if value else "☐")
        self.setStyleSheet(self.SELECTED_STYLE if value else self.DEFAULT_STYLE)

    # Mouse events -> parent handles via mousePressEvent override

    def mousePressEvent(self, event):  # noqa: N802
        """Bubble up so ProgramSelectorWidget can intercept the click."""
        super().mousePressEvent(event)

    # PyQt6 enter event requires type hints or distinct override syntax
    def enterEvent(self, event):
        if not self._selected:
            self.setStyleSheet(self.HOVER_STYLE)

    # PyQt6 leave event override for returning styling to defaults
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
        scroll.setFixedHeight(320)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #e2e8f0; border-radius: 8px; }")

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

        # Summary panel
        summary_frame = QFrame()
        summary_frame.setFrameShape(QFrame.Shape.StyledPanel)
        summary_frame.setStyleSheet(
            "QFrame { background: #f0fdf4; border: 1px solid #16a34a; border-radius: 8px; padding: 4px; }"
        )
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(8, 6, 8, 6)
        summary_layout.setSpacing(2)

        summary_title = QLabel("Selected Programs:")
        summary_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        summary_layout.addWidget(summary_title)

        self._summary_layout = QVBoxLayout()
        self._summary_layout.setSpacing(1)
        summary_layout.addLayout(self._summary_layout)

        self._empty_label = QLabel("(no program selected)")
        self._empty_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self._summary_layout.addWidget(self._empty_label)

        root.addWidget(summary_frame)

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
        # Clear old summary entries
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._selected:
            self._empty_label = QLabel("(no program selected)")
            self._empty_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
            self._summary_layout.addWidget(self._empty_label)
            return

        for prog_id in self._selected:
            row = self._rows.get(prog_id)
            if row is None:
                continue
            text = f"• {row.display_name}  [{prog_id}]"
            lbl = QLabel(text)
            lbl.setFont(QFont("Arial", 10))
            lbl.setStyleSheet("color: #166534;")
            self._summary_layout.addWidget(lbl)

        # Add a "clear all" button
        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet(
            "QPushButton { color: #dc2626; background: transparent; "
            "border: none; font-size: 10px; text-decoration: underline; }"
            "QPushButton:hover { color: #991b1b; }"
        )
        clear_btn.setFixedHeight(20)
        clear_btn.clicked.connect(self._clear_all)
        self._summary_layout.addWidget(clear_btn)

    def _clear_all(self) -> None:
        for prog_id in list(self._selected):
            self._deselect(prog_id)
