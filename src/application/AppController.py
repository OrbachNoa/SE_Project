from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSettings

from src.application.ImportBoundary import ImportMode, ImportResult
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel
from src.application.viewmodels.ClusterViewModel import (
    ClusterCardViewModel,
    ClusterComparisonViewModel,
)
from src.application.state.InputDataState import InputDataState
from src.application.state.ScheduleResultState import ScheduleResultState
from src.application.services.FileImportService import FileImportService
from src.application.services.SchedulingService import SchedulingService
from src.application.services.ScheduleExportService import ScheduleExportService
from src.application.services.ViewModelMapper import ViewModelMapper

from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.feasibility.InfeasibleScheduleError import InfeasibleScheduleError
from src.application.errors.ErrorModel import (
    AppErrorInfo,
    ErrorCategory,
    ErrorSeverity,
)
from src.application.errors.ExceptionMapper import (
    ExceptionMapperRegistry,
    default_registry,
)
from src.application.errors.ErrorLogger import ErrorLogger
from src.logic.clustering.llm import (
    ClusterRequestTranslator,
    OpenAICompatibleLLMClient,
)
from src.config import PROGRESS_POLL_INTERVAL_MS

# Import the formatting and writing utilities
from src.file_io.formatters.ScheduleCsvFormatter import format_schedule_csv
from src.file_io.writers.BaseExcelWriter import BaseExcelWriter

if TYPE_CHECKING:
    from src.infrastructure.concurrency.SchedulerWorker import SchedulerWorker
    from src.application.dto.ScheduleDTO import ScheduleDTO


