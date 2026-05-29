"""Adapter that pushes observer events into a multiprocessing Queue.
"""
from __future__ import annotations
from multiprocessing import Queue
from threading import Event
from typing import Any

from src.logic.IScheduleObserver import IScheduleObserver
from src.application.dto_viewmodel.schedule_dto import ScheduleDTO, AssignmentDTO


class QueueScheduleObserver(IScheduleObserver):
    """Pushes updates to a queue because a background process cannot update the GUI directly."""

    def __init__(self, queue: Queue, cancel_event: Event, batch_size: int = 50) -> None:
        # The communication pipe to the main process because we need Inter-Process Communication (IPC).
        self._queue = queue
        # The shared flag to stop the search early because the user might cancel via the GUI.
        self._cancel_event = cancel_event
        # The maximum number of items to hold before sending because frequent IPC calls cause performance drops.
        self._batch_size = batch_size
        # The local memory storage that aggregates schedules because sending them one by one is too expensive.
        self._buffer = []

    def on_schedule_found(self, schedule: Any) -> None:
        """Adds to buffer and pushes only when the batch is full to save IPC overhead."""
        dto = self._to_schedule_dto(schedule)
        self._buffer.append(dto)
        
        if len(self._buffer) >= self._batch_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Pushes the accumulated batch to the queue and clears the buffer."""
        if self._buffer:
            self._queue.put(("SCHEDULE_BATCH", self._buffer))
            self._buffer = []

    def on_progress(self, value: int) -> None:
        """Pushes a progress event because the QThread is listening for percentage updates."""
        self._queue.put(("PROGRESS", value))

    def should_cancel(self) -> bool:
        """Checks the event flag because the user might have clicked the cancel button."""
        return self._cancel_event is not None and self._cancel_event.is_set()

    def on_finished(self) -> None:
        """Flushes any remaining schedules before signaling the end."""
        self._flush_buffer()
        self._queue.put(("FINISHED", None))

    def on_error(self, message: str) -> None:
        """Pushes an error signal because we want to show a polite error popup in the GUI."""
        self._queue.put(("ERROR", message))

    def _to_schedule_dto(self, schedule: Any) -> ScheduleDTO:
        """Maps the domain model to a DTO, converting objects to pure primitives for safe IPC."""
        
        assignments = [
            AssignmentDTO(
                course_id=assignment.course.courseId,
                course_name=assignment.course.name,
                date=assignment.date.isoformat() if assignment.date else "",
                semester=assignment.semester.value if hasattr(assignment.semester, 'value') else assignment.semester,
                moed=assignment.moed.value if hasattr(assignment.moed, 'value') else assignment.moed
            )
            for assignment in schedule.assignments
        ]
        return ScheduleDTO(assignments=assignments, total_assignments=len(assignments))