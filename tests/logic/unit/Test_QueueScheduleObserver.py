"""
Test suite for QueueScheduleObserver.

Scope   : Constructor validation, on_progress duplicate suppression,
          _reserve_result_slot's global result-limit gating with
          cancel_event tripping, the run_id wrapping behaviour of _wrap()
          across every outgoing message kind, on_error forwarding a dict
          payload as-is, and the precise content of one compressed
          SCHEDULE_BATCH payload (a zlib + packed-rows round trip). These
          cases are additive to the existing buffering/flush/lifecycle
          coverage in Test_Observers.py and do not duplicate it.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-QSO-001 .. TC-QSO-009
Fixtures: make_course, make_assignment (tests/conftest.py)
"""
import zlib
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.infrastructure.concurrency.QueueScheduleObserver import QueueScheduleObserver
from src.application.dto.PackedScheduleCodec import is_packed_blob, unpack_rows
from src.logic.SlotBuilder import Slot
from src.models.Domain import ExamSchedule


def _build_slot(assignment):
    return Slot(assignment.course, assignment.semester, assignment.moed, [assignment.date])


# TC-QSO-001
# The constructor must reject a missing slots argument outright, since
# packed-row encoding has no meaning without a slot list to index into.
def test_constructor_raises_value_error_when_slots_is_none():
    # Arrange
    mock_queue = MagicMock()

    # Act / Assert
    with pytest.raises(ValueError):
        QueueScheduleObserver(mock_queue, cancel_event=None, batch_size=5, slots=None)


# TC-QSO-002
# on_progress must only put a message on the queue when the value actually
# changed from the last value sent — repeating the same percentage would
# waste queue bandwidth for no UI benefit.
def test_on_progress_suppresses_identical_consecutive_values():
    # Arrange
    mock_queue = MagicMock()
    observer = QueueScheduleObserver(mock_queue, cancel_event=None, batch_size=5, slots=[])

    # Act
    observer.on_progress(50)
    count_after_first = mock_queue.put_nowait.call_count
    observer.on_progress(50)
    count_after_repeat = mock_queue.put_nowait.call_count
    observer.on_progress(51)
    count_after_change = mock_queue.put_nowait.call_count

    # Assert
    assert count_after_first == 1
    assert count_after_repeat == 1  # duplicate suppressed, no second put
    assert count_after_change == 2


# TC-QSO-003
# _reserve_result_slot must allow recording while under the global result
# limit, and once the limit is reached it must stop further recording and
# set the cancel_event so all workers know to stop the search.
def test_reserve_result_slot_trips_cancel_event_once_limit_reached(make_assignment):
    # Arrange
    class _LockingCounter:
        """Minimal stand-in for multiprocessing.Value with a real lock API."""

        def __init__(self, initial=0):
            self.value = initial

        def get_lock(self):
            import contextlib
            return contextlib.nullcontext()

    mock_queue = MagicMock()
    cancel_event = MagicMock()
    cancel_event.is_set.return_value = False
    assignment = make_assignment(exam_date=date(2026, 6, 1))
    slot = _build_slot(assignment)
    counter = _LockingCounter(initial=0)
    observer = QueueScheduleObserver(
        mock_queue, cancel_event, batch_size=10, slots=[slot],
        result_counter=counter, result_limit=1,
    )
    schedule = ExamSchedule()
    schedule.addAssignment(assignment)

    # Act
    observer.on_schedule_found(schedule)  # consumes the single available slot
    rows_after_first = len(observer._packed_rows)
    observer.on_schedule_found(schedule)  # must be rejected — limit reached
    rows_after_second = len(observer._packed_rows)

    # Assert
    assert rows_after_first == 1
    assert rows_after_second == 1  # second call was dropped, buffer unchanged
    assert counter.value == 1
    cancel_event.set.assert_called_once()


# TC-QSO-004
# With no result_limit/result_counter configured (the default), every
# schedule must be recorded — the gating logic must be a strict opt-in.
def test_reserve_result_slot_allows_unlimited_recording_by_default(make_assignment):
    # Arrange
    mock_queue = MagicMock()
    cancel_event = MagicMock()
    assignment = make_assignment(exam_date=date(2026, 6, 1))
    slot = _build_slot(assignment)
    observer = QueueScheduleObserver(mock_queue, cancel_event, batch_size=10, slots=[slot])
    schedule = ExamSchedule()
    schedule.addAssignment(assignment)

    # Act
    observer.on_schedule_found(schedule)
    observer.on_schedule_found(schedule)

    # Assert
    assert len(observer._packed_rows) == 2
    cancel_event.set.assert_not_called()


