"""Application-layer driver for the clustering feature.

The pure engine (``src.logic.clustering``) turns a matrix of score vectors into
families. This coordinator knows *where the vectors live in this application*: it
samples ids, reads their score vectors straight from the SQLite ``schedule_scores``
table (no schedule is unpickled), fits the engine once, and then clusters.

It is deliberately stateful so the overview screen can change K cheaply: call
``prepare()`` once (the expensive sample + fit), then ``cluster(k)`` as many times
as the user changes K — only the fast partition step re-runs. ``gidx_for(...)``
maps a working-set position back to a global schedule id so the UI can fetch the
exact schedules of a family for drill-down and comparison.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.logic.clustering.Cluster import ClusterResult
from src.logic.clustering.ClusterConfig import ClusterConfig, K_MODE_FIXED
from src.logic.clustering.ClusteringService import ClusteringService
from src.logic.clustering.CriterionDisplay import label as _criterion_label
from src.logic.clustering.ExtendedFeatureComputer import (
    ALL_EXTENDED_FEATURES,
    ExtendedFeatureComputer,
)
from src.logic.clustering.ScheduleSampler import ScheduleSampler


@dataclass(slots=True)
class ClusteringRun:
    """A finished clustering run plus the working-index → global-id mapping."""

    result: ClusterResult
    # gidx_by_working_index[w] = global schedule id of working-set row w.
    gidx_by_working_index: List[int]

    def gidx_for(self, working_indices: Sequence[int]) -> List[int]:
        """Translate cluster member positions into global schedule ids."""
        return [self.gidx_by_working_index[w] for w in working_indices]


@dataclass(slots=True)
class ConfigRunBundle:
    """A finished manual-config clustering run, committed on the GUI thread.

    Mirrors the free-text request bundle so the existing commit path accepts it,
    but carries no LLM interpretation — just a plain description of the chosen
    criteria plus any that turned out flat (identical across every schedule).
    """

    coordinator: "ClusteringCoordinator"
    run: ClusteringRun
    interpretation: str
    flat_criteria: List[str]


def _describe_criteria(criteria: Sequence[str]) -> str:
    """Human sentence naming the criteria a manual grouping is built on."""
    names = ", ".join(_criterion_label(c) for c in criteria)
    return f"Grouping by: {names}."


class ClusteringCoordinator:
    """Runs the clustering pipeline against the schedule repository."""

    def __init__(self, repository) -> None:
        # Anything exposing count_scores() + read_score_vectors() works; the
        # SQLite repository is the production implementation.
        self._repo = repository
        self._service: Optional[ClusteringService] = None
        self._gidx_by_working_index: List[int] = []
        self._population: int = 0
        self._config: Optional[ClusterConfig] = None
        self._flat_criteria: List[str] = []

    # ── stateful path (overview: prepare once, change K cheaply) ─────────────

    @property
    def config(self) -> Optional[ClusterConfig]:
        """The config that was passed to the last prepare() call, or None if not yet prepared."""
        return self._config

    def prepare(self, config: Optional[ClusterConfig] = None) -> "ClusteringCoordinator":
        """Sample ids, read score vectors, and fit the engine — the expensive step."""
        cfg = config or ClusterConfig.default()
        self._config = cfg
        population = self._repo.count_scores()
        if population <= 0:
            raise ValueError("no scored schedules available to cluster")

        sampler = ScheduleSampler(max_sample=cfg.max_sample, seed=cfg.seed)
        sampled_ids = sampler.sample_indices(population)
        self._ensure_extended_scores(cfg, sampled_ids)
        ids, vectors = self._repo.read_score_vectors(list(cfg.criteria), sampled_ids)

        if len(vectors) == 0:
            raise ValueError("no score vectors could be read for the sample")

        service = ClusteringService(config=cfg)
        service.fit_vectors(vectors, population_size=population)

        self._service = service
        self._gidx_by_working_index = list(ids)
        self._population = population
        self._flat_criteria = self._detect_flat_criteria(ids, vectors, list(cfg.criteria))
        return self

    @property
    def is_prepared(self) -> bool:
        return self._service is not None and self._service.is_fitted

    @property
    def flat_criteria(self) -> List[str]:
        return self._flat_criteria or []

    def _detect_flat_criteria(self, ids, vectors, criteria) -> List[str]:
        """Return list of criterion IDs with near-zero variance."""
        if vectors.shape[0] < 2:
            return []
        variances = vectors.var(axis=0)
        flat = []
        for i, c in enumerate(criteria):
            if variances[i] < 1e-6:
                flat.append(c)
        return flat

    def _ensure_extended_scores(self, cfg: ClusterConfig, sampled_ids: List[int]) -> None:
        """Compute extended features only for the clustering snapshot that needs them."""
        requested = [c for c in cfg.criteria if c in ALL_EXTENDED_FEATURES]
        if not requested:
            return
        if not hasattr(self._repo, "get_schedules_by_ids") or not hasattr(self._repo, "update_extended_scores"):
            return

        schedules = self._repo.get_schedules_by_ids(sampled_ids)
        if not schedules:
            return

        score_rows = [ExtendedFeatureComputer.compute(schedule) for schedule in schedules]
        self._repo.update_extended_scores(sampled_ids[:len(score_rows)], score_rows)

    def cluster(self, k: Optional[int] = None) -> ClusteringRun:
        """Partition the already-fitted working set into K families.

        ``k`` overrides the config; ``None`` uses the configured mode (auto by
        default). Cheap — only the partition step runs, never the sampling/fit.
        """
        if not self.is_prepared:
            raise RuntimeError("prepare() must be called before cluster()")
        result = self._service.cluster(k)
        return ClusteringRun(
            result=result, gidx_by_working_index=list(self._gidx_by_working_index)
        )

    def gidx_at(self, working_index: int) -> int:
        """Global schedule id for one working-set position."""
        return self._gidx_by_working_index[working_index]

    # ── manual criteria path (the "choose criteria" UI) ──────────────────────

    @staticmethod
    def build_config_run(repository, criteria: Sequence[str], k: Optional[int] = None) -> ConfigRunBundle:
        """Prepare a fresh run for an explicit criteria selection and cluster it.

        This is the manual counterpart to the free-text request path: the criteria
        are already known, so there is no LLM translation. Selecting new criteria
        changes the feature matrix, so a fresh ``prepare()`` always runs (cheap
        enough for interactive use). ``k`` fixes the family count; ``None`` lets the
        engine choose K automatically.

        Static and self-contained so it can run on a worker thread without touching
        any shared coordinator instance — the returned bundle is committed on the
        GUI thread, exactly like the free-text bundle.
        """
        if k is not None:
            config = ClusterConfig(criteria=tuple(criteria), k_mode=K_MODE_FIXED, k=k)
        else:
            config = ClusterConfig(criteria=tuple(criteria))

        coordinator = ClusteringCoordinator(repository)
        coordinator.prepare(config)
        run = coordinator.cluster(k)

        return ConfigRunBundle(
            coordinator=coordinator,
            run=run,
            interpretation=_describe_criteria(config.criteria),
            flat_criteria=list(coordinator.flat_criteria),
        )

    # ── one-shot path (kept for tests / simple callers) ──────────────────────

    def run_default(self) -> ClusteringRun:
        """Cluster the current results with the out-of-the-box configuration."""
        return self.run(None)

    def run(self, config: Optional[ClusterConfig] = None) -> ClusteringRun:
        """Prepare and cluster in one call (K from the config, auto by default)."""
        self.prepare(config)
        return self.cluster(None)

    # ── in-memory path (small sets / tests) ──────────────────────────────────

    def run_on_schedules(
        self,
        schedules: Sequence[ScheduleDTO],
        config: Optional[ClusterConfig] = None,
    ) -> ClusteringRun:
        """Cluster an in-memory list of schedules (no repository needed)."""
        cfg = config or ClusterConfig.default()
        if not schedules:
            raise ValueError("no schedules to cluster")

        sampler = ScheduleSampler(max_sample=cfg.max_sample, seed=cfg.seed)
        sampled, original_indices = sampler.sample(list(schedules))

        service = ClusteringService(config=cfg)
        service.fit(sampled, population_size=len(schedules))
        result = service.cluster()

        return ClusteringRun(result=result, gidx_by_working_index=list(original_indices))
