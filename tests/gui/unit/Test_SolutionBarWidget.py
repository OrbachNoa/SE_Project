import pytest
from unittest.mock import MagicMock
from src.gui.features.output.widgets.SolutionBarWidget import SolutionBarWidget

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-SBW-001: test initial layout state of solution bar.
# ===========================================================================
def test_solution_bar_initial_state():
    # Arrange
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
# TC-SBW-002: test tooltips on main action buttons.
# ===========================================================================
def test_solution_bar_action_tooltips():
    # Arrange
    widget = SolutionBarWidget()
    
    # Assert
    assert "Back to input screen" in widget.back_btn.toolTip()
    assert "Save the current schedule as a PDF" in widget.export_btn.toolTip()

# ===========================================================================
# TC-SBW-003: test back and export button clicks trigger signals.
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
# TC-SBW-004: test solution navigation button clicks trigger signals.
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
# TC-SBW-005: test database paging button clicks trigger signals.
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
# TC-SBW-006: test that disabled solution navigation buttons reject clicks.
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
