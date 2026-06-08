"""Common layout widgets and functional helper wrappers for PySide/PyQt views."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QFileDialog, QWidget
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


def create_divider(parent: QWidget | None = None) -> QFrame:
    """Return a styled 1-pixel horizontal separator line."""
    line = QFrame(parent)
    line.setObjectName("divider")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


def create_vertical_divider(parent: QWidget | None = None, height: int = 24) -> QFrame:
    """Return a styled vertical separator line."""
    line = QFrame(parent)
    line.setObjectName("vertical-divider")
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFixedHeight(height)
    return line


def create_card(parent: QWidget | None = None) -> QFrame:
    """Return a styled card frame (white background, rounded border)."""
    card = QFrame(parent)
    card.setObjectName("card")
    card.setFrameShape(QFrame.Shape.NoFrame)
    return card


def create_scaled_pixmap(parent: QWidget, path: str, height: int) -> QPixmap:
    """Load a pixmap and scale it smoothly based on the parent's device pixel ratio.
    Used to scale images to the correct size for display."""
    pixmap = QPixmap(path)
    dpr = parent.devicePixelRatioF()
    scaled = pixmap.scaledToHeight(int(height * dpr), Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(dpr)
    return scaled


def prompt_open_file(parent: QWidget, title: str, file_filter: str) -> str:
    """Open a standard OS file dialog to select an existing file."""
    path, _ = QFileDialog.getOpenFileName(parent, title, "", file_filter)
    return path


def prompt_save_file(parent: QWidget, title: str, default_name: str, file_filter: str) -> str:
    """Open a standard OS file dialog to select a save destination path."""
    path, _ = QFileDialog.getSaveFileName(parent, title, default_name, file_filter)
    return path
