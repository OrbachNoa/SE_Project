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
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
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
                tag_cap = tag[0].upper() + tag[1:]
                
                # Determine colors based on semantic meaning of tag description
                tag_lower = tag.lower()
                if any(word in tag_lower for word in ["breathing room", "spread out", "few", "light busiest-day", "optimal"]):
                    tag_type = "positive"
                elif any(word in tag_lower for word in ["packed close", "bunched closely", "clashes", "clash", "more elective", "heavy busiest-day", "heavy load"]):
                    tag_type = "negative"
                elif any(word in tag_lower for word in ["wide window", "short window", "span"]):
                    tag_type = "span"
                else:
                    tag_type = "neutral"

                pill = QLabel(tag_cap)
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

        from src.logic.comparators.ScheduleScorer import (
            AVG_ALL_COURSES_GAP,
            ELECTIVE_CONFLICTS,
            MANDATORY_SPAN,
            MAX_EXAMS_PER_DAY,
            MIN_MANDATORY_GAP,
        )

        for row, (crit_key, label, value) in enumerate(card.summary):
            name = QLabel(label)
            val = QLabel(value)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            is_defining = (crit_key == card.defining_criterion)

            # Create visual indicator for Column 1
            indicator = QWidget()
            indicator.setObjectName("profile-indicator-container")
            indicator_layout = QHBoxLayout(indicator)
            indicator_layout.setContentsMargins(0, 0, 0, 0)
            indicator_layout.setSpacing(0)
            indicator_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            try:
                num_val = float(value)
            except ValueError:
                num_val = 0.0

            # Range tooltip details
            min_val, max_val_val = card.min_max.get(crit_key, (value, value))
            tooltip_txt = f"Average: {value}\nFamily range: {min_val} to {max_val_val}"
            name.setToolTip(tooltip_txt)
            val.setToolTip(tooltip_txt)
            indicator.setToolTip(tooltip_txt)

            def add_status_label(text: str, object_name: str) -> None:
                lbl = QLabel(text)
                lbl.setToolTip(tooltip_txt)
                lbl.setObjectName(object_name)
                indicator_layout.addWidget(lbl)

            if crit_key in (AVG_ALL_COURSES_GAP, MIN_MANDATORY_GAP, MANDATORY_SPAN):
                bar = QProgressBar()
                bar.setTextVisible(False)
                bar.setFixedHeight(5)
                bar.setFixedWidth(55)
                bar.setToolTip(tooltip_txt)

                # Determine max scale
                if crit_key == AVG_ALL_COURSES_GAP:
                    max_scale = 10.0
                elif crit_key == MIN_MANDATORY_GAP:
                    max_scale = 5.0
                else:  # MANDATORY_SPAN
                    max_scale = 14.0

                pct = min(100, max(0, int((num_val / max_scale) * 100)))
                bar.setValue(pct)

                bar.setObjectName("profile-progress")
                bar.setProperty("defining", is_defining)
                indicator_layout.addWidget(bar)

            elif crit_key == ELECTIVE_CONFLICTS:
                if num_val <= 0.05:
                    add_status_label("✔", "profile-status-check")
                else:
                    add_status_label("⚠", "profile-status-warning")

            elif crit_key == MAX_EXAMS_PER_DAY:
                if num_val <= 1.05:
                    add_status_label("✔", "profile-status-check")
                elif num_val >= 2.0:
                    add_status_label("⚠", "profile-status-danger")
                else:
                    add_status_label("⚠", "profile-status-warning")

            # Apply row styles depending on whether it is defining
            name.setObjectName("profile-metric-name")
            val.setObjectName("profile-metric-value")
            name.setProperty("defining", is_defining)
            val.setProperty("defining", is_defining)

            grid.addWidget(name, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(indicator, row, 1, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(val, row, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

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
