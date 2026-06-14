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
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.checkers.config.CheckerFactory import build_checkers
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository

DEFAULT_MAX_RESULTS = 1000000
DEFAULT_BATCH_SIZE = 1000


def _run_scheduler_process(slots, courses, selected_programs, config, queue, cancel_event, max_results, batch_size):
    """
    Isolated process entry point running inside an independent OS child process.
    Builds the conflict checkers locally (from the constraints config) to avoid
    heavy inter-process serialization of precomputed structures.
    """
    try:
        checkers = build_checkers(config, courses, selected_programs, slots)
        runner = SchedulerProcessRunner(slots, checkers, queue, cancel_event, max_results, batch_size)
        runner.run()
    except Exception as e:
        queue.put(("ERROR", f"Fatal scheduling error: {type(e).__name__}: {str(e)}"))


class SchedulingService:
    """Coordinates core slot compilation configurations and orchestrates background multiprocessing lifecycles."""

    def __init__(self, repository: SQLiteScheduleRepository) -> None:
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
        config: Optional[ConstraintsConfig] = None,
    ) -> SchedulerWorker:
        """
        Deploys parallel background processes that split the search space and stream
        results into a single shared queue, monitored by one synchronized QThread worker.

        config carries the Phase-3 threshold constraints (toggles + k values).
        When None, only the two base checkers run, so behaviour is unchanged.
        """
        slots = self.build_slots(program_ids, courses, periods)

        if num_processes is None:
            num_processes = max(1, (os.cpu_count() or 2) - 1)
        if slots:
            num_processes = max(1, min(num_processes, len(slots[0].candidateDates), max_results))
        else:
            num_processes = 1

        queue: Queue = Queue(maxsize=50)
        cancel_event = Event()

        partitions = self._partition_slots(slots, num_processes)
        base_budget = max_results // num_processes
        remainder   = max_results % num_processes

        processes: List[Process] = []
        for i, partition_slots in enumerate(partitions):
            budget = base_budget + (remainder if i == 0 else 0)
            process = Process(
                target=_run_scheduler_process,
                args=(partition_slots, courses, program_ids, config, queue, cancel_event, budget, DEFAULT_BATCH_SIZE),
                daemon=True,
            )
            processes.append(process)

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
        if not slots:
            return [slots]
        root = slots[0]
        tail = slots[1:]
        partitions: List[List[Slot]] = []
        for i in range(num_partitions):
            partition_dates = root.candidateDates[i::num_partitions]
            partition_root = Slot(root.course, root.semester, root.moed, partition_dates)
            partitions.append([partition_root] + tail)
        return partitions

    def cancel(self) -> None:
        """Signals active running background worker nodes to abort operational loops cleanly."""
        if self._worker is not None:
            self._worker.cancel()