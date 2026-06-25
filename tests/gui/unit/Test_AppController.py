import pytest
from unittest.mock import MagicMock
from src.application.AppController import AppController
from src.application.ImportBoundary import ImportMode, ImportResult
from src.application.errors.ErrorModel import AppErrorInfo, ErrorCategory, ErrorSeverity
from src.logic.feasibility.InfeasibleScheduleError import InfeasibleScheduleError

pytestmark = pytest.mark.usefixtures("qapp")

@pytest.fixture
def mock_importer():
    return MagicMock()

@pytest.fixture
def mock_scheduler():
    return MagicMock()

@pytest.fixture
def mock_exporter():
    return MagicMock()

@pytest.fixture
def mock_mapper():
    return MagicMock()

@pytest.fixture
def controller(mock_importer, mock_scheduler, mock_exporter, mock_mapper):
    return AppController(
        importer=mock_importer,
        scheduler=mock_scheduler,
        exporter=mock_exporter,
        mapper=mock_mapper,
    )


# ===========================================================================
# TC-AC-001: test load_file delegating to the importer
# ===========================================================================
def test_load_file(mock_importer, controller):
    # Arrange
    expected_result = ImportResult(success=True, loaded_count=10, errors=[])
    mock_importer.load_file.return_value = expected_result

    # Act
    result = controller.load_file("path/to/file.csv", "courses", ImportMode.REPLACE)

    # Assert
    assert mock_importer.load_file.call_count == 1
    assert mock_importer.load_file.call_args[0] == ("path/to/file.csv", "courses", ImportMode.REPLACE)
    assert result == expected_result

# ===========================================================================
# TC-AC-002: test update_exam_periods delegating to input state
# ===========================================================================
def test_update_exam_periods(controller):
    # Arrange
    controller._input_state = MagicMock()

    # Act
    controller.update_exam_periods(["vm1", "vm2"])

    # Assert
    assert controller._input_state.apply_period_edits.call_count == 1
    assert controller._input_state.apply_period_edits.call_args[0][0] == ["vm1", "vm2"]

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
def test_generate_schedules_starts_worker(mock_scheduler, controller):
    # Arrange
    mock_worker = MagicMock()
    mock_scheduler.generate_async.return_value = mock_worker

    # Act
    controller.generate_schedules(["83101"])

    # Assert
    assert mock_scheduler.generate_async.call_count == 1
    assert mock_scheduler.generate_async.call_args[0][0] == ["83101"]
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
# TC-AC-005b: infeasible input is shown as a clean message, not a traceback
# ===========================================================================
def test_generate_schedules_infeasible_emits_clean_message(mock_scheduler, controller):
    # Arrange
    mock_scheduler.generate_async.side_effect = InfeasibleScheduleError(
        ["too many exams in June"]
    )
    error_slot = MagicMock()
    controller.error_occurred.connect(error_slot)

    # Act
    controller.generate_schedules(["83101"])

    # Assert — the user sees the reason, never a Python traceback.
    assert error_slot.call_count == 1
    message = error_slot.call_args[0][0]
    assert "too many exams in June" in message
    assert "Traceback" not in message


# ===========================================================================
# TC-AC-005c: a MemoryError from the scheduler is shown as a resource problem
# ===========================================================================
def test_generate_schedules_memory_error_shown_as_resource(mock_scheduler, controller):
    # Arrange
    mock_scheduler.generate_async.side_effect = MemoryError("out of memory")
    error_slot = MagicMock()
    controller.error_occurred.connect(error_slot)

    # Act
    controller.generate_schedules(["83101"])

    # Assert — friendly resource message, no raw exception text.
    assert error_slot.call_count == 1
    message = error_slot.call_args[0][0]
    assert "memory" in message.lower()
    assert "MemoryError" not in message


# ===========================================================================
# TC-AC-006: test cancel_scheduling when worker is active and running
# ===========================================================================
def test_cancel_scheduling_active_worker(mock_scheduler, controller):
    # Arrange
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    controller._worker = mock_worker

    # Act
    controller.cancel_scheduling()

    # Assert
    assert mock_scheduler.cancel.call_count == 1

# ===========================================================================
# TC-AC-007: test cancel_scheduling when worker is not running
# ===========================================================================
def test_cancel_scheduling_inactive_worker(mock_scheduler, controller):
    # Arrange
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = False
    controller._worker = mock_worker

    # Act
    controller.cancel_scheduling()

    # Assert
    assert mock_scheduler.cancel.call_count == 0

