"""
Test suite for ConstraintsSettingsDialog.

Scope   : Validates that UI rows map correctly to their corresponding
          ConstraintsConfig fields when applied. Checks that toggling
          checkboxes enables/disables the field, and modifying spinbox
          values constructs the correct final payload.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CSD-001
"""
from unittest.mock import MagicMock

from src.gui.features.input.widgets.ConstraintsSettingsDialog import ConstraintsSettingsDialog
from src.logic.checkers.config.ConstraintMetadata import CONSTRAINTS
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig


# ===========================================================================
# TC-CSD-001: Dialog builds ConstraintsConfig from UI rows correctly
# ===========================================================================
def test_constraints_settings_dialog_builds_config(qapp):
    # Arrange — the dialog starts from an all-None config (every rule off).
    empty_config = ConstraintsConfig()
    mock_on_apply = MagicMock()
    dialog = ConstraintsSettingsDialog(on_apply=mock_on_apply, current_config=empty_config)
    meta_enabled, meta_disabled = CONSTRAINTS[0], CONSTRAINTS[1]

    # Act — enable the first rule with a value of 5, leave the second disabled
    # (its spinbox value must be ignored), then apply.
    checkbox_0, spinbox_0 = dialog._rows[0]
    checkbox_0.setChecked(True)
    spinbox_0.setValue(5)

    checkbox_1, spinbox_1 = dialog._rows[1]
    checkbox_1.setChecked(False)
    spinbox_1.setValue(10)

    dialog._apply()

    # Assert — the built config carries the enabled rule's value and leaves the
    # disabled rule's field at None.
    mock_on_apply.assert_called_once()
    result_config = mock_on_apply.call_args[0][0]
    assert isinstance(result_config, ConstraintsConfig)
    assert getattr(result_config, meta_enabled.field_name) == 5
    assert getattr(result_config, meta_disabled.field_name) is None
