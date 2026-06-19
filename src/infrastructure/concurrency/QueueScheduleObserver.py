"""Adapter that pushes observer events into a multiprocessing Queue for Inter-Process Communication.
"""
from __future__ import annotations
from multiprocessing import Queue
from multiprocessing.synchronize import Event
from typing import Any
import pickle
import queue as _queue_mod
import time
import zlib
from src.logic.observers.IScheduleObserver import IScheduleObserver
from src.application.dto.ScheduleDTO import ScheduleDTO, AssignmentDTO


class QueueScheduleObserver(IScheduleObserver):
    """
    Sends scheduler updates from the background process to the main UI process. 
    The scheduler works in a separate process, so it cannot update the GUI directly. 
    This observer converts schedules to DTOs and sends them through a Queue.
    """

    def __init__(
        self,
        queue: Queue,
        cancel_event: Event,
        batch_size: int,
        scorer=None,
        result_counter=None,
        result_limit: "int | None" = None,
    ) -> None:
        # Queue used to send messages from the scheduler process to the main process.
        self._queue = queue
        # Shared flag used to stop the scheduler when the user clicks cancel.
        self._cancel_event = cancel_event
        # Number of schedules to collect before sending them through the queue.
        self._batch_size = batch_size
        # Optional ScheduleScorer: when present, each schedule is scored on the
        # live domain object and the scores ride on the DTO.
        self._scorer = scorer
        # Shared cross-process counter (multiprocessing.Value). With dynamic
        # work-stealing, every work unit's search gets the full max_results as
        # its own local cap, so a process-local count cannot enforce the real
        # global limit - only a counter shared by every process can. Each
        # schedule reserves one slot here, atomically, before it is buffered,
        # so the total ever buffered across all processes cannot exceed
        # result_limit, no matter how many units/processes are in flight.
        self._result_counter = result_counter
        self._result_limit = result_limit
        # Temporary buffer for schedules waiting to be sent as one batch.
        self._buffer: list[ScheduleDTO] = []
        # Remembers the last progress value that was sent.
        # # For example,  if 50% was already reported, another 50% update will not be sent again.
        self._last_progress_sent: int = -1
        # Diagnostics: per-process counters reported once via on_finished's
        # payload. No Lock/Value needed - this instance lives in exactly one
        # process (built fresh per process by SchedulerProcessRunner), so
        # nothing else ever touches these fields concurrently. The main
        # process aggregates by summing each process's own reported total.
        self.diag_blocked_puts = 0
        self.diag_lock_wait_ms_total = 0.0
        self.diag_total_found = 0

    def _reserve_result_slot(self) -> bool:
        """Atomically reserves one global result slot. Returns False (and sets
        cancel_event once) when the shared limit is already reached, so the
        caller skips buffering this schedule instead of exceeding the cap.
        """
        if self._result_limit is None or self._result_counter is None:
            return True
        _t0 = time.perf_counter()
        with self._result_counter.get_lock():
            self.diag_lock_wait_ms_total += (time.perf_counter() - _t0) * 1000
            if self._result_counter.value >= self._result_limit:
                return False
            self._result_counter.value += 1
            if self._result_counter.value >= self._result_limit and self._cancel_event is not None:
                self._cancel_event.set()
        return True

    def _put_to_queue(self, message) -> None:
        """Routes every queue message through here so blocking puts (the
        results queue is full) can be counted without changing what gets sent.
        """
        try:
            self._queue.put_nowait(message)
        except _queue_mod.Full:
            self.diag_blocked_puts += 1
            self._queue.put(message)

    def on_schedule_found(self, schedule: Any) -> None:
        """
        Converts a found schedule to a DTO and stores it in the local batch buffer.
        The buffer is sent only when it reaches the configured batch size.
        """
        if not self._reserve_result_slot():
            return
        self.diag_total_found += 1

        dto = self._to_schedule_dto(schedule)
        # Score on the live domain schedule (year/requirement/real dates present)
        # before it is discarded; store scalars on the DTO for the runtime sort.
        if self._scorer is not None:
            dto.scores = self._scorer.score(schedule)
            
        # Add the DTO to the buffer.
        self._buffer.append(dto)
        
        # If the buffer reached the batch size, flush it to the queue.
        if len(self._buffer) >= self._batch_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Sends the current schedule batch through the queue."""
        if self._buffer:
            # Convert the DTO list to bytes and compress it before sending.
            # This reduces the amount of data passed between processes.
            data = zlib.compress(pickle.dumps(self._buffer, protocol=5), level=1)
            # Collect per-schedule scores so the main process can write them to
            # the narrow score table (Option B) without re-opening the blob.
            # Empty when scoring is off, which keeps the receiver simple.
            batch_scores = [dto.scores for dto in self._buffer] if self._scorer is not None else []
            # Send a typed message through the queue.
            # "SCHEDULE_BATCH" tells the receiver that this message contains a batch of schedules, 
            # because the same queue is also used for progress, finish, and error messages.
            self._put_to_queue(("SCHEDULE_BATCH", (data, len(self._buffer), batch_scores)))
            # Clear the buffer after the batch was sent.
            self._buffer = []

    def on_progress(self, value: int) -> None:
        """
        Sends a progress update to the main process. 
        Duplicate progress values are skipped to reduce unnecessary queue messages.
        """
        if value != self._last_progress_sent:
            self._last_progress_sent = value
            self._put_to_queue(("PROGRESS", value))

    def should_cancel(self) -> bool:
        """Returns True if the user requested to cancel the scheduling process."""
        return self._cancel_event is not None and self._cancel_event.is_set()

    def on_finished(self, extra_stats: "dict | None" = None) -> None:
        """Sends all remaining schedules, then reports that the search is
        finished. The FINISHED payload is a diagnostics dict (not None):
        this observer's own queue/lock counters, merged with whatever the
        caller (SchedulerProcessRunner) knows about its own run - e.g. how
        many cubes it processed, per-checker rejection stats.
        """
        self._flush_buffer()
        payload = {
            "blocked_puts": self.diag_blocked_puts,
            "lock_wait_ms_total": self.diag_lock_wait_ms_total,
            "schedules_found": self.diag_total_found,
        }
        if extra_stats:
            payload.update(extra_stats)
        self._queue.put(("FINISHED", payload))

    def on_error(self, message: str) -> None:
        """Sends an error message to the main process."""
        self._put_to_queue(("ERROR", message))

    def _to_schedule_dto(self, schedule: Any) -> ScheduleDTO:
        """
        Converts a domain ExamSchedule into a simple DTO. 
        This is needed because DTOs contain only simple data, 
        so they are safer and easier to send between processes.
        """
        assignments = [
            AssignmentDTO(
                course_id=assignment.course.courseId,
                course_name=assignment.course.name,
                instructor=assignment.course.instructor,
                evaluation=assignment.course.evaluation.value if hasattr(assignment.course.evaluation, "value") else str(assignment.course.evaluation),
                date=assignment.date.isoformat() if assignment.date else "",
                semester=assignment.semester.value if hasattr(assignment.semester, 'value') else assignment.semester,
                moed=assignment.moed.value if hasattr(assignment.moed, 'value') else assignment.moed,
                # Keep each related program with its requirement type. 
                # The UI uses this to show where the course belongs and whether it is obligatory or elective.
                program_requirements=[
                    (
                        entry.programId,
                        entry.requirement.value if hasattr(entry.requirement, "value") else str(entry.requirement),
                    )
                    for entry in (assignment.course.programEntries or [])
                ],
            )
            for assignment in schedule.assignments
        ]
        return ScheduleDTO(assignments=assignments, total_assignments=len(assignments))