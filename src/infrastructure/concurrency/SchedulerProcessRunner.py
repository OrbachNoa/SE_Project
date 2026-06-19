"""
Entry point for running the scheduler inside a background process. 
The backtracking search can be very heavy, so it runs in a separate process 
instead of blocking the main GUI process.
"""
from __future__ import annotations
import os
from multiprocessing import Queue
from multiprocessing.synchronize import Event
from typing import List

from .QueueScheduleObserver import QueueScheduleObserver
from src.logic.Scheduler import Scheduler
from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.SlotBuilder import Slot
from src.models.ExamSchedule import ExamAssignment


class SchedulerProcessRunner:
    """Creates the scheduler process dependencies and runs the search."""

    def __init__(
        self,
        slots: List[Slot],
        checkers: List[IConflictChecker],
        queue: Queue,
        cancel_event: Event,
        max_results: int,
        batch_size: int,
        scorer=None,
        work_source=None,
        result_counter=None,
        collect_checker_stats: bool = False,
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
        # Optional ScheduleScorer forwarded to the observer for sort scoring.
        self._scorer = scorer
        # Optional IWorkSource. When present, this process pulls work units (cubes)
        # and searches each one; when None, it runs the single full search as before.
        self._work_source = work_source
        # Shared cross-process counter (multiprocessing.Value) used to enforce
        # max_results exactly across every process/work unit. See
        # QueueScheduleObserver._reserve_result_slot for why this is needed:
        # under work-stealing, each work unit's search otherwise gets the full
        # max_results as its own independent local cap.
        self._result_counter = result_counter
        # Opt-in: when True, the Scheduler built for this run tracks per-checker
        # call/reject counts (see Scheduler.get_checker_stats). Off by default -
        # only the benchmark/diagnostics path turns this on.
        self._collect_checker_stats = collect_checker_stats

    def run(self) -> None:
        """Runs the scheduler and reports success or failure to the main process."""
        if self._work_source is None:
            self._run_single()
        else:
            self._run_work_loop()

    def _run_single(self) -> None:
        """Original behavior: one full search over all slots."""
        observer = self._create_observer()
        try:
            scheduler = self._create_scheduler()

            # Starts the actual backtracking algorithm.
            scheduler.generateSchedules(self._slots, observer, self._max_results, scorer=self._scorer)

            # Notifies the main process that we finished successfully.
            observer.on_finished(extra_stats={
                "pid": os.getpid(),
                "cubes_processed": None,
                "checker_stats": scheduler.get_checker_stats(),
            })

        except Exception as e:
            # If this process crashes, the main process still needs to know what happened.
            # Without this message, the GUI may keep waiting for results forever.
            observer.on_error(str(e))

    def _run_work_loop(self) -> None:
        """Dynamic work-stealing: pull cubes from the shared source and search
        each one, until the source is drained. One observer is reused across all
        units so batching carries across unit boundaries, and on_finished() is
        sent exactly once after the loop (SchedulerWorker counts one FINISHED per
        process, not per unit).
        """
        observer = self._create_observer()
        cubes_processed = 0
        try:
            scheduler = self._create_scheduler()
            while True:
                unit = self._work_source.get_next()
                # None means the sentinel was reached: no more work for this process.
                if unit is None:
                    break
                cubes_processed += 1

                # Rebuild the seed as real assignments from this process's own slots.
                # Only dates travel on the queue; course/moed/semester come from the
                # local slots, so object identity matches the slots the search uses.
                seeds = [
                    ExamAssignment(
                        course=self._slots[i].course,
                        date=unit.seed_dates[i],
                        moed=self._slots[i].moed,
                        semester=self._slots[i].semester,
                    )
                    for i in range(len(unit.seed_dates))
                ]
                # Full search of this cube: resume from the seed, no target_depth.
                scheduler.generateSchedules(
                    self._slots, observer, self._max_results, seed_assignments=seeds, scorer=self._scorer
                )

            # One FINISHED for the whole process, after all its units are done.
            observer.on_finished(extra_stats={
                "pid": os.getpid(),
                "cubes_processed": cubes_processed,
                "checker_stats": scheduler.get_checker_stats(),
            })

        except Exception as e:
            # If this process crashes, the main process still needs to know what happened.
            # Without this message, the GUI may keep waiting for results forever.
            observer.on_error(str(e))


    # These helper methods keep object creation separate from the run flow.
    # This makes the run method easier to read and easier to change later.

    def _create_observer(self) -> QueueScheduleObserver:
        """Creates the observer that sends scheduler updates through the queue."""
        return QueueScheduleObserver(
            self._queue,
            self._cancel_event,
            self._batch_size,
            self._scorer,
            result_counter=self._result_counter,
            result_limit=self._max_results,
            slots=self._slots,
        )

    def _create_scheduler(self) -> Scheduler:
        """Creates the scheduler with the conflict rules it should use."""
        return Scheduler(self._checkers, collect_checker_stats=self._collect_checker_stats)
