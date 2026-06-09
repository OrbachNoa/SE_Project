import pytest
from unittest.mock import MagicMock
from src.gui.features.output.OutputScreenPresenter import OutputScreenPresenter
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel, ScheduleItemViewModel
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

# ===========================================================================
# TC-OSP-001: test refresh counter when total is 0.
# ===========================================================================
def test_presenter_refresh_counter_zero_solutions():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 0
    
    # Act
    presenter.refresh_counter()
    
    # Assert
    assert view.set_solution_counter.call_count == 1
    assert view.set_solution_counter.call_args[0] == ("No solutions",)
    assert view.set_solution_controls.call_count == 1
    assert view.set_solution_controls.call_args.kwargs == {"can_prev": False, "can_next": False, "can_export": False}

# ===========================================================================
# TC-OSP-002: test refresh counter when total is greater than 0.
# ===========================================================================
def test_presenter_refresh_counter_multiple_solutions():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 5
    presenter._current_index = 2
    
    # Act
    presenter.refresh_counter()
    
    # Assert
    assert view.set_solution_counter.call_count == 1
    assert view.set_solution_counter.call_args[0] == ("Solution 3 / 5",)
    assert view.set_solution_controls.call_count == 1
    assert view.set_solution_controls.call_args.kwargs == {"can_prev": True, "can_next": True, "can_export": True}

# ===========================================================================
# TC-OSP-003: test page bar is invisible when there is only 1 page.
# ===========================================================================
def test_presenter_refresh_page_bar_single_page():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total_pages = 1
    
    # Act
    presenter.refresh_page_bar()
    
    # Assert
    assert view.set_page_bar_visible.call_count == 1
    assert view.set_page_bar_visible.call_args[0] == (False,)

# ===========================================================================
# TC-OSP-004: test page bar display when multiple pages and next is ready.
# ===========================================================================
def test_presenter_refresh_page_bar_multiple_pages_next_ready():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total_pages = 3
    presenter._current_page = 0
    presenter._sqlite_count = 15_000 
    
    # Act
    presenter.refresh_page_bar()
    
    # Assert
    assert view.set_page_bar.call_count == 1
    assert view.set_page_bar.call_args.kwargs == {
        "visible": True,
        "label": "Page 1 / 3",
        "can_first": False,
        "can_previous": False,
        "can_next": True,
        "can_last": True
    }

# ===========================================================================
# TC-OSP-005: test page bar display when next page is not ready in sqlite cache.
# ===========================================================================
def test_presenter_refresh_page_bar_multiple_pages_next_not_ready():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total_pages = 3
    presenter._current_page = 0
    presenter._sqlite_count = 5_000  # < 10,000
    
    # Act
    presenter.refresh_page_bar()
    
    # Assert
    assert view.set_page_bar.call_count == 1
    assert view.set_page_bar.call_args.kwargs == {
        "visible": True,
        "label": "Page 1 / 3",
        "can_first": False,
        "can_previous": False,
        "can_next": False,
        "can_last": False
    }

# ===========================================================================
# TC-OSP-006: test loading pages delegates to controller.
# ===========================================================================
def test_presenter_page_loads():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    controller.get_page_info.return_value = {
        "current_page": 1,
        "total_pages": 3,
        "total_count": 30,
        "window_size": 10,
        "sqlite_count": 25_000
    }
    router = MagicMock()
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total_pages = 3
    presenter._current_page = 0
    
    # Act
    presenter.on_next_page()
    
    # Assert
    assert controller.load_page.call_count == 1
    assert controller.load_page.call_args[0] == (1,)
    assert presenter._current_page == 1
    assert presenter._total == 10

# ===========================================================================
# TC-OSP-007: test show_current filters and paints correct items.
# ===========================================================================
def test_presenter_show_current_renders_calendar():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    p1 = PeriodEditViewModel(semester="FALL", moed="ALEPH", start_date="2026-06-01", end_date="2026-06-05", excluded_dates=["2026-06-02"])
    item1 = ScheduleItemViewModel(date="2026-06-03", title="Course A", subtitle="83100", tooltip="Details")
    item2 = ScheduleItemViewModel(date="2026-06-10", title="Course B", subtitle="83200", tooltip="Details")
    
    schedule_view = ScheduleViewModel(items=[item1, item2], current_index=0, total=1)
    controller.get_schedule_view.return_value = schedule_view
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1
    presenter._periods.reset([p1])
    
    # Act
    presenter.show_current()
    
    # Assert
    assert view.set_screen_updates.call_count == 2
    assert view.set_screen_updates.call_args_list[0][0] == (False,)
    assert view.set_screen_updates.call_args_list[1][0] == (True,)
    
    assert view.set_period_navigation.call_count == 1
    assert view.set_period_navigation.call_args[0] == ("Semester FALL - Moed ALEPH (1/1)", False, False)
    
    assert view.render_calendar.call_count == 1
    args = view.render_calendar.call_args[0]
    assert args[0] == ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]
    assert args[1] == ["2026-06-02"]
    assert len(args[2]) == 1
    assert args[2][0].date == "2026-06-03"

# ===========================================================================
# TC-OSP-008: test show_current handles errors when reading schedule fails.
# ===========================================================================
def test_presenter_show_current_handles_exception():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    controller.get_schedule_view.side_effect = Exception("Database read failure")
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1
    
    # Act
    presenter.show_current()
    
    # Assert
    assert view.show_display_error.call_count == 1
    assert "Database read failure" in view.show_display_error.call_args[0][0]
    assert view.set_screen_updates.call_count == 2
    assert view.set_screen_updates.call_args_list[0][0] == (False,)
    assert view.set_screen_updates.call_args_list[1][0] == (True,)

# ===========================================================================
# TC-OSP-009: test export pdf is rejected when total is 0.
# ===========================================================================
def test_presenter_export_pdf_guard_total_zero():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 0
    
    # Act
    presenter.on_export_pdf()
    
    # Assert
    assert view.show_nothing_to_export.call_count == 1
    assert view.show_nothing_to_export.call_args[0] == ("There is no schedule to export yet.",)

# ===========================================================================
# TC-OSP-010: test export pdf is rejected when schedule has no exams.
# ===========================================================================
def test_presenter_export_pdf_guard_empty_schedule():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    empty_view = ScheduleViewModel(items=[], current_index=0, total=1)
    controller.get_schedule_view.return_value = empty_view
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1
    
    # Act
    presenter.on_export_pdf()
    
    # Assert
    assert view.show_nothing_to_export.call_count == 1
    assert view.show_nothing_to_export.call_args[0] == ("This schedule has no exams to export.",)

# ===========================================================================
# TC-OSP-011: test export pdf handles errors when reading schedule fails.
# ===========================================================================
def test_presenter_export_pdf_handles_exception():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    controller.get_schedule_view.side_effect = Exception("Export retrieval failure")
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1
    
    # Act
    presenter.on_export_pdf()
    
    # Assert
    assert view.show_export_error.call_count == 1
    assert "Export retrieval failure" in view.show_export_error.call_args[0][0]

# ===========================================================================
# TC-OSP-012: test export pdf executes successfully on valid schedule.
# ===========================================================================
def test_presenter_export_pdf_success():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    valid_view = ScheduleViewModel(items=[ScheduleItemViewModel(date="2026-06-01", title="A", subtitle="B", tooltip="C")], current_index=0, total=1)
    controller.get_schedule_view.return_value = valid_view
    
    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1
    
    # Act
    presenter.on_export_pdf()
    
    # Assert
    assert view.export_schedule_pdf.call_count == 1
    assert view.export_schedule_pdf.call_args[0] == (valid_view, 0)
