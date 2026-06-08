import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import pyqtSignal, QObject
from src.gui.features.output.OutputScreen import OutputScreen
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel, ScheduleItemViewModel

pytestmark = pytest.mark.usefixtures("qapp")

class MockController(QObject):
    total_count_updated = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.get_page_info = MagicMock(return_value={
            "current_page": 0,
            "total_pages": 1,
            "total_count": 2,
            "window_size": 2,
            "sqlite_count": 2,
        })
        self.get_schedule_view = MagicMock()

# ===========================================================================
# TC-UI-OU-001: test previous schedule button.
# ===========================================================================
def test_previous_schedule_button(mock_controller, mock_router):
    # Arrange
    view0 = ScheduleViewModel(items=[], current_index=0, total=2)
    view1 = ScheduleViewModel(items=[], current_index=1, total=2)
    mock_controller.get_schedule_view.side_effect = [view0, view1, view0]
    
    screen = OutputScreen(mock_controller, mock_router)
    screen.on_enter()
    
    # Assert initial
    assert screen._prev_btn.isEnabled() is False
    assert screen._next_btn.isEnabled() is True
    
    # Act
    screen.on_next()
    
    # Assert
    assert screen._prev_btn.isEnabled() is True
    assert screen._current_index == 1
    
    # Act
    screen.on_prev()
    assert screen._current_index == 0
    assert screen._prev_btn.isEnabled() is False

# ===========================================================================
# TC-UI-OU-002: test next schedule button.
# ===========================================================================
def test_next_schedule_button(mock_controller, mock_router):
    # Arrange
    view0 = ScheduleViewModel(items=[], current_index=0, total=2)
    view1 = ScheduleViewModel(items=[], current_index=1, total=2)
    mock_controller.get_schedule_view.side_effect = [view0, view1]
    
    screen = OutputScreen(mock_controller, mock_router)
    screen.on_enter()
    
    # Assert
    assert screen._next_btn.isEnabled() is True
    
    # Act
    screen.on_next()
    
    # Assert
    assert screen._next_btn.isEnabled() is False
    assert screen._current_index == 1

# ===========================================================================
# TC-UI-OU-003: test schedule counter updates.
# ===========================================================================
def test_schedule_counter_updates(mock_controller, mock_router):
    # Arrange
    view0 = ScheduleViewModel(items=[], current_index=0, total=2)
    view1 = ScheduleViewModel(items=[], current_index=1, total=2)
    mock_controller.get_schedule_view.side_effect = [view0, view1]
    
    screen = OutputScreen(mock_controller, mock_router)
    screen.on_enter()
    
    # Assert
    assert screen._counter_label.text() == "Solution  1 / 2"
    
    # Act
    screen.on_next()
    
    # Assert
    assert screen._counter_label.text() == "Solution  2 / 2"

# ===========================================================================
# TC-UI-OU-004: test calendar shows selected month.
# ===========================================================================
def test_calendar_shows_selected_month(mock_controller, mock_router):
    # Arrange
    item = ScheduleItemViewModel(
        date="2026-06-05",
        title="Calculus 1",
        subtitle="10101",
        tooltip="Calculus 1 tooltip"
    )
    view = ScheduleViewModel(items=[item], current_index=0, total=1)
    
    mock_controller.get_page_info.return_value = {
        "current_page": 0,
        "total_pages": 1,
        "total_count": 1,
        "window_size": 1,
        "sqlite_count": 1,
    }
    mock_controller.get_schedule_view.return_value = view
    
    screen = OutputScreen(mock_controller, mock_router)
    
    # Act
    screen.on_enter()
    
    # Assert
    assert "2026-06-05" in screen.calendar_grid._day_layouts
