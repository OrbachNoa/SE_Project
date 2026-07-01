"""Background thread for the manual "choose criteria" clustering path.

Runs controller.build_config_run(criteria, k) off the GUI thread so the fresh
prepare() (~2-3 s: sample + read vectors + fit) does not block the event loop
and the busy spinner can paint.

Usage:
    worker = ClusterConfigWorker(controller, criteria, k)
    worker.finished.connect(on_done)   # (ConfigRunBundle) -> void
    worker.failed.connect(on_error)    # (str)             -> void
    worker.start()

The caller must keep a reference (e.g. self._worker) so the object is not
garbage-collected while the thread is running.
"""
from __future__ import annotations

import warnings
from typing import List, Optional, Sequence

from PyQt6.QtCore import QThread, pyqtSignal

from src.application.errors.ErrorModel import AppErrorInfo, ErrorCategory
from src.application.errors.ExceptionMapper import default_registry


class ClusterConfigWorker(QThread):
    """Runs controller.build_config_run(criteria, k) off the GUI thread."""

    finished = pyqtSignal(object)   # ConfigRunBundle
    failed   = pyqtSignal(str)      # error message

    def __init__(self, controller, criteria: Sequence[str], k: Optional[int] = None) -> None:
        super().__init__()
        self._controller = controller
        self._criteria = list(criteria)
        self._k = k
        self._errors = default_registry()
        self.last_error: Optional[AppErrorInfo] = None
        self.warnings: List[str] = []

    def run(self) -> None:
        try:
            from sklearn.exceptions import ConvergenceWarning

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", category=ConvergenceWarning)
                bundle = self._controller.build_config_run(self._criteria, self._k)
                self.warnings = [
                    str(w.message) for w in caught
                    if issubclass(w.category, ConvergenceWarning)
                ]
            self.finished.emit(bundle)
        except Exception as exc:
            info = self._errors.map(exc, {
                "category": ErrorCategory.SCHEDULING,
                "operation": "clustering",
            })
            self.last_error = info
            self.failed.emit(info.user_message)
