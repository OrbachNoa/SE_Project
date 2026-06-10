import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox
from src.gui.features.input.widgets.ProgramSelectorDialog import ProgramSelectorDialog
from src.application.viewmodels.ProgramViewModel import ProgramViewModel

pytestmark = pytest.mark.usefixtures("qapp")

@pytest.fixture
def programs_vm():
    return [
        ProgramViewModel(program_id="83101", display_name="Software Engineering", course_count=0),
        ProgramViewModel(program_id="83102", display_name="Information Systems", course_count=0),
        ProgramViewModel(program_id="83103", display_name="Industrial Engineering", course_count=0),
        ProgramViewModel(program_id="83104", display_name="Electrical Engineering", course_count=0),
        ProgramViewModel(program_id="83105", display_name="Mechanical Engineering", course_count=0),
        ProgramViewModel(program_id="83106", display_name="Civil Engineering", course_count=0),
    ]

# ===========================================================================
# TC-UI-PS-001: test initial selection.
# ===========================================================================
def test_program_selector_dialog_initial_selection(programs_vm):
    # Act
    dialog = ProgramSelectorDialog(programs_vm, preselected_ids=["83101", "83102"])

    # Assert
    assert dialog.selected_ids() == ["83101", "83102"]
    assert dialog._cards["83101"]._selected is True
    assert dialog._cards["83102"]._selected is True
    assert dialog._cards["83103"]._selected is False

# ===========================================================================
# TC-UI-PS-002: test toggle.
# ===========================================================================
def test_program_selector_dialog_toggle(programs_vm):
    # Arrange
    dialog = ProgramSelectorDialog(programs_vm, preselected_ids=["83101"])

    # Act - toggle on
    dialog._toggle("83102")
    assert "83102" in dialog.selected_ids()
    assert dialog._cards["83102"]._selected is True

    # Act - toggle off
    dialog._toggle("83101")
    assert "83101" not in dialog.selected_ids()
    assert dialog._cards["83101"]._selected is False

# ===========================================================================
# TC-UI-PS-003: test max limit.
# ===========================================================================
@patch("PyQt6.QtWidgets.QMessageBox.warning")
def test_program_selector_dialog_max_limit(mock_warning, programs_vm):
    # Arrange - preselect 5 programs
    dialog = ProgramSelectorDialog(programs_vm, preselected_ids=["83101", "83102", "83103", "83104", "83105"])

    # Act - try to toggle a 6th program
    dialog._toggle("83106")

    # Assert - should show a warning and not select
    mock_warning.assert_called_once()
    assert "83106" not in dialog.selected_ids()