# TC-QSO-005
# When a run_id is supplied, every outgoing message must be wrapped as
# (run_id, payload) so the receiving SchedulerWorker can discard messages
# left over from a previous, now-stale run on a shared queue.
def test_wrap_attaches_run_id_to_progress_and_error_messages():
    # Arrange
    mock_queue = MagicMock()
    observer = QueueScheduleObserver(
        mock_queue, cancel_event=None, batch_size=5, slots=[], run_id="run-42"
    )

    # Act
    observer.on_progress(10)
    _, progress_payload = mock_queue.put_nowait.call_args[0][0]
    observer.on_error("boom")
    _, error_payload = mock_queue.put_nowait.call_args[0][0]

    # Assert
    assert progress_payload == ("run-42", 10)
    assert error_payload == ("run-42", "boom")


# TC-QSO-006
# With no run_id given (the default, used by every existing caller), the
# payload must stay unwrapped — exactly the original, pre-run_id shape.
def test_wrap_leaves_payload_unwrapped_when_run_id_is_none():
    # Arrange
    mock_queue = MagicMock()
    observer = QueueScheduleObserver(mock_queue, cancel_event=None, batch_size=5, slots=[])

    # Act
    observer.on_progress(20)
    _, progress_payload = mock_queue.put_nowait.call_args[0][0]

    # Assert
    assert progress_payload == 20


# TC-QSO-007
# on_error must forward a dict payload (a serialised AppErrorInfo from
# build_process_error_payload) exactly as given, with no reshaping — the
# receiving side knows how to unpack both plain strings and dicts.
def test_on_error_forwards_dict_payload_as_is():
    # Arrange
    mock_queue = MagicMock()
    observer = QueueScheduleObserver(mock_queue, cancel_event=None, batch_size=5, slots=[])
    error_payload = {
        "code": "RESOURCE_MEMORY_EXHAUSTED",
        "category": "RESOURCE",
        "severity": "CRITICAL",
        "user_message": "Out of memory.",
    }

    # Act
    observer.on_error(error_payload)
    msg_type, forwarded = mock_queue.put_nowait.call_args[0][0]

    # Assert
    assert msg_type == "ERROR"
    assert forwarded == error_payload
    assert forwarded is error_payload


# TC-QSO-008
# _flush_buffer must be a no-op when the buffer is empty (e.g. on_finished()
# called with nothing pending) — it must not put an empty/degenerate batch
# message on the queue.
def test_flush_buffer_is_noop_when_buffer_is_empty():
    # Arrange
    mock_queue = MagicMock()
    cancel_event = MagicMock()
    observer = QueueScheduleObserver(mock_queue, cancel_event, batch_size=5, slots=[])

    # Act
    observer.on_finished()

    # Assert — only the terminal FINISHED message went out, no batch message.
    mock_queue.put_nowait.assert_not_called()
    assert mock_queue.put.call_count == 1
    msg_type, payload = mock_queue.put.call_args[0][0]
    assert msg_type == "FINISHED"
    assert payload is None


# TC-QSO-009
# A flushed SCHEDULE_BATCH payload must be a zlib-compressed packed blob that
# decodes back to the exact per-schedule date indexes that were observed. Two
# schedules pick different candidate dates (index 0 and index 2), so this
# verifies the compressed transport is lossless and order-preserving — not just
# that some batch with the right count was sent.
def test_flush_emits_precise_compressed_schedule_batch_payload(make_course, make_assignment):
    # Arrange — one slot offering three candidate dates; two schedules each
    # pick a different one.
    d0, d1, d2 = date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)
    course = make_course(course_id="10101")
    assignment_first = make_assignment(course=course, exam_date=d0)
    assignment_third = make_assignment(course=course, exam_date=d2)
    slot = Slot(assignment_first.course, assignment_first.semester,
                assignment_first.moed, [d0, d1, d2])

    mock_queue = MagicMock()
    observer = QueueScheduleObserver(mock_queue, cancel_event=None, batch_size=2, slots=[slot])

    schedule_first = ExamSchedule()
    schedule_first.addAssignment(assignment_first)
    schedule_second = ExamSchedule()
    schedule_second.addAssignment(assignment_third)

    # Act — the second schedule reaches batch_size=2 and triggers one flush.
    observer.on_schedule_found(schedule_first)
    observer.on_schedule_found(schedule_second)

    # Assert
    msg_type, (data, count, batch_scores) = mock_queue.put_nowait.call_args[0][0]
    assert msg_type == "SCHEDULE_BATCH"
    assert count == 2
    # The payload is genuinely zlib-compressed around a packed blob...
    decompressed = zlib.decompress(data)
    assert is_packed_blob(decompressed)
    # ...and decodes back to the exact date indexes, in order.
    slot_count, rows = unpack_rows(decompressed)
    assert slot_count == 1
    assert rows == [(0,), (2,)]
