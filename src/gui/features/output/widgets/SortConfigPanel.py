"""
SortConfigPanel — modal settings panel for schedule sorting criteria priority.

One row per criterion. A checkbox toggles the criterion on/off. Enabled
criteria can be reordered using Up/Down buttons to set primary/secondary priority.
Clicking "Apply" emits the ordered list of enabled criterion_ids. Clicking
"Cancel" closes the dialog without changes. Clicking "Reset" enables all
criteria in their default order.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget
)

from gui.core.styles.Theme import APP_STYLESHEET
from gui.core.styles.DialogStyles import DIALOG_STYLESHEET
from gui.core.styles.SortConfigPanelStyles import SORT_CONFIG_PANEL_STYLESHEET

from gui.common.components.SortRow import SortRow

from src.logic.comparators.MinMandatoryGapComparator import MinMandatoryGapComparator
from src.logic.comparators.AvgAllCoursesGapComparator import AvgAllCoursesGapComparator
from src.logic.comparators.MaxElectiveConflictsComparator import MaxElectiveConflictsComparator
from src.logic.comparators.MandatorySpanComparator import MandatorySpanComparator
from src.logic.comparators.MaxExamsPerDayComparator import MaxExamsPerDayComparator
from src.logic.comparators.ScheduleScorer import ALL_CRITERIA

COMPARATORS = [
    MinMandatoryGapComparator,
    AvgAllCoursesGapComparator,
    MaxElectiveConflictsComparator,
    MandatorySpanComparator,
    MaxExamsPerDayComparator,
]
LABELS = {c.criterion_id: c.label for c in COMPARATORS}


class SortConfigPanel(QDialog):
    """Modal dialog for ordering and enabling/disabling sorting criteria."""

    config_changed = pyqtSignal(list)

    def __init__(self, current_priority: List[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sort Configuration")
        self.setModal(True)
        self.setMinimumWidth(540)
        self.setStyleSheet(APP_STYLESHEET + DIALOG_STYLESHEET + SORT_CONFIG_PANEL_STYLESHEET)
        self.setAcceptDrops(True)
        self._dragged_row: SortRow | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("dialog-card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 24, 26, 22)
        card_layout.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title = QLabel("Sort Configuration")
        title.setObjectName("dialog-title")
        hint = QLabel(
            "Enable criteria and reorder them by priority. "
            "The top active rule acts as primary sort; subsequent rules break ties."
        )
        hint.setObjectName("dialog-hint")
        hint.setWordWrap(True)
        title_col.addWidget(title)
        title_col.addWidget(hint)
        header_row.addLayout(title_col, stretch=1)
        
        self.rules_badge = QLabel("5 rules")
        self.rules_badge.setObjectName("dialog-counter")
        header_row.addWidget(self.rules_badge, alignment=Qt.AlignmentFlag.AlignTop)
        card_layout.addLayout(header_row)

        # ── Sorting rows container ────────────────────────────────────────
        self.rows_container = QWidget()
        self.rows_container.setObjectName("sort-rows-container")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(4, 4, 4, 4)
        self.rows_layout.setSpacing(10)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Build list of rows. Show current priority list items first, then remaining.
        current_priority = [cid for cid in current_priority if cid in ALL_CRITERIA]
        remaining = [cid for cid in ALL_CRITERIA if cid not in current_priority]
        ordered_criteria = current_priority + remaining

        self._rows: List[SortRow] = []
        for cid in ordered_criteria:
            enabled = cid in current_priority
            label = LABELS.get(cid, cid)
            row_widget = SortRow(cid, label, enabled, self)
            self._rows.append(row_widget)
            self.rows_layout.addWidget(row_widget)

        card_layout.addWidget(self.rows_container)

        # ── Action Buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("dialog-cancel")
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dialog-cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("dialog-select")
        apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(apply_btn)

        card_layout.addLayout(btn_row)
        outer.addWidget(card)

        # Wire Up/Down button clicks
        for row in self._rows:
            row.up_btn.clicked.connect(self._move_row_up_sender)
            row.down_btn.clicked.connect(self._move_row_down_sender)

        self.refresh_rows()

    def _move_row_up_sender(self) -> None:
        sender = self.sender()
        for i, row in enumerate(self._rows):
            if row.up_btn == sender:
                self._move_row_up(i)
                break

    def _move_row_down_sender(self) -> None:
        sender = self.sender()
        for i, row in enumerate(self._rows):
            if row.down_btn == sender:
                self._move_row_down(i)
                break

    def _move_row_up(self, index: int) -> None:
        if index <= 0 or index >= len(self._rows):
            return
        self._rows[index], self._rows[index - 1] = self._rows[index - 1], self._rows[index]
        self.refresh_rows()

    def _move_row_down(self, index: int) -> None:
        if index < 0 or index >= len(self._rows) - 1:
            return
        self._rows[index], self._rows[index + 1] = self._rows[index + 1], self._rows[index]
        self.refresh_rows()

    def refresh_rows(self) -> None:
        """Refreshes the layout order, priority rank badges, and button states."""
        # Temporarily detach widgets from layout
        for row in self._rows:
            self.rows_layout.removeWidget(row)

        # Re-add in current list order and refresh priority badges
        enabled_count = 0
        for i, row in enumerate(self._rows):
            self.rows_layout.addWidget(row)

            # Determine button enabled state (only enabled rows can be moved)
            row.up_btn.setEnabled(i > 0 and row.is_enabled())
            row.down_btn.setEnabled(i < len(self._rows) - 1 and row.is_enabled())

            if row.is_enabled():
                enabled_count += 1
                row.set_badge(enabled_count)
            else:
                row.clear_badge()

    def _reset(self) -> None:
        """Resets the criteria list to default ALL_CRITERIA order, with all enabled."""
        # Remove existing widgets
        for row in self._rows:
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

        # Build in default order
        for cid in ALL_CRITERIA:
            label = LABELS.get(cid, cid)
            row_widget = SortRow(cid, label, False, self)
            self._rows.append(row_widget)
            self.rows_layout.addWidget(row_widget)

        # Reconnect buttons
        for row in self._rows:
            row.up_btn.clicked.connect(self._move_row_up_sender)
            row.down_btn.clicked.connect(self._move_row_down_sender)

        self.refresh_rows()

    def _apply(self) -> None:
        """Builds the priority list of enabled criterion_ids and emits it."""
        priority_list = [row.criterion_id for row in self._rows if row.is_enabled()]
        self.config_changed.emit(priority_list)
        self.accept()

    def start_row_drag(self, row: SortRow) -> None:
        self._dragged_row = row

    def end_row_drag(self) -> None:
        self._dragged_row = None

    def dragEnterEvent(self, event) -> None:
        if self._dragged_row and event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._dragged_row and event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        if not self._dragged_row:
            event.ignore()
            return
            
        pos = event.position().toPoint()
        target_index = 0
        for i, row in enumerate(self._rows):
            row_top_y = row.mapTo(self, QPoint(0, 0)).y()
            row_center_y = row_top_y + row.height() // 2
            if pos.y() > row_center_y:
                target_index = i + 1

        current_index = self._rows.index(self._dragged_row)
        if current_index != target_index:
            self._rows.remove(self._dragged_row)
            if target_index > current_index:
                self._rows.insert(target_index - 1, self._dragged_row)
            else:
                self._rows.insert(target_index, self._dragged_row)
            self.refresh_rows()
            
        event.acceptProposedAction()

