"""Reusable header bar widget containing branding logo and breadcrumb indicators."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from gui.widgets.Common import create_scaled_pixmap


class HeaderWidget(QFrame):
    """Reusable gold header branding bar with navigation step tracking indicators."""

    def __init__(self, active_step: str = "input", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("header")
        self.setFixedHeight(70)
        self.setStyleSheet("QFrame#header { background: #d4b483; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(12)

        # Brand logo
        logo_label = QLabel()
        logo_label.setStyleSheet("background: transparent;")
        logo_pixmap = create_scaled_pixmap(self, "data/logo.png", 58)
        logo_label.setPixmap(logo_pixmap)
        layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch()

        # Breadcrumbs
        crumb_input = QLabel("Input")
        crumb_sep = QLabel("›")
        crumb_output = QLabel("Output")

        if active_step == "input":
            crumb_input.setStyleSheet("color: #3396ad; font-weight: 600; background: transparent;")
            crumb_sep.setStyleSheet("color: rgba(62, 53, 47, 0.5); background: transparent;")
            crumb_output.setStyleSheet("color: rgba(62, 53, 47, 0.5); background: transparent;")
            crumb_output.setEnabled(False)
        else:
            crumb_input.setStyleSheet("color: rgba(62, 53, 47, 0.5); background: transparent;")
            crumb_input.setEnabled(False)
            crumb_sep.setStyleSheet("color: rgba(62, 53, 47, 0.5); background: transparent;")
            crumb_output.setStyleSheet("color: #3396ad; font-weight: 600; background: transparent;")

        layout.addWidget(crumb_input)
        layout.addWidget(crumb_sep)
        layout.addWidget(crumb_output)
