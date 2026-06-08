"""Service for launching schedule generation across one or more background processes."""
from __future__ import annotations

import os
from multiprocessing import Process, Queue, Event
from typing import List, Optional

from src.models.Course import Course
from src.models.ExamPeriod import ExamPeriod
from src.infrastructure.concurrency.SchedulerProcessRunner import SchedulerProcessRunner
from src.infrastructure.concurrency.SchedulerWorker import SchedulerWorker
from src.logic.SlotBuilder import SlotBuilder, Slot
from src.logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.checkers.MoedOrderChecker import MoedOrderChecker
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository

# Sets a fallback limit for tracking backtrack results safely within boundaries
DEFAULT_MAX_RESULTS = 1000000
DEFAULT_BATCH_SIZE = 1000


def _run_scheduler_process(slots, courses, selected_programs, queue, cancel_event, max_results, batch_size):
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
        runner = SchedulerProcessRunner(slots, checkers, queue, cancel_event, max_results, batch_size)
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
        num_processes: Optional[int] = None,
    ) -> SchedulerWorker:
        """
        Deploys parallel background processes that split the search space and stream
        results into a single shared queue, monitored by one synchronized QThread worker.
        """
        # Formulate active scheduling constraints based on user selections
        slots = self.build_slots(program_ids, courses, periods)

        # Decide how many parallel workers to spawn. Leave one core for the GUI/main
        # thread, never spawn more workers than the root slot has candidate dates,
        # and never spawn more workers than max_results (avoids zero-budget processes).
        if num_processes is None:
            num_processes = max(1, (os.cpu_count() or 2) - 1)
        if slots:
            num_processes = max(1, min(num_processes, len(slots[0].candidateDates), max_results))
        else:
            num_processes = 1

        # Bounded IPC channel: gives natural backpressure so a fast engine cannot
        # flood RAM with un-consumed batches while the writer drains to SQLite.
        queue: Queue = Queue(maxsize=50)
        cancel_event = Event()

        # Split the root slot's dates into disjoint subtrees. Distribute the result
        # budget so the total across all processes equals exactly max_results:
        # process 0 absorbs the remainder from floor division so no results are lost.
        partitions = self._partition_slots(slots, num_processes)
        base_budget = max_results // num_processes
        remainder   = max_results % num_processes

        # Allocate one isolated OS process per partition; all feed the same queue.
        processes: List[Process] = []
        for i, partition_slots in enumerate(partitions):
            budget = base_budget + (remainder if i == 0 else 0)
            process = Process(
                target=_run_scheduler_process,
                args=(partition_slots, courses, program_ids, queue, cancel_event, budget, DEFAULT_BATCH_SIZE),
                daemon=True,
            )
            processes.append(process)

        # Wire the long-running process monitoring pipeline inside an asynchronous worker wrapper
        self._worker = SchedulerWorker(
            queue=queue,
            cancel_event=cancel_event,
            processes=processes,
            repository=self._repository,
        )
        self._worker.start()
        return self._worker

    @staticmethod
    def _partition_slots(slots: List[Slot], num_partitions: int) -> List[List[Slot]]:
        """
        Split the search space by dividing the root slot's candidate dates into
        `num_partitions` disjoint groups. Each partition explores a subtree that
        never overlaps another, so the union covers every valid schedule exactly
        once. Round-robin slicing keeps the partitions roughly balanced.
        """
        if not slots:
            return [slots]

        root = slots[0]
        tail = slots[1:]

        partitions: List[List[Slot]] = []
        for i in range(num_partitions):
            # Round-robin: partition i owns dates[i], dates[i+K], dates[i+2K], ...
            partition_dates = root.candidateDates[i::num_partitions]
            partition_root = Slot(root.course, root.semester, root.moed, partition_dates)
            partitions.append([partition_root] + tail)
        return partitions

    def cancel(self) -> None:
        """Signals active running background worker nodes to abort operational loops cleanly."""
        if self._worker is not None:
            self._worker.cancel()