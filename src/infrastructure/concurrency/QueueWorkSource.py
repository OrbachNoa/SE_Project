"""IWorkSource backed by a shared multiprocessing Queue.

Termination is the subtle part. A multiprocessing.Queue uses a background feeder
thread, so right after put() the queue can momentarily look empty and
get_nowait()/empty() can lie - with N workers hammering it at start, that would
make a worker quit early and leave units unprocessed. So the stop signal is NOT
"queue looks empty"; it is an explicit per-worker sentinel:

    - the producer enqueues all WorkUnits, then one None sentinel per worker;
    - a real WorkUnit is returned to the caller;
    - a None sentinel means "this worker is done" -> return None;
    - a timeout (queue momentarily empty) is NOT done -> retry.

This makes the stop condition deterministic and independent of feeder timing.
An optional cancel_event lets a worker stop pulling promptly when the user
cancels, without waiting to drain remaining units.
"""
from __future__ import annotations

import queue as _queue
from multiprocessing import Queue
from typing import Optional

from src.infrastructure.concurrency.IWorkSource import IWorkSource
from src.logic.parallel.WorkUnit import WorkUnit


class QueueWorkSource(IWorkSource):
    """Pulls WorkUnits from a shared queue using sentinel-per-worker termination."""

    def __init__(self, work_queue: Queue, cancel_event=None, poll_timeout: float = 0.2) -> None:
        # Shared queue holding the WorkUnits followed by one None per worker.
        self._queue = work_queue
        # Optional shared flag: when set, stop pulling new work immediately.
        self._cancel_event = cancel_event
        # How long to block before retrying, so a momentarily-empty queue (items
        # still in flight) is not mistaken for "no more work".
        self._poll_timeout = poll_timeout

    def get_next(self) -> Optional[WorkUnit]:
        while True:
            if self._cancel_event is not None and self._cancel_event.is_set():
                return None
            try:
                item = self._queue.get(timeout=self._poll_timeout)
            except _queue.Empty:
                # Items may still be in flight from the feeder thread; retry.
                continue
            if item is None:
                # Sentinel: this worker has reached the end of the work.
                return None
            return item
