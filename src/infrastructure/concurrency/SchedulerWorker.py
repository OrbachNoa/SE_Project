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

    def __init__(self, queue: Queue, cancel_event: Event, processes: List[Process], repository: SQLiteScheduleRepository) -> None:
        super().__init__()

        # Shared queue used by all scheduler processes to send messages to this worker.
        self._queue = queue
        # Shared flag used to ask all scheduler processes to stop.
        self._cancel_event = cancel_event
        # All background processes that run parts of the scheduling search.
        self._processes = processes
        # Repository used to save compressed schedule batches to SQLite.
        self._repository = repository

        # Each process sends one FINISHED message when it completes. 
        # The whole search is done only after all processes have finished.
        self._expected_finishes = len(processes)
        self._finished_count = 0

        # Maps each queue message type to the method that handles it.
        self._dispatch = {
            "SCHEDULE_BATCH": self._handle_schedule_batch,
            "PROGRESS": self._handle_progress,
            "ERROR": self._handle_error,
            "FINISHED": self._handle_finished,
        }

    def run(self) -> None:
        """Starts the scheduler processes and keeps reading messages from the queue."""
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
                    # If all processes are dead, decide whether the search ended normally or crashed.
                    if not any(p.is_alive() for p in self._processes):
                        if self._cancel_event.is_set():
                            break
                        # Fallback for cases where a process ended without sending FINISHED.
                        self._emit_terminal_state()
                        break
                    # Some processes are still alive, so keep waiting for more messages.
                    continue
                except ValueError:
                    # The queue was probably closed while this worker was waiting.
                    break
                except Exception as e:
                    # Report unexpected queue/IPC errors instead of leaving the GUI waiting forever.
                    self.error_occurred.emit(f"IPC communication error with the scheduling engine: {str(e)}")
                    break

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
            self.error_occurred.emit(
                f"The scheduling engine crashed unexpectedly (Exit code: {crashed[0].exitcode})"
            )
        else:
            self.search_finished.emit()

    def cancel(self) -> None:
        """Requests cancellation and then stops any process that did not exit by itself."""
        if self._cancel_event is not None:
            self._cancel_event.set()

        # First, give each process a short chance to stop normally.
        for process in self._processes:
            if process is not None and process.is_alive():
                process.join(timeout=0.5)

        # Then force-stop any process that is still running.
        for process in self._processes:
            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout=1.0)

        # Clear remaining queue messages so old data will not stay in the IPC pipe.
        try:
            while not self._queue.empty():
                self._queue.get_nowait()
        except (queue.Empty, ValueError, OSError):
            pass

    def _shutdown(self) -> None:
        """
        Cleans up all scheduler processes after the worker loop ends. 
        This runs for every ending case: normal finish, error, or cancellation. 
        It does not emit GUI signals; it only releases process and queue resources.
        """
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

        # Clear leftover queue messages so the queue can close cleanly.
        try:
            while not self._queue.empty():
                self._queue.get_nowait()
        except (queue.Empty, ValueError, OSError):
            pass
        

    def _handle_schedule_batch(self, payload) -> bool:
        """Saves one compressed schedule batch and notifies the GUI how many schedules were added."""
        data, count = payload
        if count:
            self._repository.insert_compressed_batch(data, count)
            self.schedules_batch_found.emit(count)
        return True

    def _handle_progress(self, payload) -> bool:
        """Sends a progress update to the GUI."""
        self.progress_updated.emit(payload)
        return True

    def _handle_error(self, payload) -> bool:
        """Reports an error to the GUI and stops the worker loop."""
        self.error_occurred.emit(payload)
        return False

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