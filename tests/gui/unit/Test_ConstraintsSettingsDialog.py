"""Unit tests for ConstraintsSettingsDialog — the per-constraint threshold editor.

The dialog renders one row per configurable threshold checker (5 total:
min_gap_obligatory, min_gap_any, elective_conflict_cap, exam_span,
max_exams_per_day), each with a checkbox and a threshold spinbox that is
only enabled while its checkbox is checked. Tests cover the all-off default
when no ConstraintsConfig is supplied, that enabling a row and clicking
Apply builds a config carrying exactly that row's threshold (every other
field staying None), and the reverse: disabling an already-active row
clears its threshold back to None on Apply.

Conventions:
- Each test carries a unique TC-CSD-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- Tests use the shared `qapp` fixture (tests/conftest.py) via
  `pytestmark = pytest.mark.usefixtures("qapp")`, plus pytest-qt's `qtbot`
  fixture for widget lifecycle management and simulated clicks; no
  conftest fixture models ConstraintsConfig or the dialog itself.
"""
import pytest
from unittest.mock import MagicMock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from src.gui.features.input.widgets.ConstraintsSettingsDialog import ConstraintsSettingsDialog
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig

pytestmark = pytest.mark.usefixtures("qapp")


# ===========================================================================
# TC-CSD-001: the dialog constructs and opens without raising, with the
# expected window title.
# ===========================================================================
def test_constraints_settings_dialog_opens_without_error(qtbot):
    # Arrange
    on_apply = MagicMock()

    # Act
    dialog = ConstraintsSettingsDialog(on_apply=on_apply, current_config=None)
    qtbot.addWidget(dialog)

    # Assert
    assert dialog is not None
    assert dialog.windowTitle() == "Scheduling Constraints"


# ===========================================================================
# TC-CSD-002: with current_config=None, every constraint row starts
# unchecked and its threshold spinbox starts disabled.
# ===========================================================================
def test_constraints_settings_dialog_all_toggles_off_when_config_is_none(qtbot):
    # Arrange
    on_apply = MagicMock()
    dialog = ConstraintsSettingsDialog(on_apply=on_apply, current_config=None)
    qtbot.addWidget(dialog)

    # Act
    rows = dialog._rows

    # Assert
    assert len(rows) == 5
    for checkbox, spinbox in rows:
        assert checkbox.isChecked() is False
        assert spinbox.isEnabled() is False


# ===========================================================================
# TC-CSD-003: checking a row's box, setting its threshold, and clicking
# Apply builds a ConstraintsConfig carrying exactly that k for that
# constraint, leaving every other constraint at None.
# ===========================================================================
def test_constraints_settings_dialog_enabling_a_toggle_sets_its_threshold(qtbot):
    # Arrange
    captured = {}
    on_apply = lambda config: captured.setdefault("config", config)
    dialog = ConstraintsSettingsDialog(on_apply=on_apply, current_config=None)
    qtbot.addWidget(dialog)
    checkbox, spinbox = dialog._rows[0]  # min_gap_obligatory row

    # Act
    checkbox.setChecked(True)
    spinbox.setValue(5)
    apply_btn = dialog.findChild(QPushButton, "dialog-select")
    qtbot.mouseClick(apply_btn, Qt.MouseButton.LeftButton)

    # Assert
    config = captured["config"]
    assert config.min_gap_obligatory == 5
    assert config.min_gap_any is None
    assert config.elective_conflict_cap is None
    assert config.exam_span is None
    assert config.max_exams_per_day is None


# ===========================================================================
# TC-CSD-004: starting from a config with one constraint already active,
# unchecking its row and clicking Apply returns a config with None for
# that constraint.
# ===========================================================================
def test_constraints_settings_dialog_disabling_a_toggle_clears_its_threshold(qtbot):
    # Arrange — elective_conflict_cap starts active at k=4.
    captured = {}
    on_apply = lambda config: captured.setdefault("config", config)
    current_config = ConstraintsConfig(elective_conflict_cap=4)
    dialog = ConstraintsSettingsDialog(on_apply=on_apply, current_config=current_config)
    qtbot.addWidget(dialog)
    checkbox, spinbox = dialog._rows[2]  # elective_conflict_cap row
    assert checkbox.isChecked() is True

    # Act
    checkbox.setChecked(False)
    apply_btn = dialog.findChild(QPushButton, "dialog-select")
    qtbot.mouseClick(apply_btn, Qt.MouseButton.LeftButton)

    # Assert
    config = captured["config"]
    assert config.elective_conflict_cap is None
