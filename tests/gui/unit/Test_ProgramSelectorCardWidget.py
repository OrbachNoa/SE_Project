import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QLabel
from src.gui.features.input.widgets.ProgramSelectorCardWidget import ProgramSelectorCardWidget

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-PSCW-001: test initial badge text and empty selection list.
# ===========================================================================
def test_program_selector_card_initial_state_badge_and_selection():
    # Act
    widget = ProgramSelectorCardWidget(max_programs=5)
    
    # Assert
    assert widget._programs_count_badge.text() == "0 / 5"
    assert len(widget.selected_program_ids()) == 0

# ===========================================================================
# TC-PSCW-002: test initial placeholder label exists with correct text.
# ===========================================================================
def test_program_selector_card_initial_state_placeholder():
    # Act
    widget = ProgramSelectorCardWidget(max_programs=5)
    
    # Assert
    placeholder = widget.findChild(QLabel, "card-placeholder")
    assert placeholder is not None
    assert placeholder.text() == "Click to select programs"

# ===========================================================================
# TC-PSCW-003: test that rendering chips updates the count badge.
# ===========================================================================
def test_program_selector_card_rendering_chips_updates_badge():
    # Arrange
    widget = ProgramSelectorCardWidget(max_programs=5)
    widget._selected_program_ids = ["83101", "83102"]
    
    # Act
    widget._refresh_program_summary()
    
    # Assert
    assert widget._programs_count_badge.text() == "2 / 5"

# ===========================================================================
# TC-PSCW-004: test that rendering chips removes the placeholder label.
# ===========================================================================
def test_program_selector_card_rendering_chips_removes_placeholder():
    # Arrange
    widget = ProgramSelectorCardWidget(max_programs=5)
    widget._selected_program_ids = ["83101", "83102"]
    
    # Act
    widget._refresh_program_summary()
    
    # Assert
    placeholder_in_layout = False
    for i in range(widget._summary_layout.count()):
        item = widget._summary_layout.itemAt(i)
        w = item.widget()
        if w and w.objectName() == "card-placeholder":
            placeholder_in_layout = True
    assert not placeholder_in_layout

# ===========================================================================
# TC-PSCW-005: test that rendering chips generates the correct chip labels.
# ===========================================================================
def test_program_selector_card_rendering_chips_populates_labels():
    # Arrange
    widget = ProgramSelectorCardWidget(max_programs=5)
    widget._selected_program_ids = ["83101", "83102"]
    
    # Act
    widget._refresh_program_summary()
    
    # Assert
    chips = widget.findChildren(QLabel, "program-chip")
    assert len(chips) == 2
    assert "83101" in chips[0].text()
    assert "83102" in chips[1].text()


# ===========================================================================
# TC-PSCW-006: test mouse press dialog flow when selection is accepted.
# ===========================================================================
def test_program_selector_card_mouse_click_flow_accept():
    # Arrange
    widget = ProgramSelectorCardWidget(max_programs=5)
    mock_choose = MagicMock(return_value=["83101", "83102"])
    widget._selection_controller.choose_program_ids = mock_choose
    
    mock_slot = MagicMock()
    widget.selection_changed.connect(mock_slot)
    
    # Act
    widget.mousePressEvent(None)
    
    # Assert
    assert mock_choose.call_count == 1
    assert mock_choose.call_args[0] == (widget, [])
    assert widget.selected_program_ids() == ["83101", "83102"]
    assert mock_slot.call_count == 1

# ===========================================================================
# TC-PSCW-007: test that the program selector card mouse click flow is rejected when selection is cancelled/rejected.
# ===========================================================================
def test_program_selector_card_mouse_click_flow_cancel():
    # Arrange
    widget = ProgramSelectorCardWidget(max_programs=5)
    widget._selected_program_ids = ["83101"]
    widget._refresh_program_summary()
    
    mock_choose = MagicMock(return_value=None)  
    widget._selection_controller.choose_program_ids = mock_choose
    
    mock_slot = MagicMock()
    widget.selection_changed.connect(mock_slot)
    
    # Act
    widget.mousePressEvent(None)
    
    # Assert
    assert mock_choose.call_count == 1
    assert mock_choose.call_args[0] == (widget, ["83101"])
    assert widget.selected_program_ids() == ["83101"]  
    assert mock_slot.call_count == 0 
