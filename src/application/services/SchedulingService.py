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

# Used only to read the physical core count.
# This does not pin the processes to P-cores.
try:
    import psutil
except ImportError:
    # If psutil is not installed, we fall back to os.cpu_count.
    psutil = None

DEFAULT_MAX_RESULTS = 1000000
DEFAULT_BATCH_SIZE = 1000


def _default_num_processes() -> int:
    """Pick a safe number of worker processes.

    We use psutil to ask the OS how many physical cores it sees.
    This helps us avoid using every logical CPU.

    It does not choose P-cores for us.
    The OS still decides where each process actually runs.
    """
    if psutil is not None:
        # If psutil is installed, use logical = false to ask for real CPU cores, not the extra logical threads.
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
        partition_checkers = build_checkers(config, courses, selected_programs, slots)
        # Slice the problem into smaller work units.
        work_units = SearchSpacePartitioner(partition_checkers).partition(slots, num_processes)
        # Feed these units into the queue one by one.
        for unit in work_units:
            # If the user clicked 'Cancel', stop feeding work immediately.
            if cancel_event.is_set():
                break
            work_queue.put(unit)
    except Exception as e:
        # If something breaks while slicing the problem, let the main system know.
        result_queue.put(("ERROR", f"Fatal partitioning error: {type(e).__name__}: {str(e)}"))
    finally:
        # We put one 'None' into the queue for every worker process.
        # When a worker pulls a 'None', it knows there is no more work left and it can shut down.
        for _ in range(num_processes):
            work_queue.put(None)
        # This prevents the program from getting stuck (hanging) when it closes, 
        # which is a known bug in Windows multiprocessing.
        work_queue.cancel_join_thread()


def _run_scheduler_process(slots, courses, selected_programs, queue, cancel_event, max_results, batch_size, work_source, config=None, result_counter=None, collect_checker_stats=False):
    """
    This is the actual code that runs INSIDE each independent background worker.
    Each worker gets a copy of the raw data, builds its own tools, and starts crunching numbers.
    """
    try:
        # Build local copies of the rules (checkers) and the scoring system.
        # We do this here inside the worker to avoid passing heavy objects between processes.
        checkers = build_checkers(config, courses, selected_programs, slots)
        scorer = ScheduleScorer(courses, selected_programs)

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
            collect_checker_stats=collect_checker_stats,
        )
        runner.run()
    except Exception as e:
        # If the worker crashes, send an error message back to the main app.
        if queue is not None:
            queue.put(("ERROR", f"Fatal scheduling error: {type(e).__name__}: {str(e)}"))


class SchedulingService:
    """
    The main coordinator class. It prepares the data, checks for obvious impossible situations,
    and then spins up the multi-processing army to find the schedules.
    """

    def __init__(self, repository: SQLiteScheduleRepository) -> None:
        self._repository = repository
        self._slot_builder: Optional[SlotBuilder] = None
        self._checkers: List = []
        self._worker: Optional[SchedulerWorker] = None

    def build_slots(
        self, program_ids: List[str], courses: List[Course], periods: List[ExamPeriod]
    ) -> List[Slot]:
        """
        Convert raw courses and dates into 'Slots'. 
        Think of a Slot as an empty bucket waiting to be assigned a specific exam date.
        """
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
        # Decide how many worker processes to hire.
        if num_processes is None:
            num_processes = _default_num_processes()
        # Set up communication channels between the main app and the workers.
        cancel_event = Event()
        # "q" means the value is big number
        result_counter = Value("q", 0)

        # Workers send found schedules here; maxsize keeps pending batches from using too much RAM.
        queue: Queue = Queue(maxsize=50)
        # 'work_queue' is where workers go to pick up their next assignment.
        work_queue: Queue = Queue()
        work_source = QueueWorkSource(work_queue, cancel_event=cancel_event)

       # We create them and tell them to wait for work to appear in the 'work_queue'
        processes: List[Process] = []
        for i in range(num_processes):
            process = Process(
                target=_run_scheduler_process,
                args=(slots, courses, program_ids, queue, cancel_event,
                      max_results, DEFAULT_BATCH_SIZE, work_source),
                kwargs={"result_counter": result_counter, "config": config},
                daemon=True, # Daemon means they will automatically die if the main app closes.
            )
            processes.append(process)

        # This is a special worker that just watches the 'queue' and brings results to the user interface.
        self._worker = SchedulerWorker(
            queue=queue,
            cancel_event=cancel_event,
            processes=processes,
            repository=self._repository,
            max_results=max_results,
        )
        self._worker.start()

        # We start a separate thread to chop up the problem and put it in the 'work_queue'.
        # We do this on a separate thread so the user interface doesn't freeze while we do the math.
        feeder = threading.Thread(
            target=_feed_work_queue,
            args=(config, courses, program_ids, slots, num_processes, work_queue, cancel_event, queue),
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
