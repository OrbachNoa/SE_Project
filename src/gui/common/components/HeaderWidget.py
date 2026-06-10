"""Reusable header bar widget containing branding logo and breadcrumb indicators."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from gui.common.helpers import create_scaled_pixmap

# Creates the top banner (header) of the application, which usually contains the logo
class HeaderWidget(QFrame):
    """Reusable gold header branding bar with navigation step tracking indicators."""

    # Initializes the header and sets its basic properties
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        
        # Give it a specific name so we can apply custom colors and styles to it later
        self.setObjectName("header")
        
        # Lock the height to exactly 70 pixels so it doesn't stretch or shrink randomly
        self.setFixedHeight(70)

        # Create a horizontal layout to arrange items side-by-side (from left to right)
        layout = QHBoxLayout(self)
        
        # Add some empty space (padding) on the left and right sides so the logo doesn't touch the edge
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(12)

        # Create an empty label container that will eventually hold our logo image
        logo_label = QLabel()
        logo_label.setObjectName("header-logo")
        
        # Load the logo image file from the computer and resize it to fit the header nicely
        logo_pixmap = create_scaled_pixmap(self, "data/assets/logo.png", 58)
        logo_label.setPixmap(logo_pixmap)
        
        # Put the logo into our horizontal layout and make sure it is centered vertically
        layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Add an invisible "spring" that pushes the logo to the left and fills up the rest of the empty space on the right
        layout.addStretch()