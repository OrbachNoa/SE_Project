"""A single family card on the cluster overview screen.

Shows the family's size, a one-line description, its average feature profile
(each criterion emphasised on its own row), and two actions: open the family to
browse its schedules, and toggle it for side-by-side comparison.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.application.viewmodels.ClusterViewModel import ClusterCardViewModel


class ClusterCardWidget(QFrame):
    """Displays one family summary; emits open / compare-toggle signals."""

    open_requested = pyqtSignal(int)            # cluster_id
    compare_toggled = pyqtSignal(int, bool)     # cluster_id, selected

    def __init__(self, card: ClusterCardViewModel, parent=None) -> None:
        super().__init__(parent)
        self._cluster_id = card.cluster_id
        self.setObjectName("card")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Title + size.
        title = QLabel(f"<b>{card.title}</b>")
        title.setStyleSheet("font-size: 15px;")
        layout.addWidget(title)

        if card.sampled:
            size_text = f"{card.size} schedules  (~{card.estimated_population_size} of full set)"
        else:
            size_text = f"{card.size} schedules"
        size_label = QLabel(size_text)
        size_label.setStyleSheet("color: #0f766e; font-weight: 600;")
        layout.addWidget(size_label)

        # One-line description of the family's character.
        if card.description:
            desc = QLabel(card.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #444; font-style: italic;")
            layout.addWidget(desc)

        # Feature profile (the "archetype" summary): one emphasised row per criterion.
        profile = QFrame()
        grid = QGridLayout(profile)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(3)
        for row, (label, value) in enumerate(card.summary):
            name = QLabel(label)
            name.setStyleSheet("color: #555;")
            val = QLabel(value)
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            val.setStyleSheet("font-weight: 600;")
            grid.addWidget(name, row, 0)
            grid.addWidget(val, row, 1)
        layout.addWidget(profile)

        # Actions.
        actions = QHBoxLayout()
        open_btn = QPushButton("Open ▶")
        open_btn.setObjectName("btn-secondary")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(lambda: self.open_requested.emit(self._cluster_id))

        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setCheckable(True)
        self._compare_btn.setObjectName("btn-ghost")
        self._compare_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compare_btn.toggled.connect(
            lambda checked: self.compare_toggled.emit(self._cluster_id, checked)
        )

        actions.addWidget(open_btn)
        actions.addWidget(self._compare_btn)
        layout.addLayout(actions)

    @property
    def cluster_id(self) -> int:
        return self._cluster_id

    def set_compare_checked(self, checked: bool) -> None:
        """Set the compare toggle without emitting (used to enforce max 2)."""
        self._compare_btn.blockSignals(True)
        self._compare_btn.setChecked(checked)
        self._compare_btn.blockSignals(False)
