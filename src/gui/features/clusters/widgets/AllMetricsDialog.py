"""A pop-up dialog showing the full profile of all 10 criteria."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from gui.features.clusters.widgets.MetricWidgetFactory import create_metric_widgets


class AllMetricsDialog(QDialog):
    """A pop-up dialog showing the full profile of all 10 criteria."""

    def __init__(self, title: str, summary: list, min_max: dict, defining_criterion: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{title} - All Metrics")
        self.setMinimumSize(450, 520)
        self.setModal(True)

        self.setObjectName("all-metrics-dialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        header = QLabel(f"<h3><b>Detailed Metrics for {title}</b></h3>")
        header.setObjectName("all-metrics-header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Scroll Area for the list of metrics
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("all-metrics-scroll")

        # We wrap the content in a QFrame with object name "card" so it inherits all styles
        content_frame = QFrame()
        content_frame.setObjectName("card")

        grid = QGridLayout(content_frame)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)

        from src.logic.clustering.CriterionDisplay import display_value_to_percentage
        
        sorted_summary = sorted(
            summary,
            key=lambda item: display_value_to_percentage(item[0], item[2]),
            reverse=True
        )

        for row, (crit_key, label_txt, value) in enumerate(sorted_summary):
            is_defining = (crit_key == defining_criterion)
            name, indicator, val = create_metric_widgets(
                crit_key=crit_key,
                label_txt=label_txt,
                value=value,
                min_max=min_max,
                is_defining=is_defining,
                bar_width=60,
                bar_height=6,
            )

            grid.addWidget(name, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(indicator, row, 1, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(val, row, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        scroll.setWidget(content_frame)
        layout.addWidget(scroll, stretch=1)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("btn-secondary")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
