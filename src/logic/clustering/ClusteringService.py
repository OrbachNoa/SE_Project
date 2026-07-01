"""Orchestrates the clustering pipeline end to end.

Wires the Strategy components together:

    (sample) -> extract features -> normalize -> choose K -> cluster
             -> pick representatives -> summarize

and exposes the result as a `ClusterResult`. The expensive work — building and
normalizing the feature matrix — happens once in `fit`. Re-running with a
different K (a future manual override) only re-runs `cluster` on the cached
matrix, which is cheap, so the UI stays responsive. The scheduling engine is
never re-run.

The service is deliberately ignorant of *where* the vectors come from. It is
driven by a `ClusterConfig` (criteria, weights, K mode, seed), which is exactly
the object the future custom-clustering UI / LLM layer will produce — so that
feature slots in here with no engine change.
"""
from __future__ import annotations

import warnings
from typing import List, Optional, Sequence

import numpy as np

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.logic.clustering.AutoKSelector import AutoKSelector
from src.logic.clustering.Cluster import Cluster, ClusterResult
from src.logic.clustering.ClusterConfig import ClusterConfig, K_MODE_AUTO
from src.logic.clustering.ClusterSummarizer import ClusterSummarizer
from src.logic.clustering.EuclideanDistanceMetric import EuclideanDistanceMetric
from src.logic.clustering.FeatureNormalizer import FeatureNormalizer, ZScoreNormalizer
from src.logic.clustering.IClusteringStrategy import IClusteringStrategy
from src.logic.clustering.IDistanceMetric import IDistanceMetric
from src.logic.clustering.KMeansClusteringStrategy import KMeansClusteringStrategy
from src.logic.clustering.ScoreFeatureExtractor import ScoreFeatureExtractor
from src.logic.clustering.WeightedEuclideanDistanceMetric import (
    WeightedEuclideanDistanceMetric,
)

try:
    from src.logic.clustering.ScikitLearnKMeansStrategy import ScikitLearnKMeansStrategy
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    warnings.warn(
        "scikit-learn not found — clustering will use the slower pure-Python "
        "K-means fallback. Install scikit-learn for full performance.",
        RuntimeWarning,
        stacklevel=2,
    )


# How many schedules the user can page through inside one family. A family may
# hold thousands of sampled schedules; browsing is capped to a small,
# representative handful of them (the family's true size is shown separately).
FAMILY_BROWSE_CAP = 30


