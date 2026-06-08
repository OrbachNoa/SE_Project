"""Reusable header bar widget containing branding logo and breadcrumb indicators."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from gui.common.helpers import create_scaled_pixmap


class HeaderWidget(QFrame):
    """Reusable gold header branding bar with navigation step tracking indicators."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("header")
        self.setFixedHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(12)

        # Brand logo
        logo_label = QLabel()
        logo_label.setObjectName("header-logo")
        logo_pixmap = create_scaled_pixmap(self, "data/assets/logo.png", 58)
        logo_label.setPixmap(logo_pixmap)
        layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch()
