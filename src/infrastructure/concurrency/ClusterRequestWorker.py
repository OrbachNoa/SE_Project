"""Background thread for the text-based "Apply request" clustering path.

Runs controller.build_request_run(text, k) off the GUI thread so the
LLM call (~5-10 s) and prepare() (~2-3 s) do not block the event loop
and the busy spinner can paint.

Usage:
    worker = ClusterRequestWorker(controller, text, k)
    worker.finished.connect(on_done)   # (_RequestRunBundle) -> void
    worker.failed.connect(on_error)    # (str)               -> void
    worker.start()

The caller must keep a reference (e.g. self._worker) so the object is
not garbage-collected while the thread is running.
"""
from __future__ import annotations

import warnings
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from src.application.errors.ErrorModel import AppErrorInfo, ErrorCategory
from src.application.errors.ExceptionMapper import default_registry


class ClusterRequestWorker(QThread):
    """Runs controller.build_request_run(text, k) off the GUI thread."""

    finished = pyqtSignal(object)   # _RequestRunBundle
    failed   = pyqtSignal(str)      # error message

    def __init__(self, controller, text: str, k: Optional[int] = None) -> None:
        super().__init__()
        self._controller = controller
        self._text = text
        self._k = k
        self._errors = default_registry()
        self.last_error: Optional[AppErrorInfo] = None
        self.warnings: List[str] = []

    def run(self) -> None:
        try:
            from sklearn.exceptions import ConvergenceWarning

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", category=ConvergenceWarning)
                bundle = self._controller.build_request_run(self._text, self._k)
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
