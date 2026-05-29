"""Service for launching schedule generation in a background process."""
from __future__ import annotations

from multiprocessing import Process, Queue, Event
from typing import List

from src.application.app_state import AppState
from src.concurrency.SchedulerProcessRunner import SchedulerProcessRunner
from src.concurrency.SchedulerWorker import SchedulerWorker
from src.logic.SlotBuilder import SlotBuilder, Slot
from src.logic.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.MoedOrderChecker import MoedOrderChecker

DEFAULT_MAX_RESULTS = 100


def _run_scheduler_process(slots, courses, selected_programs, queue, cancel_event, max_results):
    """Process entry point: builds checkers in-child, then runs the search.

    Checkers are constructed here rather than passed in because the conflict
    graph is cheaper to recompute in the child than to pickle across processes.
    """
    program_checker = ProgramYearConflictChecker()
    program_checker.precompute_conflicts(courses, selected_programs)
    checkers = [program_checker, MoedOrderChecker()]

    runner = SchedulerProcessRunner(slots, checkers, queue, cancel_event, max_results)
    runner.run()


class SchedulingService:
    """Builds slots from state and starts a background SchedulerWorker.
    
    The worker runs the backtracking algorithm in a separate process and reports results via a Queue.
    """

    def __init__(self, app_state: AppState) -> None:
        self._app_state = app_state

    def start(self, program_ids: List[str], max_results: int = DEFAULT_MAX_RESULTS) -> SchedulerWorker:
        """Launch generation for the given programs and return a running worker."""
        input_state = self._app_state.get_input_state()
        courses = input_state.get_courses()
        periods = input_state.get_periods()

        slots: List[Slot] = SlotBuilder(periods, program_ids).build(courses)

        queue: Queue = Queue()
        cancel_event = Event()
        process = Process(
            target=_run_scheduler_process,
            args=(slots, courses, program_ids, queue, cancel_event, max_results),
            daemon=True,
        )

        worker = SchedulerWorker(queue, cancel_event, process)
        # Starts the process after creating the worker so that the worker is ready to receive messages immediately.
        worker.start()
        return worker