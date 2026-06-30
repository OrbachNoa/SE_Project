"""Integration tests for the concurrency layer: SchedulerWorker (the QThread
that bridges a worker process's queue to GUI-thread Qt signals) and
SchedulerProcessRunner (the entry point that actually runs inside that
worker process).

SchedulerWorker tests cover normal message dispatch (batch/progress/
finished), the process-crash drainage path when the queue goes empty and
the process has died, a structured AppErrorInfo payload arriving over the
queue, an unexpected IPC read failure being mapped to a clean message
instead of leaking raw exception text, and the cancel flow (set the event,
drain the queue non-blocking, terminate the process if it didn't exit in
time). SchedulerProcessRunner tests cover the success path and two error
paths (a generic RuntimeError and a MemoryError, the latter required to
keep its RESOURCE category rather than becoming a generic infrastructure
failure) — TC-SCHED-WORK-006 also follows that error payload through a
real SchedulerWorker to confirm the two halves of the pipeline agree on
the same structured record.

Conventions:
- Each test carries a unique TC-SCHED-WORK-NNN identifier in the comment
  block above its definition, numbered sequentially (with lettered
  variants for closely related scenarios on the same method).
- Each test body is split into Arrange / Act / Assert sections.
- Tests use the shared `qapp` fixture (tests/conftest.py) via
  `pytestmark = pytest.mark.usefixtures("qapp")`, since SchedulerWorker is
  a QThread. `mock_repository` (also shared) is used wherever a
  SchedulerWorker needs a repository — it is plain `MagicMock(spec=
  SQLiteScheduleRepository)`, identical to what these tests would
  otherwise build locally.
"""
import queue
import pytest
from unittest.mock import MagicMock, patch, ANY

from src.infrastructure.concurrency.SchedulerWorker import SchedulerWorker
from src.infrastructure.concurrency.SchedulerProcessRunner import SchedulerProcessRunner
from src.logic.parallel.WorkUnit import WorkUnit

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-SCHED-WORK-001: Test that SchedulerWorker dispatches queue messages to corresponding signals.
# ===========================================================================
def test_worker_dispatches_messages(mock_repository):
    # Arrange
    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()

    mock_queue.get.side_effect = [
        ("SCHEDULE_BATCH", (b"compressed_data", 2)),
        ("PROGRESS", 50),
        ("FINISHED", None)
    ]
    # A real Queue.get_nowait() raises Empty once drained; SchedulerWorker's
    # shutdown path drains the queue in a `while True` loop that relies on
    # that exception to exit, so a bare MagicMock must be told to raise it
    # too, or the loop (and the test) never returns.
    mock_queue.get_nowait.side_effect = queue.Empty

    worker = SchedulerWorker(mock_queue, mock_cancel_event, [mock_process], mock_repository)

    batch_counts = []
    progress_vals = []
    finished_calls = []

    worker.schedules_batch_found.connect(batch_counts.append)
    worker.progress_updated.connect(progress_vals.append)
    worker.search_finished.connect(lambda: finished_calls.append(True))

    # Act
    worker.run()

    # Assert
    mock_repository.insert_compressed_batch.assert_called_once_with(b"compressed_data", 2, ANY)
    assert batch_counts == [2]
    assert progress_vals == [50]
    assert finished_calls == [True]


# ===========================================================================
# TC-SCHED-WORK-002: Test that if the process dies unexpectedly, SchedulerWorker handles it and emits error.
# ===========================================================================
def test_worker_process_crash_drainage_path(mock_repository):
    # Arrange
    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()

    mock_queue.get.side_effect = queue.Empty()
    mock_queue.get_nowait.side_effect = queue.Empty

    mock_process.is_alive.return_value = False
    mock_process.exitcode = 137
    mock_cancel_event.is_set.return_value = False

    worker = SchedulerWorker(mock_queue, mock_cancel_event, [mock_process], mock_repository)

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
    # The structured record is available for triage with a stable code.
    assert worker.last_error is not None
    assert worker.last_error.code == "SCHEDULER_PROCESS_CRASHED"
    assert worker.last_error.recoverable is False