# ===========================================================================
# TC-AC-008: test get_schedule_view delegating to the mapper
# ===========================================================================
def test_get_schedule_view(mock_mapper, controller):
    # Arrange
    controller._schedule_state = MagicMock()
    controller._schedule_state.count.return_value = 10

    # Act
    controller.get_schedule_view(3)

    # Assert
    assert mock_mapper.to_schedule_vm.call_count == 1
    assert mock_mapper.to_schedule_vm.call_args.kwargs["current_index"] == 3

# ===========================================================================
# TC-AC-009: test save_schedule delegating to the exporter
# ===========================================================================
def test_save_schedule(mock_exporter, controller):
    # Arrange
    controller._schedule_state = MagicMock()
    dto = controller._schedule_state.get_schedule.return_value

    # Act
    controller.save_schedule(2, "output.pdf")

    # Assert
    assert mock_exporter.save.call_count == 1
    assert mock_exporter.save.call_args[0] == (dto, "output.pdf")

# ===========================================================================
# TC-AC-010: test load_page delegating to the schedule state
# ===========================================================================
def test_load_page(controller):
    # Arrange
    controller._schedule_state = MagicMock()

    # Act
    controller.load_page(5)

    # Assert
    assert controller._schedule_state.load_page.call_count == 1
    assert controller._schedule_state.load_page.call_args[0][0] == 5

# ===========================================================================
# TC-AC-011: test get_page_info delegating to the schedule state
# ===========================================================================
def test_get_page_info(controller):
    # Arrange
    mock_state = MagicMock()
    mock_state.current_page = 1
    mock_state.total_pages.return_value = 3
    mock_state.count.return_value = 30
    mock_state.current_window_size.return_value = 10
    mock_state.sqlite_count.return_value = 30
    controller._schedule_state = mock_state

    # Act
    info = controller.get_page_info()

    # Assert
    assert info["current_page"] == 1
    assert info["total_pages"] == 3
    assert info["total_count"] == 30

# ===========================================================================
# TC-AC-012: test get_loaded_courses, get_loaded_periods, and get_mapper
# ===========================================================================
def test_facade_getters(mock_mapper, controller):
    # Act
    courses = controller.get_loaded_courses()
    periods = controller.get_loaded_periods()
    mapper = controller.get_mapper()

    # Assert
    assert courses == []
    assert periods == []
    assert mapper is mock_mapper

# ===========================================================================
# TC-AC-013: test on_app_closing cancels scheduling
# ===========================================================================
def test_on_app_closing(mock_scheduler, controller):
    # Arrange
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    controller._worker = mock_worker

    # Act
    controller.on_app_closing()

    # Assert
    assert mock_scheduler.cancel.call_count == 1

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
def test_handle_schedules_batch_found_with_early_nav(controller):
    # Arrange
    mock_state = MagicMock()
    mock_state.count.return_value = 150
    mock_state.is_first_window_ready.return_value = True
    controller._schedule_state = mock_state

    batch_slot = MagicMock()
    total_slot = MagicMock()
    early_slot = MagicMock()
    controller.schedules_batch_found.connect(batch_slot)
    controller.total_count_updated.connect(total_slot)
    controller.early_results_ready.connect(early_slot)

    # Act
    controller._handle_schedules_batch_found(10)

    # Assert
    assert batch_slot.call_count == 1
    assert batch_slot.call_args[0][0] == 10
    assert mock_state.add_schedules_batch.call_args[0][0] == 10
    assert total_slot.call_count == 1
    assert total_slot.call_args[0][0] == 150
    assert early_slot.call_count == 1
    assert controller._early_nav_fired is True

# ===========================================================================
# TC-AC-016: test handle_schedules_batch_found suppresses second early nav
# ===========================================================================
def test_handle_schedules_batch_found_early_nav_only_once(controller):
    # Arrange
    mock_state = MagicMock()
    mock_state.count.return_value = 200
    mock_state.is_first_window_ready.return_value = True
    controller._schedule_state = mock_state

    early_slot = MagicMock()
    controller.early_results_ready.connect(early_slot)
    controller._early_nav_fired = True

    # Act
    controller._handle_schedules_batch_found(10)

    # Assert
    assert early_slot.call_count == 0
    assert controller._early_nav_fired is True

