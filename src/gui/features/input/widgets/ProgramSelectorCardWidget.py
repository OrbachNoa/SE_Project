"""Program selector card widget for selecting study programs on the input screen."""
from __future__ import annotations

from typing import List
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal

from gui.features.input.widgets.ProgramSelectorDialog import ProgramSelectorDialog
from src.application.viewmodels.ProgramViewModel import ProgramViewModel
from gui.common.helpers import create_scaled_pixmap
from data.programs import programs_data


# This is a behind-the-scenes helper class. It is responsible for popping open the dialog box 
# where the user actually checks off the programs they want.
class _ProgramSelectionController:
    """Owns the modal selection flow for the program selector card."""

    def __init__(self, program_view_models: List[ProgramViewModel]) -> None:
        self._program_view_models = program_view_models

    # Opens the pop-up window and returns a list of the chosen programs if the user clicks "Save"
    def choose_program_ids(self, parent: QWidget, current_ids: List[str]) -> List[str] | None:
        dialog = ProgramSelectorDialog(
            self._program_view_models,
            preselected_ids=current_ids,
            parent=parent,
        )
        # If the user clicks "OK" or "Save" (exec returns True), give back what they selected
        if dialog.exec():
            return dialog.selected_ids()
        # If they hit "Cancel", return None so we don't change anything
        return None


# This is the main white box (card) you see on the screen that says "Study Programs"
# It shows what you have selected and acts as a big button to open the pop-up menu.
class ProgramSelectorCardWidget(QFrame):
    # This signal is like an alarm that goes off whenever the user changes their selected programs.
    # Other parts of the app listen to this alarm so they can update themselves.
    selection_changed = pyqtSignal()
    
    def __init__(self, max_programs: int = 5, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.max_programs = max_programs
        self._selected_program_ids: List[str] = []

        # Load up all the possible study programs from our data file
        self._program_view_models = [
            ProgramViewModel(program_id=p_id, display_name=p_name, course_count=0)
            for p_id, p_name in programs_data.items()
        ]
        self._selection_controller = _ProgramSelectionController(self._program_view_models)

        # Give the card a specific name for styling, and change the mouse to a pointing hand
        # so the user knows they can click on this whole box.
        self.setObjectName("selector-card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Build the top row of the card (Icon + Title + Counter)
        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        icon_lbl = QLabel()
        icon_lbl.setObjectName("card-icon")
        try:
            icon_pix = create_scaled_pixmap(self, "data/assets/icon.png", 18)
            icon_lbl.setPixmap(icon_pix)
        except Exception:
            icon_lbl.setText("📚")
            icon_lbl.setObjectName("card-icon")

        prog_title = QLabel("Study Programs")
        prog_title.setObjectName("card-title")

        header_row.addWidget(icon_lbl)
        header_row.addWidget(prog_title)
        header_row.addStretch()

        # The little badge on the right that shows "0 / 5" selected
        self._programs_count_badge = QLabel(f"0 / {self.max_programs}")
        self._programs_count_badge.setObjectName("badge")
        header_row.addWidget(self._programs_count_badge)

        # A small downward arrow icon just to show it's a dropdown menu
        chevron = QLabel("▾")
        chevron.setObjectName("chevron")
        header_row.addWidget(chevron)
        layout.addLayout(header_row)

        # Create an empty container underneath the header. We will put the selected "chips" (tags) here.
        self._summary_container = QWidget()
        self._summary_layout = QVBoxLayout(self._summary_container)
        self._summary_layout.setContentsMargins(0, 0, 0, 0)
        self._summary_layout.setSpacing(6)
        layout.addWidget(self._summary_container)

        self._refresh_program_summary()

    # This built-in function triggers whenever the user clicks anywhere inside this card.
    def mousePressEvent(self, event) -> None:
        """Open the program selection popup when the selector card is clicked."""
        self._open_program_dialog()

    # Opens the dialog. If the user picks new programs, it saves them and updates the screen.
    def _open_program_dialog(self) -> None:
        """Show the modal popup and commit the new selection only on accept."""
        selected_ids = self._selection_controller.choose_program_ids(
            self,
            self._selected_program_ids,
        )
        if selected_ids is None:
            return

        self._selected_program_ids = selected_ids
        self._refresh_program_summary()
        self.selection_changed.emit()

    # Redraws the list of selected programs inside the card.
    def _refresh_program_summary(self) -> None:
        """Rebuild the selector summary: placeholder when empty, chips otherwise."""
        # First, clean out any old tags that were drawn previously
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
                
        # Update the counter badge to show the current number (e.g., "2 / 5")
        count = len(self._selected_program_ids)
        self._programs_count_badge.setText(f"{count} / {self.max_programs}")
        
        # If nothing is selected, just show a gray placeholder text
        if count == 0:
            placeholder = QLabel("Click to select programs")
            placeholder.setObjectName("card-placeholder")
            self._summary_layout.addWidget(placeholder)
            return

        # Create a dictionary to easily find the full name of a program using its short ID
        name_by_id = {vm.program_id: vm.display_name for vm in self._program_view_models}

        # For every program the user picked, create a nice little visual tag ("chip") and add it to the card.
        for pid in self._selected_program_ids:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            row.setAlignment(Qt.AlignmentFlag.AlignLeft)
            row_holder = QWidget()
            row_holder.setLayout(row)
            self._summary_layout.addWidget(row_holder)

            label = name_by_id.get(pid, pid)
            chip = QLabel(f"{pid} · {label}")
            chip.setObjectName("program-chip")
            row.addWidget(chip)
            row.addStretch()

    # A simple way for the rest of the application to ask this card what the user has chosen.
    def selected_program_ids(self) -> List[str]:
        """Return the program IDs the user has committed via the popup."""
        return list(self._selected_program_ids)