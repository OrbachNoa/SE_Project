from __future__ import annotations

from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QCheckBox, QApplication
)


class SortRow(QFrame):
    """Visual row for a single sorting criterion."""

    def __init__(self, criterion_id: str, label: str, enabled: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.criterion_id = criterion_id
        self.setObjectName("sort-row")
        self.setMinimumHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)

        # 1. Drag handle decoration
        self.handle = QLabel("⠿")
        self.handle.setObjectName("sort-drag-handle")
        self.handle.setFixedWidth(20)
        layout.addWidget(self.handle)

        # 2. Priority rank badge
        self.badge = QLabel()
        self.badge.setObjectName("sort-priority-badge")
        self.badge.setFixedSize(24, 24)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.badge)

        # 3. Label text
        self.label = QLabel(label)
        self.label.setObjectName("sort-label")
        self.label.setWordWrap(True)
        layout.addWidget(self.label, stretch=1)

        # 4. Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(enabled)
        layout.addWidget(self.checkbox)

        # 5. Up/Down buttons
        self.btn_layout = QVBoxLayout()
        self.btn_layout.setSpacing(2)

        self.up_btn = QPushButton("▲")
        self.up_btn.setObjectName("settings-step")
        self.up_btn.setFixedSize(24, 18)

        self.down_btn = QPushButton("▼")
        self.down_btn.setObjectName("settings-step")
        self.down_btn.setFixedSize(24, 18)

        self.btn_layout.addWidget(self.up_btn)
        self.btn_layout.addWidget(self.down_btn)
        layout.addLayout(self.btn_layout)

        # Connect toggling to local update
        self.checkbox.toggled.connect(self._on_toggled)
        self._update_style(enabled)

    def _on_toggled(self, checked: bool) -> None:
        self._update_style(checked)
        # Notify the dialog to refresh badges and button states
        dialog = self.window()
        if hasattr(dialog, "refresh_rows"):
            dialog.refresh_rows()

    def _update_style(self, checked: bool) -> None:
        self.setProperty("active", "true" if checked else "false")
        if checked:
            self.handle.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.handle.setCursor(Qt.CursorShape.ArrowCursor)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.is_enabled():
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self.is_enabled() and hasattr(self, "_drag_start_pos"):
            if (event.position().toPoint() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self._start_drag(event)
                return
        super().mouseMoveEvent(event)

    def _start_drag(self, event) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.criterion_id)
        drag.setMimeData(mime)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())
        
        dialog = self.window()
        if hasattr(dialog, "start_row_drag"):
            dialog.start_row_drag(self)
            
        drag.exec(Qt.DropAction.MoveAction)
        
        if hasattr(dialog, "end_row_drag"):
            dialog.end_row_drag()

    def set_badge(self, rank: int) -> None:
        """Sets the priority badge value and styling."""
        self.badge.setText(str(rank))
        self.badge.setProperty("has_rank", "true")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)

    def clear_badge(self) -> None:
        """Clears the priority badge value."""
        self.badge.setText("")
        self.badge.setProperty("has_rank", "false")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)

    def is_enabled(self) -> bool:
        return self.checkbox.isChecked()
