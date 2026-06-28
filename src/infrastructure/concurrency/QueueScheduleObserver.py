"""
Observer used by worker processes to send scheduler events to the main process.

The scheduler runs in a separate process, so it cannot update the GUI directly.
This observer batches schedules, compresses them, and sends them through a Queue.
"""
from __future__ import annotations
from multiprocessing import Queue
from multiprocessing.synchronize import Event
from typing import Any
import queue as _queue_mod
import zlib
from src.logic.observers.IScheduleObserver import IScheduleObserver
from src.application.dto.PackedScheduleCodec import encode_schedule, pack_rows


class QueueScheduleObserver(IScheduleObserver):
    """
    Queue based observer for scheduler results.

    It receives events from the scheduler inside a worker process and sends them
    to the main process as queue messages.
    """

    def __init__(
        self,
        queue: Queue,
        cancel_event: Event,
        batch_size: int,
        scorer=None,
        result_counter=None,
        result_limit: "int | None" = None,
        slots: list | None = None,
        run_id=None,
    ) -> None:
       # Queue used to send messages back to the main process.
        self._queue = queue
        # Shared cancel flag used when the user stops the search.
        self._cancel_event = cancel_event
        # Number of schedules to collect before sending one batch.
        self._batch_size = batch_size
        # Identifies which generation run this observer belongs to. None
        # (the default, used by every caller that does not pass one) keeps
        # every outgoing message in its old, unwrapped shape -- only callers
        # that opt in by passing a real run_id get the wrapped
        # (run_id, payload) shape that SchedulerWorker can use to drop stale
        # messages from a previous run on the shared result queue.
        self._run_id = run_id
        # Optional scorer used to attach scores to each schedule.
        self._scorer = scorer
        # Shared counter used to keep the total result count under the global limit.
        self._result_counter = result_counter
        self._result_limit = result_limit

        # Compact buffers used by the current GUI path.
        self._packed_rows: list[bytes] = []
        self._batch_scores: list[dict] = []
        # Slots are needed so schedules can be encoded as compact date indexes.
        if slots is None:
            raise ValueError("QueueScheduleObserver requires slots for packed schedule encoding")
        self._slots = list(slots)
        self._slot_count = len(self._slots)
        # Map each assignment identity to its slot index.
        self._assignment_to_slot = {
            (slot.course, slot.semester, slot.moed): i
            for i, slot in enumerate(self._slots)
        }
        # For each slot, map every possible date to a small index.
        self._date_index_by_slot = [
            {d: i for i, d in enumerate(slot.candidateDates)}
            for slot in self._slots
        ]
        # Remember the last progress value so we do not send duplicates.
        self._last_progress_sent: int = -1

    def _reserve_result_slot(self) -> bool:
        """Reserve one global result slot before storing a schedule."""
        if self._result_limit is None or self._result_counter is None:
            return True
        
        # Lock the shared counter so two processes cannot reserve the same slot.
        with self._result_counter.get_lock():
            if self._result_counter.value >= self._result_limit:
                return False
            self._result_counter.value += 1
            # Once the global limit is reached, ask all workers to stop.
            if self._result_counter.value >= self._result_limit and self._cancel_event is not None:
                self._cancel_event.set()
        return True

    def _wrap(self, payload):
        """Attach this observer's run_id to a payload, unless none was given."""
        return payload if self._run_id is None else (self._run_id, payload)

    def _put_to_queue(self, message) -> None:
        """Send one message to the result queue."""
        try:
            # Try to send without blocking first.
            self._queue.put_nowait(message)
        except _queue_mod.Full:
            # If the queue is full, wait instead of losing the message.
            self._queue.put(message)

    def on_schedule_found(self, schedule: Any) -> None:
        # Score the schedule if needed, then add it to the current batch.
        scores = self._scorer.score(schedule) if self._scorer is not None else {}
        self._record_schedule(schedule, scores)

    def on_scored_schedule_found(self, schedule: Any, scores: dict) -> None:
        # Used when the scheduler already calculated the scores.
        self._record_schedule(schedule, dict(scores))

    def _record_schedule(self, schedule: Any, scores: "dict | None") -> None:
        """Store one found schedule in the local batch buffer."""
        # Do not store more schedules after the global limit was reached.
        if not self._reserve_result_slot():
            return

        # Encode the schedule as small date indexes instead of a full DTO.
        self._packed_rows.append(
            encode_schedule(
                schedule,
                self._assignment_to_slot,
                self._date_index_by_slot,
                self._slot_count,
            )
        )
        self._batch_scores.append(scores or {})
        # Send the batch when it reaches the configured size.
        if len(self._packed_rows) >= self._batch_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Send the current schedule batch through the queue."""
        if self._packed_rows:
            # Pack all compact rows into one binary block
            packed = pack_rows(self._packed_rows, self._slot_count, len(self._packed_rows))
            # Compress with level 1 to reduce data size without spending too much CPU.
            data = zlib.compress(packed, level=1)
            # Send one batch message to the main process.
            self._put_to_queue(("SCHEDULE_BATCH", self._wrap((data, len(self._packed_rows), self._batch_scores))))
            # Clear the packed buffers after sending.
            self._packed_rows = []
            self._batch_scores = []
            return

    def on_progress(self, value: int) -> None:
        """Send progress updates to the main process."""

        # Send progress only when the value actually changed.
        if value != self._last_progress_sent:
            self._last_progress_sent = value
            self._put_to_queue(("PROGRESS", self._wrap(value)))

    def should_cancel(self) -> bool:
        """Return True when the scheduler should stop searching."""
        return self._cancel_event is not None and self._cancel_event.is_set()

    def on_finished(self) -> None:
        """Send remaining schedules and then report that the search finished."""

        # Flush the last partial batch before telling the main process we are done.
        self._flush_buffer()
        self._queue.put(("FINISHED", self._wrap(None)))

    def on_error(self, message) -> None:
        """Send an error to the main process.

        ``message`` may be a plain user-facing string (legacy callers) or a
        serialised ``AppErrorInfo`` payload (a plain dict, built by
        ``build_process_error_payload``) — either is just forwarded as-is;
        ``SchedulerWorker`` on the receiving end knows how to unpack both.
        """
        self._put_to_queue(("ERROR", self._wrap(message)))
