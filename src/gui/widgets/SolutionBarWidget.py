"""Solution navigation bar widget containing back, export, within-page solutions navigator, and page flippers."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QGroupBox, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence


class SolutionBarWidget(QFrame):
    """Encapsulates the navigation, export and double-deck database paging toolbar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("nav-bar")
        self.setFixedHeight(78)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 4, 20, 4)
        layout.setSpacing(12)

        # Back returns to the input screen using the router history. The
        # Alt+Left shortcut makes it reachable from the keyboard as well.
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("btn-ghost")
        self.back_btn.setShortcut(QKeySequence("Alt+Left"))
        self.back_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.back_btn.setToolTip("Back to input screen (Alt+Left)")
        self.back_btn.setFixedHeight(36)
        layout.addWidget(self.back_btn)

        # Export saves the schedule on screen to a PDF.
        self.export_btn = QPushButton("⬇  Export PDF")
        self.export_btn.setObjectName("btn-export")
        self.export_btn.setToolTip("Save the current schedule as a PDF file")
        self.export_btn.setFixedHeight(36)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setStyleSheet(
            "QPushButton#btn-export {"
            "  background-color: #3396ad; color: #FFFFFF; border: none;"
            "  border-radius: 8px; padding: 0 18px; font-weight: 600; font-size: 13px;"
            "}"
            "QPushButton#btn-export:hover { background-color: #297B8F; }"
            "QPushButton#btn-export:disabled { background-color: #CBD5E1; color: #F1F5F9; }"
        )
        layout.addWidget(self.export_btn)

        layout.addStretch()

        # ── Group 1: SOLUTIONS IN CURRENT VIEW ──
        self.solutions_group = QGroupBox("SOLUTIONS IN CURRENT VIEW")
        solutions_layout = QHBoxLayout(self.solutions_group)
        solutions_layout.setContentsMargins(10, 10, 10, 6)
        solutions_layout.setSpacing(8)

        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.setObjectName("btn-secondary")
        self.prev_btn.setToolTip("Previous solution")
        self.prev_btn.setFixedSize(70, 28)

        self.counter_label = QLabel("No solutions")
        self.counter_label.setObjectName("counter-label")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_label.setStyleSheet("min-width: 150px; font-weight: 600; font-size: 12px; color: #3E352F;")

        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setObjectName("btn-secondary")
        self.next_btn.setToolTip("Next solution")
        self.next_btn.setFixedSize(70, 28)

        solutions_layout.addWidget(self.prev_btn)
        solutions_layout.addWidget(self.counter_label)
        solutions_layout.addWidget(self.next_btn)
        layout.addWidget(self.solutions_group)

        # ── Group 2: DATABASE PAGES (10k sets / pg) ──
        self.pages_group = QGroupBox("DATABASE PAGES (10k sets / pg)")
        pages_layout = QHBoxLayout(self.pages_group)
        pages_layout.setContentsMargins(10, 10, 10, 6)
        pages_layout.setSpacing(8)

        self.first_page_btn = QPushButton("⏮ First")
        self.first_page_btn.setObjectName("btn-secondary")
        self.first_page_btn.setToolTip("First page")
        self.first_page_btn.setFixedSize(75, 28)

        self.prev_page_btn = QPushButton("◀")
        self.prev_page_btn.setObjectName("btn-secondary")
        self.prev_page_btn.setToolTip("Previous page")
        self.prev_page_btn.setFixedSize(28, 28)
        self.prev_page_btn.setStyleSheet("padding: 0px;")

        self.page_label = QLabel("Page 1 / 1")
        self.page_label.setObjectName("page-label")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("min-width: 90px; font-weight: 600; font-size: 12px; color: #3E352F;")

        self.next_page_btn = QPushButton("▶")
        self.next_page_btn.setObjectName("btn-secondary")
        self.next_page_btn.setToolTip("Next page")
        self.next_page_btn.setFixedSize(28, 28)
        self.next_page_btn.setStyleSheet("padding: 0px;")

        self.last_page_btn = QPushButton("⏭ Last")
        self.last_page_btn.setObjectName("btn-secondary")
        self.last_page_btn.setToolTip("Last page")
        self.last_page_btn.setFixedSize(75, 28)

        pages_layout.addWidget(self.first_page_btn)
        pages_layout.addWidget(self.prev_page_btn)
        pages_layout.addWidget(self.page_label)
        pages_layout.addWidget(self.next_page_btn)
        pages_layout.addWidget(self.last_page_btn)
        layout.addWidget(self.pages_group)

        self.pages_group.setVisible(False)
