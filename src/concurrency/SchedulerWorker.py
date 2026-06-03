"""Bridge between the background process queue and the PyQt GUI.
"""
from __future__ import annotations
import queue  # Required to catch the specific queue.Empty exception
from multiprocessing import Queue, Process
from multiprocessing.synchronize import Event
from PyQt6.QtCore import QThread, pyqtSignal 

from src.data.SQLiteScheduleRepository import SQLiteScheduleRepository


class SchedulerWorker(QThread):
    """
    Asynchronous worker thread that unloads background process execution streams.
    Monitors engine states and dispatches clean execution status updates directly to UI views.
    """

    # --- PyQt Signals to safely communicate asynchronous engine events to the GUI thread ---
    schedule_found        = pyqtSignal(object)      # Kept for backward compatibility profiles
    schedules_batch_found = pyqtSignal(int)         # Emits lightweight packet size scalar to bypass UI event lag
    progress_updated      = pyqtSignal(int)   
    search_finished       = pyqtSignal()       
    error_occurred        = pyqtSignal(str)     

    def __init__(self, queue: Queue, cancel_event: Event, process: Process, repository: SQLiteScheduleRepository) -> None:
        super().__init__()
        
        # Inter-process pipeline conduit feeding raw solution blocks from child process
        self._queue = queue
        # Shared cancellation state monitor flag to interrupt generation steps mid-run
        self._cancel_event = cancel_event
        # Concrete operating system process handle running back-tracking operations
        self._process = process
        # Local SQLite storage client invoked directly inside this background worker context
        self._repository = repository
        
        # Maps operational message string signatures over to active execution handler routes
        self._dispatch = {
            "SCHEDULE_BATCH": self._handle_schedule_batch,
            "PROGRESS": self._handle_progress,
            "ERROR": self._handle_error,
            "FINISHED": self._handle_finished,
        }

    def run(self) -> None:
        """Main active event monitoring loop parsing cross-process IPC channel streams."""
        # Spin up the secondary heavy computation child process layer
        self._process.start()

        while True:
            try:
                # Capture next signal transmission frame boundary passing down the stream
                msg_type, payload = self._queue.get(timeout=1.0)
            except queue.Empty:
                # Interrogate process health if communication channels go dry unexpectedly
                if not self._process.is_alive():
                    if self._cancel_event.is_set():
                        break
                    # Trap abnormal operating system level code exceptions early
                    if self._process.exitcode is not None and self._process.exitcode != 0:
                        self.error_occurred.emit(f"The scheduling engine crashed unexpectedly (Exit code: {self._process.exitcode})")
                    else:
                        # Fallback recovery route to close sessions gracefully if finished message skipped
                        self.search_finished.emit()
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
            
            # Fire targets and break loops immediately if structural updates request termination
            if handler and not handler(payload):
                break

        # Reclamation block to purge and join dead operating system handle listings cleanly
        if self._process.is_alive():
            self._process.join(timeout=1.0)
        else:
            self._process.join()

    def cancel(self) -> None:
        """Triggers operational shutdown flags to terminate underlying computation streams gracefully."""
        if self._cancel_event is not None:
            self._cancel_event.set()

        if self._process is not None and self._process.is_alive():
            # Grant a tight grace window period for clean internal thread termination processing
            self._process.join(timeout=0.5) 
            
            # Force close unresponsive nodes if thread constraints exceed fallback thresholds
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1.0) 

        # Empty data remnants to release internal buffers and avoid pipeline deadlocks
        try:
            while not self._queue.empty():
                self._queue.get_nowait()
        except (queue.Empty, ValueError,OSError):
            pass

    # --- Dispatch Handlers ---

    def _handle_schedule_batch(self, payload: list) -> bool:
        """
        Intercepts raw array packets directly on the background worker pipeline loop.
        Persists datasets to the SQLite repository and broadcasts lightweight metadata to the GUI.
        """
        if payload:
            # Commit raw blocks to SQLite directly from this non-UI background thread segment
            self._repository.insert_batch(payload)
            # Emit integer metrics to let view windows update trackers without dropping frame rates
            self.schedules_batch_found.emit(len(payload))
        return True

    def _handle_progress(self, payload) -> bool:
        """Passes calculation progress indexes upwards to drive active interface components."""
        self.progress_updated.emit(payload)
        return True

    def _handle_error(self, payload) -> bool:
        """Broadcasts error messages and halts current execution monitoring routines."""
        self.error_occurred.emit(payload)
        return False

    def _handle_finished(self, payload) -> bool:
        """Signals generation sequence finalization and wraps up operational thread scopes cleanly."""
        self.search_finished.emit()
        return False