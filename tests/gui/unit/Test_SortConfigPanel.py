"""
Test suite for SortConfigPanel.

Scope   : Validates GUI logic for ordering sorting criteria. Tests that
          reordering rows updates the internal state, resetting restores
          default states, and applying emits the correct ordered list.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SCP-001..002
"""
from src.gui.features.output.widgets.SortConfigPanel import SortConfigPanel
from src.logic.comparators.SortCriteria import ALL_CRITERIA


# ===========================================================================
# TC-SCP-001: Dialog emits config_changed with correctly ordered criteria
# after simulating moving a row up or down.
# ===========================================================================
def test_sort_config_panel_reorders_and_emits(qapp):
    # Arrange
    # Start with a specific priority list
    initial_priority = [ALL_CRITERIA[1], ALL_CRITERIA[0]]
    dialog = SortConfigPanel(current_priority=initial_priority)

    emitted_configs = []
    dialog.config_changed.connect(emitted_configs.append)

    # Act 1 - Move the first row down
    # dialog._rows contains SortRow widgets.
    # _move_row_down(index) moves the row at `index` down.
    dialog._move_row_down(0)

    # Act 2 - Click Apply
    dialog._apply()

    # Assert
    assert len(emitted_configs) == 1
    # After moving index 0 down, it swapped with index 1
    expected_priority = [ALL_CRITERIA[0], ALL_CRITERIA[1]]

    # Since only two were enabled originally, the emitted config should match
    # the enabled ones in their new order
    assert emitted_configs[0] == expected_priority


# ===========================================================================
# TC-SCP-002: Reset button restores default ALL_CRITERIA ordering and enables all.
# ===========================================================================
def test_sort_config_panel_resets_to_defaults(qapp):
    # Arrange
    # Start with only one criterion
    initial_priority = [ALL_CRITERIA[2]]
    dialog = SortConfigPanel(current_priority=initial_priority)

    # Act
    dialog._reset()

    # Assert
    # After reset, ALL rows should be enabled and in the ALL_CRITERIA order
    for idx, row in enumerate(dialog._rows):
        assert row.criterion_id == ALL_CRITERIA[idx]
        assert row.is_enabled() is True
