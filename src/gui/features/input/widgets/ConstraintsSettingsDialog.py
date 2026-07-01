from __future__ import annotations

from typing import Callable, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox, QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from gui.core.styles.Theme import APP_STYLESHEET
from gui.core.styles.DialogStyles import DIALOG_STYLESHEET, SETTINGS_DIALOG_STYLESHEET
from src.logic.checkers.config.ConstraintMetadata import CONSTRAINTS, ConstraintMeta
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig


class ConstraintsSettingsDialog(QDialog):
    """
    Dialog for choosing which threshold constraints are active.

    The dialog does not run the scheduler and does not apply constraints directly.
    It only builds a ConstraintsConfig and sends it back using on_apply.
    """

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

        # Callback from InputScreenPresenter.
        # When the user clicks Apply, the new ConstraintsConfig is passed there.
        self._on_apply = on_apply

        # Checkbox+spinbox per row, in CONSTRAINTS order. _apply() zips this with
        # CONSTRAINTS to read each row's value by field name.
        self._rows: list[Tuple[QCheckBox, QSpinBox]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("dialog-card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 24, 26, 22)
        card_layout.setSpacing(14)

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
        rules_badge = QLabel(f"{len(CONSTRAINTS)} rules")
        rules_badge.setObjectName("dialog-counter")
        header_row.addWidget(rules_badge, alignment=Qt.AlignmentFlag.AlignTop)
        card_layout.addLayout(header_row)

        for meta in CONSTRAINTS:
            row_widget = self._build_row(meta, current_config)
            card_layout.addWidget(row_widget)

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

    def _build_row(
        self,
        meta: ConstraintMeta,
        current_config: Optional[ConstraintsConfig],
    ) -> QFrame:
        """
        Build one constraint row.

        If current_config has value for this row, the row starts enabled.
        If the value is None, the row starts disabled.
        """

        current_k = self._current_k(current_config, meta)
        is_on = current_k is not None

        row = QFrame()
        row.setObjectName("settings-row")
        row.setMinimumHeight(78)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 12, 16, 12)
        row_layout.setSpacing(14)

        checkbox = QCheckBox()
        checkbox.setChecked(is_on)
        row_layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignTop)

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

        spin_col = QHBoxLayout()
        spin_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        spin_col.setSpacing(8)
        spinbox = QSpinBox()
        spinbox.setObjectName("settings-comparator")
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

        checkbox.toggled.connect(spinbox.setEnabled)
        checkbox.toggled.connect(up_btn.setEnabled)
        checkbox.toggled.connect(down_btn.setEnabled)
        checkbox.toggled.connect(unit_lbl.setEnabled)
        checkbox.toggled.connect(lambda checked, current_row=row: self._set_row_active(current_row, checked))
        self._set_row_active(row, is_on)

        self._rows.append((checkbox, spinbox))
        return row

    def _set_row_active(self, row: QFrame, active: bool) -> None:
        """Update the row style after enabling or disabling it."""

        row.setProperty("active", "true" if active else "false")
        row.style().unpolish(row)
        row.style().polish(row)

    @staticmethod
    def _current_k(
        config: Optional[ConstraintsConfig], meta: ConstraintMeta
    ) -> Optional[int]:
        """Get the saved k value for a constraint by its config field name."""
        if config is None:
            return None
        return getattr(config, meta.field_name)

    def _apply(self) -> None:
        """
        Build ConstraintsConfig from the GUI rows and send it back.

        Checked row means the constraint is active and gets an integer k.
        Unchecked row means the constraint is disabled and gets None.
        """
        values = {
            meta.field_name: (spinbox.value() if checkbox.isChecked() else None)
            for meta, (checkbox, spinbox) in zip(CONSTRAINTS, self._rows)
        }
        config = ConstraintsConfig(**values)

        self._on_apply(config)
        self.accept()
