import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QLabel
from src.gui.features.input.widgets.ProgramSelectorCardWidget import ProgramSelectorCardWidget
from src.application.viewmodels.ProgramViewModel import ProgramViewModel

pytestmark = pytest.mark.usefixtures("qapp")


def _make_view_models():
    return [
        ProgramViewModel(program_id="83101", display_name="Software Engineering", course_count=0),
        ProgramViewModel(program_id="83102", display_name="Computer Science", course_count=0),
    ]


# ===========================================================================
# TC-PSCW-001: test initial badge text and empty selection list.
# ===========================================================================
def test_program_selector_card_initial_state_badge_and_selection():
    # Act
    widget = ProgramSelectorCardWidget(5, _make_view_models())

    # Assert
    assert widget._programs_count_badge.text() == "0 / 5"
    assert len(widget.selected_program_ids()) == 0

# ===========================================================================
# TC-PSCW-002: test initial placeholder label exists with correct text.
# ===========================================================================
def test_program_selector_card_initial_state_placeholder():
    # Act
    widget = ProgramSelectorCardWidget(5, _make_view_models())

    # Assert
    placeholder = widget.findChild(QLabel, "card-placeholder")
    assert placeholder is not None
    assert placeholder.text() == "Click to select programs"

# ===========================================================================
# TC-PSCW-003: test that rendering chips updates the count badge.
# ===========================================================================
def test_program_selector_card_rendering_chips_updates_badge():
    # Arrange
    widget = ProgramSelectorCardWidget(5, _make_view_models())
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
    widget = ProgramSelectorCardWidget(5, _make_view_models())
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
    widget = ProgramSelectorCardWidget(5, _make_view_models())
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
    widget = ProgramSelectorCardWidget(5, _make_view_models())
    mock_slot = MagicMock()
    widget.selection_changed.connect(mock_slot)

    with patch(
        "src.gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"
    ) as mock_dialog_cls:
        mock_dialog = mock_dialog_cls.return_value
        mock_dialog.exec.return_value = True
        mock_dialog.selected_ids.return_value = ["83101", "83102"]

        # Act
        widget.mousePressEvent(None)

        # Assert
        assert mock_dialog_cls.call_args.kwargs["preselected_ids"] == []
    assert widget.selected_program_ids() == ["83101", "83102"]
    assert mock_slot.call_count == 1

# ===========================================================================
# TC-PSCW-007: test that the program selector card mouse click flow is rejected when selection is cancelled/rejected.
# ===========================================================================
def test_program_selector_card_mouse_click_flow_cancel():
    # Arrange
    widget = ProgramSelectorCardWidget(5, _make_view_models())
    widget._selected_program_ids = ["83101"]
    widget._refresh_program_summary()

    mock_slot = MagicMock()
    widget.selection_changed.connect(mock_slot)

    with patch(
        "src.gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"
    ) as mock_dialog_cls:
        mock_dialog = mock_dialog_cls.return_value
        mock_dialog.exec.return_value = False

        # Act
        widget.mousePressEvent(None)

        # Assert
        assert mock_dialog_cls.call_args.kwargs["preselected_ids"] == ["83101"]
    assert widget.selected_program_ids() == ["83101"]
    assert mock_slot.call_count == 0

# ===========================================================================
# TC-PSCW-008: test set_program_view_models keeps a still-valid selection
# and drops a selection that no longer exists, without emitting a signal
# when nothing actually changed.
# ===========================================================================
def test_set_program_view_models_keeps_valid_selection():
    # Arrange
    widget = ProgramSelectorCardWidget(5, _make_view_models())
    widget._selected_program_ids = ["83101"]
    mock_slot = MagicMock()
    widget.selection_changed.connect(mock_slot)

    # Act: new list still contains the selected program
    widget.set_program_view_models(_make_view_models())

    # Assert: selection untouched, no spurious signal
    assert widget.selected_program_ids() == ["83101"]
    assert mock_slot.call_count == 0

# ===========================================================================
# TC-PSCW-009: test set_program_view_models drops selections that are no
# longer present in the new list and resets the badge to 0.
# ===========================================================================
def test_set_program_view_models_drops_stale_selection():
    # Arrange
    widget = ProgramSelectorCardWidget(5, _make_view_models())
    widget._selected_program_ids = ["83101", "83102"]
    widget._refresh_program_summary()
    mock_slot = MagicMock()
    widget.selection_changed.connect(mock_slot)

    only_83108 = [ProgramViewModel(program_id="83108", display_name="Industrial Eng.", course_count=0)]

    # Act: new list no longer contains either previously selected program
    widget.set_program_view_models(only_83108)

    # Assert
    assert widget.selected_program_ids() == []
    assert widget._programs_count_badge.text() == "0 / 5"
    assert mock_slot.call_count == 1

# ===========================================================================
# TC-PSCW-010: test that with no programs available, the card shows the
# "load courses" placeholder and does not open the selection dialog.
# ===========================================================================
def test_no_programs_available_placeholder_and_no_dialog():
    # Arrange
    widget = ProgramSelectorCardWidget(5, [])

    # Assert placeholder text
    placeholder = widget.findChild(QLabel, "card-placeholder")
    assert placeholder is not None
    assert placeholder.text() == "Load courses to select programs"

    # Act: clicking should warn the user instead of opening the dialog
    with patch(
        "src.gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"
    ) as mock_dialog_cls, patch(
        "src.gui.features.input.widgets.ProgramSelectorCardWidget.QMessageBox.information"
    ) as mock_info_box:
        widget.mousePressEvent(None)

        # Assert
        assert mock_dialog_cls.call_count == 0
        assert mock_info_box.call_count == 1
        assert mock_info_box.call_args[0][1] == "No courses loaded"

    # Selection/badge state should be untouched by the click
    assert widget.selected_program_ids() == []
    assert widget._programs_count_badge.text() == "0 / 5"
