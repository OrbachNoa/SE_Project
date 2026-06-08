"""Action bar widget containing file loader triggers, import mode toggle, and scheduler run controls."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QRadioButton, QButtonGroup, QWidget
from PyQt6.QtCore import Qt        
from PyQt6.QtGui import QIcon
from gui.common.helpers import create_scaled_pixmap, create_vertical_divider

# Action bar widget containing file loader triggers, import mode toggle, and scheduler run controls.
class ActionBarWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setObjectName("action-bar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        # ----- File loader triggers -----
        # Courses loader button
        self.courses_load_btn = QPushButton("  Load Courses")
        self.courses_load_btn.setObjectName("btn-secondary")
        self.courses_load_btn.setFixedHeight(36)
        try:
            courses_pix = create_scaled_pixmap(self, "data/assets/courseIcon.png", 18)
            self.courses_load_btn.setIcon(QIcon(courses_pix))
        except Exception:
            self.courses_load_btn.setText("📂  Load Courses")
        layout.addWidget(self.courses_load_btn)

        # Periods loader button
        self.periods_load_btn = QPushButton("  Load Periods")
        self.periods_load_btn.setObjectName("btn-secondary")
        self.periods_load_btn.setFixedHeight(36)
        try:
            periods_pix = create_scaled_pixmap(self, "data/assets/periodIcon.png", 18)
            self.periods_load_btn.setIcon(QIcon(periods_pix))
        except Exception:
            self.periods_load_btn.setText("📅  Load Periods")
        layout.addWidget(self.periods_load_btn)

        # ----- Import mode selectors -----
        v_sep = create_vertical_divider(self)
        layout.addWidget(v_sep)
        mode_label = QLabel("Mode:")
        mode_label.setObjectName("mode-label")
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

        # ----- Results group buttons -----
        # Generate button
        self.generate_btn = QPushButton("▶  Generate Schedule")
        self.generate_btn.setObjectName("btn-primary")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setFixedHeight(40)
        layout.addWidget(self.generate_btn)
        # Cancel button
        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setObjectName("btn-danger")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedHeight(40)
        layout.addWidget(self.cancel_btn)
        # View results button
        self.view_results_btn = QPushButton("   View Results")
        self.view_results_btn.setObjectName("btn-secondary")
        self.view_results_btn.setVisible(False)
        self.view_results_btn.setFixedHeight(40)
        try:
            view_pix = create_scaled_pixmap(self, "data/assets/verify.png", 18)
            self.view_results_btn.setIcon(QIcon(view_pix))
        except Exception:
            self.view_results_btn.setText("👁  View Results")
        layout.addWidget(self.view_results_btn)
