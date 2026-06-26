"""Unit tests for SolutionBarWidget — the output screen's navigation toolbar.

The widget exposes back/export controls, prev/next schedule navigation, and
a four-button database paging group (first/prev/next/last page), plus a
solution-number input and counters. Tests cover the default state before
any schedule is loaded (paging group hidden, counters at placeholder
values), button tooltips, that every button's click reaches a connected
slot exactly once, and that a disabled button's click never fires its slot.

Conventions:
- Each test carries a unique TC-SBW-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections. Where
  construction itself is the behaviour under test (default state, static
  tooltips), the construction call is placed under Act rather than Arrange.
- Tests use the shared `qapp` fixture (tests/conftest.py) via
  `pytestmark = pytest.mark.usefixtures("qapp")`; no other conftest fixture
  applies to this widget's plain construction.
"""
import pytest
from unittest.mock import MagicMock
from src.gui.features.output.widgets.SolutionBarWidget import SolutionBarWidget

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-SBW-001: before any schedule is loaded, the database paging group must
# stay hidden and the counters/input must show their placeholder values —
# the bar should not imply paged results exist until there are any.
# ===========================================================================
def test_solution_bar_initial_state():
    # Act — construction itself produces the default state under test.
    widget = SolutionBarWidget()

    # Assert
    assert widget.back_btn is not None
    assert widget.export_btn is not None
    assert widget.prev_btn is not None
    assert widget.next_btn is not None
    assert widget.first_page_btn is not None
    assert widget.prev_page_btn is not None
    assert widget.next_page_btn is not None
    assert widget.last_page_btn is not None
    
    assert widget.solution_input.text() == ""
    assert widget.solution_input.placeholderText() == "Solution number"
    assert widget.total_solutions_label.text() == "/ 10,000"
    assert widget.page_label.text() == "Page 1 / 1"
    assert widget.pages_group.isHidden() is True

# ===========================================================================
# TC-SBW-002: back_btn and export_btn must carry tooltips explaining their
# purpose — the user has no other label on these icon-only buttons.
# ===========================================================================
def test_solution_bar_action_tooltips():
    # Act — construction itself sets the tooltips under test.
    widget = SolutionBarWidget()

    # Assert
    assert "Back to input screen" in widget.back_btn.toolTip()
    assert "Export the current schedule as PDF or TXT" in widget.export_btn.toolTip()

# ===========================================================================
# TC-SBW-003: back_btn and export_btn must each reach a connected slot
# exactly once per click — confirms real Qt signals, not inert buttons.
# ===========================================================================
def test_solution_bar_back_and_export_clicks():
    # Arrange
    widget = SolutionBarWidget()
    mock_back = MagicMock()
    mock_export = MagicMock()
    
    widget.back_btn.clicked.connect(mock_back)
    widget.export_btn.clicked.connect(mock_export)
    
    # Act
    widget.back_btn.click()
    widget.export_btn.click()
    
    # Assert
    assert mock_back.call_count == 1
    assert mock_export.call_count == 1

# ===========================================================================
# TC-SBW-004: prev_btn/next_btn (in-memory schedule navigation) must each
# fire their connected slot exactly once per click, independent of the
# database-paging buttons tested separately below.
# ===========================================================================
def test_solution_bar_navigation_clicks():
    # Arrange
    widget = SolutionBarWidget()
    mock_prev = MagicMock()
    mock_next = MagicMock()
    
    widget.prev_btn.clicked.connect(mock_prev)
    widget.next_btn.clicked.connect(mock_next)
    
    # Act
    widget.prev_btn.click()
    widget.next_btn.click()
    
    # Assert
    assert mock_prev.call_count == 1
    assert mock_next.call_count == 1

# ===========================================================================
# TC-SBW-005: all four database-paging buttons (first/prev/next/last page)
# must each fire their connected slot exactly once per click — the SQLite-
# backed paging window depends on each one being wired correctly.
# ===========================================================================
def test_solution_bar_paging_clicks():
    # Arrange
    widget = SolutionBarWidget()
    mock_first_page = MagicMock()
    mock_prev_page = MagicMock()
    mock_next_page = MagicMock()
    mock_last_page = MagicMock()
    
    widget.first_page_btn.clicked.connect(mock_first_page)
    widget.prev_page_btn.clicked.connect(mock_prev_page)
    widget.next_page_btn.clicked.connect(mock_next_page)
    widget.last_page_btn.clicked.connect(mock_last_page)
    
    # Act
    widget.first_page_btn.click()
    widget.prev_page_btn.click()
    widget.next_page_btn.click()
    widget.last_page_btn.click()
    
    # Assert
    assert mock_first_page.call_count == 1
    assert mock_prev_page.call_count == 1
    assert mock_next_page.call_count == 1
    assert mock_last_page.call_count == 1

# ===========================================================================
# TC-SBW-006: a click on a disabled prev_btn must not reach its connected
# slot — the button has to be genuinely disabled at the Qt level, the same
# guard the output presenter relies on at the first/last schedule.
# ===========================================================================
def test_solution_bar_disabled_clicks_rejection():
    # Arrange
    widget = SolutionBarWidget()
    mock_prev = MagicMock()
    widget.prev_btn.clicked.connect(mock_prev)
    
    # Act
    widget.prev_btn.setEnabled(False)
    widget.prev_btn.click()
    
    # Assert
    assert mock_prev.call_count == 0