# ===========================================================================
# TC-SCHED-WORK-002b: a serialised AppErrorInfo ERROR payload from a worker
# process is unpacked into a clean message + structured record.
# ===========================================================================
def test_worker_handles_structured_error_payload(mock_repository):
    # Arrange
    from src.application.errors.ErrorModel import AppErrorInfo, ErrorCategory, ErrorSeverity

    info = AppErrorInfo(
        code="RESOURCE_MEMORY_EXHAUSTED",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.CRITICAL,
        user_message="The scheduler ran out of memory.",
        technical_message="MemoryError during scheduling",
        recoverable=False,
    )

    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()
    mock_queue.get.side_effect = [("ERROR", info.to_payload())]
    mock_queue.get_nowait.side_effect = queue.Empty

    worker = SchedulerWorker(mock_queue, mock_cancel_event, [mock_process], mock_repository)
    messages = []
    worker.error_occurred.connect(messages.append)

    # Act
    worker.run()

    # Assert
    assert messages == ["The scheduler ran out of memory."]
    assert worker.last_error.code == "RESOURCE_MEMORY_EXHAUSTED"


# ===========================================================================
# TC-SCHED-WORK-002c: an unexpected IPC/queue read failure (anything other
# than queue.Empty or the "queue closed" ValueError) is routed through the
# mapper registry instead of building user_message with str(e) directly —
# the raw exception text must never reach the GUI-facing message.
# ===========================================================================
def test_worker_unexpected_queue_read_error_is_mapped_not_raw(mock_repository):
    # Arrange
    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()

    mock_queue.get.side_effect = RuntimeError("pipe broke unexpectedly")
    mock_queue.get_nowait.side_effect = queue.Empty

    worker = SchedulerWorker(mock_queue, mock_cancel_event, [mock_process], mock_repository)
    messages = []
    worker.error_occurred.connect(messages.append)

    # Act
    worker.run()

    # Assert — clean, generic message; the raw exception text/type never leaks.
    assert len(messages) == 1
    assert "pipe broke unexpectedly" not in messages[0]
    assert "RuntimeError" not in messages[0]
    assert worker.last_error is not None
    assert worker.last_error.code == "SCHEDULER_IPC_ERROR"
    assert worker.last_error.recoverable is False
    assert "pipe broke unexpectedly" in worker.last_error.technical_message


# ===========================================================================
# TC-SCHED-WORK-002d: when run_id filtering is enabled, malformed unwrapped
# queue payloads are reported as clean IPC errors instead of escaping the worker.
# ===========================================================================
def test_worker_malformed_run_id_payload_is_mapped_not_raised(mock_repository):
    # Arrange
    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()

    mock_queue.get.side_effect = [("PROGRESS", 50)]
    mock_queue.get_nowait.side_effect = queue.Empty

    worker = SchedulerWorker(
        mock_queue,
        mock_cancel_event,
        [mock_process],
        mock_repository,
        expected_run_id=7,
    )
    messages = []
    worker.error_occurred.connect(messages.append)

    # Act
    worker.run()

    # Assert
    assert len(messages) == 1
    assert "Malformed scheduler IPC message" not in messages[0]
    assert worker.last_error is not None
    assert worker.last_error.code == "SCHEDULER_IPC_ERROR"
    assert worker.last_error.recoverable is False
    assert "Malformed scheduler IPC message" in worker.last_error.technical_message


