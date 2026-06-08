"""Bridge between the background scheduler processes and the PyQt GUI."""
from __future__ import annotations
import queue  # Required to catch the specific queue.Empty exception
from multiprocessing import Queue, Process
from multiprocessing.synchronize import Event
from typing import List
from PyQt6.QtCore import QThread, pyqtSignal

from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository


class SchedulerWorker(QThread):
    """
    Asynchronous worker thread that monitors one or more background scheduler
    processes. All processes stream their results into a single shared queue;
    this thread drains that queue, persists batches to SQLite, and forwards
    lightweight status updates to the GUI thread via Qt signals.
    """

    # --- PyQt Signals to safely communicate asynchronous engine events to the GUI thread ---
    schedule_found        = pyqtSignal(object)      # Kept for backward compatibility profiles
    schedules_batch_found = pyqtSignal(int)         # Emits lightweight packet size scalar to bypass UI event lag
    progress_updated      = pyqtSignal(int)
    search_finished       = pyqtSignal()
    error_occurred        = pyqtSignal(str)

    def __init__(self, queue: Queue, cancel_event: Event, processes: List[Process], repository: SQLiteScheduleRepository) -> None:
        super().__init__()

        # Inter-process pipeline conduit feeding raw solution blocks from all child processes
        self._queue = queue
        # Shared cancellation state monitor flag to interrupt every partition mid-run
        self._cancel_event = cancel_event
        # All parallel partition processes feeding the single shared queue
        self._processes = processes
        # Local SQLite storage client invoked directly inside this background worker context
        self._repository = repository

        # Each partition emits exactly one FINISHED when its subtree is exhausted;
        # the whole search is complete only after every partition has reported in.
        self._expected_finishes = len(processes)
        self._finished_count = 0

        # Maps operational message string signatures over to active execution handler routes
        self._dispatch = {
            "SCHEDULE_BATCH": self._handle_schedule_batch,
            "PROGRESS": self._handle_progress,
            "ERROR": self._handle_error,
            "FINISHED": self._handle_finished,
        }

    def run(self) -> None:
        """Main loop: start every partition process and drain the shared queue."""
        # Spin up all secondary heavy computation child processes
        for process in self._processes:
            process.start()

        try:
            while True:
                try:
                    # Capture next signal transmission frame boundary passing down the stream
                    msg_type, payload = self._queue.get(timeout=1.0)
                except queue.Empty:
                    # The channel went quiet — only act once every process has exited.
                    if not any(p.is_alive() for p in self._processes):
                        if self._cancel_event.is_set():
                            break
                        # Crash-recovery fallback if a clean FINISHED handshake was skipped
                        self._emit_terminal_state()
                        break
                    continue
                except ValueError:
                    break
                except Exception as e:
                    # Trap unexpected marshaling or runtime crashes safely to prevent silent GUI lockups
                    self.error_occurred.emit(f"IPC communication error with the scheduling engine: {str(e)}")
                    break

                # Resolve packet identifiers against registered operation routes
                handler = self._dispatch.get(msg_type)
                if handler and not handler(payload):
                    break
        finally:
            # Reap every child handle regardless of how the loop ended
            self._shutdown()

    def _emit_terminal_state(self) -> None:
        """
        Decides the final outcome when the queue drains and all processes died
        without a clean FINISHED handshake. A non-zero exit on any partition
        means the result set is incomplete and cannot be trusted.
        """
        crashed = [p for p in self._processes if p.exitcode not in (0, None)]
        if crashed:
            self.error_occurred.emit(
                f"The scheduling engine crashed unexpectedly (Exit code: {crashed[0].exitcode})"
            )
        else:
            self.search_finished.emit()

    def cancel(self) -> None:
        """Signal every partition process to abort, then force-stop stragglers (UI-facing path)."""
        if self._cancel_event is not None:
            self._cancel_event.set()

        # Grace phase: all processes share the same cancel flag, so a short wait
        # lets cooperative ones exit on their own before we force-terminate.
        for process in self._processes:
            if process is not None and process.is_alive():
                process.join(timeout=0.5)

        # Force phase: terminate anything still running.
        for process in self._processes:
            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout=1.0)

        # Empty data remnants to release internal buffers and avoid pipeline deadlocks
        try:
            while not self._queue.empty():
                self._queue.get_nowait()
        except (queue.Empty, ValueError, OSError):
            pass

    def _shutdown(self) -> None:
        """
        Stop and reap all partition processes when the monitoring loop ends, for
        any reason. Handles the clean-finish case (nothing left alive — just join)
        and the early-exit case (a partition errored while others were still
        running — signal the rest, then terminate) uniformly. Emits no signals.
        """
        # Early-exit case: survivors are still running, so signal them to stop first.
        if any(p.is_alive() for p in self._processes):
            if self._cancel_event is not None:
                self._cancel_event.set()
            for process in self._processes:
                if process.is_alive():
                    process.join(timeout=0.5)

        # Reap every handle; force-terminate anything that ignored the flag.
        for process in self._processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
            else:
                process.join()

        # Release any leftover IPC items so the queue's feeder thread can shut down.
        try:
            while not self._queue.empty():
                self._queue.get_nowait()
        except (queue.Empty, ValueError, OSError):
            pass
        

    def _handle_schedule_batch(self, payload) -> bool:
        """Receives a pre-compressed blob + its count; only writes bytes to SQLite."""
        data, count = payload
        if count:
            self._repository.insert_compressed_batch(data, count)
            self.schedules_batch_found.emit(count)
        return True

    def _handle_progress(self, payload) -> bool:
        """Passes calculation progress indexes upwards to drive active interface components."""
        self.progress_updated.emit(payload)
        return True

    def _handle_error(self, payload) -> bool:
        """Broadcasts an error message and halts monitoring; _shutdown stops any survivors."""
        self.error_occurred.emit(payload)
        return False

    def _handle_finished(self, payload) -> bool:
        """
        One partition just finished. Keep listening until every partition has
        checked in; only then is the whole search genuinely complete.
        """
        self._finished_count += 1
        if self._finished_count >= self._expected_finishes:
            self.search_finished.emit()
            return False  # all partitions done — stop the loop
        return True       # other partitions still streaming