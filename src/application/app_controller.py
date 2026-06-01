"""AppController — thin UI controller bridging GUI screens and ApplicationFacade.

Every user action (load file, generate, cancel, save) is routed through here.
Screens connect to the four Qt signals below and call the public methods;
they never import services or domain objects directly.

The controller holds only the facade (UML) plus a transient worker handle
used solely to wire the background worker's signals to its own re-emitted
signals, so each screen connects once — to the controller — rather than to
every worker instance.

OCP: extending the application means updating ApplicationFacade —
this class stays closed for modification.

SCRUM-135 / SCRUM-98
"""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from src.application.import_mode import ImportMode
from src.application.import_result import ImportResult
from src.application.import_request import ImportRequest
from src.application.dto_viewmodel.schedule_view_model import ScheduleViewModel

if TYPE_CHECKING:
    from src.application.application_facade import ApplicationFacade
    from src.concurrency.SchedulerWorker import SchedulerWorker
    from src.application.dto_viewmodel.schedule_dto import ScheduleDTO


class AppController(QObject):
    """
    Thin UI controller. Mediates between GUI screens and ApplicationFacade.

    Signals
    -------
    schedule_found(object)
        ScheduleDTO streamed live from the background process.
    progress_updated(int)
        Number of schedules found so far — drives the live counter.
    search_finished()
        Backtracking completed (or was cancelled).
    error_occurred(str)
        Human-readable error message ready to display.
    """

    schedule_found   = pyqtSignal(object)
    progress_updated = pyqtSignal(int)
    search_finished  = pyqtSignal()
    error_occurred   = pyqtSignal(str)

    def __init__(self, facade: "ApplicationFacade") -> None:
        super().__init__()
        self._facade = facade
        # Transient handle, set during a run only so worker signals can be wired.
        self._worker: Optional["SchedulerWorker"] = None

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def load_file(self, path: str, file_type: str, mode: ImportMode) -> ImportResult:
        """Load one file (file_type is 'courses' or 'periods')."""
        return self._facade.import_file(
            ImportRequest(path=path, file_type=file_type, mode=mode)
        )

    # ------------------------------------------------------------------
    # Schedule generation
    # ------------------------------------------------------------------

    def generate_schedules(self, program_ids: List[str]) -> None:
        """
        Start background generation and wire the worker's signals.

        Emits error_occurred immediately if no programs are selected so the
        UI can explain what is missing before anything runs.
        """
        if not program_ids:
            self.error_occurred.emit(
                "Please select at least one program before running the scheduler."
            )
            return

        # The facade starts the worker (and wires result storage internally),
        # then returns it so the controller can forward signals to the screens.
        self._worker = self._facade.generate(program_ids)

        self._worker.schedule_found.connect(self._handle_schedule_found)
        self._worker.progress_updated.connect(self._handle_progress_updated)
        self._worker.search_finished.connect(self._handle_search_finished)
        self._worker.error_occurred.connect(self._handle_error_occurred)

    def cancel_scheduling(self) -> None:
        """Stop a running scheduling job. Safe to call when idle."""
        if self._worker is not None and self._worker.isRunning():
            self._facade.cancel_scheduling()

    # ------------------------------------------------------------------
    # Results / export (called by the output screen)
    # ------------------------------------------------------------------

    def get_schedule_view(self, index: int) -> ScheduleViewModel:
        """Return a display-ready ViewModel (carries 'X of Y' via its total field)."""
        return self._facade.get_schedule_vm(index)

    def save_schedule(self, index: int, path: str) -> None:
        """Write the schedule at index to a file at path."""
        self._facade.export(index, path)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_app_closing(self) -> None:
        """Cancel any running job so the background process does not become an orphan."""
        self.cancel_scheduling()

    # ------------------------------------------------------------------
    # Private — SchedulerWorker signal handlers (forward to screens)
    # ------------------------------------------------------------------

    def _handle_schedule_found(self, dto: "ScheduleDTO") -> None:
        # Storage is handled inside the facade; here we only forward to the UI.
        self.schedule_found.emit(dto)

    def _handle_progress_updated(self, count: int) -> None:
        self.progress_updated.emit(count)

    def _handle_search_finished(self) -> None:
        self.search_finished.emit()

    def _handle_error_occurred(self, message: str) -> None:
        self.error_occurred.emit(message)