"""Adapter that pushes observer events into a multiprocessing Queue for Inter-Process Communication.
"""
from __future__ import annotations
from multiprocessing import Queue
from multiprocessing.synchronize import Event
from typing import Any

from src.logic.IScheduleObserver import IScheduleObserver
from src.application.dto_viewmodel.schedule_dto import ScheduleDTO, AssignmentDTO


class QueueScheduleObserver(IScheduleObserver):
    """
    Pushes computation lifecycle events into a multiprocessing Queue.
    Enables safe data streaming from the isolated background engine process back to the UI environment.
    """

    def __init__(self, queue: Queue, cancel_event: Event, batch_size: int = 1000) -> None:
        # The cross-process IPC communication pipe mapped directly to the parent process listener
        self._queue = queue
        # Shared cancellation flag monitored to interrupt execution loops early on user request
        self._cancel_event = cancel_event
        # Threshold limit configuring the max capacity frame footprint of localized item packages
        self._batch_size = batch_size
        # Local memory storage buffer that aggregates processed data packets before flushing
        self._buffer: list[ScheduleDTO] = []
        # Suppresses redundant traffic updates by blocking unchanged sequential progress values
        self._last_progress_sent: int = -1

    def on_schedule_found(self, schedule: Any) -> None:
        """
        Transforms domain objects into pure data primitives and queues them inside the local buffer.
        Flushes data over the IPC line only when the batch fills to optimize context-switching costs.
        """
        dto = self._to_schedule_dto(schedule)
        self._buffer.append(dto)
        
        if len(self._buffer) >= self._batch_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Transfers accumulated data frame blocks onto the IPC queue pipe and flushes local memory references."""
        if self._buffer:
            self._queue.put(("SCHEDULE_BATCH", self._buffer))
            self._buffer = []

    def on_progress(self, value: int) -> None:
        """
        Pushes search progression values down the channel context tree.
        Suppresses identical duplicate signals to drop communication packet costs from O(N) to O(100).
        """
        if value != self._last_progress_sent:
            self._last_progress_sent = value
            self._queue.put(("PROGRESS", value))

    def should_cancel(self) -> bool:
        """Interrogates shared memory flag status criteria to determine if generation parameters were aborted."""
        return self._cancel_event is not None and self._cancel_event.is_set()

    def on_finished(self) -> None:
        """Flushes remaining cached record allocations and transmits a termination sequence message."""
        self._flush_buffer()
        self._queue.put(("FINISHED", None))

    def on_error(self, message: str) -> None:
        """Formats error crash reports into standard IPC signals to pop open notifications inside user views."""
        self._queue.put(("ERROR", message))

    def _to_schedule_dto(self, schedule: Any) -> ScheduleDTO:
        """
        Deconstructs heavy domain object graphs into flat, primitive-based DTO structures.
        Guarantees memory nodes are clean and safe for pipe marshaling across OS boundary lines.
        """
        assignments = [
            AssignmentDTO(
                course_id=assignment.course.courseId,
                course_name=assignment.course.name,
                instructor=assignment.course.instructor,
                date=assignment.date.isoformat() if assignment.date else "",
                semester=assignment.semester.value if hasattr(assignment.semester, 'value') else assignment.semester,
                moed=assignment.moed.value if hasattr(assignment.moed, 'value') else assignment.moed
            )
            for assignment in schedule.assignments
        ]
        return ScheduleDTO(assignments=assignments, total_assignments=len(assignments))