class ClusteringService:
    """Single entry point for turning a set of schedules into K families."""

    def __init__(
        self,
        config: Optional[ClusterConfig] = None,
        strategy: Optional[IClusteringStrategy] = None,
        summarizer: Optional[ClusterSummarizer] = None,
    ) -> None:
        self._config = config or ClusterConfig.default()
        self._extractor = ScoreFeatureExtractor(self._config.criteria)
        self._metric = self._build_metric(self._config)
        self._strategy_override = strategy is not None
        # Prefer the scikit-learn strategy (faster, multiple restarts); fall
        # back to the in-house implementation when sklearn is not installed.
        if strategy is not None:
            self._strategy = strategy
        else:
            self._strategy = self._build_strategy(self._config, self._metric)
        self._auto_k = AutoKSelector(
            strategy=self._strategy, metric=self._metric, seed=self._config.seed
        )
        self._summarizer = summarizer or ClusterSummarizer()

        # Cached state set by fit() and reused by cluster().
        self._matrix: Optional[np.ndarray] = None        # normalized (n, d)
        self._raw_matrix: Optional[np.ndarray] = None     # un-normalized (n, d)
        self._population_size: int = 0
        self._fitted: bool = False
        self._cached_auto_k: Optional[int] = None        # memoised silhouette result

    # ── fit (expensive, done once per working set) ───────────────────────────

    def fit_vectors(
        self,
        raw_vectors: np.ndarray,
        population_size: Optional[int] = None,
    ) -> "ClusteringService":
        """Fit on an already-extracted (n, d) matrix of raw score vectors.

        This is the scale-friendly entry: the caller (e.g. the SQLite path) can
        read score vectors straight from storage without building ScheduleDTOs.
        """
        raw = np.asarray(raw_vectors, dtype=float)
        if raw.size == 0:
            raise ValueError("cannot cluster an empty set of vectors")
        if raw.ndim != 2 or raw.shape[1] != len(self._config.criteria):
            raise ValueError(
                f"expected (n, {len(self._config.criteria)}) matrix, got {raw.shape}"
            )

        self._raw_matrix = raw
        if self._config.normalizer == "zscore":
            normalizer = ZScoreNormalizer()
        else:
            normalizer = FeatureNormalizer()
        self._matrix = normalizer.fit_transform(raw)
        self._population_size = population_size or raw.shape[0]
        self._fitted = True
        self._cached_auto_k = None   # new matrix → silhouette must re-run
        return self

    def fit(
        self,
        schedules: Sequence[ScheduleDTO],
        population_size: Optional[int] = None,
    ) -> "ClusteringService":
        """Fit on a list of schedules, extracting their score vectors."""
        if not schedules:
            raise ValueError("cannot cluster an empty set of schedules")

        self._validate_schedule_scores(schedules)
        raw = self._extractor.extract_many(list(schedules))
        return self.fit_vectors(raw, population_size=population_size or len(schedules))

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    # ── cluster (cheap, re-run on every K change) ────────────────────────────

    def cluster(self, k: Optional[int] = None) -> ClusterResult:
        """Partition the cached matrix into K families and describe them.

        ``k`` overrides the config. When neither is given and the config is in
        auto mode, K is chosen by silhouette.
        """
        if not self._fitted or self._matrix is None:
            raise RuntimeError("fit() must be called before cluster()")

        requested_k = self._resolve_k(k)
        k = requested_k

        output = self._strategy.cluster(self._matrix, k)
        labels = output.labels
        centroids = output.centroids
        actual_k = centroids.shape[0]
        n = self._matrix.shape[0]

        sampled = self._population_size > n
        scale = (self._population_size / n) if (sampled and n > 0) else 1.0
        names = self._extractor.feature_names()

        clusters: List[Cluster] = []
        for c in range(actual_k):
            member_indices = [int(i) for i in np.where(labels == c)[0]]
            if not member_indices:
                continue

            representative_index = self._pick_representative(member_indices, centroids[c])
            # Profile, size estimate and ranges use ALL of the family's members;
            # only the browse list is capped to a small representative sample so
            # the user pages through a handful, not thousands.
            browse_members = self._sample_members(member_indices, representative_index, centroids[c])
            clusters.append(
                Cluster(
                    cluster_id=c,
                    member_indices=browse_members,
                    representative_index=representative_index,
                    size=len(browse_members),
                    estimated_population_size=int(round(len(member_indices) * scale)),
                    summary=self._summarize(member_indices, names),
                    representative_features=self._features_at(representative_index, names),
                    min_max=self._summarize_min_max(member_indices, names),
                )
            )
        
        # Renumber 0..m-1 so ids stay contiguous even if a cluster came out empty.
        for new_id, cluster in enumerate(clusters):
            cluster.cluster_id = new_id

        # Default, dependency-free descriptions.
        self._summarizer.describe_all(clusters)

        active_k = len(clusters)
        return ClusterResult(
            k=active_k,
            clusters=clusters,
            criteria=list(names),
            working_set_size=n,
            population_size=self._population_size,
            sampled=sampled,
            requested_k=requested_k if requested_k != active_k else None,
        )

    def auto_cluster(self) -> ClusterResult:
        """Convenience: cluster with K chosen automatically (the default path)."""
        return self.cluster(k=None)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _validate_schedule_scores(self, schedules: Sequence[ScheduleDTO]) -> None:
        """Fail clearly when DTOs are missing criteria required by this config."""
        missing = []
        for index, schedule in enumerate(schedules):
            scores = schedule.scores or {}
            missing_criteria = [
                criterion for criterion in self._config.criteria
                if criterion not in scores
            ]
            if missing_criteria:
                missing.append((index, missing_criteria))

        if not missing:
            return

        examples = "; ".join(
            f"schedule[{index}] missing {criteria}"
            for index, criteria in missing[:3]
        )
        suffix = "" if len(missing) <= 3 else f"; and {len(missing) - 3} more schedules"
        raise ValueError(
            "cannot cluster schedules with missing required scores: "
            f"{examples}{suffix}"
        )

    def _resolve_k(self, k: Optional[int]) -> int:
        if k is not None:
            if k <= 0:
                raise ValueError("k must be a positive integer")
            return k
        if self._config.k_mode == K_MODE_AUTO:
            if self._cached_auto_k is None:
                self._cached_auto_k = self._auto_k.choose(
                    self._matrix, self._config.k_min, self._config.k_max
                ).k
            return self._cached_auto_k
        return self._config.k

    @staticmethod
    def _build_metric(config: ClusterConfig) -> IDistanceMetric:
        # Only build a weighted metric when weights actually differ from 1.
        weights = config.weight_vector()
        if any(abs(w - 1.0) > 1e-9 for w in weights):
            return WeightedEuclideanDistanceMetric(weights)
        return EuclideanDistanceMetric()

    @staticmethod
    def _build_strategy(config: ClusterConfig, metric: IDistanceMetric) -> IClusteringStrategy:
        if _SKLEARN_AVAILABLE:
            return ScikitLearnKMeansStrategy(
                random_state=config.seed,
                weights=config.weight_vector(),
            )
        return KMeansClusteringStrategy(metric=metric, seed=config.seed)

    def _pick_representative(self, member_indices: List[int], centroid: np.ndarray) -> int:
        """Member closest to the centroid is the family's archetype."""
        member_points = self._matrix[member_indices]
        distances = self._metric.distance_to_centroids(
            member_points, centroid[np.newaxis, :]
        ).ravel()
        return member_indices[int(distances.argmin())]

    def _sample_members(
        self, member_indices: List[int], representative_index: int, centroid: np.ndarray
    ) -> List[int]:
        """A bounded, representative browse sample: archetype first, then a spread.

        Small families are returned whole (archetype first). Large ones are sorted
        by distance to the centroid and sampled with an even stride, so the user
        sees typical-through-atypical members rather than the first N encountered.
        """
        cap = FAMILY_BROWSE_CAP
        if len(member_indices) <= cap:
            candidates = member_indices
        else:
            points = self._matrix[member_indices]
            distances = self._metric.distance_to_centroids(
                points, centroid[np.newaxis, :]
            ).ravel()
            order = np.argsort(distances)
            stride = len(member_indices) / cap
            positions = sorted({int(i * stride) for i in range(cap)})
            candidates = [member_indices[int(order[p])] for p in positions]

        picked = [representative_index]
        seen = {representative_index}
        for member in candidates:
            if member not in seen:
                picked.append(member)
                seen.add(member)
                if len(picked) >= cap:
                    break
        return picked

    def _summarize(self, member_indices: List[int], names: List[str]) -> dict:
        """Average *raw* (un-normalized) feature values — the family profile."""
        raw = self._raw_matrix[member_indices]
        means = raw.mean(axis=0)
        return {name: float(value) for name, value in zip(names, means)}

    def _summarize_min_max(self, member_indices: List[int], names: List[str]) -> dict:
        """Min/max raw (un-normalized) feature values of the cluster's members."""
        raw = self._raw_matrix[member_indices]
        mins = raw.min(axis=0)
        maxs = raw.max(axis=0)
        return {name: (float(mi), float(ma)) for name, mi, ma in zip(names, mins, maxs)}

    def _features_at(self, index: int, names: List[str]) -> dict:
        return {name: float(value) for name, value in zip(names, self._raw_matrix[index])}
