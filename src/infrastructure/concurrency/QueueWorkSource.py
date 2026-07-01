"""
Work source that lets worker processes pull WorkUnits from a shared queue.

Workers keep pulling WorkUnits until they get None.
None is used as the stop signal because queue.empty() is not reliable with
multiprocessing.Queue.
"""
from __future__ import annotations

import queue as _queue
from multiprocessing import Queue
from typing import Optional

from src.infrastructure.concurrency.IWorkSource import IWorkSource
from src.logic.parallel.WorkUnit import WorkUnit


class QueueWorkSource(IWorkSource):
    """Gives worker processes their next WorkUnit from the shared queue."""

    def __init__(self, work_queue: Queue, cancel_event=None, poll_timeout: float = 0.2) -> None:
        # Shared queue with all WorkUnits waiting for the workers.
        self._queue = work_queue
        # Shared cancel flag. If the user cancels, workers stop taking new work.
        self._cancel_event = cancel_event
        # For waiting briefly so a temporary empty queue does not stop the worker.
        self._poll_timeout = poll_timeout

    def get_next(self) -> Optional[WorkUnit]:
        """Return the next WorkUnit, or None when this worker should stop."""
        while True:
            # If the user cancelled the search, stop this worker.
            if self._cancel_event is not None and self._cancel_event.is_set():
                return None
            try:
                # Wait a little for the next WorkUnit.
                item = self._queue.get(timeout=self._poll_timeout)
            except _queue.Empty:
                # The queue may be briefly empty while work is still arriving, so retry.
                continue

            # None is the real stop signal for this worker.
            if item is None:
                return None
            
            return item
