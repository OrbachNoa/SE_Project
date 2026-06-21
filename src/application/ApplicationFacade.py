"""ApplicationFacade - the single entry point for the GUI into the application.

Coordinates the services, the runtime state, and the view-model mapper. Holds no
business logic of its own: every operation delegates to a service and, where
relevant, updates AppState or maps domain data to view models.
"""
from __future__ import annotations

from typing import List

from src.application.state.AppState import AppState
from src.application.services.FileImportService import FileImportService
from src.application.services.SchedulingService import SchedulingService
from src.application.services.ScheduleExportService import ScheduleExportService
from src.application.services.ViewModelMapper import ViewModelMapper
from src.application.ImportBoundary import ImportRequest, ImportResult
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel
from src.application.viewmodels.ClusterViewModel import (
    ClusterCardViewModel,
    ClusterComparisonViewModel,
)
from src.infrastructure.concurrency.SchedulerWorker import SchedulerWorker
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.clustering.llm import (
    ClusterRequestTranslator,
    OpenAICompatibleLLMClient,
)


class ApplicationFacade:
    """Coordinates state buffers, file loading parsers, scheduling engines, and view-model mapping integrations."""

    def __init__(
        self,
        state: AppState,
        importer: FileImportService,
        scheduler: SchedulingService,
        exporter: ScheduleExportService,
        mapper: ViewModelMapper,
    ) -> None:
        self._state = state
        self._importer = importer
        self._scheduler = scheduler
        self._exporter = exporter
        self._mapper = mapper
        # Keeps track of the current worker so the previous one can be cleanly
        # cancelled and disconnected when a new generation run starts.
        self._worker = None
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

    def import_file(self, request: ImportRequest) -> ImportResult:
        """Imports a single data asset file using the parsing engine; internal state registers adapt accordingly."""
        return self._importer.load_file(request.path, request.file_type, request.mode)
    
    def update_periods(self, edited_vms) -> None:
        """Apply edited exam periods from the calendar editor into state."""
        self._state.get_input_state().apply_period_edits(edited_vms)

    def generate(self, program_ids: List[str]) -> SchedulerWorker:
        """
        Launches the scheduling computation pipeline asynchronously inside a dedicated background process thread.
        Clears out stale operational states prior to startup execution to prevent data bleeding across multiple runs.
        """
        # Cancel the previous worker and disconnect its signal before starting a new run.
        # Without this, old worker processes keep writing to the (now-cleared) SQLite
        # repository and keep emitting signals that corrupt the new run's state — which
        # caused crashes when sort was active (old blobs decoded with new slots).
        if self._worker is not None:
            try:
                self._worker.schedules_batch_found.disconnect(self._on_schedules_batch_received)
            except RuntimeError:
                pass  # Already disconnected or worker was garbage-collected
            self._worker.cancel()
            self._worker = None

        # Clear previous run data to ensure a completely clean execution target context
        self._state.get_schedule_state().set_schedules([])
        # A new run invalidates any cached clustering session.
        self._invalidate_clustering()

        # Extract required input parameters cached inside the state layer
        input_state = self._state.get_input_state()
        input_state.set_selected_programs(program_ids)
        # Deploy the background process worker with correct state properties
        config = input_state.get_constraints_config()
        worker = self._scheduler.generate_async(
            program_ids, input_state.get_courses(), input_state.get_periods(),
            config=config
        )

        # Connect the asynchronous stream notification line to capture batch updates live
        worker.schedules_batch_found.connect(self._on_schedules_batch_received)
        self._worker = worker
        return worker

    def _on_schedules_batch_received(self, batch_size: int) -> None:
        """
        Internal receiver slot triggered whenever the background process writer persists a data packet frame to SQLite.
        Accepts a scalar integer primitive size tracker instead of heavy list instances to guarantee high UI rendering speeds.
        """
        self._state.get_schedule_state().add_schedules_batch(batch_size)
        
    def get_loaded_courses(self) -> list:
        """Return the courses currently loaded in state (for display)."""
        return self._state.get_input_state().get_courses()

    def get_loaded_periods(self) -> list:
        """Return the exam periods currently loaded in state (for display)."""
        return self._state.get_input_state().get_periods()

    def get_mapper(self):
        """Return the ViewModelMapper for the GUI to build view models."""
        return self._mapper

    # ------------------------------------------------------------------
    # Page navigation 
    # ------------------------------------------------------------------

    def is_first_window_ready(self) -> bool:
        """Validates if initial data slices have reached storage, declaring it safe to pop open output view panels."""
        return self._state.get_schedule_state().is_first_window_ready()

    def get_total_count(self) -> int:
        """Fetches the aggregated volume size metrics of all valid schedules recorded across the active repository."""
        return self._state.get_schedule_state().count()

    def load_page(self, page: int) -> None:
        """Instructs the lower storage layer state targets to rotate active navigation frames over to the specified page index."""
        self._state.get_schedule_state().load_page(page)

    def get_page_info(self) -> dict:
        """Extracts a structural configuration dictionary detailing current navigation pagination thresholds for UI binding components."""
        state = self._state.get_schedule_state()
        window_size = getattr(state, "_window_size", 10000)
        return {
            "current_page":  state.current_page,
            "total_pages":   state.total_pages(),
            "total_count":   state.count(),
            "window_size":   state.current_window_size(),
            "sqlite_count":  state.sqlite_count(),
            "window_capacity": window_size,
        }

    def set_constraints_config(self, config: ConstraintsConfig) -> None:
        self._state.get_input_state().set_constraints_config(config)

    def get_constraints_config(self):
        return self._state.get_input_state().get_constraints_config()

    def cancel_scheduling(self) -> None:
        """Signals active running asynchronous worker processes to terminate operational procedures immediately."""
        self._scheduler.cancel()

    def get_schedule_vm(self, index: int) -> ScheduleViewModel:
        schedule_state = self._state.get_schedule_state()
        dto = schedule_state.get_schedule(index)
        selected = self._state.get_input_state().get_selected_programs()
        return self._mapper.to_schedule_vm(dto, current_index=index, total=schedule_state.count(), selected_programs=selected)

    def export(self, index: int, path: str) -> None:
        """Routes targeted on-memory result profiles directly out towards concrete disk serialization endpoints."""
        dto = self._state.get_schedule_state().get_schedule(index)
        self._exporter.save(dto, path)

    def apply_sort(self, priority_list: List[str]) -> None:
        """Applies sort order synchronously (GUI thread)."""
        self._state.get_schedule_state().set_sort_priority(priority_list)

    def get_active_sort_priority(self) -> list:
        state = self._state.get_schedule_state()
        if hasattr(state, "get_active_sort_priority"):
            return state.get_active_sort_priority()
        return []

    def refresh_sort(self) -> None:
        """Re-run the active sort once (e.g. when generation finishes)."""
        state = self._state.get_schedule_state()
        if hasattr(state, "refresh_sort"):
            state.refresh_sort()

    def compute_sort_data(self, priority_list: List[str]) -> dict:
        """Reads the data needed to apply a new sort order. Touches only the
        SQLite repository (thread-safe) and does not mutate the live schedule
        state, so it is safe to call from a background thread.
        """
        return self._state.get_schedule_state().compute_sort_data(priority_list)

    def apply_sort_data(self, data: dict) -> None:
        """Applies sort data previously computed by compute_sort_data().
        Mutates the live schedule state, so must be called on the GUI thread.
        """
        self._state.get_schedule_state().apply_sort_data(data)

    # ------------------------------------------------------------------
    # Clustering (groups the generated schedules into families)
    # ------------------------------------------------------------------

    def _get_schedule_repository(self):
        """The SQLite-backed result store, if the active schedule state exposes
        one. Returns None for the in-memory base state (no clustering there)."""
        state = self._state.get_schedule_state()
        getter = getattr(state, "get_repository", None)
        return getter() if callable(getter) else None

    def _invalidate_clustering(self) -> None:
        """Drop any cached clustering session (e.g. after a new generation run)."""
        self._cluster_coordinator = None
        self._cluster_run = None
        self._active_k = 0
        self._cluster_interpretation = ""

    def compute_clusters(self, k=None) -> List[ClusterCardViewModel]:
        """Sample, fit the engine, and cluster into families.

        The expensive sample + fit happens here, once. ``k`` is the requested
        number of families; ``None`` lets the engine choose K automatically.
        Use ``recompute_clusters`` to change K afterwards without re-fitting.
        """
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

    def compute_clusters_from_request(self, text: str) -> List[ClusterCardViewModel]:
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
        coordinator = ClusteringCoordinator(repo)
        coordinator.prepare(translation.config)      # criteria/weights/sample from request
        run = coordinator.cluster(None)              # K from the config (auto or fixed)
        self._cluster_coordinator = coordinator
        self._cluster_run = run
        self._active_k = run.result.k
        self._cluster_interpretation = translation.interpretation
        return self._mapper.to_cluster_cards(run.result)

    def get_cluster_interpretation(self) -> str:
        """Human-readable summary of how the last free-text request was applied."""
        return self._cluster_interpretation

    def recompute_clusters(self, k: int) -> List[ClusterCardViewModel]:
        """Re-cluster the already-fitted working set with a new K (fast)."""
        if self._cluster_coordinator is None or not self._cluster_coordinator.is_prepared:
            return self.compute_clusters(k)
        run = self._cluster_coordinator.cluster(k)
        self._cluster_run = run
        self._active_k = run.result.k
        return self._mapper.to_cluster_cards(run.result)

    def has_clusters(self) -> bool:
        """True when a clustering result is available to browse."""
        return self._cluster_run is not None

    def get_active_k(self) -> int:
        """The number of families in the current clustering result."""
        return self._active_k

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
        """Number of schedules in the family (within the working set)."""
        if self._cluster_run is None:
            return 0
        return self._cluster_run.result.get_cluster(cluster_id).size

    def get_cluster_schedule_vm(self, cluster_id: int, index_in_cluster: int) -> ScheduleViewModel:
        """A schedule from inside a family, by its position in the family."""
        run = self._require_run()
        cluster = run.result.get_cluster(cluster_id)
        working_index = cluster.member_indices[index_in_cluster]
        dto = self._cluster_dto(working_index)
        selected = self._state.get_input_state().get_selected_programs()
        return self._mapper.to_schedule_vm(
            dto, current_index=index_in_cluster, total=cluster.size, selected_programs=selected
        )

    def get_representative_vm(self, cluster_id: int) -> ScheduleViewModel:
        """The representative (archetype) schedule of a family."""
        run = self._require_run()
        cluster = run.result.get_cluster(cluster_id)
        dto = self._cluster_dto(cluster.representative_index)
        selected = self._state.get_input_state().get_selected_programs()
        return self._mapper.to_schedule_vm(dto, selected_programs=selected)

    def get_cluster_comparison(self, cluster_id_a: int, cluster_id_b: int) -> ClusterComparisonViewModel:
        """Side-by-side comparison of two families' representatives."""
        run = self._require_run()
        cluster_a = run.result.get_cluster(cluster_id_a)
        cluster_b = run.result.get_cluster(cluster_id_b)
        rep_a = self._cluster_dto(cluster_a.representative_index)
        rep_b = self._cluster_dto(cluster_b.representative_index)
        selected = self._state.get_input_state().get_selected_programs()
        return self._mapper.to_cluster_comparison(
            run.result, cluster_a, cluster_b, rep_a, rep_b, selected_programs=selected
        )

    def export_cluster_schedule(self, cluster_id: int, index_in_cluster: int, path: str) -> None:
        """Save a chosen schedule from a family to a file."""
        run = self._require_run()
        cluster = run.result.get_cluster(cluster_id)
        working_index = cluster.member_indices[index_in_cluster]
        dto = self._cluster_dto(working_index)
        self._exporter.save(dto, path)