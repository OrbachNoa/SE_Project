"""Modal dialog for choosing which criteria the clustering groups by.

The user ticks any subset of the criteria the engine supports and presses Apply;
the overview presenter then rebuilds the families on exactly that selection. This
is the manual alternative to the free-text (LLM) grouping request.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.logic.clustering.CriterionDisplay import (
    SELECTABLE_CRITERIA,
    criterion_summary,
    label as criterion_label,
)


class CriteriaSelectionDialog(QDialog):
    """Checklist of every supported criterion, pre-ticked with the active set."""

    def __init__(self, current: Optional[List[str]] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose clustering criteria")
        self.setModal(True)
        self.setMinimumWidth(440)

        current_set = set(current or [])
        self._boxes = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        intro = QLabel("Select the criteria to group the schedules by, then press Apply.")
        intro.setWordWrap(True)
        root.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)
        col.setAlignment(Qt.AlignmentFlag.AlignTop)

        for criterion in SELECTABLE_CRITERIA:
            box = QCheckBox(criterion_label(criterion))
            box.setChecked(criterion in current_set)
            summary = criterion_summary(criterion)
            if summary:
                box.setToolTip(summary)
            self._boxes[criterion] = box
            col.addWidget(box)

        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("btn-secondary")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        buttons.addWidget(apply_btn)
        root.addLayout(buttons)

    def _on_apply(self) -> None:
        if not self.selected_criteria():
            QMessageBox.information(
                self, "Choose clustering criteria", "Select at least one criterion."
            )
            return
        self.accept()

    def selected_criteria(self) -> List[str]:
        """The criterion ids currently ticked, in the dialog's display order."""
        return [criterion for criterion, box in self._boxes.items() if box.isChecked()]
