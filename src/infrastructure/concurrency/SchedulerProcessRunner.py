"""
Runs the heavy scheduler search inside a background process.

The GUI starts several processes, and each process uses this runner to search
one part of the scheduling space and send results back through the queue.
"""
from __future__ import annotations
from multiprocessing import Queue
from multiprocessing.synchronize import Event
from typing import List

from .QueueScheduleObserver import QueueScheduleObserver
from src.logic.Scheduler import Scheduler
from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.SlotBuilder import Slot
from src.models.ExamSchedule import ExamAssignment
from src.application.errors.ExceptionMapper import build_process_error_payload
from src.logic.clustering.ExtendedFeatureComputer import ExtendedFeatureComputerProvider


class SchedulerProcessRunner:
    """Runs one scheduler worker process and sends its results back."""

    def __init__(
        self,
        slots: List[Slot],
        checkers: List[IConflictChecker],
        queue: Queue,
        cancel_event: Event,
        max_results: int,
        batch_size: int,
        work_source,
        scorer=None,
        result_counter=None,
        run_id=None,
    ) -> None:
        if work_source is None:
            raise ValueError("SchedulerProcessRunner requires a work_source")
        # Exams that still need dates.
        self._slots = slots
        # Rules used to reject invalid schedules.
        self._checkers = checkers
        # Queue used to send results back to the main process.
        self._queue = queue
        # Shared cancel flag for stopping the search.
        self._cancel_event = cancel_event
        # Global result limit for the search.
        self._max_results = max_results
        # Number of schedules sent in one batch.
        self._batch_size = batch_size
        # Optional scorer used for sorting/ranking schedules.
        self._scorer = scorer
        # Shared source of work units (cubes) that this process pulls from.
        self._work_source = work_source
        # Shared counter so all processes respect the same max_results limit.
        self._result_counter = result_counter
        # Identifies which generation run this process is working on; forwarded
        # to the observer so its messages can be told apart from a stale,
        # just-cancelled run on the shared result queue.
        self._run_id = run_id


    def run(self) -> None:
        """Run this process by pulling work units from the shared work source."""
        self._run_work_loop()


    def _run_work_loop(self) -> None:
        """Pull work units from the shared source and search each one."""

        # Reuse one observer so batches can continue across work units.
        observer = self._create_observer()

        try:
            # One scheduler is reused for all units handled by this process.
            scheduler = self._create_scheduler()
            # Keep taking work until the queue sends None, which means there is no more work.
            while True:
                unit = self._work_source.get_next()
                # None is the real stop signal.
                if unit is None:
                    break

                # The work unit stores only dates, so we rebuild real assignments from local slots.
                seeds = [
                    ExamAssignment(
                        course=self._slots[i].course,
                        date=unit.seed_dates[i],
                        moed=self._slots[i].moed,
                        semester=self._slots[i].semester,
                    )
                    for i in range(len(unit.seed_dates))
                ]
                # Search only the subtree that starts from this seed.
                scheduler.generateSchedules(
                    self._slots, observer, self._max_results, seed_assignments=seeds, scorer=self._scorer
                )

            # Send one FINISHED message for the whole process, not per work unit.
            observer.on_finished()

        except Exception as e:
            # Report crashes so the main process can stop waiting. Sent as a
            # structured AppErrorInfo payload (not str(e)) so MemoryError keeps
            # its RESOURCE category and anything else is a clean INFRASTRUCTURE
            # message — never a raw exception string reaching the GUI.
            observer.on_error(build_process_error_payload(e, "scheduling"))



    def _create_observer(self) -> QueueScheduleObserver:
        """Create the object that sends scheduler updates through the queue."""

        # The observer batches schedules and pushes them to the result queue.
        return QueueScheduleObserver(
            self._queue,
            self._cancel_event,
            self._batch_size,
            self._scorer,
            result_counter=self._result_counter,
            result_limit=self._max_results,
            slots=self._slots,
            extension_provider=ExtendedFeatureComputerProvider(),
            run_id=self._run_id,
        )

    def _create_scheduler(self) -> Scheduler:
        """Create the backtracking scheduler with this process rules."""
        return Scheduler(self._checkers)
