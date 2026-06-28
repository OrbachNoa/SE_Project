"""Service for launching schedule generation across one or more background processes."""
from __future__ import annotations

import itertools
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
from src.infrastructure.concurrency.CpuTopology import (
    performance_core_groups,
    recommended_worker_count,
)
from src.application.errors.ExceptionMapper import build_process_error_payload
from src.config import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_BATCH_SIZE,
    WORK_UNITS_PER_WORKER,
    RESULT_QUEUE_BATCHES_PER_WORKER,
    WORKER_PROCESS_COUNT,
    WORKER_AFFINITY_ENABLED,
    RESERVED_CORES_FOR_MAIN,
)

# Used only to read the physical core count.
# This does not pin the processes to P-cores.
import psutil


def _default_num_processes() -> int:
    """Resolve the worker count: env override > config constant > CPU topology.

    On hybrid CPUs the topology default is one worker per physical performance
    (P) core -- see CpuTopology -- not every physical core, because workers
    placed on the slow efficiency (E) cores become stragglers and (on laptops)
    drive thermal throttling, which made the old "all physical cores" default
    slower under sustained load.
    """
    # 1. Runtime override, so the count can be tuned without code changes.
    env_value = os.environ.get("SCHEDULER_WORKER_PROCESSES")
    if env_value:
        try:
            parsed = int(env_value)
            if parsed > 0:
                return parsed
        except ValueError:
            pass  # Ignore a malformed override and fall through to the defaults.

    # 2. Explicit project config wins over auto-detection.
    if WORKER_PROCESS_COUNT is not None:
        return max(1, int(WORKER_PROCESS_COUNT))

    # 3. Auto: one worker per P-core, minus any cores reserved for the main
    # thread -- the reservation only applies on a detected hybrid CPU; on a
    # non-hybrid CPU this returns every physical core, unreduced.
    return recommended_worker_count(reserved_for_main=RESERVED_CORES_FOR_MAIN)


def _feed_work_queue(config, courses, selected_programs, slots, num_processes, work_queue, cancel_event, result_queue, run_id=None):
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
        # Wrapped with run_id (when given) so SchedulerWorker can tell this
        # apart from a stale error left over from a just-cancelled run.
        error_payload = build_process_error_payload(e, "work partitioning")
        result_queue.put(("ERROR", error_payload if run_id is None else (run_id, error_payload)))
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
                           result_counter=None,
                           run_id=None,
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
        scorer = ScheduleScorer(courses, selected_programs, selected_index, slots=slots)

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
            run_id=run_id,
        )
        runner.run()
    except Exception as e:
        # If the worker crashes, send an error message back to the main app.
        # Wrapped with run_id (when given) so SchedulerWorker can tell this
        # apart from a stale error left over from a just-cancelled run.
        if queue is not None:
            error_payload = build_process_error_payload(e, "scheduling")
            queue.put(("ERROR", error_payload if run_id is None else (run_id, error_payload)))


def _drain_queue(q) -> None:
    """Empty a multiprocessing Queue of any stale leftover messages."""
    try:
        while True:
            q.get_nowait()
    except (queue.Empty, ValueError, OSError):
        pass


# How often an idle worker checks that its parent is still alive while
# waiting for the next run. Short enough that a killed app does not leave
# orphans running for long; long enough not to matter for CPU usage.
_PARENT_LIVENESS_CHECK_SECONDS = 2.0


def _parent_is_alive(parent_pid: int, parent_create_time: float) -> bool:
    """True if the process at parent_pid is still the same one we started under.

    Comparing create_time (not just PID) guards against the OS recycling
    parent_pid for an unrelated process after the real parent exits.
    """
    try:
        return psutil.Process(parent_pid).create_time() == parent_create_time
    except psutil.NoSuchProcess:
        return False


def _apply_worker_affinity(affinity_ids) -> None:
    """Pin this worker to a fixed set of logical CPUs (its assigned P-core).

    Best-effort: any failure (unsupported platform, permission, bad id list)
    is swallowed so a worker never dies just because it could not be pinned.
    """
    if not affinity_ids:
        return
    try:
        psutil.Process().cpu_affinity(list(affinity_ids))
    except (psutil.Error, OSError, ValueError, AttributeError):
        pass


