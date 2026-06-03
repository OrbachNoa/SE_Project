"""Service for launching schedule generation in a background process."""
from __future__ import annotations

from multiprocessing import Process, Queue, Event
from typing import List, Optional

from src.models.Course import Course
from models.ExamPeriod import ExamPeriod
from infrastructure.concurrency.SchedulerProcessRunner import SchedulerProcessRunner
from infrastructure.concurrency.SchedulerWorker import SchedulerWorker
from src.logic.SlotBuilder import SlotBuilder, Slot
from logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker
from logic.checkers.MoedOrderChecker import MoedOrderChecker
from infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository

# Sets a fallback limit for tracking backtrack results safely within boundaries
DEFAULT_MAX_RESULTS = 1000000  


def _run_scheduler_process(slots, courses, selected_programs, queue, cancel_event, max_results):
    """
    Isolated process entry point running inside an independent OS child process.
    Instantiates conflict checkers locally to avoid heavy inter-process serialization overhead.
    """
    try:
        # Precompute internal data structures within the isolated child process context
        program_checker = ProgramYearConflictChecker()
        program_checker.precompute_conflicts(courses, selected_programs)
        checkers = [program_checker, MoedOrderChecker()]

        # Execute the heavy back-tracking algorithm loop away from the main thread
        runner = SchedulerProcessRunner(slots, checkers, queue, cancel_event, max_results)
        runner.run()
    except Exception as e:
        queue.put(("ERROR", f"Fatal scheduling error: {type(e).__name__}: {str(e)}"))


class SchedulingService:
    """Coordinates core slot compilation configurations and orchestrates background multiprocessing lifecycles."""

    def __init__(self, repository: SQLiteScheduleRepository) -> None:
        # Injects the shared tracking repository to pass downstream towards background worker loops
        self._repository = repository
        self._slot_builder: Optional[SlotBuilder] = None
        self._checkers: List = []
        self._worker: Optional[SchedulerWorker] = None

    def build_slots(
        self, program_ids: List[str], courses: List[Course], periods: List[ExamPeriod]
    ) -> List[Slot]:
        """Compiles structural calendar slot constraints derived from raw model input frames."""
        self._slot_builder = SlotBuilder(periods, program_ids)
        return self._slot_builder.build(courses)

    def generate_async(
        self,
        program_ids: List[str],
        courses: List[Course],
        periods: List[ExamPeriod],
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> SchedulerWorker:
        """
        Deploys an independent background process pipeline for heavy computations.
        Spawns a synchronized QThread worker to monitor pipeline state events without UI lag.
        """
        # Formulate active scheduling constraints based on user selections
        slots = self.build_slots(program_ids, courses, periods)

        # Establish isolated IPC channels and cancellation tokens for the child node
        queue: Queue = Queue()
        cancel_event = Event()
        
        # Allocate a dedicated operating system process thread for calculation isolation
        process = Process(
            target=_run_scheduler_process,
            args=(slots, courses, program_ids, queue, cancel_event, max_results),
            daemon=True,
        )

        # Wire the long-running process monitoring pipeline inside an asynchronous worker wrapper
        self._worker = SchedulerWorker(
            queue=queue, 
            cancel_event=cancel_event, 
            process=process,
            repository=self._repository
        )
        self._worker.start()
        return self._worker

    def cancel(self) -> None:
        """Signals active running background worker nodes to abort operational loops cleanly."""
        if self._worker is not None:
            self._worker.cancel()