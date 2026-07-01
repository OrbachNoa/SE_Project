"""
Test suite for ConstraintsPresenter.

Scope   : Verifies constraints dialog launching and applying global settings/periods.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-CON-001..003
"""
from unittest.mock import MagicMock, patch
from src.gui.features.input.ConstraintsPresenter import ConstraintsPresenter

# TC-GUI-CON-001
# ConstraintsPresenter must launch the constraints dialog with current settings.
@patch("src.gui.features.input.ConstraintsPresenter.ConstraintsSettingsDialog")
def test_constraints_presenter_opens_dialog(MockDialog):
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    on_changed = MagicMock()

    controller.get_constraints_config.return_value = "fake_config"
    presenter = ConstraintsPresenter(view, controller, on_changed)

    # Act
    presenter.on_settings_clicked()

    # Assert
    MockDialog.assert_called_once_with(
        on_apply=presenter._apply_constraints_config,
        current_config="fake_config",
        parent=view,
    )
    MockDialog.return_value.exec.assert_called_once()


# TC-GUI-CON-002
# ConstraintsPresenter must apply config to controller and mark inputs dirty.
def test_constraints_presenter_applies_config():
    # Arrange
    view = MagicMock()
    # Ensure view has mark_inputs_dirty method
    view.mark_inputs_dirty = MagicMock()

    controller = MagicMock()
    on_changed = MagicMock()

    presenter = ConstraintsPresenter(view, controller, on_changed)

    # Act
    presenter._apply_constraints_config("new_config")

    # Assert
    controller.set_constraints_config.assert_called_once_with("new_config")
    view.mark_inputs_dirty.assert_called_once()
    on_changed.assert_not_called()


# TC-GUI-CON-003
# ConstraintsPresenter must update exam periods and trigger on_changed.
def test_constraints_presenter_saves_periods():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    on_changed = MagicMock()

    presenter = ConstraintsPresenter(view, controller, on_changed)

    # Act
    presenter.on_constraints_saved(["vm1", "vm2"])

    # Assert
    controller.update_exam_periods.assert_called_once_with(["vm1", "vm2"])
    on_changed.assert_called_once()
