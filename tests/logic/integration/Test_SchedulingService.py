import pytest
from unittest.mock import MagicMock, patch, ANY
from src.application.services.SchedulingService import SchedulingService, _run_scheduler_process
from src.models.Enums import Semester

# ===========================================================================
# TC-SCHED-SVC-001 : Test that build_slots instantiates SlotBuilder and builds slots correctly
# ===========================================================================
def test_build_slots(make_course, make_period, make_program_entry, mock_repository):
    # Arrange
    service = SchedulingService(mock_repository)
    program_id="83101"
    pe = make_program_entry(program_id=program_id)
    c = make_course(course_id="10101", program_entries=[pe])
    p = make_period()
    
    # Act
    slots = service.build_slots([program_id], [c], [p])
    
    # Assert
    assert len(slots) > 0
    assert slots[0].course.courseId == "10101"


# ===========================================================================
# TC-SCHED-SVC-002 : Test that generate_async starts background process and starts the QThread worker.
# ===========================================================================
@patch("src.application.services.SchedulingService.Process")
@patch("src.application.services.SchedulingService.Queue")
@patch("src.application.services.SchedulingService.Event")
@patch("src.application.services.SchedulingService.SchedulerWorker")
def test_generate_async(mock_worker_cls, mock_event, mock_queue, mock_process_cls, make_course, make_period, mock_repository):
    # Arrange
    service = SchedulingService(mock_repository)
    c = make_course()
    p = make_period()
    
    mock_worker = MagicMock()
    mock_worker_cls.return_value = mock_worker
    
    mock_process = MagicMock()
    mock_process_cls.return_value = mock_process
    
    # Act
    worker = service.generate_async(["83101"], [c], [p], max_results=50, num_processes=1)
    
    # Assert
    # assert the process is created and is a daemon
    assert mock_process_cls.call_count == 1
    kwargs = mock_process_cls.call_args[1]
    assert kwargs.get("daemon") is True
    
    # assert the worker is created and started
    assert mock_worker_cls.call_count == 1
    kwargs = mock_worker_cls.call_args[1]
    assert kwargs.get("repository") == mock_repository
    assert mock_worker.start.call_count == 1
    assert worker == mock_worker


# ===========================================================================
# TC-SCHED-SVC-003: Test that cancel is a safe no-op when no worker is active.
# ===========================================================================
def test_cancel_no_active_worker(mock_repository):
    # Arrange
    service = SchedulingService(mock_repository)
    
    # Act
    service.cancel()
    
    # Assert
    assert service._worker is None


# ===========================================================================
# TC-SCHED-SVC-004: Test that cancel triggers the cancel method on the active worker.
# ===========================================================================
def test_cancel_with_active_worker(mock_repository):
    # Arrange
    service = SchedulingService(mock_repository)
    mock_worker = MagicMock()
    service._worker = mock_worker
    
    # Act
    service.cancel()
    
    # Assert
    assert mock_worker.cancel.call_count == 1


# ===========================================================================
# TC-SCHED-SVC-005: Test that _run_scheduler_process helper instantiates SchedulerProcessRunner and calls run.
# ===========================================================================
@patch("src.application.services.SchedulingService.SchedulerProcessRunner")
def test_run_scheduler_process_helper(mock_runner_cls):
    # Arrange
    mock_runner = MagicMock()
    mock_runner_cls.return_value = mock_runner
    
    slots = []
    courses = []
    selected_programs = []
    queue = MagicMock()
    cancel_event = MagicMock()
    
    # Act
    _run_scheduler_process(slots, courses, selected_programs, queue, cancel_event, max_results=10, batch_size=1000)
    
    # Assert
    assert mock_runner_cls.call_count == 1
    args, kwargs = mock_runner_cls.call_args
    assert args[0] == slots
    assert args[1] == ANY
    assert args[2] == queue
    assert args[3] == cancel_event
    assert args[4] == 10
    assert mock_runner.run.call_count == 1


# ===========================================================================
# TC-SCHED-SVC-006: Test that generate_async propagates ValueError if a course has no matching exam period.
# ===========================================================================
def test_generate_async_raises_value_error_for_orphan_course(make_course, make_period, make_program_entry, mock_repository):
    # Arrange
    service = SchedulingService(mock_repository)
    pe = make_program_entry(program_id="83101", semester=Semester.SPRI)
    orphan_course = make_course(course_id="10101", program_entries=[pe])
    fall_period = make_period(semester=Semester.FALL)
    
    # Act & Assert
    with pytest.raises(ValueError):
        service.generate_async(["83101"], [orphan_course], [fall_period])


# ===========================================================================
# TC-SCHED-SVC-007: Test that build_slots propagates ValueError if a course has no matching exam period.
# ===========================================================================
def test_build_slots_raises_value_error_for_orphan_course(make_course, make_period, make_program_entry, mock_repository):
    # Arrange
    service = SchedulingService(mock_repository)
    pe = make_program_entry(program_id="83101", semester=Semester.SPRI)
    orphan_course = make_course(course_id="10101", program_entries=[pe])
    fall_period = make_period(semester=Semester.FALL)
    
    # Act & Assert
    with pytest.raises(ValueError):
        service.build_slots(["83101"], [orphan_course], [fall_period])


# ===========================================================================
# TC-SCHED-SVC-008: Test that generate_async uses the DEFAULT_MAX_RESULTS constant.
# ===========================================================================
@patch("src.application.services.SchedulingService.Process")
@patch("src.application.services.SchedulingService.Queue")
@patch("src.application.services.SchedulingService.Event")
@patch("src.application.services.SchedulingService.SchedulerWorker")
def test_generate_async_uses_default_max_results(mock_worker_cls, mock_event, mock_queue, mock_process_cls, make_course, make_period, mock_repository):
    # Arrange
    service = SchedulingService(mock_repository)
    c = make_course()
    p = make_period()
    
    # Act
    service.generate_async(["83101"], [c], [p], num_processes=1)
    
    # Assert
    assert mock_process_cls.call_count == 1
    args, kwargs = mock_process_cls.call_args
    process_args = kwargs.get("args") or args[0]
    assert process_args[-2] == 1000000
    assert process_args[-1] == 1000
