"""
Test suite for ProgramSelectorDialog.

Scope   : Validates GUI logic for selecting/deselecting study programs,
          specifically enforcing the selection limits (MAX_PROGRAMS).
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-PSD-001..002
"""
from unittest.mock import patch

from PyQt6.QtWidgets import QMessageBox

from src.config import MAX_PROGRAMS
from src.gui.features.input.widgets.ProgramSelectorDialog import ProgramSelectorDialog


class DummyProgramVM:
    def __init__(self, pid):
        self.program_id = pid
        self.display_name = f"Program {pid}"


# ===========================================================================
# TC-PSD-001: Dialog enforces MAX_PROGRAMS limit, showing a warning and
# ignoring the selection if the limit is exceeded.
# ===========================================================================
@patch.object(QMessageBox, "warning")
def test_program_selector_enforces_max_limit(mock_warning, qapp):
    # Arrange
    # Create N+1 dummy programs
    vms = [DummyProgramVM(f"P{i}") for i in range(MAX_PROGRAMS + 1)]
    # Start with exact maximum selected
    preselected = [f"P{i}" for i in range(MAX_PROGRAMS)]

    dialog = ProgramSelectorDialog(vms, preselected)

    # Act
    # Try to toggle the one unselected program
    target_card = dialog._cards[f"P{MAX_PROGRAMS}"]
    target_card.mousePressEvent(None)

    # Assert
    # The new program should not be selected
    assert f"P{MAX_PROGRAMS}" not in dialog.selected_ids()
    assert len(dialog.selected_ids()) == MAX_PROGRAMS
    # A warning must have been shown
    mock_warning.assert_called_once()


# ===========================================================================
# TC-PSD-002: Dialog toggles selection state on click properly.
# ===========================================================================
def test_program_selector_toggles_selection(qapp):
    # Arrange
    vms = [DummyProgramVM("P1"), DummyProgramVM("P2")]
    preselected = ["P1"]

    dialog = ProgramSelectorDialog(vms, preselected)

    # Act 1 - Deselect P1
    dialog._cards["P1"].mousePressEvent(None)

    # Assert 1
    assert "P1" not in dialog.selected_ids()
    assert dialog._cards["P1"]._selected is False

    # Act 2 - Select P2
    dialog._cards["P2"].mousePressEvent(None)

    # Assert 2
    assert "P2" in dialog.selected_ids()
    assert dialog._cards["P2"]._selected is True
