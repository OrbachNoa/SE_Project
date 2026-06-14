"""ConstraintsSettingsDialog — modal settings panel for Phase-3 threshold constraints.

One row per constraint. A checkbox toggles the constraint on or off; its
matching spinbox is disabled when the constraint is off. Clicking "Apply"
builds a ConstraintsConfig and fires the on_apply callback. Clicking
"Cancel" closes the dialog without making any change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox, QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from gui.core.styles.Theme import APP_STYLESHEET
from gui.core.styles.DialogStyles import DIALOG_STYLESHEET, SETTINGS_DIALOG_STYLESHEET
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig


@dataclass(frozen=True)
class _ConstraintMeta:
    """Static metadata for one constraint row."""
    label: str
    description: str
    unit: str
    min_k: int
    max_k: int
    default_k: int


_CONSTRAINTS: list[_ConstraintMeta] = [
    _ConstraintMeta(
        label="Min. gap — obligatory exams",
        description="Minimum calendar days between two mandatory exams in the same program-year.",
        unit="days",
        min_k=1, max_k=30, default_k=3,
    ),
    _ConstraintMeta(
        label="Min. gap — all exams",
        description="Minimum calendar days between any two exams (mandatory or elective) in the same program-year.",
        unit="days",
        min_k=1, max_k=30, default_k=2,
    ),
    _ConstraintMeta(
        label="Elective clash cap",
        description="Maximum elective exams from the same program-year allowed on one day.",
        unit="exams / day",
        min_k=0, max_k=10, default_k=2,
    ),
    _ConstraintMeta(
        label="Exam period span",
        description="Minimum days between the first and last mandatory exam in a program-year-moed group.",
        unit="days",
        min_k=1, max_k=60, default_k=7,
    ),
    _ConstraintMeta(
        label="Max exams per day",
        description="Maximum exams from the same program allowed on one day.",
        unit="exams / day",
        min_k=1, max_k=10, default_k=3,
    ),
]


class ConstraintsSettingsDialog(QDialog):
    """Modal dialog for configuring the five Phase-3 threshold constraints."""

    def __init__(
        self,
        on_apply: Callable[[ConstraintsConfig], None],
        current_config: Optional[ConstraintsConfig] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scheduling Constraints")
        self.setModal(True)
        self.setMinimumWidth(680)
        self.setStyleSheet(APP_STYLESHEET + DIALOG_STYLESHEET + SETTINGS_DIALOG_STYLESHEET)

        self._on_apply = on_apply
        # Each entry is (QCheckBox, QSpinBox) for the five constraints in order.
        self._rows: list[Tuple[QCheckBox, QSpinBox]] = []

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
        title = QLabel("Scheduling Constraints")
        title.setObjectName("dialog-title")
        hint = QLabel(
            "Enable a constraint and set its threshold (k). "
            "Disabled constraints are not applied during scheduling."
        )
        hint.setObjectName("dialog-hint")
        hint.setWordWrap(True)
        title_col.addWidget(title)
        title_col.addWidget(hint)
        header_row.addLayout(title_col, stretch=1)
        rules_badge = QLabel("5 rules")
        rules_badge.setObjectName("dialog-counter")
        header_row.addWidget(rules_badge, alignment=Qt.AlignmentFlag.AlignTop)
        card_layout.addLayout(header_row)

        # ── Constraint rows ───────────────────────────────────────────────
        for i, meta in enumerate(_CONSTRAINTS):
            row_widget = self._build_row(meta, current_config, i)
            card_layout.addWidget(row_widget)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
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

    # ── Private helpers ────────────────────────────────────────────────────

    def _build_row(
        self,
        meta: _ConstraintMeta,
        current_config: Optional[ConstraintsConfig],
        index: int,
    ) -> QFrame:
        """Build one constraint row: checkbox, text, spinbox."""
        current_k = self._current_k(current_config, index)
        is_on = current_k is not None

        row = QFrame()
        row.setObjectName("settings-row")
        row.setMinimumHeight(78)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 12, 16, 12)
        row_layout.setSpacing(14)

        # Checkbox that toggles the whole constraint on/off.
        checkbox = QCheckBox()
        checkbox.setChecked(is_on)
        row_layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignTop)

        # Label column: bold name + muted description.
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name_lbl = QLabel(meta.label)
        name_lbl.setObjectName("settings-row-title")
        desc_lbl = QLabel(meta.description)
        desc_lbl.setObjectName("settings-row-desc")
        desc_lbl.setWordWrap(True)
        text_col.addWidget(name_lbl)
        text_col.addWidget(desc_lbl)
        row_layout.addLayout(text_col, stretch=1)

        # Spinbox + unit label on the right.
        spin_col = QHBoxLayout()
        spin_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        spin_col.setSpacing(8)
        spinbox = QSpinBox()
        spinbox.setRange(meta.min_k, meta.max_k)
        spinbox.setValue(current_k if current_k is not None else meta.default_k)
        spinbox.setFixedWidth(62)
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setEnabled(is_on)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        spinbox.lineEdit().setReadOnly(True)
        step_col = QVBoxLayout()
        step_col.setSpacing(2)
        up_btn = QToolButton()
        up_btn.setObjectName("settings-step")
        up_btn.setArrowType(Qt.ArrowType.UpArrow)
        up_btn.setFixedSize(24, 15)
        up_btn.setEnabled(is_on)
        down_btn = QToolButton()
        down_btn.setObjectName("settings-step")
        down_btn.setArrowType(Qt.ArrowType.DownArrow)
        down_btn.setFixedSize(24, 15)
        down_btn.setEnabled(is_on)
        up_btn.clicked.connect(spinbox.stepUp)
        down_btn.clicked.connect(spinbox.stepDown)
        step_col.addWidget(up_btn)
        step_col.addWidget(down_btn)
        unit_lbl = QLabel(meta.unit)
        unit_lbl.setObjectName("settings-unit")
        unit_lbl.setEnabled(is_on)
        spin_col.addWidget(spinbox)
        spin_col.addLayout(step_col)
        spin_col.addWidget(unit_lbl)
        row_layout.addLayout(spin_col)

        # Wire checkbox → enable/disable spinbox.
        checkbox.toggled.connect(spinbox.setEnabled)
        checkbox.toggled.connect(up_btn.setEnabled)
        checkbox.toggled.connect(down_btn.setEnabled)
        checkbox.toggled.connect(unit_lbl.setEnabled)
        checkbox.toggled.connect(lambda checked, current_row=row: self._set_row_active(current_row, checked))
        self._set_row_active(row, is_on)

        self._rows.append((checkbox, spinbox))
        return row

    def _set_row_active(self, row: QFrame, active: bool) -> None:
        row.setProperty("active", "true" if active else "false")
        row.style().unpolish(row)
        row.style().polish(row)

    @staticmethod
    def _current_k(
        config: Optional[ConstraintsConfig], index: int
    ) -> Optional[int]:
        """Extract the k value for the constraint at *index* from an existing config."""
        if config is None:
            return None
        fields = [
            config.min_gap_obligatory,
            config.min_gap_any,
            config.elective_conflict_cap,
            config.exam_span,
            config.max_exams_per_day,
        ]
        return fields[index]

    def _apply(self) -> None:
        """Read each row and build a ConstraintsConfig, then fire the callback."""
        def k(index: int) -> Optional[int]:
            checkbox, spinbox = self._rows[index]
            return spinbox.value() if checkbox.isChecked() else None

        config = ConstraintsConfig(
            min_gap_obligatory=k(0),
            min_gap_any=k(1),
            elective_conflict_cap=k(2),
            exam_span=k(3),
            max_exams_per_day=k(4),
        )
        self._on_apply(config)
        self.accept()
