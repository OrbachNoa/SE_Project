"""Bridge between the background scheduler processes and the PyQt GUI."""
from __future__ import annotations
import queue  # Required to catch the specific queue.Empty exception
from multiprocessing import Queue, Process
from multiprocessing.synchronize import Event
from typing import List
from PyQt6.QtCore import QThread, pyqtSignal

from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository
from src.application.errors.ErrorModel import (
    AppErrorInfo,
    ErrorCategory,
    ErrorSeverity,
)
from src.application.errors.ExceptionMapper import default_registry


class SchedulerWorker(QThread):
    """
    Monitors the scheduler processes and updates the GUI safely. 
    The heavy backtracking work runs in separate processes. 
    This QThread listens to their shared queue, saves schedule batches to SQLite, 
    and sends small status updates to the GUI using Qt signals.
    """

    # Signals are used because the GUI must be updated only from the Qt-safe signal system.
    
    # Old signal for sending one full schedule to the GUI.
    # The current code uses batches instead, but this is kept so older code will not crash.
    schedule_found        = pyqtSignal(object)      
    schedules_batch_found = pyqtSignal(int)         # Sends how many schedules were saved in the last batch.
    progress_updated      = pyqtSignal(int)
    search_finished       = pyqtSignal()
    error_occurred        = pyqtSignal(str)

    def __init__(self, queue: Queue, cancel_event: Event, processes: List[Process], repository: SQLiteScheduleRepository, max_results: int = None, owns_processes: bool = True, expected_run_id=None) -> None:
        super().__init__()

        # Shared queue used by all scheduler processes to send messages to this worker.
        self._queue = queue
        # Shared flag used to ask all scheduler processes to stop.
        self._cancel_event = cancel_event
        # All background processes that run parts of the scheduling search.
        self._processes = processes
        # Repository used to save compressed schedule batches to SQLite.
        self._repository = repository
        # When set, every message is expected to be wrapped as (run_id, payload)
        # by the producing QueueScheduleObserver; messages tagged with a
        # different run_id are stale leftovers from a just-cancelled run on
        # the shared, cross-run result queue and are dropped. None (the
        # default, used by every caller that does not pass one) disables this
        # check entirely and reads every message in its old, unwrapped shape.
        self._expected_run_id = expected_run_id
        # False when `processes` are persistent workers owned by a long-lived
        # pool (SchedulingService): this worker must then never start, join,
        # or terminate them -- only the (per-run) cancel_event may signal them
        # to stop, since the same OS processes are reused for the next run.
        self._owns_processes = owns_processes
        # Global result cap. With dynamic work-stealing there are no per-process
        # budgets, so the cap is enforced here across all processes. None disables it.
        self._max_results = max_results
        # Running total of schedules saved so far, used to trip the global cap.
        self._saved_count = 0

        # Each process sends one FINISHED message when it completes.
        # The whole search is done only after all processes have finished.
        self._expected_finishes = len(processes)
        self._finished_count = 0

        # The structured form of the last failure (code/category/severity).
        # error_occurred stays a str signal for the GUI, but callers/tests that
        # want the full record can read this after a failure.
        self.last_error: AppErrorInfo = None
        # Maps an unexpected IPC-read exception to a safe AppErrorInfo instead
        # of leaking its raw str() into the user-facing message.
        self._errors = default_registry()

        # Maps each queue message type to the method that handles it.
        self._dispatch = {
            "SCHEDULE_BATCH": self._handle_schedule_batch,
            "PROGRESS": self._handle_progress,
            "ERROR": self._handle_error,
            "FINISHED": self._handle_finished,
        }

    def run(self) -> None:
        """Starts the scheduler processes and keeps reading messages from the queue."""
        if self._owns_processes:
            # Start all background processes that perform the heavy scheduling work.
            for process in self._processes:
                process.start()

        try:
            while True:
                try:
                    # Wait for the next message from any scheduler process.
                    msg_type, payload = self._queue.get(timeout=1.0)
                except queue.Empty:
                    # No message arrived during the timeout.
                    if self._owns_processes:
                        # If all processes are dead, decide whether the search ended normally or crashed.
                        if not any(p.is_alive() for p in self._processes):
                            if self._cancel_event.is_set():
                                break
                            # Fallback for cases where a process ended without sending FINISHED.
                            self._emit_terminal_state()
                            break
                    else:
                        # Persistent pool: processes stay alive between runs, so
                        # "all dead" never naturally happens here. Still watch
                        # for an individual worker crashing unexpectedly.
                        crashed = [p for p in self._processes if p.exitcode not in (0, None)]
                        if crashed:
                            self._emit_terminal_state()
                            break
                    # Some processes are still alive, so keep waiting for more messages.
                    continue
                except ValueError:
                    # The queue was probably closed while this worker was waiting.
                    break
                except Exception as e:
                    # Report unexpected queue/IPC errors instead of leaving the GUI waiting
                    # forever. Routed through the same mapper registry as every other
                    # boundary so the user never sees a raw str(e); the unknown-fallback
                    # context keeps the historical CRITICAL/non-recoverable/IPC code for
                    # whatever this exception turns out to be.
                    info = self._errors.map(e, {
                        "category": ErrorCategory.INFRASTRUCTURE,
                        "severity": ErrorSeverity.CRITICAL,
                        "recoverable": False,
                        "fallback_code": "SCHEDULER_IPC_ERROR",
                        "stage": "ipc_read",
                    })
                    self._emit_error(info)
                    break

                if self._expected_run_id is not None:
                    # Producer wraps every message as (run_id, payload) when
                    # given a run_id; drop anything tagged for a different
                    # (stale) run instead of acting on it.
                    run_id, payload = payload
                    if run_id != self._expected_run_id:
                        continue

                # Choose the correct handler according to the message type.
                handler = self._dispatch.get(msg_type)
                # If the handler returns False, stop the monitoring loop.
                if handler and not handler(payload):
                    break
        finally:
            # Always clean up child processes, even after errors or cancellation.
            self._shutdown()

    def _emit_terminal_state(self) -> None:
        """
        Handles the case where all processes stopped but not all FINISHED messages arrived.
        If any process exited with an error code, the result may be incomplete. 
        Otherwise, we treat the search as finished.
        """
        crashed = [p for p in self._processes if p.exitcode not in (0, None)]
        if crashed:
            exit_code = crashed[0].exitcode
            self._emit_error(AppErrorInfo(
                code="SCHEDULER_PROCESS_CRASHED",
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.CRITICAL,
                user_message=f"The scheduling engine crashed unexpectedly (Exit code: {exit_code})",
                technical_message=f"Worker process exited with code {exit_code}",
                recoverable=False,
                context={"exit_code": exit_code},
            ))
        else:
            self.search_finished.emit()

    def cancel(self) -> None:
        """Requests cancellation and then stops any process that did not exit by itself."""
        if self._cancel_event is not None:
            self._cancel_event.set()

        if not self._owns_processes:
            # Persistent pool: the cancel_event alone tells the (reused) OS
            # processes to stop this run. Joining/terminating them here would
            # kill processes the pool needs for the next "Generate" click.
            self._drain_queue()
            return

        # First, give each process a short chance to stop normally.
        for process in self._processes:
            if process is not None and process.is_alive():
                process.join(timeout=0.5)

        # Then force-stop any process that is still running.
        for process in self._processes:
            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout=1.0)

        self._drain_queue()

    def _shutdown(self) -> None:
        """
        Cleans up after the worker loop ends. Runs for every ending case:
        normal finish, error, or cancellation. Does not emit GUI signals; it
        only releases process and queue resources.
        """
        if not self._owns_processes:
            # Persistent pool: never join/terminate these processes -- just
            # drain leftovers so the queue is clean for the pool's next run.
            self._drain_queue()
            return

        # If some processes are still alive, ask them to stop first.
        if any(p.is_alive() for p in self._processes):
            if self._cancel_event is not None:
                self._cancel_event.set()
            for process in self._processes:
                if process.is_alive():
                    process.join(timeout=0.5)

        # Join every process, and force-terminate processes that ignored the cancel flag.
        for process in self._processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
            else:
                process.join()

        self._drain_queue()

    def _drain_queue(self) -> None:
        """Clear remaining queue messages so stale data never leaks into the next read."""
        try:
            while not self._queue.empty():
                self._queue.get_nowait()
        except (queue.Empty, ValueError, OSError):
            pass


    def _handle_schedule_batch(self, payload) -> bool:
        """Saves one compressed schedule batch and notifies the GUI how many schedules were added."""
        # Payload is (data, count) or (data, count, batch_scores); the third
        # element carries per-schedule scores for the narrow score table.
        data, count = payload[0], payload[1]
        batch_scores = payload[2] if len(payload) > 2 else None
        if count:
            self._repository.insert_compressed_batch(data, count, batch_scores)
            self.schedules_batch_found.emit(count)
            # Enforce the global result cap across all processes: once enough
            # schedules are saved, ask every process to stop via the shared cancel
            # flag (already polled inside the search loop). The boundary batch may
            # overshoot by up to ~N*batch_size, which is accepted for now.
            self._saved_count += count
            if self._max_results is not None and self._saved_count >= self._max_results:
                if self._cancel_event is not None:
                    self._cancel_event.set()
        return True

    def _handle_progress(self, payload) -> bool:
        """Sends a progress update to the GUI."""
        self.progress_updated.emit(payload)
        return True

    def _handle_error(self, payload) -> bool:
        """Reports an error to the GUI and stops the worker loop.

        ``payload`` from a worker process is a user-facing string today, but may
        also be an AppErrorInfo serialised dict; both are normalised to a clean
        string for the GUI while keeping the structured record in last_error.
        """
        if isinstance(payload, dict):
            self._emit_error(AppErrorInfo.from_payload(payload))
        else:
            self.last_error = AppErrorInfo(
                code="SCHEDULER_PROCESS_ERROR",
                category=ErrorCategory.SCHEDULING,
                severity=ErrorSeverity.ERROR,
                user_message=str(payload),
            )
            self.error_occurred.emit(str(payload))
        return False

    def _emit_error(self, info: AppErrorInfo) -> None:
        """Store the structured error and emit its clean user message."""
        self.last_error = info
        self.error_occurred.emit(info.user_message)

    def _handle_finished(self, payload) -> bool:
        """ Handles a FINISHED message from one scheduler process.
            The worker keeps listening until every process has sent FINISHED.
            Only then the whole scheduling search is complete.
        """
        self._finished_count += 1
        if self._finished_count >= self._expected_finishes:
            self.search_finished.emit()
            return False  # All processes finished, so stop the loop.
        return True       # Other processes may still send more results.