class AppController(QObject):
    """
    UI controller and application coordinator: the single entry point GUI screens use
    to reach services, runtime state, and the view-model mapper. Ensures GUI components
    remain entirely decoupled from domain business logic.
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

    def __init__(
        self,
        importer: FileImportService,
        scheduler: SchedulingService,
        exporter: ScheduleExportService,
        mapper: ViewModelMapper,
        input_state: Optional[InputDataState] = None,
        schedule_state: Optional[ScheduleResultState] = None,
        error_registry: Optional[ExceptionMapperRegistry] = None,
        error_logger: Optional[ErrorLogger] = None,
    ) -> None:
        super().__init__()
        self._importer = importer
        self._scheduler = scheduler
        self._exporter = exporter
        self._mapper = mapper
        # Central translation of any raw exception into a presentation-ready
        # AppErrorInfo, plus a logger for the technical detail. The controller
        # works with AppErrorInfo internally and emits only the user message,
        # so error_occurred can stay a str signal for existing GUI consumers.
        self._errors = error_registry or default_registry()
        self._error_logger = error_logger or ErrorLogger()
        # Holds loaded courses and exam periods.
        self._input_state = input_state if input_state is not None else InputDataState()
        # Use the injected state if provided, otherwise default to in-memory only.
        self._schedule_state = schedule_state if schedule_state is not None else ScheduleResultState()
        # Holds transient worker instances across operational lifecycles
        self._worker: Optional["SchedulerWorker"] = None
        # State flag to guarantee early navigation signal triggers exactly once per operational run
        self._early_nav_fired: bool = False
        # Polls repository count periodically instead of relying on per-schedule queue messages
        self._progress_timer: Optional[QTimer] = None
        # Clustering session state (built lazily when the cluster screen opens,
        # invalidated when a new generation run starts).
        self._cluster_coordinator = None
        self._cluster_run = None
        self._active_k = 0
        self._cluster_interpretation = ""
        # Free-text → ClusterConfig translator. The LLM client reads its API key
        # from the environment; with no key it stays disabled and the translator
        # falls back to its dependency-free keyword parser.
        self._request_translator = ClusterRequestTranslator(
            OpenAICompatibleLLMClient.from_env()
        )
        # In-memory sorting priority configuration for the current run
        self._current_sort_priority: List[str] = []

    # ------------------------------------------------------------------
    # File loading & input state updates
    # ------------------------------------------------------------------

    def load_file(self, path: str, file_type: str, mode: ImportMode) -> ImportResult:
        """Loads a specific academic data file into the system configuration."""
        return self._importer.load_file(path, file_type, mode)

    def update_exam_periods(self, edited_vms) -> None:
        """Apply edits made in the calendar editor GUI to the loaded exam periods."""
        self._input_state.apply_period_edits(edited_vms)

    # ------------------------------------------------------------------
    # Schedule generation
    # ------------------------------------------------------------------

    def set_constraints_config(self, config: ConstraintsConfig) -> None:
        self._input_state.set_constraints_config(config)

    def get_constraints_config(self):
        return self._input_state.get_constraints_config()

    def generate_schedules(self, program_ids: List[str]) -> None:
        """
        Starts the background engine process and wires up signal listeners safely.
        Validates input prior to operational launch to trap empty configurations early.
        Clears out stale operational states prior to startup execution to prevent data
        bleeding across multiple runs.
        """
        if not program_ids:
            self._emit_error(
                AppErrorInfo(
                    code="VALIDATION_NO_PROGRAM_SELECTED",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.WARNING,
                    user_message="Please select at least one program before running the scheduler.",
                )
            )
            return

        # Clear previous worker instances to guarantee isolated signal connectivity profiles
        self._disconnect_worker()
        # Cancel the previous worker before starting a new run. Without this, old worker
        # processes keep writing to the (now-cleared) SQLite repository and keep emitting
        # signals that corrupt the new run's state.
        if self._worker is not None:
            self._worker.cancel()
        self._worker = None
        self._early_nav_fired = False

        self._current_sort_priority = []

        # Clear previous run data to ensure a completely clean execution target context
        self._schedule_state.set_schedules([])
        # A new run invalidates any cached clustering session.
        self._invalidate_clustering()

        # Extract required input parameters cached inside the state layer
        self._input_state.set_selected_programs(program_ids)
        config = self._input_state.get_constraints_config()

        # Request a new active execution worker handle from the scheduler
        try:
            self._worker = self._scheduler.generate_async(
                program_ids, self._input_state.get_courses(), self._input_state.get_periods(),
                config=config
            )
        except (InfeasibleScheduleError, MemoryError, Exception) as exc:
            # Infeasible input is a clean, recoverable message; MemoryError maps
            # to a resource problem; anything else falls back to a safe generic.
            # All three are routed through the same central mapper so the GUI
            # only ever sees a user message, never a raw traceback.
            self._emit_error(self._errors.map(exc, {"program_ids": program_ids}), cause=exc)
            return

        # Establish concurrent execution pipeline routing mappings
        self._worker.schedules_batch_found.connect(self._handle_schedules_batch_found)
        self._worker.schedule_found.connect(self._handle_schedule_found)
        self._worker.search_finished.connect(self._handle_search_finished)
        self._worker.error_occurred.connect(self._handle_error_occurred)

        # Poll the repository count every 500 ms and emit progress_updated.
        # This replaces the old per-schedule queue messages from the Scheduler,
        # keeping the IPC channel free for SCHEDULE_BATCH and FINISHED only.
        self._start_progress_timer()

    def cancel_scheduling(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._scheduler.cancel()
            self._stop_progress_timer()
            self.search_finished.emit()

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
        selected = self._input_state.get_selected_programs()
        return self._mapper.to_schedule_vm(
            self._schedule_state.get_schedule(index),
            current_index=index,
            total=self._schedule_state.count(),
            selected_programs=selected,
        )

    def save_schedule(self, index: int, path: str) -> None:
        """Exports the targeted processed schedule out onto disk storage locations."""
        dto = self._schedule_state.get_schedule(index)
        self._exporter.save(dto, path)

    def save_schedule_excel(self, index: int, path: str) -> None:
        """Exports the main schedule directly to an auto-fitted Excel file."""
        schedule_view = self.get_schedule_view(index)
        # Convert the complex view model into a flat table structure
        headers, rows = format_schedule_csv(schedule_view)
        # Write the formatted data to the physical file
        BaseExcelWriter.write(path, headers, rows)

    # ------------------------------------------------------------------
    # Page navigation
    # ------------------------------------------------------------------

    def load_page(self, page: int) -> None:
        """Requests the storage state controller to swap cache window pages inside SQLite memory segments."""
        self._schedule_state.load_page(page)

    def get_page_info(self) -> dict:
        """Extracts metadata snapshots detailing current navigation cursor index bounds information."""
        state = self._schedule_state
        window_size = getattr(state, "_window_size", 10000)
        return {
            "current_page":  state.current_page,
            "total_pages":   state.total_pages(),
            "total_count":   state.count(),
            "window_size":   state.current_window_size(),
            "sqlite_count":  state.sqlite_count(),
            "window_capacity": window_size,
        }

    # ------------------------------------------------------------------
    # Sort configuration
    # ------------------------------------------------------------------

    def apply_sort_config(self, priority_list: List[str]) -> None:
        """Applies sort order synchronously (GUI thread)."""
        self._schedule_state.set_sort_priority(priority_list)

    def get_active_sort_priority(self) -> list:
        state = self._schedule_state
        if hasattr(state, "get_active_sort_priority"):
            return state.get_active_sort_priority()
        return []

    def refresh_sort(self) -> None:
        """Re-run the active sort once (called when generation finishes)."""
        state = self._schedule_state
        if hasattr(state, "refresh_sort"):
            state.refresh_sort()

    def compute_sort_data(self, priority_list: List[str]) -> dict:
        """Heavy, read-only sort computation (safe to call on a background thread)."""
        return self._schedule_state.compute_sort_data(priority_list)

    def apply_sort_data(self, data: dict) -> None:
        """Apply precomputed sort data to the live state (GUI thread only)."""
        self._schedule_state.apply_sort_data(data)

    def load_sort_config(self) -> List[str]:
        """Loads sort configuration from persistent settings."""
        settings = QSettings("SE_Project", "Scheduler")
        val = settings.value("output/sort_priority", [])
        if isinstance(val, str):
            return [val] if val else []
        elif val is None:
            return []
        else:
            return [str(x) for x in val]

    def save_sort_config(self, priority_list: List[str]) -> None:
        """Saves sort configuration to persistent settings."""
        self._current_sort_priority = priority_list
        settings = QSettings("SE_Project", "Scheduler")
        settings.setValue("output/sort_priority", priority_list)

    def get_current_sort_priority(self) -> List[str]:
        """Returns the current active sort configuration for the run."""
        return self._current_sort_priority

    # ------------------------------------------------------------------
    # Clustering (groups the generated schedules into families)
    # ------------------------------------------------------------------

    def _get_schedule_repository(self):
        """The SQLite-backed result store, if the active schedule state exposes
        one. Returns None for the in-memory base state (no clustering there)."""
        state = self._schedule_state
        getter = getattr(state, "get_repository", None)
        return getter() if callable(getter) else None

    def _invalidate_clustering(self) -> None:
        """Drop any cached clustering session (e.g. after a new generation run).

        _active_k is intentionally kept so the next cluster screen entry re-uses
        the same K the user was looking at rather than re-running auto-K and
        potentially landing on a different value.
        """
        self._cluster_coordinator = None
        self._cluster_run = None
        self._cluster_interpretation = ""

    def get_cluster_coordinator(self, fresh: bool = False):
        """Return (or create) the ClusteringCoordinator for background use."""
        from src.application.services.ClusteringCoordinator import ClusteringCoordinator

        repo = self._get_schedule_repository()
        if repo is None:
            return None
        cache_valid = (
            self._cluster_coordinator is not None
            and self._cluster_coordinator.is_prepared
            and self._cluster_run is not None
        )
        if not cache_valid:
            self._cluster_coordinator = ClusteringCoordinator(repo)
        return self._cluster_coordinator

    def invalidate_clustering(self):
        """Discard the cached cluster result (e.g. called after generation completes)."""
        self._invalidate_clustering()

    def cards_from_run(self, run):
        """Store a finished ClusteringRun and return its card view models."""
        self._cluster_run = run
        self._active_k = run.result.k
        self._cluster_interpretation = ""
        return self._mapper.to_cluster_cards(run.result)

    def compute_clusters(self, k=None):
        """Cluster the generated results into families (first computation)."""
        from src.application.services.ClusteringCoordinator import ClusteringCoordinator

        repo = self._get_schedule_repository()
        if repo is None:
            raise RuntimeError("clustering requires the SQLite-backed result store")

        coordinator = ClusteringCoordinator(repo)
        coordinator.prepare()                       # sample + read vectors + fit
        run = coordinator.cluster(k)                 # k None -> automatic K
        self._cluster_coordinator = coordinator
        self._cluster_run = run
        self._active_k = run.result.k
        self._cluster_interpretation = ""           # automatic, no custom request
        return self._mapper.to_cluster_cards(run.result)

    def recompute_clusters(self, k: int):
        """Re-cluster with a new K without re-running the scheduler."""
        if self._cluster_coordinator is None or not self._cluster_coordinator.is_prepared:
            return self.compute_clusters(k)
        run = self._cluster_coordinator.cluster(k)
        self._cluster_run = run
        self._active_k = run.result.k
        return self._mapper.to_cluster_cards(run.result)

    def cluster_from_request(self, text: str, k: Optional[int] = None):
        """Cluster according to a free-text request.

        The request is translated (LLM if configured, else a keyword parser) into
        a ClusterConfig, which drives the same engine. The human interpretation of
        the request is stored for the UI to display. Falls back gracefully: an
        unparseable request becomes an automatic grouping rather than an error.
        """
        from src.application.services.ClusteringCoordinator import ClusteringCoordinator

        repo = self._get_schedule_repository()
        if repo is None:
            raise RuntimeError("clustering requires the SQLite-backed result store")

        translation = self._request_translator.translate(text)
        if k is not None:
            from src.logic.clustering.ClusterConfig import K_MODE_FIXED
            translation.config.k_mode = K_MODE_FIXED
            translation.config.k = k

        cached = self._cluster_coordinator
        if (cached is not None
                and cached.is_prepared
                and cached.config == translation.config):
            run = cached.cluster(None)
        else:
            coordinator = ClusteringCoordinator(repo)
            coordinator.prepare(translation.config)
            run = coordinator.cluster(None)
            self._cluster_coordinator = coordinator

        self._cluster_run = run
        self._active_k = run.result.k
        self._cluster_interpretation = translation.interpretation
        return self._mapper.to_cluster_cards(run.result)

    def get_cluster_interpretation(self) -> str:
        """How the last free-text clustering request was understood."""
        return self._cluster_interpretation

    def get_active_k(self) -> int:
        """The number of families in the current clustering result."""
        return self._active_k

    def has_clusters(self) -> bool:
        return self._cluster_run is not None

    def _require_run(self):
        if self._cluster_run is None:
            raise RuntimeError("compute_clusters() must run before browsing clusters")
        return self._cluster_run

    def _cluster_dto(self, working_index: int) -> ScheduleViewModel:
        """Fetch the schedule DTO for a working-set position via its global id."""
        repo = self._get_schedule_repository()
        global_id = self._cluster_coordinator.gidx_at(working_index)
        dtos = repo.get_schedules_by_ids([global_id])
        if not dtos:
            raise IndexError(f"schedule with global id {global_id} not found")
        return dtos[0]

    def get_cluster_size(self, cluster_id: int) -> int:
        if self._cluster_run is None:
            return 0
        return self._cluster_run.result.get_cluster(cluster_id).size

    def get_cluster_schedule_view(self, cluster_id: int, index_in_cluster: int) -> ScheduleViewModel:
        run = self._require_run()
        cluster = run.result.get_cluster(cluster_id)
        working_index = cluster.member_indices[index_in_cluster]
        dto = self._cluster_dto(working_index)
        selected = self._input_state.get_selected_programs()
        return self._mapper.to_schedule_vm(
            dto, current_index=index_in_cluster, total=cluster.size, selected_programs=selected
        )

    def get_representative_view(self, cluster_id: int) -> ScheduleViewModel:
        run = self._require_run()
        cluster = run.result.get_cluster(cluster_id)
        dto = self._cluster_dto(cluster.representative_index)
        selected = self._input_state.get_selected_programs()
        return self._mapper.to_schedule_vm(dto, selected_programs=selected)

    def get_cluster_comparison(self, cluster_id_a: int, cluster_id_b: int) -> ClusterComparisonViewModel:
        run = self._require_run()
        cluster_a = run.result.get_cluster(cluster_id_a)
        cluster_b = run.result.get_cluster(cluster_id_b)
        rep_a = self._cluster_dto(cluster_a.representative_index)
        rep_b = self._cluster_dto(cluster_b.representative_index)
        selected = self._input_state.get_selected_programs()
        return self._mapper.to_cluster_comparison(
            run.result, cluster_a, cluster_b, rep_a, rep_b, selected_programs=selected
        )

    def save_cluster_schedule(self, cluster_id: int, index_in_cluster: int, path: str) -> None:
        run = self._require_run()
        cluster = run.result.get_cluster(cluster_id)
        working_index = cluster.member_indices[index_in_cluster]
        dto = self._cluster_dto(working_index)
        self._exporter.save(dto, path)

    def save_cluster_schedule_excel(self, cluster_id: int, index_in_cluster: int, path: str) -> None:
        """Exports a specific cluster family schedule directly to an auto-fitted Excel file."""
        # Retrieve the specific schedule view model for this cluster item
        schedule_view = self.get_cluster_schedule_view(cluster_id, index_in_cluster)
        # Format the data and write to the file
        headers, rows = format_schedule_csv(schedule_view)
        BaseExcelWriter.write(path, headers, rows)

    # ------------------------------------------------------------------
    # State accessors for GUI components
    # ------------------------------------------------------------------

    def get_loaded_courses(self) -> list:
        """Courses currently loaded (for the course list widget)."""
        return self._input_state.get_courses()

    def get_loaded_periods(self) -> list:
        """Exam periods currently loaded (for the calendar editor)."""
        return self._input_state.get_periods()

    def get_mapper(self):
        """ViewModelMapper, for building display view models."""
        return self._mapper

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
        self._schedule_state.add_schedules_batch(batch_size)
        self.schedules_batch_found.emit(batch_size)

        # Pull the accurate tracking register size value across the synchronized repository
        total = self._schedule_state.count()
        self.total_count_updated.emit(total)

        # Trigger navigation once the first frame boundary satisfies page sizing constraints
        if not self._early_nav_fired and self._schedule_state.is_first_window_ready():
            self._early_nav_fired = True
            self.early_results_ready.emit()

    def _start_progress_timer(self) -> None:
        """Start polling the repository count every 500 ms during an active run."""
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(PROGRESS_POLL_INTERVAL_MS)
        self._progress_timer.timeout.connect(self._poll_progress)
        self._progress_timer.start()

    def _stop_progress_timer(self) -> None:
        """Stop the polling timer when the run ends or is cancelled."""
        if self._progress_timer is not None and self._progress_timer.isActive():
            self._progress_timer.stop()
        self._progress_timer = None

    def _poll_progress(self) -> None:
        """Emit the current schedule count so the GUI label stays up to date."""
        self.progress_updated.emit(self._schedule_state.count())

    def _handle_search_finished(self) -> None:
        """Handles completion steps cleanly and resets control state logic for subsequent jobs."""
        self._stop_progress_timer()
        self._early_nav_fired = False
        # Discard any mid-generation cluster result so the next visit to the
        # cluster screen re-computes on the complete post-generation dataset.
        self._invalidate_clustering()
        self.search_finished.emit()

    def _handle_error_occurred(self, error) -> None:
        """Routes background-worker failures up to the GUI as a clean message.

        Workers may report a serialised AppErrorInfo payload (dict), an
        AppErrorInfo directly, or a plain legacy string. For the string case,
        every current worker error path already stores the same failure as
        structured data on ``self._worker.last_error`` before emitting the
        signal — so we prefer that record (full category/severity/log detail)
        over the bare string. Only a string with no such record behind it
        (e.g. no worker reference at all) falls back to mapping, since
        forwarding an unmapped string straight to the GUI is exactly what
        this whole error layer exists to avoid.
        """
        self._stop_progress_timer()
        if isinstance(error, dict):
            info = AppErrorInfo.from_payload(error)
            self._emit_error(info)
        elif isinstance(error, AppErrorInfo):
            self._emit_error(error)
        else:
            last_error = getattr(self._worker, "last_error", None)
            if last_error is not None:
                self._emit_error(last_error)
            else:
                info = self._errors.map(
                    RuntimeError(str(error)), {"category": ErrorCategory.INFRASTRUCTURE}
                )
                self._emit_error(info)

    # ------------------------------------------------------------------
    # Error presentation — used by presenters so they never format f"{error}"
    # ------------------------------------------------------------------

    def map_error(self, exc: BaseException, context: Optional[dict] = None) -> str:
        """Map a raw exception to a clean, user-facing message.

        Presenters call this instead of building their own ``f"...{error}"``
        string, so every screen shows a consistent, safe message and the
        technical detail still reaches the log via this same call. Pass a
        ``context`` dict with keys like ``operation``/``screen``/``path`` so
        the log entry says where the failure happened.
        """
        info = self._errors.map(exc, context or {})
        self._error_logger.log(info, cause=exc)
        return info.user_message

    def _emit_error(self, info: AppErrorInfo, cause: Optional[BaseException] = None) -> None:
        """Log the technical detail and emit only the clean user message."""
        self._error_logger.log(info, cause=cause)
        self.error_occurred.emit(info.user_message)

    def log_worker_error(self, info: Optional[AppErrorInfo]) -> None:
        """Log a structured error a background worker already mapped itself.

        SortWorker and ClusterWorker own their own registry and emit only the
        clean ``user_message`` on ``failed`` (their presenter shows that message
        directly, unlike SchedulerWorker which routes through error_occurred).
        This lets those presenters still get the structured record — code,
        category, technical detail — into the same technical log as every
        other boundary, without re-emitting ``error_occurred``.
        """
        if info is not None:
            self._error_logger.log(info)
