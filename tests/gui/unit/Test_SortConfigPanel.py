"""Unit tests for SortConfigPanel and its SortRow widgets.

The panel renders one SortRow per known scoring criterion (ALL_CRITERIA).
Checking a row's box adds it to the active priority list and assigns it the
next rank badge automatically; rows can be reordered, and Apply emits the
priority list in whatever order the rows are currently displayed — not the
order the panel was constructed with. Tests cover the initial unconfigured
display, automatic badge assignment on enabling a criterion, and that a
manual reorder is reflected in the emitted priority.

Conventions:
- Each test carries a unique TC-SCP-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- Tests use the shared `qapp` fixture (tests/conftest.py) via
  `pytestmark = pytest.mark.usefixtures("qapp")`, plus pytest-qt's `qtbot`
  fixture; no conftest fixture models SortConfigPanel or its rows.
"""
import pytest

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from src.gui.features.output.widgets.SortConfigPanel import SortConfigPanel
from src.logic.comparators.ScheduleScorer import (
    ALL_CRITERIA,
    MANDATORY_SPAN,
    MIN_MANDATORY_GAP,
)

pytestmark = pytest.mark.usefixtures("qapp")


# ===========================================================================
# TC-SCP-001: the panel displays without raising, with one SortRow per
# known criterion.
# ===========================================================================
def test_sort_config_panel_displays_without_error(qtbot):
    # Arrange
    panel = SortConfigPanel(current_priority=[])

    # Act
    qtbot.addWidget(panel)

    # Assert
    assert panel is not None
    assert panel.windowTitle() == "Sort Configuration"
    assert len(panel._rows) == len(ALL_CRITERIA)


# ===========================================================================
# TC-SCP-002: checking a previously-disabled row's checkbox enables it —
# it now counts as part of the active priority list and gets rank badge 1.
# ===========================================================================
def test_sort_config_panel_enabling_a_criterion_adds_it_to_the_list(qtbot):
    # Arrange
    panel = SortConfigPanel(current_priority=[])
    qtbot.addWidget(panel)
    row = panel._rows[0]
    assert row.is_enabled() is False

    # Act
    row.checkbox.setChecked(True)

    # Assert
    assert row.is_enabled() is True
    assert row.badge.text() == "1"


# ===========================================================================
# TC-SCP-003: clicking Apply emits the priority list in the order the rows
# are currently displayed, including after a manual reorder — not the
# order the panel was originally constructed with.
# ===========================================================================
def test_sort_config_panel_apply_emits_priority_matching_displayed_order(qtbot):
    # Arrange — MANDATORY_SPAN listed first, MIN_MANDATORY_GAP second.
    panel = SortConfigPanel(current_priority=[MANDATORY_SPAN, MIN_MANDATORY_GAP])
    qtbot.addWidget(panel)
    received = []
    panel.config_changed.connect(received.append)

    # Act — swap the two enabled rows, then apply.
    panel._move_row_down(0)
    apply_btn = panel.findChild(QPushButton, "dialog-select")
    qtbot.mouseClick(apply_btn, Qt.MouseButton.LeftButton)

    # Assert — the emitted priority follows the post-swap display order.
    assert received == [[MIN_MANDATORY_GAP, MANDATORY_SPAN]]
