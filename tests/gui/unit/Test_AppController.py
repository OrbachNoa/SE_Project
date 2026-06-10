import pytest
from unittest.mock import MagicMock
from src.application.AppController import AppController
from src.application.ImportBoundary import ImportMode, ImportResult

pytestmark = pytest.mark.usefixtures("qapp")

@pytest.fixture
def mock_facade():
    return MagicMock()

@pytest.fixture
def controller(mock_facade):
    return AppController(mock_facade)


# ===========================================================================
# TC-AC-001: test load_file delegating to facade
# ===========================================================================
def test_load_file(mock_facade, controller):
    # Arrange
    expected_result = ImportResult(success=True, loaded_count=10, errors=[])
    mock_facade.import_file.return_value = expected_result

    # Act
    result = controller.load_file("path/to/file.csv", "courses", ImportMode.REPLACE)

    # Assert
    assert mock_facade.import_file.call_count == 1
    req = mock_facade.import_file.call_args[0][0]
    assert req.path == "path/to/file.csv"
    assert req.file_type == "courses"
    assert req.mode == ImportMode.REPLACE
    assert result == expected_result

# ===========================================================================
# TC-AC-002: test update_exam_periods delegating to facade
# ===========================================================================
def test_update_exam_periods(mock_facade, controller):
    # Act
    controller.update_exam_periods(["vm1", "vm2"])

    # Assert
    assert mock_facade.update_periods.call_count == 1
    assert mock_facade.update_periods.call_args[0][0] == ["vm1", "vm2"]

# ===========================================================================
# TC-AC-003: test generate_schedules with empty program list emits error
# ===========================================================================
def test_generate_schedules_empty_programs_emits_error(controller):
    # Arrange
    error_slot = MagicMock()
    controller.error_occurred.connect(error_slot)

    # Act
    controller.generate_schedules([])

    # Assert
    assert error_slot.call_count == 1
    assert error_slot.call_args[0][0] == "Please select at least one program before running the scheduler."

# ===========================================================================
# TC-AC-005: test generate_schedules starts worker and connects signals
# ===========================================================================
def test_generate_schedules_starts_worker(mock_facade, controller):
    # Arrange
    mock_worker = MagicMock()
    mock_facade.generate.return_value = mock_worker

    # Act
    controller.generate_schedules(["83101"])

    # Assert
    assert mock_facade.generate.call_count == 1
    assert mock_facade.generate.call_args[0][0] == ["83101"]
    assert controller._worker == mock_worker
    assert controller._early_nav_fired is False
    # Verify signal connections
    assert mock_worker.schedules_batch_found.connect.call_count == 1
    assert mock_worker.schedule_found.connect.call_count == 1
    assert mock_worker.search_finished.connect.call_count == 1
    assert mock_worker.error_occurred.connect.call_count == 1
    assert controller._progress_timer is not None
    assert controller._progress_timer.isActive() is True

# ===========================================================================
# TC-AC-006: test cancel_scheduling when worker is active and running
# ===========================================================================
def test_cancel_scheduling_active_worker(mock_facade, controller):
    # Arrange
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    controller._worker = mock_worker

    # Act
    controller.cancel_scheduling()

    # Assert
    assert mock_facade.cancel_scheduling.call_count == 1

# ===========================================================================
# TC-AC-007: test cancel_scheduling when worker is not running
# ===========================================================================
def test_cancel_scheduling_inactive_worker(mock_facade, controller):
    # Arrange
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = False
    controller._worker = mock_worker

    # Act
    controller.cancel_scheduling()

    # Assert
    assert mock_facade.cancel_scheduling.call_count == 0

# ===========================================================================
# TC-AC-008: test get_schedule_view delegating to facade
# ===========================================================================
def test_get_schedule_view(mock_facade, controller):
    # Act
    controller.get_schedule_view(3)

    # Assert
    assert mock_facade.get_schedule_vm.call_count == 1
    assert mock_facade.get_schedule_vm.call_args[0][0] == 3

# ===========================================================================
# TC-AC-009: test save_schedule delegating to facade
# ===========================================================================
def test_save_schedule(mock_facade, controller):
    # Act
    controller.save_schedule(2, "output.pdf")

    # Assert
    assert mock_facade.export.call_count == 1
    assert mock_facade.export.call_args[0] == (2, "output.pdf")

# ===========================================================================
# TC-AC-010: test load_page delegating to facade
# ===========================================================================
def test_load_page(mock_facade, controller):
    # Act
    controller.load_page(5)

    # Assert
    assert mock_facade.load_page.call_count == 1
    assert mock_facade.load_page.call_args[0][0] == 5

