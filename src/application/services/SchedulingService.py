"""Service for launching schedule generation across one or more background processes."""
from __future__ import annotations

import os
import queue
import threading
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
from src.logic.indexes.SelectedProgramIndex import SelectedProgramIndex
from src.logic.parallel.SearchSpacePartitioner import SearchSpacePartitioner
from src.infrastructure.concurrency.QueueWorkSource import QueueWorkSource
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository
from src.application.errors.ExceptionMapper import build_process_error_payload
from src.config import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_BATCH_SIZE,
    WORK_UNITS_PER_WORKER,
    RESULT_QUEUE_BATCHES_PER_WORKER,
)

# Used only to read the physical core count.
# This does not pin the processes to P-cores.
import psutil


def _default_num_processes() -> int:
    """Pick a safe number of worker processes.

    We use psutil to ask the OS how many physical cores it sees.
    This helps us avoid using every logical CPU.

    It does not choose P-cores for us.
    The OS still decides where each process actually runs.
    """
    # Use logical = false to ask for real CPU cores, not the extra logical threads.
    physical = psutil.cpu_count(logical=False)
    # If the OS returned a valid physical core count, use it as the worker count.
    if physical:
        return max(1, physical)
    # os.cpu_count gives logical CPUs, so we use half as a safer number.
    return max(1, (os.cpu_count() or 2) // 2)


def _feed_work_queue(config, courses, selected_programs, slots, num_processes, work_queue, cancel_event, result_queue):
    """This runs in its own background thread. 
    Its only job is to break the massive scheduling problem into smaller, manageable 
    chunks (called 'work units') and push them into the shared work queue for the workers to grab.
    """
    try:
        # Build the checkers so we do not create WorkUnits from invalid starting points.
        selected_index = SelectedProgramIndex(courses, selected_programs, slots)
        partition_checkers = build_checkers(config, courses, selected_programs, slots, selected_index)
        # Create several work units per worker so fast workers can grab more work.
        desired_units = max(1, num_processes * WORK_UNITS_PER_WORKER)
        # Slice the problem into smaller work units.
        work_units = SearchSpacePartitioner(partition_checkers).partition(slots, desired_units)
        # Feed these units into the queue one by one.
        for unit in work_units:
            # If the user clicked 'Cancel', stop feeding work immediately.
            if cancel_event.is_set():
                break
            work_queue.put(unit)
    except Exception as e:
        # If something breaks while slicing the problem, let the main system know.
        result_queue.put(("ERROR", build_process_error_payload(e, "work partitioning")))
    finally:
        # We put one 'None' into the queue for every worker process.
        # When a worker pulls a 'None', it knows there is no more work left and it can shut down.
        for _ in range(num_processes):
            work_queue.put(None)
        # This prevents the program from getting stuck (hanging) when it closes, 
        # which is a known bug in Windows multiprocessing.
        work_queue.cancel_join_thread()


def _run_scheduler_process(slots, 
                           courses, 
                           selected_programs, 
                           queue, 
                           cancel_event, 
                           max_results, 
                           batch_size, 
                           work_source, 
                           config=None, 
                           result_counter=None
                           ):
    """
    This is the actual code that runs INSIDE each independent background worker.
    Each worker gets a copy of the raw data, builds its own tools, and starts crunching numbers.
    """
    try:
        # Build local copies of the rules (checkers) and the scoring system.
        # We do this here inside the worker to avoid passing heavy objects between processes.
        selected_index = SelectedProgramIndex(courses, selected_programs, slots)
        checkers = build_checkers(config, courses, selected_programs, slots, selected_index)
        scorer = ScheduleScorer(courses, selected_programs, selected_index)

        # Start the runner. It will automatically ask the 'work_source' for units of work,
        # find schedules, and push the results into the 'queue'.
        runner = SchedulerProcessRunner(
            slots,
            checkers,
            queue,
            cancel_event,
            max_results,
            batch_size,
            work_source,
            scorer=scorer,
            result_counter=result_counter,
        )
        runner.run()
    except Exception as e:
        # If the worker crashes, send an error message back to the main app.
        if queue is not None:
            queue.put(("ERROR", build_process_error_payload(e, "scheduling")))


def _drain_queue(q) -> None:
    """Empty a multiprocessing Queue of any stale leftover messages."""
    try:
        while not q.empty():
            q.get_nowait()
    except (queue.Empty, ValueError, OSError):
        pass


def _persistent_worker_loop(control_queue, ready_queue, work_queue, result_queue, cancel_event, result_counter):
    """Runs inside a long-lived worker process owned by the pool.

    Spawning a fresh OS process (and re-importing this whole module) on every
    single 'Generate' click is the dominant share of the click-to-results
    delay on Windows. This loop pays that cost once per app session: it waits
    on 'control_queue' for the parameters of a new run, executes it via the
    existing one-shot '_run_scheduler_process' helper, then loops back and
    waits for the next run instead of exiting.
    """
    work_source = QueueWorkSource(work_queue, cancel_event=cancel_event)
    while True:
        # Signal idle/ready *before* blocking for the next run, so whoever
        # is waiting for this process to become available (see
        # SchedulingService._pool_start_run) is unblocked as soon as this
        # worker is free to take a new assignment.
        ready_queue.put(True)
        payload = control_queue.get()
        if payload is None:
            break
        courses, selected_programs, slots, config, max_results, batch_size = payload
        _run_scheduler_process(
            slots, courses, selected_programs, result_queue, cancel_event,
            max_results, batch_size, work_source,
            config=config, result_counter=result_counter,
        )


class SchedulingService:
    """
    The main coordinator class. It prepares the data, checks for obvious impossible situations,
    and then spins up the multi-processing army to find the schedules.
    """

    def __init__(self, repository: SQLiteScheduleRepository) -> None:
        self._repository = repository
        self._worker: Optional[SchedulerWorker] = None

        # Persistent worker-process pool: created once (lazily, or eagerly via
        # warm_up_async) and reused by every generate_async call, so the OS
        # process spawn / interpreter cold-start cost is paid once per app
        # session instead of once per "Generate" click.
        self._pool_lock = threading.Lock()
        self._pool_processes: Optional[List[Process]] = None
        self._pool_control_queue: Optional[Queue] = None
        self._pool_ready_queue: Optional[Queue] = None
        self._pool_work_queue: Optional[Queue] = None
        self._pool_result_queue: Optional[Queue] = None
        self._pool_cancel_event = None
        self._pool_result_counter = None
        self._pool_num_processes: Optional[int] = None

    def warm_up_async(self, num_processes: Optional[int] = None) -> None:
        """Start the persistent worker pool on a background thread.

        Safe to call once at app startup so process spawn happens during idle
        time (e.g. while the user loads files) rather than on first Generate.
        """
        threading.Thread(
            target=self.ensure_pool_started, args=(num_processes,), daemon=True
        ).start()

    def ensure_pool_started(self, num_processes: Optional[int] = None) -> None:
        """Create the persistent worker pool if it isn't running yet. Idempotent."""
        if self._pool_processes is not None:
            return
        with self._pool_lock:
            if self._pool_processes is not None:
                return
            if num_processes is None:
                num_processes = _default_num_processes()

            cancel_event = Event()
            # "q" means the value is a big number
            result_counter = Value("q", 0)
            # Workers send found schedules here. maxsize counts pending result
            # batches, not individual schedules.
            result_queue: Queue = Queue(maxsize=max(1, num_processes * RESULT_QUEUE_BATCHES_PER_WORKER))
            # 'work_queue' is where workers go to pick up their next assignment.
            work_queue: Queue = Queue()
            # Carries each new run's parameters to the already-running workers.
            control_queue: Queue = Queue()
            # Workers post here when they are idle and ready for a new run.
            ready_queue: Queue = Queue()

            processes: List[Process] = []
            for _ in range(num_processes):
                process = Process(
                    target=_persistent_worker_loop,
                    args=(control_queue, ready_queue, work_queue, result_queue, cancel_event, result_counter),
                    daemon=True,  # Daemon means they will automatically die if the main app closes.
                )
                processes.append(process)
            for process in processes:
                process.start()

            self._pool_num_processes = num_processes
            self._pool_cancel_event = cancel_event
            self._pool_result_counter = result_counter
            self._pool_result_queue = result_queue
            self._pool_work_queue = work_queue
            self._pool_control_queue = control_queue
            self._pool_ready_queue = ready_queue
            self._pool_processes = processes

    def _pool_start_run(self, courses, selected_programs, slots, config, max_results, batch_size) -> None:
        """Reset the shared pool state for a new run and hand it to every worker.

        Blocks until every worker has returned to idle from any previous run
        (including one that was just cancelled): the pool's queues/event/
        counter are reused across runs, so a worker still winding down from
        the previous run must not see this run's freshly-cleared state. In
        the steady state (workers already idle) this returns immediately; it
        only blocks meaningfully right after a cancel.
        """
        for _ in range(self._pool_num_processes):
            try:
                self._pool_ready_queue.get(timeout=10.0)
            except queue.Empty:
                raise RuntimeError("Scheduler pool did not become ready for a new run in time.")

        self._pool_cancel_event.clear()
        with self._pool_result_counter.get_lock():
            self._pool_result_counter.value = 0
        _drain_queue(self._pool_work_queue)
        _drain_queue(self._pool_result_queue)

        payload = (courses, selected_programs, slots, config, max_results, batch_size)
        for _ in range(self._pool_num_processes):
            self._pool_control_queue.put(payload)

    def shutdown_pool(self) -> None:
        """Stop every persistent worker process. Call once, on app exit."""
        if self._pool_processes is None:
            return
        if self._pool_cancel_event is not None:
            self._pool_cancel_event.set()
        for _ in range(self._pool_num_processes):
            self._pool_control_queue.put(None)
        for process in self._pool_processes:
            process.join(timeout=1.0)
        for process in self._pool_processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
        self._pool_processes = None

    def build_slots(
        self, program_ids: List[str], courses: List[Course], periods: List[ExamPeriod]
    ) -> List[Slot]:
        """
        Convert raw courses and dates into 'Slots'.
        Think of a Slot as an empty bucket waiting to be assigned a specific exam date.
        """
        return SlotBuilder(periods, program_ids).build(courses)

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
        This is the main engine starter. It sets up the parallel processing environment
        and starts the whole operation in the background
        """
        # Build the slot list and give it to the repository for decoding packed results later.
        slots = self.build_slots(program_ids, courses, periods)
        self._repository.configure_slots(slots)

        # Before we waste CPU time, we make sure the schedule isnt mathematically impossible
        errors = ScheduleFeasibilityValidator().validate(
            courses, program_ids, slots, config
        )
        if errors:
            raise InfeasibleScheduleError(errors)

        # Make sure the persistent pool exists (no-op if warm_up_async already
        # started it). The pool's size is fixed the first time it is created;
        # later calls reuse it regardless of what num_processes they ask for.
        self.ensure_pool_started(num_processes)
        active_num_processes = self._pool_num_processes

        # Reset the pool's shared state for this run and hand it to every
        # already-running worker -- no new OS process is created here.
        self._pool_start_run(courses, program_ids, slots, config, max_results, DEFAULT_BATCH_SIZE)

        # This is a special worker that just watches the 'queue' and brings results to the user interface.
        self._worker = SchedulerWorker(
            queue=self._pool_result_queue,
            cancel_event=self._pool_cancel_event,
            processes=self._pool_processes,
            repository=self._repository,
            max_results=max_results,
            owns_processes=False,
        )
        self._worker.start()

        # We start a separate thread to chop up the problem and put it in the 'work_queue'.
        # We do this on a separate thread so the user interface doesn't freeze while we do the math.
        feeder = threading.Thread(
            target=_feed_work_queue,
            args=(config, courses, program_ids, slots, active_num_processes,
                  self._pool_work_queue, self._pool_cancel_event, self._pool_result_queue),
            daemon=True,
        )
        feeder.start()
        # Give the worker back to the main app so it can watch the progress.
        return self._worker

    def cancel(self) -> None:
        """Emergency Stop. Triggers the 'cancel_event',
          which forces all background workers to drop what they are doing and shut down cleanly.
          """
        if self._worker is not None:
            self._worker.cancel()
