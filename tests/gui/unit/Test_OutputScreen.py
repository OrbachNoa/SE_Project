import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import pyqtSignal, QObject
from src.gui.features.output.OutputScreen import OutputScreen
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel, ScheduleItemViewModel

pytestmark = pytest.mark.usefixtures("qapp")

# --- Mock controller for testing purposes. ---
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

@pytest.fixture
def mock_controller(viewmodel_mapper):
    controller = MockController()
    from datetime import date
    from src.models.Domain import ExamPeriod
    from src.models.Enums import Semester, Moed
    p = ExamPeriod(semester=Semester.FALL, moed=Moed.ALEPH, start_date=date(2026, 6, 1), end_date=date(2026, 6, 30), excluded_dates=[])
    controller.get_loaded_periods = MagicMock(return_value=[p])
    controller.get_mapper = MagicMock(return_value=viewmodel_mapper)
    return controller

# ===========================================================================
# TC-OU-UI-001: test initial solution navigation button states.
# ===========================================================================
def test_solution_navigation_initial_state(mock_controller, mock_router):
    # Arrange
    view = ScheduleViewModel(items=[], current_index=0, total=2)
    mock_controller.get_schedule_view.return_value = view
    
    screen = OutputScreen(mock_controller, mock_router)
    
    # Act
    screen.on_enter()
    
    # Assert
    assert screen._prev_btn.isEnabled() is False
    assert screen._next_btn.isEnabled() is True


# ===========================================================================
# TC-OU-UI-002: test next schedule button navigates forward.
# ===========================================================================
def test_next_schedule_button_navigates_forward(mock_controller, mock_router):
    # Arrange
    view0 = ScheduleViewModel(items=[], current_index=0, total=2)
    view1 = ScheduleViewModel(items=[], current_index=1, total=2)
    mock_controller.get_schedule_view.side_effect = [view0, view1]  
    
    screen = OutputScreen(mock_controller, mock_router)
    screen.on_enter()
    
    # Act
    screen.on_next()
    
    # Assert
    assert screen._prev_btn.isEnabled() is True
    assert screen._next_btn.isEnabled() is False
    assert screen._presenter.current_index == 1


# ===========================================================================
# TC-OU-UI-003: test previous schedule button navigates backward.
# ===========================================================================
def test_previous_schedule_button_navigates_backward(mock_controller, mock_router):
    # Arrange
    view0 = ScheduleViewModel(items=[], current_index=0, total=2)
    view1 = ScheduleViewModel(items=[], current_index=1, total=2)
    mock_controller.get_schedule_view.side_effect = [view0, view1, view0]
    
    screen = OutputScreen(mock_controller, mock_router)
    screen.on_enter()
    screen.on_next()  # Setup state: now at index 1
    
    # Act
    screen.on_prev()
    
    # Assert
    assert screen._presenter.current_index == 0
    assert screen._prev_btn.isEnabled() is False
    assert screen._next_btn.isEnabled() is True


# ===========================================================================
# TC-OU-UI-004: test schedule counter updates.
# ===========================================================================
def test_schedule_counter_updates(mock_controller, mock_router):
    # Arrange
    view0 = ScheduleViewModel(items=[], current_index=0, total=2)
    view1 = ScheduleViewModel(items=[], current_index=1, total=2)
    mock_controller.get_schedule_view.side_effect = [view0, view1]
    
    screen = OutputScreen(mock_controller, mock_router)
    screen.on_enter()
    
    # Assert - initial state
    assert screen.solution_bar.solution_input.text() == "1"
    
    # Act
    screen.on_next()
    
    # Assert - after navigation
    assert screen.solution_bar.solution_input.text() == "2"

# ===========================================================================
# TC-OU-UI-005: test calendar shows selected month.
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


# ===========================================================================
# TC-OU-UI-006: test that clicking the back button navigates back to input.
# ===========================================================================
def test_back_button_navigates_to_input_screen(mock_controller, mock_router):
    # Arrange
    screen = OutputScreen(mock_controller, mock_router)
    
    # Act
    screen.solution_bar.back_btn.click()
    
    # Assert
    assert mock_router.back.call_count == 1