# ===========================================================================
# TC-AC-011: test get_page_info delegating to facade
# ===========================================================================
def test_get_page_info(mock_facade, controller):
    # Arrange
    mock_info = {"current_page": 1}
    mock_facade.get_page_info.return_value = mock_info

    # Act
    info = controller.get_page_info()

    # Assert
    assert mock_facade.get_page_info.call_count == 1
    assert info == mock_info

# ===========================================================================
# TC-AC-012: test get_loaded_courses, get_loaded_periods, and get_mapper delegating to facade
# ===========================================================================
def test_facade_getters(mock_facade, controller):
    # Act
    controller.get_loaded_courses()
    controller.get_loaded_periods()
    controller.get_mapper()

    # Assert
    assert mock_facade.get_loaded_courses.call_count == 1
    assert mock_facade.get_loaded_periods.call_count == 1
    assert mock_facade.get_mapper.call_count == 1

# ===========================================================================
# TC-AC-013: test on_app_closing cancels scheduling
# ===========================================================================
def test_on_app_closing(mock_facade, controller):
    # Arrange
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    controller._worker = mock_worker

    # Act
    controller.on_app_closing()

    # Assert
    assert mock_facade.cancel_scheduling.call_count == 1

# ===========================================================================
# TC-AC-014: test handle_schedule_found emits schedule_found signal
# ===========================================================================
def test_handle_schedule_found(controller):
    # Arrange
    mock_slot = MagicMock()
    controller.schedule_found.connect(mock_slot)
    dto = MagicMock()

    # Act
    controller._handle_schedule_found(dto)

    # Assert
    assert mock_slot.call_count == 1
    assert mock_slot.call_args[0][0] == dto

# ===========================================================================
# TC-AC-015: test handle_schedules_batch_found emits batch and early navigation signals
# ===========================================================================
def test_handle_schedules_batch_found_with_early_nav(mock_facade, controller):
    # Arrange
    batch_slot = MagicMock()
    total_slot = MagicMock()
    early_slot = MagicMock()
    controller.schedules_batch_found.connect(batch_slot)
    controller.total_count_updated.connect(total_slot)
    controller.early_results_ready.connect(early_slot)

    mock_facade.get_total_count.return_value = 150
    mock_facade.is_first_window_ready.return_value = True

    # Act
    controller._handle_schedules_batch_found(10)

    # Assert
    assert batch_slot.call_count == 1
    assert batch_slot.call_args[0][0] == 10
    assert mock_facade.get_total_count.call_count == 1
    assert total_slot.call_count == 1
    assert total_slot.call_args[0][0] == 150
    assert early_slot.call_count == 1
    assert controller._early_nav_fired is True

# ===========================================================================
# TC-AC-016: test handle_schedules_batch_found suppresses second early nav
# ===========================================================================
def test_handle_schedules_batch_found_early_nav_only_once(mock_facade, controller):
    # Arrange
    early_slot = MagicMock()
    controller.early_results_ready.connect(early_slot)
    controller._early_nav_fired = True

    mock_facade.get_total_count.return_value = 200
    mock_facade.is_first_window_ready.return_value = True

    # Act
    controller._handle_schedules_batch_found(10)

    # Assert
    assert early_slot.call_count == 0
    assert controller._early_nav_fired is True

# ===========================================================================
# TC-AC-017: test poll_progress emits progress_updated signal with total count
# ===========================================================================
def test_poll_progress(mock_facade, controller):
    # Arrange
    mock_slot = MagicMock()
    controller.progress_updated.connect(mock_slot)
    mock_facade.get_total_count.return_value = 85

    # Act
    controller._poll_progress()

    # Assert
    assert mock_slot.call_count == 1
    assert mock_slot.call_args[0][0] == 85
    assert mock_facade.get_total_count.call_count == 1

# ===========================================================================
# TC-AC-018: test handle_search_finished emits search_finished signal
# ===========================================================================
def test_handle_search_finished(controller):
    # Arrange
    mock_slot = MagicMock()
    controller.search_finished.connect(mock_slot)
    controller._early_nav_fired = True

    # Act
    controller._handle_search_finished()

    # Assert
    assert mock_slot.call_count == 1
    assert controller._early_nav_fired is False

# ===========================================================================
# TC-AC-019: test handle_error_occurred emits error_occurred signal
# ===========================================================================
def test_handle_error_occurred(controller):
    # Arrange
    mock_slot = MagicMock()
    controller.error_occurred.connect(mock_slot)

    # Act
    controller._handle_error_occurred("Process died")

    # Assert
    assert mock_slot.call_count == 1
    assert mock_slot.call_args[0][0] == "Process died"
