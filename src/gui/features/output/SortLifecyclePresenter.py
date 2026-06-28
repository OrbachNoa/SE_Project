"""Owns the SortWorker QThread lifecycle: start and stale-result cleanup.

Split out of OutputScreenPresenter (the "background sort thread" concern).
This class only knows how to create/track/retire a SortWorker — it has no
opinion on what happens with a successful or failed result; the caller wires
the worker's `ready`/`failed` signals to its own handlers after `start()`.
"""
from __future__ import annotations

from typing import List, Optional

from gui.features.output.workers.SortWorker import SortWorker


class SortLifecyclePresenter:
    """Creates, tracks, and safely retires the background sort worker."""

    def __init__(self, controller) -> None:
        self._controller = controller
        self.worker: Optional[SortWorker] = None
        self.retired_workers: list = []

    @property
    def last_error(self):
        return self.worker.last_error if self.worker is not None else None

    # Create and start a new SortWorker; the caller connects ready/failed first.
    def start(self, priority_list: List[str]) -> SortWorker:
        worker = SortWorker(self._controller, priority_list)
        self.worker = worker
        return worker

    # Disconnect and retire a running worker so its late signals are dropped
    # (called on screen leave) — the worker keeps running but nothing acts on it.
    def stop(self) -> None:
        worker = self.worker
        if worker is not None and worker.isRunning():
            try:
                worker.ready.disconnect()
                worker.failed.disconnect()
            except (RuntimeError, TypeError):
                pass
            worker.quit()
            self.retired_workers.append(worker)
            worker.finished.connect(lambda w=worker: self._cleanup_retired(w))
        self.worker = None

    def _cleanup_retired(self, worker) -> None:
        try:
            self.retired_workers.remove(worker)
        except ValueError:
            pass
        try:
            worker.deleteLater()
        except RuntimeError:
            pass