# ===========================================================================
# TC-AC-017: test poll_progress emits progress_updated signal with total count
# ===========================================================================
def test_poll_progress(controller):
    # Arrange
    mock_state = MagicMock()
    mock_state.count.return_value = 85
    controller._schedule_state = mock_state

    mock_slot = MagicMock()
    controller.progress_updated.connect(mock_slot)

    # Act
    controller._poll_progress()

    # Assert
    assert mock_slot.call_count == 1
    assert mock_slot.call_args[0][0] == 85

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
# TC-AC-019: a bare legacy string with no structured record behind it (no
# worker reference at all) is mapped to a safe message, never forwarded
# verbatim — this is exactly what the error layer exists to prevent.
# ===========================================================================
def test_handle_error_occurred_bare_string_without_worker_maps_safe(controller):
    # Arrange
    mock_slot = MagicMock()
    controller.error_occurred.connect(mock_slot)
    assert controller._worker is None

    # Act
    controller._handle_error_occurred("Process died")

    # Assert
    assert mock_slot.call_count == 1
    message = mock_slot.call_args[0][0]
    assert message != "Process died"
    assert "Process died" not in message


# ===========================================================================
# TC-AC-019b: when the originating worker carries a structured last_error,
# the legacy string signal is overridden by that record's clean message
# (full category/severity reaches the log, the string itself is discarded).
# ===========================================================================
def test_handle_error_occurred_prefers_worker_last_error_over_string(controller):
    # Arrange
    mock_worker = MagicMock()
    mock_worker.last_error = AppErrorInfo(
        code="SCHEDULER_PROCESS_ERROR",
        category=ErrorCategory.SCHEDULING,
        severity=ErrorSeverity.ERROR,
        user_message="The scheduler reported a problem during the search.",
        technical_message="Process died",
    )
    controller._worker = mock_worker
    mock_slot = MagicMock()
    controller.error_occurred.connect(mock_slot)

    # Act — the signal itself still only carries the bare legacy string.
    controller._handle_error_occurred("Process died")

    # Assert — the structured record's clean message wins.
    assert mock_slot.call_count == 1
    assert mock_slot.call_args[0][0] == "The scheduler reported a problem during the search."


# ===========================================================================
# TC-AC-020: a structured AppErrorInfo payload from a worker is unpacked and
# only its clean user message reaches the GUI.
# ===========================================================================
def test_handle_error_occurred_unpacks_payload(controller):
    # Arrange
    info = AppErrorInfo(
        code="SCHEDULER_PROCESS_CRASHED",
        category=ErrorCategory.INFRASTRUCTURE,
        severity=ErrorSeverity.CRITICAL,
        user_message="The scheduling engine crashed unexpectedly.",
        technical_message="exit code 137",
    )
    mock_slot = MagicMock()
    controller.error_occurred.connect(mock_slot)

    # Act
    controller._handle_error_occurred(info.to_payload())

    # Assert — the GUI gets the user message, never the technical detail.
    assert mock_slot.call_count == 1
    assert mock_slot.call_args[0][0] == "The scheduling engine crashed unexpectedly."


# ===========================================================================
# TC-AC-021: map_error gives presenters a friendly message for a file-locked
# export (PermissionError), with no raw exception text or traceback leaking.
# ===========================================================================
def test_map_error_permission_denied_export_is_friendly(controller):
    # Act
    message = controller.map_error(
        PermissionError(13, "denied", "report.xlsx"),
        {"operation": "save_schedule", "screen": "output", "export_format": "excel"},
    )

    # Assert
    assert "report.xlsx" in message
    assert "Traceback" not in message
    assert "PermissionError" not in message


# ===========================================================================
# TC-AC-022: map_error never leaks raw exception text for an unmapped error;
# it shows a safe, category-appropriate generic message instead.
# ===========================================================================
def test_map_error_unknown_exception_is_safe_generic(controller):
    # Act
    message = controller.map_error(
        Exception("some internal detail nobody should see"),
        {"operation": "render_calendar", "screen": "output"},
    )

    # Assert
    assert "some internal detail nobody should see" not in message
    assert "Traceback" not in message
    assert message  # always something to show


# ===========================================================================
# TC-AC-023: map_error logs the technical detail even though the returned
# message is the clean one (verifies the log is not silently skipped).
# ===========================================================================
def test_map_error_logs_technical_detail(controller, monkeypatch):
    # Arrange
    logged = []
    monkeypatch.setattr(
        controller._error_logger, "log", lambda info, cause=None: logged.append((info, cause))
    )
    exc = ValueError("Row 3: invalid date")

    # Act
    message = controller.map_error(exc, {"operation": "load_file", "screen": "input"})

    # Assert
    assert message == "Row 3: invalid date"
    assert len(logged) == 1
    info, cause = logged[0]
    assert info.technical_message == "ValueError: Row 3: invalid date"
    assert cause is exc
