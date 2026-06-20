"""Runs a sort computation off the GUI thread so Apply doesn't freeze the UI.

The heavy part of applying a sort — get_sorted_ids() (an ORDER BY over the whole
score table) plus the first page fetch — runs entirely inside SQLite's C code,
which releases the GIL. So even though this is a QThread (and Python threads
don't give true parallelism for pure-Python work), the GUI thread genuinely
stays responsive while this runs, because the work is in SQLite, not Python.

The worker only READS the repository (thread-safe via its own lock) and produces
a plain dict. The GUI thread receives that dict via the `ready` signal and calls
apply_sort_data() — a fast, reference-only assignment — to update the live state.
"""
from __future__ import annotations

from typing import List

from PyQt6.QtCore import QThread, pyqtSignal


class SortWorker(QThread):
    """Computes sort data in the background; emits the result for the GUI thread."""

    ready = pyqtSignal(dict)     # emitted with the computed sort data on success
    failed = pyqtSignal(str)     # emitted with an error message on failure

    def __init__(self, controller, priority: List[str]) -> None:
        super().__init__()
        self._controller = controller
        self._priority = list(priority)

    def run(self) -> None:
        try:
            # Heavy, read-only, background-safe (SQLite releases the GIL).
            data = self._controller.compute_sort_data(self._priority)
            self.ready.emit(data)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")