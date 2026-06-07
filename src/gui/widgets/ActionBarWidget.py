"""Action bar widget containing file loader triggers, import mode toggle, and scheduler run controls."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QRadioButton, QButtonGroup, QWidget
from PyQt6.QtCore import Qt


class ActionBarWidget(QFrame):
    """Encapsulates the load triggers, import settings and computation controls panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(
            "QFrame { background: white; border-bottom: 1px solid #E2E8F0; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        # File loading triggers
        self.courses_load_btn = QPushButton("📂  Load Courses")
        self.courses_load_btn.setObjectName("btn-secondary")
        self.courses_load_btn.setFixedHeight(36)
        layout.addWidget(self.courses_load_btn)

        self.periods_load_btn = QPushButton("📅  Load Periods")
        self.periods_load_btn.setObjectName("btn-secondary")
        self.periods_load_btn.setFixedHeight(36)
        layout.addWidget(self.periods_load_btn)

        # Vertical divider between load buttons and the mode selector.
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.Shape.VLine)
        v_sep.setFixedHeight(24)
        v_sep.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(v_sep)

        # Import mode selectors
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("color: #64748B; background: transparent;")
        self.mode_replace = QRadioButton("Replace")
        self.mode_replace.setChecked(True)
        self.mode_update = QRadioButton("Update")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_replace)
        self.mode_group.addButton(self.mode_update)

        layout.addWidget(mode_label)
        layout.addWidget(self.mode_replace)
        layout.addWidget(self.mode_update)
        layout.addStretch()

        # Generate / Cancel button pairing
        self.generate_btn = QPushButton("▶  Generate Schedule")
        self.generate_btn.setObjectName("btn-primary")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setFixedHeight(40)
        layout.addWidget(self.generate_btn)

        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setObjectName("btn-danger")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedHeight(40)
        layout.addWidget(self.cancel_btn)
