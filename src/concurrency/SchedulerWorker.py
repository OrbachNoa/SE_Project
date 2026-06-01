"""Bridge between the background process queue and the PyQt GUI.
"""
from __future__ import annotations
import queue  # Required to catch the specific queue.Empty exception
from multiprocessing import Queue, Process
from multiprocessing.synchronize import Event
from PyQt6.QtCore import QThread, pyqtSignal 


class SchedulerWorker(QThread):
    """Listens to the background process because the GUI needs to update safely without freezing."""

    schedule_found = pyqtSignal(object)  
    progress_updated = pyqtSignal(int)   
    search_finished = pyqtSignal()       
    error_occurred = pyqtSignal(str)     

    def __init__(self, queue: Queue, cancel_event: Event, process: Process) -> None:
        super().__init__()
        
        # The communication pipe from the background process because we need to read incoming data.
        self._queue = queue
        # The shared flag to trigger cancellation because the Worker acts as the middleman for user actions.
        self._cancel_event = cancel_event
        # The actual heavy computation process because the Worker is responsible for starting and terminating it.
        self._process = process
        
        # Maps message types to handlers because dictionary dispatch replaces ugly if-else chains.
        self._dispatch = {
            "SCHEDULE_BATCH": self._handle_schedule_batch,
            "PROGRESS": self._handle_progress,
            "ERROR": self._handle_error,
            "FINISHED": self._handle_finished,
        }

    def run(self) -> None:
        """Runs the listener loop because we need to continuously check the queue for live updates."""
        self._process.start()

        while True:
            try:
                msg_type, payload = self._queue.get(timeout=1.0)
            except queue.Empty:
                # The queue is empty. We check if the process died unexpectedly.
                if not self._process.is_alive():
                    # Exitcode 0 means normal termination. Anything else means an OS-level crash.
                    if self._process.exitcode is not None and self._process.exitcode != 0:
                        self.error_occurred.emit(f"The scheduling engine crashed unexpectedly (Exit code: {self._process.exitcode})")
                    else:
                        # Fallback: process died normally but didn't send FINISHED (or we missed it).
                        self.search_finished.emit()
                    break
                continue
            except Exception as e:
                # Catching real unexpected IPC errors so they don't crash the GUI thread silently.
                self.error_occurred.emit(f"IPC communication error with the scheduling engine: {str(e)}")
                break
            
            handler = self._dispatch.get(msg_type)
            
            # Executes the handler and breaks the loop if it returns False because the process ended.
            if handler and not handler(payload):
                break

        # Cleans up the OS process table because otherwise it remains as a 'zombie' process.
        if self._process.is_alive():
            self._process.join(timeout=1.0)
        else:
            self._process.join()

    def cancel(self) -> None:
        """Stops the background process gracefully, falling back to termination if needed."""
        
        if self._cancel_event is not None:
            self._cancel_event.set()

        if self._process is not None and self._process.is_alive():
            # Gives the process a short grace period to read the flag and exit cleanly.
            self._process.join(timeout=0.5) 
            
            # Forcefully terminates the process if it ignored the flag to prevent infinite hangs.
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1.0) 

        # Drains the queue because unread messages can cause the process to deadlock when terminating.
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    # --- Dispatch Handlers ---

    def _handle_schedule_batch(self, payload: list) -> bool:
        """Iterates over the received batch and emits them to the GUI thread."""
        for dto in payload:
            self.schedule_found.emit(dto)
        return True

    def _handle_progress(self, payload) -> bool:
        """Emits progress and returns True because the search is still running."""
        self.progress_updated.emit(payload)
        return True

    def _handle_error(self, payload) -> bool:
        """Emits error and returns False because a crash stops the search."""
        self.error_occurred.emit(payload)
        return False

    def _handle_finished(self, payload) -> bool:
        """Emits finished and returns False because there are no more schedules to find."""
        self.search_finished.emit()
        return False