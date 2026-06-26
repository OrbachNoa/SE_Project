"""Background thread for the clustering pipeline.

Running prepare() + cluster() on the GUI thread freezes the event loop for
2-3 seconds (ORDER BY RANDOM() full-table scan + sklearn auto-K × 9 passes).
This worker moves that work off the main thread so the UI stays responsive.

Usage:
    worker = ClusterWorker(coordinator, k=None)
    worker.finished.connect(on_done)      # (ClusteringRun) → void
    worker.failed.connect(on_error)       # (str)           → void
    worker.start()

The caller must keep a reference to the worker (e.g. self._cluster_worker)
so it is not garbage-collected while the thread runs.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List
import warnings
from sklearn.exceptions import ConvergenceWarning
from PyQt6.QtCore import QThread, pyqtSignal

from src.application.errors.ErrorModel import AppErrorInfo, ErrorCategory
from src.application.errors.ExceptionMapper import default_registry

if TYPE_CHECKING:
    # Only used as type hints below: this module never constructs these
    # classes itself, just receives already-built instances. Importing them
    # for real would pull in ClusteringCoordinator -> ClusteringService ->
    # scikit-learn/scipy/pandas (~2.3s) just to define this QThread's
    # signature -- and this class is imported every time the cluster screens
    # are built, regardless of whether clustering is ever used.
    from src.application.services.ClusteringCoordinator import ClusteringCoordinator, ClusteringRun
    from src.logic.clustering.ClusterConfig import ClusterConfig


class ClusterWorker(QThread):
    """Runs coordinator.prepare() + coordinator.cluster(k) off the GUI thread."""

    finished = pyqtSignal(object)   # ClusteringRun
    failed   = pyqtSignal(str)      # error message

    def __init__(
        self,
        coordinator: ClusteringCoordinator,
        config: Optional[ClusterConfig] = None,
        k: Optional[int] = None,
    ) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._config = config
        self._k = k
        self._errors = default_registry()
        # The structured form of the last failure; failed stays a str signal.
        self.last_error: AppErrorInfo = None
        self.warnings: List[str] = []

    def run(self) -> None:
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", category=ConvergenceWarning)

                if not self._coordinator.is_prepared:
                    self._coordinator.prepare(self._config)
                run = self._coordinator.cluster(self._k)

                self.warnings = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]

            self.finished.emit(run)
        except Exception as exc:
            info = self._errors.map(exc, {
                "category": ErrorCategory.SCHEDULING,
                "operation": "clustering",
            })
            self.last_error = info
            self.failed.emit(info.user_message)
