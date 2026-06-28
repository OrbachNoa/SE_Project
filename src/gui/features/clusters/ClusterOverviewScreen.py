"""Cluster overview screen — a card per family.

Lets the user see the families, choose the number of clusters K, open a family to
browse it, and select two families to compare their representatives side by side.
"""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.common.BusyCursorGuard import BusyCursorGuard
from gui.common.components.HeaderWidget import HeaderWidget
from gui.core.screen import Screen
from gui.features.clusters.ClusterOverviewPresenter import ClusterOverviewPresenter
from gui.features.clusters.widgets.ClusterCardWidget import ClusterCardWidget

_COLUMNS = 3


class ClusterOverviewScreen(Screen):
    """Grid of family cards plus the K control and comparison entry point."""

    def __init__(self, controller, router, detail_screen, compare_screen,
                 detail_name: str, compare_name: str) -> None:
        super().__init__()
        self._detail_name = detail_name
        self._compare_name = compare_name
        self._cards: Dict[int, ClusterCardWidget] = {}
        # Tracks whether this screen currently holds the shared busy cursor, so
        # repeated set_busy(False) calls (e.g. on leave) never unbalance it.
        self._busy_active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(HeaderWidget(parent=self))
        self._build_toolbar(root)
        self._build_request_bar(root)
        self._build_cards_area(root)

        self._presenter = ClusterOverviewPresenter(
            self, controller, router, detail_screen, compare_screen
        )
        self._connect_events()

    # ── layout ─────────────────────────────────────────────────────────────

    def _build_toolbar(self, root: QVBoxLayout) -> None:
        bar = QFrame()
        bar.setObjectName("nav-bar")
        bar.setFixedHeight(70)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(12)

        self._back_btn = QPushButton("← Back to schedules")
        self._back_btn.setObjectName("btn-ghost")
        layout.addWidget(self._back_btn)

        title = QLabel("<b>Cluster overview</b>")
        title.setObjectName("cluster-overview-title")
        layout.addWidget(title)

        self._summary_label = QLabel("")
        self._summary_label.setObjectName("cluster-overview-summary")
        layout.addWidget(self._summary_label)
        layout.addStretch()

        layout.addWidget(QLabel("Number of families (K):"))
        self._k_spin = QSpinBox()
        self._k_spin.setObjectName("k-spin")
        self._k_spin.setRange(1, 50)
        self._k_spin.setValue(3)
        self._k_spin.setFixedWidth(80)
        layout.addWidget(self._k_spin)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setObjectName("btn-secondary")
        layout.addWidget(self._apply_btn)

        self._compare_btn = QPushButton("Compare selected")
        self._compare_btn.setToolTip("In order to compare select two families")
        self._compare_btn.setObjectName("btn-secondary")
        self._compare_btn.setEnabled(False)
        layout.addWidget(self._compare_btn)

        root.addWidget(bar)

    def _build_cards_area(self, root: QVBoxLayout) -> None:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(24, 20, 24, 20)
        self._grid.setHorizontalSpacing(18)
        self._grid.setVerticalSpacing(18)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, stretch=1)

    def _build_request_bar(self, root: QVBoxLayout) -> None:
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(24, 16, 24, 10)
        container_layout.setSpacing(0)

        bar = QFrame()
        bar.setObjectName("clustering-request-bar")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(10)
        prompt = QLabel("Describe a grouping:")
        prompt.setObjectName("cluster-request-prompt")
        row.addWidget(prompt)

        self._request_input = QLineEdit()
        self._request_input.setPlaceholderText(
            "e.g. \"group by the lightest exam days, into 4 groups\" — leave empty for automatic"
        )
        self._request_input.setClearButtonEnabled(True)
        row.addWidget(self._request_input, stretch=1)

        self._request_btn = QPushButton("Apply request")
        self._request_btn.setObjectName("btn-secondary")
        self._request_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(self._request_btn)
        layout.addLayout(row)

        self._busy_bar = QProgressBar()
        self._busy_bar.setRange(0, 0)  # indeterminate
        self._busy_bar.setTextVisible(False)
        self._busy_bar.setFixedHeight(4)
        self._busy_bar.setVisible(False)
        layout.addWidget(self._busy_bar)

        self._interpretation_label = QLabel("")
        self._interpretation_label.setObjectName("interpretation-label")
        self._interpretation_label.setWordWrap(True)
        self._interpretation_label.setVisible(False)
        layout.addWidget(self._interpretation_label)

        container_layout.addWidget(bar)
        root.addLayout(container_layout)

    def _connect_events(self) -> None:
        self._back_btn.clicked.connect(self._presenter.on_back)
        self._apply_btn.clicked.connect(lambda: self._presenter.on_apply_k(self._k_spin.value()))
        self._compare_btn.clicked.connect(self._presenter.on_compare)
        self._request_btn.clicked.connect(self._on_apply_request)
        self._request_input.returnPressed.connect(self._on_apply_request)

    def _on_apply_request(self) -> None:
        self._presenter.on_apply_request(self._request_input.text())

    # ── view API used by the presenter ───────────────────────────────────────

    def render_cards(self, cards: List) -> None:
        # Clear the existing grid.
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

        for index, card_vm in enumerate(cards):
            card = ClusterCardWidget(card_vm)
            card.open_requested.connect(self._presenter.on_open_cluster)
            card.compare_toggled.connect(self._presenter.on_compare_toggled)
            self._cards[card_vm.cluster_id] = card
            self._grid.addWidget(card, index // _COLUMNS, index % _COLUMNS)

    def set_k_value(self, k: int) -> None:
        self._k_spin.blockSignals(True)
        self._k_spin.setValue(k)
        self._k_spin.blockSignals(False)

    def get_k_value(self) -> int:
        return self._k_spin.value()

    def set_summary(self, text: str) -> None:
        self._summary_label.setText(text)

    def get_request_text(self) -> str:
        return self._request_input.text()

    def set_request_text(self, text: str) -> None:
        self._request_input.setText(text)

    def clear_request_text(self) -> None:
        self._request_input.clear()

    def set_interpretation(self, text: str) -> None:
        self._interpretation_label.setText(text)
        self._interpretation_label.setVisible(bool(text.strip()))

    def set_busy(self, busy: bool) -> None:
        self._busy_bar.setVisible(busy)
        self._request_btn.setEnabled(not busy)
        self._request_input.setEnabled(not busy)
        if busy and not self._busy_active:
            BusyCursorGuard.push()
            self._busy_active = True
        elif not busy and self._busy_active:
            BusyCursorGuard.pop()
            self._busy_active = False

    def uncheck_card(self, cluster_id: int) -> None:
        card = self._cards.get(cluster_id)
        if card is not None:
            card.set_compare_checked(False)

    def set_compare_enabled(self, enabled: bool) -> None:
        self._compare_btn.setEnabled(enabled)
        self._compare_btn.setText(
            "Compare selected (2/2)" if enabled else "Compare selected"
        )

    def show_message(self, message: str) -> None:
        QMessageBox.information(self, "Clusters", message)

    def detail_screen_name(self) -> str:
        return self._detail_name

    def compare_screen_name(self) -> str:
        return self._compare_name

    # ── Screen lifecycle ─────────────────────────────────────────────────────

    def on_enter(self) -> None:
        self._presenter.on_enter()

    def on_leave(self) -> None:
        self._presenter.on_leave()
