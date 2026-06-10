"""
Entry point for running the scheduler inside a background process. 
The backtracking search can be very heavy, so it runs in a separate process 
instead of blocking the main GUI process.
"""
from __future__ import annotations
from multiprocessing import Queue
from multiprocessing.synchronize import Event
from typing import List

from .QueueScheduleObserver import QueueScheduleObserver
from src.logic.Scheduler import Scheduler
from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.SlotBuilder import Slot


class SchedulerProcessRunner:
    """Creates the scheduler process dependencies and runs the search."""

    def __init__(
        self, 
        slots: List[Slot], 
        checkers: List[IConflictChecker], 
        queue: Queue, 
        cancel_event: Event, 
        max_results: int,
        batch_size: int
    ) -> None:
        # Slots are the exams that the scheduler needs to assign to dates.
        self._slots = slots
        # Checkers are the rules used to reject invalid assignments.
        self._checkers = checkers
        # Queue used to send schedules, progress, errors, and finish messages to the main process.
        self._queue = queue
        # Shared flag used to stop the search when the user clicks cancel.
        self._cancel_event = cancel_event
        # Maximum number of valid schedules the process should generate.
        self._max_results = max_results
        # Number of schedules to send together in one queue message.
        self._batch_size = batch_size

    def run(self) -> None:
        """Runs the scheduler and reports success or failure to the main process."""
        observer = self._create_observer()
        try:
            scheduler = self._create_scheduler()
            
            # Starts the actual backtracking algorithm.
            scheduler.generateSchedules(self._slots, observer, self._max_results)
            
            # Notifies the main process that we finished successfully.
            observer.on_finished()
            
        except Exception as e:
            # If this process crashes, the main process still needs to know what happened. 
            # Without this message, the GUI may keep waiting for results forever.
            observer.on_error(str(e))


    # These helper methods keep object creation separate from the run flow.
    # This makes the run method easier to read and easier to change later.

    def _create_observer(self) -> QueueScheduleObserver:
        """Creates the observer that sends scheduler updates through the queue."""
        return QueueScheduleObserver(self._queue, self._cancel_event, self._batch_size)

    def _create_scheduler(self) -> Scheduler:
        """Creates the scheduler with the conflict rules it should use."""
        return Scheduler(self._checkers)
