"""A single family card on the cluster overview screen.

Shows the family's size, a one-line description, its average feature profile
(each criterion emphasised on its own row), and two actions: open the family to
browse its schedules, and toggle it for side-by-side comparison.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.application.viewmodels.ClusterViewModel import ClusterCardViewModel
from src.logic.clustering.CriterionDisplay import display_value, label
from src.gui.features.clusters.widgets.AllMetricsDialog import AllMetricsDialog
from src.gui.features.clusters.widgets.MetricWidgetFactory import create_metric_widgets



class ClusterCardWidget(QFrame):
    """Displays one family summary; emits open / compare-toggle signals."""

    open_requested = pyqtSignal(int)            # cluster_id
    compare_toggled = pyqtSignal(int, bool)     # cluster_id, selected

    def __init__(self, card: ClusterCardViewModel, parent=None) -> None:
        super().__init__(parent)
        self._cluster_id = card.cluster_id
        self.setObjectName("card")
        self.setMinimumWidth(300)
        # Subtle premium drop shadow
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(12)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(2)
        self._shadow.setColor(QColor(0, 0, 0, 20)) # 8% opacity shadow
        self.setGraphicsEffect(self._shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Title + size.
        title = QLabel(f"<b>{card.title}</b>")
        title.setObjectName("card-title")
        layout.addWidget(title)

        if card.sampled:
            size_text = f"{card.size} schedules  (~{card.estimated_population_size} of full set)"
        else:
            size_text = f"{card.size} schedules"
        size_label = QLabel(size_text)
        size_label.setObjectName("card-size-label")
        layout.addWidget(size_label)

        # One-line description converted into pill tags
        if card.description:
            pills_widget = QWidget()
            pills_widget.setObjectName("card-pills-widget")
            pills_layout = QVBoxLayout(pills_widget)
            pills_layout.setContentsMargins(0, 0, 0, 0)
            pills_layout.setSpacing(4)
            pills_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            tags = [t.strip() for t in card.description.split(";")] if card.description else []
            for tag in tags:
                if not tag:
                    continue
                
                # Determine colors based on semantic meaning of tag description
                tag_lower = tag.lower()
                if any(word in tag_lower for word in ["breathing room", "spread out", "few", "light busiest-day", "low rate", "grading gaps"]):
                    tag_type = "positive"
                elif any(word in tag_lower for word in ["packed close", "bunched closely", "clashes", "clash", "heavy busiest-day", "heavy load", "unevenly", "high rate"]):
                    tag_type = "negative"
                elif any(word in tag_lower for word in ["window", "span", "max rest"]):
                    tag_type = "span"
                else:
                    tag_type = "neutral"

                pill = QLabel(tag)
                pill.setObjectName(f"pill-{tag_type}")
                pills_layout.addWidget(pill, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(pills_widget)
        # Feature profile (the "archetype" summary): 3 columns per row
        profile = QFrame()
        grid = QGridLayout(profile)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 1)  # Metric label stretches

        # Store full summary for popup dialog
        self._card_title_text = card.title
        self._full_summary = card.summary
        self._min_max = card.min_max
        self._defining_criterion = card.defining_criterion

        # Sort all summary items by their goodness percentage and display the top 5
        from src.gui.features.clusters.widgets.MetricWidgetFactory import display_value_to_percentage
        sorted_summary = sorted(
            card.summary,
            key=lambda item: display_value_to_percentage(item[0], item[2]),
            reverse=True
        )
        summary_to_show = sorted_summary[:5]
        has_extra = len(card.summary) > 5

        for row, (crit_key, label, value) in enumerate(summary_to_show):
            is_defining = (crit_key == card.defining_criterion)
            name, indicator, val = create_metric_widgets(
                crit_key=crit_key,
                label_txt=label,
                value=value,
                min_max=card.min_max,
                is_defining=is_defining,
                bar_width=55,
                bar_height=5,
            )
            grid.addWidget(name, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(indicator, row, 1, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(val, row, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(profile)

        if has_extra:
            more_btn = QPushButton("Show All Metrics...")
            more_btn.setObjectName("more-metrics-btn")
            more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            more_btn.clicked.connect(self._show_all_metrics)
            layout.addWidget(more_btn)

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
        self._compare_btn.toggled.connect(self._on_compare_toggled)

        actions.addWidget(open_btn)
        actions.addWidget(self._compare_btn)
        layout.addLayout(actions)

    @property
    def cluster_id(self) -> int:
        return self._cluster_id

    def _on_compare_toggled(self, checked: bool) -> None:
        self._update_selection_state(checked)
        self.compare_toggled.emit(self._cluster_id, checked)

    def _update_selection_state(self, checked: bool) -> None:
        self.setProperty("selected", checked)
        self.style().unpolish(self)
        self.style().polish(self)
        if checked:
            self._compare_btn.setText("Comparing")
        else:
            self._compare_btn.setText("Compare")

    def set_compare_checked(self, checked: bool) -> None:
        """Set the compare toggle without emitting (used to enforce max 2)."""
        self._compare_btn.blockSignals(True)
        self._compare_btn.setChecked(checked)
        self._compare_btn.blockSignals(False)
        self._update_selection_state(checked)

    def _show_all_metrics(self) -> None:
        dialog = AllMetricsDialog(
            title=self._card_title_text,
            summary=self._full_summary,
            min_max=self._min_max,
            defining_criterion=self._defining_criterion,
            parent=self.window()
        )
        dialog.exec()
