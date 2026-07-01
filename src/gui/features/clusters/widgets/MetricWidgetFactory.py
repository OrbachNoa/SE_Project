"""Factory functions for creating metric rendering widgets.

Centralizes progress bar, status check, warning, and tooltip logic to ensure
consistent styling and avoid code duplication across cards and dialog popups.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

from src.logic.clustering.CriterionDisplay import criterion_summary, display_value_to_percentage

def create_metric_widgets(
    crit_key: str,
    label_txt: str,
    value: str,
    min_max: dict,
    is_defining: bool,
    bar_width: int = 55,
    bar_height: int = 5,
) -> tuple[QLabel, QWidget, QLabel]:
    """Create aligned QLabel (name), QWidget (indicator), and QLabel (value) for a metric row."""
    name = QLabel(label_txt)
    val = QLabel(value)
    val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    indicator = QWidget()
    indicator.setObjectName("profile-indicator-container")
    indicator_layout = QHBoxLayout(indicator)
    indicator_layout.setContentsMargins(0, 0, 0, 0)
    indicator_layout.setSpacing(0)
    indicator_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    desc = criterion_summary(crit_key)
    min_val, max_val_val = min_max.get(crit_key, (value, value))
    tooltip_txt = f"{desc}\n\nAverage: {value}\nFamily range: {min_val} to {max_val_val}"
    name.setToolTip(tooltip_txt)
    val.setToolTip(tooltip_txt)
    indicator.setToolTip(tooltip_txt)

    pct = display_value_to_percentage(crit_key, value)

    bar = QProgressBar()
    bar.setTextVisible(False)
    bar.setFixedHeight(bar_height)
    bar.setFixedWidth(bar_width)
    bar.setToolTip(tooltip_txt)
    bar.setValue(pct)
    bar.setObjectName("profile-progress")
    bar.setProperty("defining", is_defining)
    indicator_layout.addWidget(bar)

    name.setObjectName("profile-metric-name")
    val.setObjectName("profile-metric-value")
    name.setProperty("defining", is_defining)
    val.setProperty("defining", is_defining)

    return name, indicator, val
