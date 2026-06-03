from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from application.ImportMode import ImportMode
from application.ImportResult import ImportResult
from application.ImportRequest import ImportRequest
from application.viewmodels.ScheduleViewModel import ScheduleViewModel

if TYPE_CHECKING:
    from application.ApplicationFacade import ApplicationFacade
    from infrastructure.concurrency.SchedulerWorker import SchedulerWorker
    from application.dto.SchedulDTO import ScheduleDTO


class AppController(QObject):
    """
    Thin UI controller acting as a mediator between GUI screens and ApplicationFacade.
    Ensures GUI components remain entirely decoupled from domain business logic.
    """

    # --- PyQt Signals to communicate asynchronous events back to GUI views ---
    schedule_found        = pyqtSignal(object)  
    schedules_batch_found = pyqtSignal(int)     # Emits lightweight batch scalar size to prevent UI thread choking
    progress_updated      = pyqtSignal(int)
    search_finished       = pyqtSignal()
    error_occurred        = pyqtSignal(str)
    
    # --- Navigation signals to coordinate screen switching during active generation ---
    early_results_ready   = pyqtSignal()
    total_count_updated   = pyqtSignal(int)

    def __init__(self, facade: "ApplicationFacade") -> None:
        super().__init__()
        self._facade = facade
        # Holds transient worker instances across operational lifecycles
        self._worker: Optional["SchedulerWorker"] = None
        # State flag to guarantee early navigation signal triggers exactly once per operational run
        self._early_nav_fired: bool = False

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def load_file(self, path: str, file_type: str, mode: ImportMode) -> ImportResult:
        """Loads a specific academic data file into the system configuration via the facade."""
        return self._facade.import_file(
            ImportRequest(path=path, file_type=file_type, mode=mode)
        )

    # ------------------------------------------------------------------
    # Schedule generation
    # ------------------------------------------------------------------

    def generate_schedules(self, program_ids: List[str]) -> None:
        """
        Starts the background engine process and wires up signal listeners safely.
        Validates input prior to operational launch to trap empty configurations early.
        """
        if not program_ids:
            self.error_occurred.emit(
                "Please select at least one program before running the scheduler."
            )
            return

        # Clear previous worker instances to guarantee isolated signal connectivity profiles
        self._disconnect_worker()
        self._early_nav_fired = False

        # Request a new active execution worker handle from the centralized facade component
        self._worker = self._facade.generate(program_ids)

        # Establish concurrent execution pipeline routing mappings
        self._worker.schedules_batch_found.connect(self._handle_schedules_batch_found)
        self._worker.schedule_found.connect(self._handle_schedule_found)
        self._worker.progress_updated.connect(self._handle_progress_updated)
        self._worker.search_finished.connect(self._handle_search_finished)
        self._worker.error_occurred.connect(self._handle_error_occurred)

    def cancel_scheduling(self) -> None:
        """Stops the active running scheduling job safely without trapping process execution loops."""
        if self._worker is not None and self._worker.isRunning():
            self._facade.cancel_scheduling()

    def _disconnect_worker(self) -> None:
        """
        Safely detaches signal lines from the stored worker target.
        Prevents duplicate callback responses when aborting tasks mid-run.
        """
        if self._worker is None:
            return
        try:
            self._worker.schedules_batch_found.disconnect(self._handle_schedules_batch_found)
            self._worker.schedule_found.disconnect(self._handle_schedule_found)
            self._worker.progress_updated.disconnect(self._handle_progress_updated)
            self._worker.search_finished.disconnect(self._handle_search_finished)
            self._worker.error_occurred.disconnect(self._handle_error_occurred)
        except RuntimeError:
            # Handles edge cases where underlying C++ object nodes were garbage collected prematurely
            pass  

    # ------------------------------------------------------------------
    # Results / export 
    # ------------------------------------------------------------------

    def get_schedule_view(self, index: int) -> ScheduleViewModel:
        """Returns a structural, display-ready ViewModel at the specified result index position."""
        return self._facade.get_schedule_vm(index)

    def save_schedule(self, index: int, path: str) -> None:
        """Exports the targeted processed schedule out onto disk storage locations."""
        self._facade.export(index, path)

    # ------------------------------------------------------------------
    # Page navigation 
    # ------------------------------------------------------------------

    def load_page(self, page: int) -> None:
        """Requests the storage state controller to swap cache window pages inside SQLite memory segments."""
        self._facade.load_page(page)

    def get_page_info(self) -> dict:
        """Extracts metadata snapshots detailing current navigation cursor index bounds information."""
        return self._facade.get_page_info()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_app_closing(self) -> None:
        """Acts as a cleanup intercept hook to eliminate zombie or orphan background worker allocations."""
        self.cancel_scheduling()

    # ------------------------------------------------------------------
    # Private — SchedulerWorker signal handlers 
    # ------------------------------------------------------------------

    def _handle_schedule_found(self, dto: "ScheduleDTO") -> None:
        """Forwards standard system notification structures up towards the interface context."""
        self.schedule_found.emit(dto)

    def _handle_schedules_batch_found(self, batch_size: int) -> None:
        """
        Receives notification updates indicating a background write event to SQLite finalized.
        Fires navigational updates dynamically while keeping interface response speeds high.
        """
        self.schedules_batch_found.emit(batch_size)

        # Pull the accurate tracking register size value across the synchronized repository
        total = self._facade.get_total_count()
        self.total_count_updated.emit(total)

        # Trigger navigation once the first frame boundary satisfies page sizing constraints
        if not self._early_nav_fired and self._facade.is_first_window_ready():
            self._early_nav_fired = True
            self.early_results_ready.emit()

    def _handle_progress_updated(self, count: int) -> None:
        """Passes search progression percentages up into application views."""
        self.progress_updated.emit(count)

    def _handle_search_finished(self) -> None:
        """Handles completion steps cleanly and resets control state logic for subsequent jobs."""
        self._early_nav_fired = False
        self.search_finished.emit()

    def _handle_error_occurred(self, message: str) -> None:
        """Routes pipeline validation crashes up into interface message dialog display handlers."""
        self.error_occurred.emit(message)