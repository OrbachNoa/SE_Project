"""The entry point for the background scheduling process.

This runs entirely in a separate CPU process because the backtracking algorithm
is very heavy and would freeze the main GUI thread.
"""
from __future__ import annotations
from multiprocessing import Queue
from multiprocessing.synchronize import Event
from typing import List

from .QueueScheduleObserver import QueueScheduleObserver
from ..logic.Scheduler import Scheduler
from ..logic.IConflictChecker import IConflictChecker
from ..logic.SlotBuilder import Slot


class SchedulerProcessRunner:
    """Sets up and runs the scheduler in a new process because we need an isolated execution environment."""

    def __init__(
        self, 
        slots: List[Slot], 
        checkers: List[IConflictChecker], 
        queue: Queue, 
        cancel_event: Event, 
        max_results: int
    ) -> None:
        self._slots = slots
        self._checkers = checkers
        self._queue = queue
        self._cancel_event = cancel_event
        self._max_results = max_results

    def run(self) -> None:
        """Executes the search safely because we must catch crashes and report them to the main app."""
        try:
            observer = self._create_observer()
            scheduler = self._create_scheduler()
            
            # Starts the actual backtracking algorithm.
            scheduler.generateSchedules(self._slots, observer, self._max_results)
            
            # Notifies the main process that we finished successfully.
            observer.on_finished()
            
        except Exception as e:
            # Catches unexpected crashes because the main app will hang forever if the queue goes silent.
            error_observer = self._create_observer()
            error_observer.on_error(f"Fatal scheduling error: {str(e)}")

    def _create_observer(self) -> QueueScheduleObserver:
        """Creates the queue adapter because the scheduler needs a way to talk to the outside world."""
        return QueueScheduleObserver(self._queue, self._cancel_event)

    def _create_scheduler(self) -> Scheduler:
        """Creates the core engine because it contains the actual backtracking logic."""
        return Scheduler(self._checkers)