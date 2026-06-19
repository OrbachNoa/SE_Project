"""Service for launching schedule generation across one or more background processes."""
from __future__ import annotations

import os
import threading
import time
from multiprocessing import Process, Queue, Event, Value
from typing import List, Optional

from src.models.Course import Course
from src.models.ExamPeriod import ExamPeriod
from src.infrastructure.concurrency.SchedulerProcessRunner import SchedulerProcessRunner
from src.infrastructure.concurrency.SchedulerWorker import SchedulerWorker
from src.logic.SlotBuilder import SlotBuilder, Slot
from src.logic.ScheduleFeasibilityValidator import ScheduleFeasibilityValidator
from src.logic.feasibility.InfeasibleScheduleError import InfeasibleScheduleError
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.checkers.config.CheckerFactory import build_checkers
from src.logic.comparators.ScheduleScorer import ScheduleScorer
from src.logic.parallel.SearchSpacePartitioner import SearchSpacePartitioner
from src.infrastructure.concurrency.QueueWorkSource import QueueWorkSource
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository

try:
    import psutil
except ImportError:
    psutil = None

DEFAULT_MAX_RESULTS = 1000000
DEFAULT_BATCH_SIZE = 1000


def _default_num_processes() -> int:
    """Picks a worker count for dynamic work-stealing.

    Backtracking is CPU-bound (no I/O waits to fill), so it gets little benefit
    from SMT/hyperthreading: two such processes sharing one physical core mostly
    contend for the same cache and execution ports instead of running faster.
    Measured ~21% higher throughput from physical-core count workers than from
    logical-core count workers on a 16-logical/10-physical hybrid CPU.

    psutil.cpu_count(logical=False) gives the true physical core count across
    platforms. Without psutil, os.cpu_count() (logical) is halved as an
    approximation - imperfect on a true N-physical/N-logical machine (it would
    underuse it), but safe: it never oversubscribes.
    """
    if psutil is not None:
        physical = psutil.cpu_count(logical=False)
        if physical:
            return max(1, physical)
    return max(1, (os.cpu_count() or 2) // 2)


def _feed_work_queue(config, courses, selected_programs, slots, num_processes, work_queue, cancel_event, result_queue):
    """Runs on a background thread, concurrently with process spawn/startup
    (see generate_async). Computes the work units - still one blocking call,
    SearchSpacePartitioner is not a streaming generator - and feeds them into
    work_queue one at a time, checking cancel_event before each put so an
    early cap-hit (max_results already reached) stops feeding immediately
    instead of enqueueing units nobody will ever read.

    Always finishes by sending one sentinel per worker, even on error, so
    QueueWorkSource.get_next() never blocks forever waiting for a sentinel
    that was never sent. Partitioning errors are reported on the regular
    result queue (the same ERROR message type workers already use) since
    there is no other channel back to SchedulerWorker from this thread.
    """
    try:
        _t0 = time.perf_counter()
        partition_checkers = build_checkers(config, courses, selected_programs, slots)
        work_units = SearchSpacePartitioner(partition_checkers).partition(slots, num_processes)
        # Diagnostics only: how long partitioning itself took, now overlapped
        # with process startup instead of preceding it. Unrecognized message
        # types are silently ignored by SchedulerWorker's dispatch table, so
        # this is harmless for normal (non-benchmark) callers.
        result_queue.put(("PARTITION_DONE", time.perf_counter() - _t0))
        for unit in work_units:
            if cancel_event.is_set():
                break
            work_queue.put(unit)
    except Exception as e:
        result_queue.put(("ERROR", f"Fatal partitioning error: {type(e).__name__}: {str(e)}"))
    finally:
        for _ in range(num_processes):
            work_queue.put(None)
        # No producer touches this queue after the sentinels above. Tell its
        # feeder thread not to block flushing on process exit - otherwise a
        # worker terminated mid-poll can leave it joining forever and hang
        # the main process on shutdown (a Windows multiprocessing quirk).
        work_queue.cancel_join_thread()


def _run_scheduler_process(slots, courses, selected_programs, config, queue, cancel_event, max_results, batch_size, work_source=None, result_counter=None, collect_checker_stats=False):
    """
    Isolated process entry point running inside an independent OS child process.
    Builds the conflict checkers locally (from the constraints config) to avoid
    heavy inter-process serialization of precomputed structures.
    """
    try:
        checkers = build_checkers(config, courses, selected_programs, slots)
        scorer = ScheduleScorer(courses, selected_programs)
        runner = SchedulerProcessRunner(
            slots, checkers, queue, cancel_event, max_results, batch_size, scorer, work_source, result_counter,
            collect_checker_stats=collect_checker_stats,
        )
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
        errors = ScheduleFeasibilityValidator().validate(
            courses, program_ids, slots, config
        )
        if errors:
            raise InfeasibleScheduleError(errors)

        if num_processes is None:
            num_processes = _default_num_processes()

        cancel_event = Event()
        # Shared cross-process counter: under work-stealing, every work unit's
        # search gets the full max_results as its own independent local cap
        # (it has no notion of "remaining" budget across units/processes), so a
        # process-local count cannot enforce the real global limit. Every
        # accepted schedule reserves one slot here atomically (see
        # QueueScheduleObserver._reserve_result_slot), making the cap exact
        # instead of an approximate after-the-fact check in the consumer.
        result_counter = Value("q", 0)

        # Two separate queues: results (schedules/progress/finish/error) and work.
        # work_queue starts EMPTY - cube generation (build_checkers +
        # SearchSpacePartitioner.partition, ~1-1.3s measured) no longer blocks
        # here before any process exists. It used to run synchronously on this
        # thread, serializing partitioning and OS process startup even though
        # neither depends on the other's result. QueueWorkSource.get_next()
        # already retries on a momentarily-empty queue, so a process started
        # before any work exists just waits - it doesn't error or exit early.
        queue: Queue = Queue(maxsize=50)
        work_queue: Queue = Queue()
        work_source = QueueWorkSource(work_queue, cancel_event=cancel_event)

        # A fixed pool of persistent processes. Each gets the FULL slots list (not a
        # partition) and the SAME shared work source, then steals units until drained.
        # work_source/result_counter ride as keyword args so the positional args keep
        # their existing layout (..., max_results, batch_size), preserving backward
        # compatibility. num_processes is used as-is now (not capped to
        # len(work_units)) since that count isn't known yet; if fewer units exist
        # than processes, the extra processes just get their sentinel immediately
        # and exit cleanly.
        processes: List[Process] = []
        for _ in range(num_processes):
            process = Process(
                target=_run_scheduler_process,
                args=(slots, courses, program_ids, config, queue, cancel_event,
                      max_results, DEFAULT_BATCH_SIZE),
                kwargs={"work_source": work_source, "result_counter": result_counter},
                daemon=True,
            )
            processes.append(process)

        self._worker = SchedulerWorker(
            queue=queue,
            cancel_event=cancel_event,
            processes=processes,
            repository=self._repository,
            max_results=max_results,
        )
        self._worker.start()

        # Now compute the cubes, on a separate thread, concurrently with the
        # process spawn/startup that .start() just triggered asynchronously.
        feeder = threading.Thread(
            target=_feed_work_queue,
            args=(config, courses, program_ids, slots, num_processes, work_queue, cancel_event, queue),
            daemon=True,
        )
        feeder.start()

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