# ===========================================================================
# TC-SCHED-WORK-003: Test that cancel flow sets event, drains queue, and terminates process if needed.
# ===========================================================================
def test_worker_cancel_graceful_and_terminate(mock_repository):
    # Arrange
    mock_queue = MagicMock()
    mock_process = MagicMock()
    mock_cancel_event = MagicMock()

    mock_process.is_alive.return_value = True
    mock_queue.empty.side_effect = [False, False, True]
    # _drain_queue() drains via get_nowait() until it raises Empty (mirroring
    # a real Queue), not via .empty(); one drained item then Empty gives the
    # 2 calls asserted below.
    mock_queue.get_nowait.side_effect = [None, queue.Empty()]

    worker = SchedulerWorker(mock_queue, mock_cancel_event, [mock_process], mock_repository)

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
@patch("src.infrastructure.concurrency.SchedulerProcessRunner.Scheduler")
@patch("src.infrastructure.concurrency.SchedulerProcessRunner.QueueScheduleObserver")
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

    work_source = MagicMock()
    work_source.get_next.side_effect = [WorkUnit(seed_dates=[]), None]

    runner = SchedulerProcessRunner(
        slots, checkers, queue, cancel_event, max_results=10, batch_size=1000, work_source=work_source
    )

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
@patch("src.infrastructure.concurrency.SchedulerProcessRunner.Scheduler")
@patch("src.infrastructure.concurrency.SchedulerProcessRunner.QueueScheduleObserver")
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

    work_source = MagicMock()
    work_source.get_next.side_effect = [WorkUnit(seed_dates=[]), None]

    runner = SchedulerProcessRunner(
        slots, checkers, queue, cancel_event, max_results=10, batch_size=1000, work_source=work_source
    )

    # Act
    runner.run()

    # Assert — on_error receives a structured AppErrorInfo payload (a dict),
    # not str(e): the raw exception text only reaches the technical_message,
    # never something that could be shown to the user as-is.
    assert mock_scheduler.generateSchedules.call_count == 1
    assert mock_observer.on_error.call_count == 1
    payload = mock_observer.on_error.call_args[0][0]
    assert isinstance(payload, dict)
    assert payload["category"] == "INFRASTRUCTURE"
    assert "backtracking error" in payload["technical_message"]
    assert "backtracking error" not in payload["user_message"]


# ===========================================================================
# TC-SCHED-WORK-006: a MemoryError raised mid-search keeps its RESOURCE
# category through SchedulerProcessRunner, instead of becoming a generic
# scheduling/infrastructure failure.
# ===========================================================================
@patch("src.infrastructure.concurrency.SchedulerProcessRunner.Scheduler")
@patch("src.infrastructure.concurrency.SchedulerProcessRunner.QueueScheduleObserver")
def test_process_runner_memory_error_maps_to_resource(mock_obs_cls, mock_sched_cls, mock_repository):
    # Arrange
    mock_scheduler = MagicMock()
    mock_sched_cls.return_value = mock_scheduler
    mock_scheduler.generateSchedules.side_effect = MemoryError("oom")

    mock_observer = MagicMock()
    mock_obs_cls.return_value = mock_observer

    runner_queue = MagicMock()
    cancel_event = MagicMock()
    work_source = MagicMock()
    work_source.get_next.side_effect = [WorkUnit(seed_dates=[]), None]

    runner = SchedulerProcessRunner(
        [], [], runner_queue, cancel_event, max_results=10, batch_size=1000, work_source=work_source
    )

    # Act
    runner.run()

    # Assert
    payload = mock_observer.on_error.call_args[0][0]
    assert payload["code"] == "RESOURCE_MEMORY_EXHAUSTED"
    assert payload["category"] == "RESOURCE"
    assert payload["recoverable"] is False

    # And the full pipeline: SchedulerWorker rebuilds the same record from the
    # payload it receives over the queue, with last_error reflecting it.
    worker_queue = MagicMock()
    worker_queue.get.side_effect = [("ERROR", payload)]
    worker_queue.get_nowait.side_effect = queue.Empty
    worker_process = MagicMock()
    worker = SchedulerWorker(worker_queue, MagicMock(), [worker_process], mock_repository)
    messages = []
    worker.error_occurred.connect(messages.append)

    worker.run()

    assert worker.last_error.code == "RESOURCE_MEMORY_EXHAUSTED"
    assert messages == [payload["user_message"]]
