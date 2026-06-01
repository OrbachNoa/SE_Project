import queue
import pytest
import sys
from unittest.mock import MagicMock, patch

from src.concurrency.SchedulerWorker import SchedulerWorker
from src.concurrency.SchedulerProcessRunner import SchedulerProcessRunner

# ===========================================================================
# TC-SCHED-WORK-001: Test that SchedulerWorker dispatches queue messages to corresponding signals.
# ===========================================================================
def test_worker_dispatches_messages():
    # Arrange
    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()
    
    mock_queue.get.side_effect = [
        ("SCHEDULE_BATCH", ["dto1", "dto2"]),
        ("PROGRESS", 50),
        ("FINISHED", None)
    ]
    
    worker = SchedulerWorker(mock_queue, mock_cancel_event, mock_process)
    
    found_schedules = []
    progress_vals = []
    finished_called = False
    
    worker.schedule_found.connect(found_schedules.append)
    worker.progress_updated.connect(progress_vals.append)
    worker.search_finished.connect(lambda: setattr(sys.modules[__name__], "finished_called", True))
    
    setattr(sys.modules[__name__], "finished_called", False)
    
    # Act
    worker.run()
    
    # Assert
    assert found_schedules == ["dto1", "dto2"]
    assert progress_vals == [50]
    assert getattr(sys.modules[__name__], "finished_called") is True


# ===========================================================================
# TC-SCHED-WORK-002: Test that if the process dies unexpectedly, SchedulerWorker handles it and emits error.
# ===========================================================================
def test_worker_process_crash_drainage_path():
    # Arrange
    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()
    
    mock_queue.get.side_effect = queue.Empty()
    
    mock_process.is_alive.return_value = False
    mock_process.exitcode = 137
    
    worker = SchedulerWorker(mock_queue, mock_cancel_event, mock_process)
    
    error_msg = None
    def on_error(msg):
        nonlocal error_msg
        error_msg = msg
    worker.error_occurred.connect(on_error)
    
    # Act
    worker.run()
    
    # Assert
    assert error_msg is not None
    assert "crashed unexpectedly" in error_msg
    assert "137" in error_msg


# ===========================================================================
# TC-SCHED-WORK-003: Test that cancel flow sets event, drains queue, and terminates process if needed.
# ===========================================================================
def test_worker_cancel_graceful_and_terminate():
    # Arrange
    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()
    
    mock_process.is_alive.return_value = True
    mock_queue.empty.side_effect = [False, False, True]
    
    worker = SchedulerWorker(mock_queue, mock_cancel_event, mock_process)
    
    # Act
    worker.cancel()
    
    # Assert
    assert mock_cancel_event.set.call_count == 1
    assert any(kwargs.get("timeout") == 0.5 for _, _, kwargs in mock_process.join.mock_calls)
    assert mock_process.terminate.call_count == 1
    assert mock_queue.get_nowait.call_count == 2


# ===========================================================================
# TC-SCHED-WORK-004: Test that SchedulerProcessRunner sets up observer, scheduler, and runs search.
# ===========================================================================
@patch("src.concurrency.SchedulerProcessRunner.Scheduler")
@patch("src.concurrency.SchedulerProcessRunner.QueueScheduleObserver")
def test_process_runner_success(mock_obs_cls, mock_sched_cls):
    # Arrange
    mock_scheduler = MagicMock()
    mock_sched_cls.return_value = mock_scheduler
    mock_observer = MagicMock()
    mock_obs_cls.return_value = mock_observer
    
    queue = MagicMock()
    cancel_event = MagicMock()
    slots = []
    checkers = []
    
    runner = SchedulerProcessRunner(slots, checkers, queue, cancel_event, max_results=10)
    
    # Act
    runner.run()
    
    # Assert
    assert mock_scheduler.generateSchedules.call_count == 1
    call_args = mock_scheduler.generateSchedules.call_args[0]
    assert call_args[0] == slots
    assert call_args[1] == mock_observer
    assert call_args[2] == 10
    assert mock_observer.on_finished.call_count == 1


# ===========================================================================
# TC-SCHED-WORK-005: Test that SchedulerProcessRunner handles exceptions and reports them via observer.
# ===========================================================================
@patch("src.concurrency.SchedulerProcessRunner.Scheduler")
@patch("src.concurrency.SchedulerProcessRunner.QueueScheduleObserver")
def test_process_runner_error_handling(mock_obs_cls, mock_sched_cls):
    # Arrange
    mock_scheduler = MagicMock()
    mock_sched_cls.return_value = mock_scheduler
    mock_scheduler.generateSchedules.side_effect = RuntimeError("backtracking error")
    
    mock_observer = MagicMock()
    mock_obs_cls.return_value = mock_observer
    
    queue = MagicMock()
    cancel_event = MagicMock()
    slots = []
    checkers = []
    
    runner = SchedulerProcessRunner(slots, checkers, queue, cancel_event, max_results=10)
    
    # Act
    runner.run()
    
    # Assert
    assert mock_observer.on_error.call_count == 1
    error_msg = mock_observer.on_error.call_args[0][0]
    assert "Fatal scheduling error" in error_msg
    assert "backtracking error" in error_msg
