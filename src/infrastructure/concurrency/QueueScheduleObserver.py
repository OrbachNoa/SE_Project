"""Adapter that pushes observer events into a multiprocessing Queue for Inter-Process Communication.
"""
from __future__ import annotations
from multiprocessing import Queue
from multiprocessing.synchronize import Event
from typing import Any
import pickle
import zlib
from src.logic.observers.IScheduleObserver import IScheduleObserver
from src.application.dto.ScheduleDTO import ScheduleDTO, AssignmentDTO


class QueueScheduleObserver(IScheduleObserver):
    """
    Sends scheduler updates from the background process to the main UI process. 
    The scheduler works in a separate process, so it cannot update the GUI directly. 
    This observer converts schedules to DTOs and sends them through a Queue.
    """

    def __init__(self, queue: Queue, cancel_event: Event, batch_size: int) -> None:
        # Queue used to send messages from the scheduler process to the main process.
        self._queue = queue
        # Shared flag used to stop the scheduler when the user clicks cancel.
        self._cancel_event = cancel_event
        # Number of schedules to collect before sending them through the queue.
        self._batch_size = batch_size
        # Temporary buffer for schedules waiting to be sent as one batch.
        self._buffer: list[ScheduleDTO] = []
        # Remembers the last progress value that was sent. 
        # # For example,  if 50% was already reported, another 50% update will not be sent again.
        self._last_progress_sent: int = -1

    def on_schedule_found(self, schedule: Any) -> None:
        """
        Converts a found schedule to a DTO and stores it in the local batch buffer.
        The buffer is sent only when it reaches the configured batch size.
        """
        dto = self._to_schedule_dto(schedule)
        self._buffer.append(dto)
        
        if len(self._buffer) >= self._batch_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Sends the current schedule batch through the queue."""
        if self._buffer:
            # Convert the DTO list to bytes and compress it before sending.
            # This reduces the amount of data passed between processes.
            data = zlib.compress(pickle.dumps(self._buffer, protocol=4), level=1)
            # Send a typed message through the queue.
            # "SCHEDULE_BATCH" tells the receiver that this message contains a batch of schedules, 
            # because the same queue is also used for progress, finish, and error messages.
            self._queue.put(("SCHEDULE_BATCH", (data, len(self._buffer))))
            # Clear the buffer after the batch was sent.
            self._buffer = []

    def on_progress(self, value: int) -> None:
        """
        Sends a progress update to the main process. 
        Duplicate progress values are skipped to reduce unnecessary queue messages.
        """
        if value != self._last_progress_sent:
            self._last_progress_sent = value
            self._queue.put(("PROGRESS", value))

    def should_cancel(self) -> bool:
        """Returns True if the user requested to cancel the scheduling process."""
        return self._cancel_event is not None and self._cancel_event.is_set()

    def on_finished(self) -> None:
        """Sends all remaining schedules and then reports that the search is finished."""
        self._flush_buffer()
        self._queue.put(("FINISHED", None))

    def on_error(self, message: str) -> None:
        """Sends an error message to the main process."""
        self._queue.put(("ERROR", message))

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
