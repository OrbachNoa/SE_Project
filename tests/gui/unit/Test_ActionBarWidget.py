"""
Test suite for ActionBarWidget.

Scope   : Validates GUI state toggles for the action bar (replace/update mode,
          and ensuring generate button can be enabled/disabled).
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-ABW-001..002
"""
from src.gui.features.input.widgets.ActionBarWidget import ActionBarWidget


# ===========================================================================
# TC-ABW-001: Radio buttons for Replace/Update modes toggle exclusively.
# ===========================================================================
def test_action_bar_mode_toggles(qapp):
    # Arrange
    bar = ActionBarWidget()

    # Assert initial state (Replace is default)
    assert bar.mode_replace.isChecked() is True
    assert bar.mode_update.isChecked() is False

    # Act
    bar.mode_update.setChecked(True)

    # Assert
    assert bar.mode_replace.isChecked() is False
    assert bar.mode_update.isChecked() is True


# ===========================================================================
# TC-ABW-002: the run controls start in their idle configuration — Generate is
# disabled (nothing loaded yet) and Cancel / View Results are hidden until a
# run begins. This guards the flow "you cannot generate, cancel, or view
# results before loading inputs".
# ===========================================================================
def test_action_bar_run_controls_start_idle(qapp):
    # Arrange / Act
    bar = ActionBarWidget()

    # Assert — isHidden() reflects the explicit hidden flag set at construction,
    # independent of the (unshown) widget's ancestor visibility.
    assert bar.generate_btn.isEnabled() is False
    assert bar.cancel_btn.isHidden() is True
    assert bar.view_results_btn.isHidden() is True
