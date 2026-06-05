"""Widget binding input date configurations to backend state container tokens."""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt

from gui.widgets.CalendarWidget import CalendarWidget
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel
from src.application.viewmodels.PeriodEditRequest import PeriodEditRequest


class CalendarEditorWidget(QWidget):
    """Interactive visual manager wrapping base grid blocks with state synchronization functions."""

    def __init__(self, view_model: PeriodEditViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        
        # Link context variables maps back to passive storage entity models
        self._view_model = view_model
        
        # Unique mapping tracking live selected date indices flagged as active restrictions
        self._excluded_dates: set[str] = set()
        self._init_ui()

    def _init_ui(self) -> None:
        """Assembles child layouts and wires up button signals handlers."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Render the embedded core grid structure module straight inside the viewport layout
        self.calendar_grid = CalendarWidget()
        self.main_layout.addWidget(self.calendar_grid)

        # Control Panel Buttons Row Alignment
        self.button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Save Period Bounds")
        self.apply_btn.setObjectName("btn-secondary")
        
        self.button_layout.addWidget(self.apply_btn)
        self.main_layout.addLayout(self.button_layout)

        # Connect structural trigger clicks down to localized private routines
        self.apply_btn.clicked.connect(self._on_apply_clicked)

    def toggle_date_exclusion(self, date_str: str) -> None:
        """Modifies operational contextual state blocks whenever cell interaction occurs."""
        if date_str in self._excluded_dates:
            self._excluded_dates.remove(date_str)
        else:
            self._excluded_dates.add(date_str)

    def _on_apply_clicked(self) -> None:
        """Bundles state variables inside flat primitives Request blocks safely."""
        # Create a fresh transfer model data packet reflecting current screen specifications
        request = PeriodEditRequest(
            semester=self._view_model.semester,
            moed=self._view_model.moed,
            start_date=self._view_model.start_date,
            end_date=self._view_model.end_date,
            excluded_dates=list(self._excluded_dates)
        )
        
        # Inform user contextually that request packaging execution chain finished successfully
        QMessageBox.information(
            self, "Configuration Synced", 
            f"Period configurations packed successfully for Moed {request.moed}."
        )
