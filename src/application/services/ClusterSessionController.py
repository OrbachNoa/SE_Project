"""Owns the interactive clustering *session* for the GUI cluster screens.

This controller holds the transient clustering session state (the prepared
coordinator, the latest run, the active K, and the free-text interpretation)
and exposes the operations the four cluster presenters need. It is kept
separate from ``AppController`` so the top-level controller stays out of the
clustering domain entirely.

The session is invalidated whenever the underlying schedule result set
changes. Rather than let AppController reach in and call us, AppController
emits a Qt signal on such changes and the composition root connects that
signal to :meth:`invalidate_clustering` -- so the coupling runs one way,
through the observer seam, exactly like the scheduling engine's observers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel
from src.application.viewmodels.ClusterViewModel import (
    ClusterComparisonViewModel,
)
from src.application.errors.ErrorModel import (
    AppErrorInfo,
    ErrorCategory,
    ErrorSeverity,
)
from src.application.errors.ApplicationErrors import ApplicationError

# Import the formatting utility (cheap, stdlib-only -- safe at module level).
from src.file_io.formatters.ScheduleCsvFormatter import format_schedule_csv

if TYPE_CHECKING:
    from src.logic.clustering.llm.ClusterRequestTranslator import ClusterRequestTranslator
    from src.application.services.ClusteringCoordinator import (
        ClusteringCoordinator,
        ClusteringRun,
    )


@dataclass
class _RequestRunBundle:
    """Immutable result from build_request_run(); committed on the GUI thread."""
    coordinator: "ClusteringCoordinator"
    run: "ClusteringRun"
    interpretation: str


class ClusterSessionController:
    """Holds the clustering session and drives the cluster presenters.

    Collaborators are the same instances AppController already owns -- the
    active schedule state (for the SQLite result store), the view-model mapper,
    the input state (for selected programs), and the export service -- injected
    here so this controller can run the clustering API without going through
    AppController.
    """

    def __init__(
        self,
        schedule_state,
        mapper,
        input_state,
        exporter,
    ) -> None:
        self._schedule_state = schedule_state
        self._mapper = mapper
        self._input_state = input_state
        self._exporter = exporter
        # Clustering session state (built lazily when the cluster screen opens,
        # invalidated when a new generation run starts).
        self._cluster_coordinator = None
        self._cluster_run = None
        self._active_k = 0
        self._cluster_interpretation = ""
        # Free-text → ClusterConfig translator. Built lazily (see
        # _get_request_translator) so importing this optional LLM-backed
        # feature doesn't cost every app launch.
        self._request_translator: Optional["ClusterRequestTranslator"] = None

    # ------------------------------------------------------------------
    # Repository / translator access
    # ------------------------------------------------------------------

    def _get_schedule_repository(self):
        """The SQLite-backed result store, if the active schedule state exposes
        one. Returns None for the in-memory base state (no clustering there)."""
        state = self._schedule_state
        getter = getattr(state, "get_repository", None)
        return getter() if callable(getter) else None

    def _get_request_translator(self) -> "ClusterRequestTranslator":
        """Build (once) and return the free-text -> ClusterConfig translator.

        Imported and constructed lazily: this pulls in the optional LLM
        client, only needed when the user actually types a free-text
        clustering request -- not on every app launch.
        """
        if self._request_translator is None:
            from src.logic.clustering.llm.ClusterRequestTranslator import ClusterRequestTranslator
            from src.logic.clustering.llm.OpenAICompatibleLLMClient import OpenAICompatibleLLMClient
            self._request_translator = ClusterRequestTranslator(OpenAICompatibleLLMClient.from_env())
        return self._request_translator

    # ------------------------------------------------------------------
    # Session lifecycle / invalidation
    # ------------------------------------------------------------------

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

    def _prepare_compatible(self, a, b) -> bool:
        """True iff configs a and b require the same prepare()/fit_vectors() run.

        k and k_mode are consumed only by cluster(), not by prepare(), so they
        are excluded. Everything else that affects the sampled data or the fitted
        matrix is compared. If unsure, a field is INCLUDED (safe re-prepare >
        serving stale vectors).
        """
        return (
            a.criteria   == b.criteria
            and a.weights    == b.weights
            and a.normalizer == b.normalizer
            and a.k_min      == b.k_min
            and a.k_max      == b.k_max
            and a.max_sample == b.max_sample
            and a.seed       == b.seed
        )

    def build_request_run(self, text: str, k=None) -> "_RequestRunBundle":
        """Thread-safe: translate + (reuse-or-prepare) + cluster.

        Does NOT mutate any self state. Reads self._cluster_coordinator
        read-only for the prepare-cache check.
        """
        from src.application.services.ClusteringCoordinator import ClusteringCoordinator

        repo = self._get_schedule_repository()
        if repo is None:
            raise RuntimeError("clustering requires the SQLite-backed result store")

        translation = self._get_request_translator().translate(text)

        if k is not None:
            from src.logic.clustering.ClusterConfig import K_MODE_FIXED
            translation.config.k_mode = K_MODE_FIXED
            translation.config.k = k

        cached = self._cluster_coordinator
        from src.logic.clustering.ClusterConfig import K_MODE_FIXED as _K_FIXED
        if (cached is not None
                and cached.is_prepared
                and cached.config is not None
                and self._prepare_compatible(cached.config, translation.config)):
            coordinator = cached
            _explicit_k = (
                translation.config.k
                if translation.config.k_mode == _K_FIXED and translation.config.k
                else None
            )
        else:
            _explicit_k = None
            coordinator = ClusteringCoordinator(repo)
            coordinator.prepare(translation.config)

        run = coordinator.cluster(_explicit_k)

        return _RequestRunBundle(
            coordinator=coordinator,
            run=run,
            interpretation=translation.interpretation,
        )

    def commit_request_run(self, bundle) -> list:
        """GUI thread only: commit a bundle returned by build_request_run()."""
        self._cluster_coordinator = bundle.coordinator
        self._cluster_run = bundle.run
        self._active_k = bundle.run.result.k
        self._cluster_interpretation = bundle.interpretation
        return self._mapper.to_cluster_cards(bundle.run.result)

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

        translation = self._get_request_translator().translate(text)
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

    def build_config_run(self, criteria, k=None):
        """Thread-safe: build a fresh clustering run from an explicit criteria list.

        The manual "choose criteria" UI calls this instead of the free-text path.
        All clustering logic lives in ClusteringCoordinator; this is a thin
        delegate. Does NOT mutate self state — the returned bundle is committed on
        the GUI thread via commit_request_run().
        """
        from src.application.services.ClusteringCoordinator import ClusteringCoordinator

        repo = self._get_schedule_repository()
        if repo is None:
            raise RuntimeError("clustering requires the SQLite-backed result store")
        return ClusteringCoordinator.build_config_run(repo, criteria, k)

    def get_active_criteria(self) -> list:
        """The criteria the current clustering groups by (defaults if none yet)."""
        from src.logic.clustering.ClusterConfig import ClusterConfig

        cfg = self._cluster_coordinator.config if self._cluster_coordinator else None
        if cfg is None:
            cfg = ClusterConfig.default()
        return list(cfg.criteria)

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
            raise ApplicationError(
                "The clustering results were updated by a new schedule run. "
                "Go back to the family overview to see the latest groups.",
                info=AppErrorInfo(
                    code="CLUSTER_SESSION_EXPIRED",
                    category=ErrorCategory.PERSISTENCE,
                    severity=ErrorSeverity.WARNING,
                    user_message=(
                        "The clustering results were updated by a new schedule run. "
                        "Go back to the family overview to see the latest groups."
                    ),
                    technical_message=(
                        "compute_clusters() must run before browsing clusters "
                        "(cluster_run invalidated by a background regeneration)"
                    ),
                    recoverable=True,
                ),
            )
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

    def get_cluster_schedule_scores(self, cluster_id: int, index_in_cluster: int) -> dict:
        """Return all display metrics for one schedule, computing extended scores on demand."""
        run = self._require_run()
        cluster = run.result.get_cluster(cluster_id)
        working_index = cluster.member_indices[index_in_cluster]
        global_id = self._cluster_coordinator.gidx_at(working_index)
        dto = self._cluster_dto(working_index)

        from src.logic.clustering.ExtendedFeatureComputer import ExtendedFeatureComputer

        scores = dict(dto.scores or {})
        extended_scores = ExtendedFeatureComputer.compute(dto)
        scores.update(extended_scores)
        dto.scores = scores

        repo = self._get_schedule_repository()
        updater = getattr(repo, "update_extended_scores", None)
        if callable(updater):
            updater([global_id], [extended_scores])

        return scores

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
        # Imported lazily -- see save_schedule_excel for why.
        from src.file_io.writers.BaseExcelWriter import BaseExcelWriter

        # Retrieve the specific schedule view model for this cluster item
        schedule_view = self.get_cluster_schedule_view(cluster_id, index_in_cluster)
        # Format the data and write to the file
        headers, rows = format_schedule_csv(schedule_view)
        BaseExcelWriter.write(path, headers, rows)
