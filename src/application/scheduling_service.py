"""Service for launching schedule generation in a background process."""
from __future__ import annotations

from multiprocessing import Process, Queue, Event
from typing import List, Optional

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.concurrency.SchedulerProcessRunner import SchedulerProcessRunner
from src.concurrency.SchedulerWorker import SchedulerWorker
from src.logic.SlotBuilder import SlotBuilder, Slot
from src.logic.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.MoedOrderChecker import MoedOrderChecker

DEFAULT_MAX_RESULTS = 100


def _run_scheduler_process(slots, courses, selected_programs, queue, cancel_event, max_results):
    """Process entry point that builds checkers in-child and runs the search."""

    # Build checkers inside the child because the conflict graph is cheaper to recompute than to pickle
    program_checker = ProgramYearConflictChecker()
    program_checker.precompute_conflicts(courses, selected_programs)
    checkers = [program_checker, MoedOrderChecker()]

    runner = SchedulerProcessRunner(slots, checkers, queue, cancel_event, max_results)
    runner.run()


class SchedulingService:
    """Builds slots from state and runs generation on a background worker."""

    def __init__(self) -> None:
        self._slot_builder: Optional[SlotBuilder] = None
        self._checkers: List = []
        self._worker: Optional[SchedulerWorker] = None

    def build_slots(
        self, program_ids: List[str], courses: List[Course], periods: List[ExamPeriod]
    ) -> List[Slot]:
        """Builds the scheduling slots for the selected programs from supplied data."""
        self._slot_builder = SlotBuilder(periods, program_ids)
        return self._slot_builder.build(courses)

    def generate_async(
        self,
        program_ids: List[str],
        courses: List[Course],
        periods: List[ExamPeriod],
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> SchedulerWorker:
        """Starts generation in the background and returns the running worker."""
        slots = self.build_slots(program_ids, courses, periods)

        # IPC channel and cancellation flag shared with the child process
        queue: Queue = Queue()
        cancel_event = Event()
        process = Process(
            target=_run_scheduler_process,
            args=(slots, courses, program_ids, queue, cancel_event, max_results),
            daemon=True,
        )

        # The worker owns the process lifecycle and starts it inside its own run()
        self._worker = SchedulerWorker(queue, cancel_event, process)
        self._worker.start()
        return self._worker

    def cancel(self) -> None:
        """Cancels the current generation run if one is active."""

        # Only cancel when a worker exists; safe to call otherwise
        if self._worker is not None:
            self._worker.cancel()