def _persistent_worker_loop(control_queue, ready_queue, work_queue, result_queue, cancel_event, result_counter, run_id_holder, parent_pid, parent_create_time, affinity_ids=None):
    """Runs inside a long-lived worker process owned by the pool.

    Spawning a fresh OS process (and re-importing this whole module) on every
    single 'Generate' click is the dominant share of the click-to-results
    delay on Windows. This loop pays that cost once per app session: it waits
    on 'control_queue' for the parameters of a new run, executes it via the
    existing one-shot '_run_scheduler_process' helper, then loops back and
    waits for the next run instead of exiting.

    'run_id_holder' is a separate shared Value (not part of the control
    payload tuple itself) so each worker can tag its outgoing messages with
    the active run id without changing the payload's shape.

    Normal shutdown (app closes cleanly) sends a None sentinel through
    control_queue -- see SchedulingService.shutdown_pool(). But if the main
    process is killed outright (closed console window, taskkill, hard crash)
    that sentinel never arrives, and daemon=True only auto-kills children
    during a *normal* Python interpreter shutdown -- not when the parent is
    killed externally. So while idle, this loop also polls for parent death
    on its own and exits itself rather than becoming an orphan.
    """
    # Pin to the assigned P-core once, before any work, so the OS keeps this
    # CPU-bound worker on a fast core instead of drifting it onto an E-core.
    _apply_worker_affinity(affinity_ids)

    work_source = QueueWorkSource(work_queue, cancel_event=cancel_event)
    while True:
        # Signal idle/ready *before* blocking for the next run, so whoever
        # is waiting for this process to become available (see
        # SchedulingService._pool_start_run) is unblocked as soon as this
        # worker is free to take a new assignment.
        ready_queue.put(True)
        payload = None
        got_payload = False
        while not got_payload:
            try:
                payload = control_queue.get(timeout=_PARENT_LIVENESS_CHECK_SECONDS)
                got_payload = True
            except queue.Empty:
                if not _parent_is_alive(parent_pid, parent_create_time):
                    return
        if payload is None:
            break
        courses, selected_programs, slots, config, max_results, batch_size = payload
        run_id = run_id_holder.value
        _run_scheduler_process(
            slots, courses, selected_programs, result_queue, cancel_event,
            max_results, batch_size, work_source,
            config=config, result_counter=result_counter, run_id=run_id,
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
        self._pool_run_id_holder = None
        self._pool_num_processes: Optional[int] = None

        # Monotonic id for each generate_async() call, used to tell a stale
        # message from a just-cancelled run apart from the current run's
        # messages on the shared, cross-run result queue.
        self._run_id_counter = itertools.count(1)

    def warm_up_async(self, num_processes: Optional[int] = None) -> None:
        """Start the persistent worker pool on a background thread.

        Safe to call once at app startup so process spawn happens during idle
        time (e.g. while the user loads files) rather than on first Generate.
        """
        threading.Thread(
            target=self.ensure_pool_started, args=(num_processes,), daemon=True
        ).start()

    @staticmethod
    def _resolve_pool_size(num_processes: Optional[int]) -> int:
        """Return the requested pool size, validating explicit overrides."""
        if num_processes is None:
            return _default_num_processes()
        if num_processes <= 0:
            raise ValueError("num_processes must be a positive integer")
        return int(num_processes)

    def _validate_pool_size_request(self, num_processes: Optional[int]) -> None:
        """Reject explicit pool-size changes after the persistent pool exists."""
        if num_processes is None or self._pool_processes is None:
            return

        requested = self._resolve_pool_size(num_processes)
        if requested != self._pool_num_processes:
            raise ValueError(
                "scheduler worker pool is already started with "
                f"{self._pool_num_processes} process(es); requested {requested}. "
                "Call shutdown_pool() before changing the process count."
            )

    def ensure_pool_started(self, num_processes: Optional[int] = None) -> None:
        """Create the persistent worker pool if it isn't running yet. Idempotent."""
        if self._pool_processes is not None:
            self._validate_pool_size_request(num_processes)
            return
        with self._pool_lock:
            if self._pool_processes is not None:
                self._validate_pool_size_request(num_processes)
                return
            num_processes = self._resolve_pool_size(num_processes)

            cancel_event = Event()
            # "q" means the value is a big number
            result_counter = Value("q", 0)
            # Holds the active run's id, separate from the control payload so
            # the payload's own shape never changes between runs.
            run_id_holder = Value("q", 0)
            # Workers send found schedules here. maxsize counts pending result
            # batches, not individual schedules.
            result_queue: Queue = Queue(maxsize=max(1, num_processes * RESULT_QUEUE_BATCHES_PER_WORKER))
            # 'work_queue' is where workers go to pick up their next assignment.
            work_queue: Queue = Queue()
            # Carries each new run's parameters to the already-running workers.
            control_queue: Queue = Queue()
            # Workers post here when they are idle and ready for a new run.
            ready_queue: Queue = Queue()

            # Captured once, here in the main process, so every worker can
            # later verify the *same* parent is still alive (not just that
            # some process happens to occupy this pid now).
            parent_pid = os.getpid()
            parent_create_time = psutil.Process(parent_pid).create_time()

            # One logical-id group per physical P-core, so worker i can be pinned
            # to its own fast core. Empty when affinity is off or the CPU has no
            # P/E split -- in that case no worker is pinned (old behaviour).
            affinity_groups = performance_core_groups() if WORKER_AFFINITY_ENABLED else []

            processes: List[Process] = []
            for worker_index in range(num_processes):
                affinity_ids = (
                    affinity_groups[worker_index % len(affinity_groups)]
                    if affinity_groups
                    else None
                )
                process = Process(
                    target=_persistent_worker_loop,
                    args=(control_queue, ready_queue, work_queue, result_queue, cancel_event, result_counter, run_id_holder, parent_pid, parent_create_time, affinity_ids),
                    daemon=True,  # Daemon means they will automatically die if the main app closes normally.
                )
                processes.append(process)
            for process in processes:
                process.start()

            self._pool_num_processes = num_processes
            self._pool_cancel_event = cancel_event
            self._pool_result_counter = result_counter
            self._pool_run_id_holder = run_id_holder
            self._pool_result_queue = result_queue
            self._pool_work_queue = work_queue
            self._pool_control_queue = control_queue
            self._pool_ready_queue = ready_queue
            self._pool_processes = processes

    def _pool_start_run(self, courses, selected_programs, slots, config, max_results, batch_size, run_id) -> None:
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
        # Set before the control payload is queued, so every worker reads the
        # new run's id as soon as it picks up that payload.
        self._pool_run_id_holder.value = run_id
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
        and starts the whole operation in the background.

        ``num_processes`` is only allowed to choose the persistent pool size
        before that pool is started. Later calls with ``None`` reuse the active
        pool; later calls with a different explicit value fail clearly.
        """
        # Identifies this run on the shared, cross-run result queue so a
        # message left over from a just-cancelled run can be told apart from
        # this run's own messages.
        run_id = next(self._run_id_counter)

        # Reject an invalid config before it can reach the checkers, where an
        # out-of-range k would otherwise just silently disable the rule.
        if config is not None:
            config.validate()

        # Build the slot list and give it to the repository for decoding packed results later.
        slots = self.build_slots(program_ids, courses, periods)
        self._repository.configure_slots(slots)

        # This service starts the run, so it also owns clearing previous
        # results -- independent of whether the GUI controller already did.
        self._repository.clear()

        # Before we waste CPU time, we make sure the schedule isnt mathematically impossible
        errors = ScheduleFeasibilityValidator().validate(
            courses, program_ids, slots, config
        )
        if errors:
            raise InfeasibleScheduleError(errors)

        # Make sure the persistent pool exists (no-op if warm_up_async already
        # started it). The pool's size is fixed the first time it is created
        # (resolved by _default_num_processes: env > config > CPU topology);
        # later calls reuse it regardless of what num_processes they ask for.
        self.ensure_pool_started(num_processes)
        active_num_processes = self._pool_num_processes

        # Reset the pool's shared state for this run and hand it to every
        # already-running worker -- no new OS process is created here.
        self._pool_start_run(courses, program_ids, slots, config, max_results, DEFAULT_BATCH_SIZE, run_id)

        # This is a special worker that just watches the 'queue' and brings results to the user interface.
        self._worker = SchedulerWorker(
            queue=self._pool_result_queue,
            cancel_event=self._pool_cancel_event,
            processes=self._pool_processes,
            repository=self._repository,
            max_results=max_results,
            owns_processes=False,
            expected_run_id=run_id,
        )
        self._worker.start()

        # We start a separate thread to chop up the problem and put it in the 'work_queue'.
        # We do this on a separate thread so the user interface doesn't freeze while we do the math.
        feeder = threading.Thread(
            target=_feed_work_queue,
            args=(config, courses, program_ids, slots, active_num_processes,
                  self._pool_work_queue, self._pool_cancel_event, self._pool_result_queue, run_id),
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
