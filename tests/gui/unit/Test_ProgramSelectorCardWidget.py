"""
Test suite for ProgramSelectorCardWidget.

Scope   : The study-program selector card's real state logic — the
          "selected / max" count badge that reflects the committed selection,
          and the commit-on-accept rule that only writes the dialog's choice
          back into the card (and notifies observers) when the picker dialog
          is accepted. Both gate a user flow (choosing programs before a run),
          so they are exercised on the live widget.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SEL-001, TC-SEL-002
Fixtures: qapp (tests/conftest.py)
"""
import pytest
from unittest.mock import patch

from src.gui.features.input.widgets.ProgramSelectorCardWidget import ProgramSelectorCardWidget

pytestmark = pytest.mark.usefixtures("qapp")

_DIALOG_PATH = "src.gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"


# ===========================================================================
# TC-SEL-001: the count badge must render "selected / max" and track the
# committed selection — "0 / 5" with nothing chosen, "2 / 5" after two
# programs are committed.
# ===========================================================================
def test_program_selector_badge_reflects_selection_count():
    # Arrange
    card = ProgramSelectorCardWidget(max_programs=5, program_view_models=[])

    # Assert — initial badge before any selection.
    assert card.programs_count_badge.text() == "0 / 5"

    # Act — commit a two-program selection.
    card.set_selected_program_ids(["83101", "83102"])

    # Assert — the badge tracks the committed count against the configured max.
    assert card.programs_count_badge.text() == "2 / 5"


# ===========================================================================
# TC-SEL-002: accepting the picker dialog must commit the dialog's chosen IDs
# into the card and emit selection_changed exactly once; cancelling must leave
# the existing selection untouched and emit nothing.
# ===========================================================================
def test_program_selector_commits_dialog_choice_only_on_accept():
    # Arrange
    card = ProgramSelectorCardWidget(max_programs=5, program_view_models=[])
    emissions = []
    card.selection_changed.connect(lambda: emissions.append(1))

    # Act — user accepts the dialog with two programs picked.
    with patch(_DIALOG_PATH) as MockDialog:
        MockDialog.return_value.exec.return_value = True
        MockDialog.return_value.selected_ids.return_value = ["83101", "83102"]
        card._open_program_dialog()

    # Assert — the accepted choice is committed and observers are notified once.
    assert card.selected_program_ids() == ["83101", "83102"]
    assert len(emissions) == 1

    # Act — user cancels a second dialog (exec returns False).
    with patch(_DIALOG_PATH) as MockDialog:
        MockDialog.return_value.exec.return_value = False
        MockDialog.return_value.selected_ids.return_value = ["83108"]
        card._open_program_dialog()

    # Assert — a cancel must not change the committed selection or notify again.
    assert card.selected_program_ids() == ["83101", "83102"]
    assert len(emissions) == 1
