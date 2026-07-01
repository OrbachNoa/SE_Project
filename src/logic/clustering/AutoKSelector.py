"""Automatic selection of the number of clusters K (silhouette method).

Users should not have to know how many families their schedules fall into, so on
the default path the engine picks K itself. For every candidate K in a small
range we cluster and score the partition with the mean *silhouette* — how much
tighter points sit with their own cluster than with the nearest other cluster.
The K with the best silhouette wins.

Silhouette is O(n^2) in the number of points, which would be punishing on a
10K-point sample. So selection runs on a capped random sub-sample (a few thousand
points): enough to see the shape of the data, cheap enough to stay snappy. The
chosen K is then handed to the real run on the full working set.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.logic.clustering.EuclideanDistanceMetric import EuclideanDistanceMetric
from src.logic.clustering.IClusteringStrategy import IClusteringStrategy
from src.logic.clustering.IDistanceMetric import IDistanceMetric
from src.logic.clustering.KMeansClusteringStrategy import KMeansClusteringStrategy

try:
    from sklearn.metrics import silhouette_score as _sklearn_silhouette
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


@dataclass(slots=True)
class KSelection:
    """Outcome of auto-K: the chosen K and the score of every candidate tried."""

    k: int
    scores: dict  # {candidate_k: silhouette_score}


class AutoKSelector:
    """Chooses the K with the highest mean silhouette over a candidate range."""

    def __init__(
        self,
        strategy: Optional[IClusteringStrategy] = None,
        metric: Optional[IDistanceMetric] = None,
        max_eval_points: int = 2000,
        seed: int = 42,
    ) -> None:
        self._metric = metric or EuclideanDistanceMetric()
        self._strategy = strategy or KMeansClusteringStrategy(metric=self._metric)
        self._max_eval_points = max_eval_points
        self._seed = seed

    def choose(self, points: np.ndarray, k_min: int = 2, k_max: int = 10) -> KSelection:
        """Return the best K in [k_min, k_max] for the (n, d) ``points``."""
        points = np.asarray(points, dtype=float)
        n = points.shape[0]

        # Degenerate populations: not enough points to form >=2 clusters.
        if n <= 2 or k_min >= n:
            return KSelection(k=max(1, min(k_min, n)), scores={})

        # Cap the work: silhouette is quadratic, so evaluate on a sub-sample.
        eval_points = self._subsample(points, n)

        # Never search for more clusters than we have points to evaluate on.
        upper = min(k_max, eval_points.shape[0] - 1)
        lower = max(2, k_min)
        if upper < lower:
            return KSelection(k=lower, scores={})

        # Build the pairwise distance matrix once — eval_points is constant
        # across all K candidates, so the matrix is identical every iteration.
        # sklearn recomputes it internally on every silhouette_score() call;
        # the numpy fallback allocates O(n²d) on every call. Computing it here
        # eliminates (k_max - k_min) redundant builds.
        dist = self._build_dist_matrix(eval_points)

        scores: dict = {}
        best_k, best_score = lower, -1.0
        for k in range(lower, upper + 1):
            labels = self._strategy.cluster(eval_points, k).labels
            score = self._silhouette_precomputed(dist, labels)
            scores[k] = score
            if score > best_score:
                best_k, best_score = k, score

        return KSelection(k=best_k, scores=scores)

    # ── helpers ────────────────────────────────────────────────────────────────

    def _subsample(self, points: np.ndarray, n: int) -> np.ndarray:
        if n <= self._max_eval_points:
            return points
        rng = np.random.default_rng(self._seed)
        idx = rng.choice(n, size=self._max_eval_points, replace=False)
        return points[idx]

    def _build_dist_matrix(self, points: np.ndarray) -> np.ndarray:
        """Pairwise distance matrix for the eval sub-sample."""
        p32 = points.astype(np.float32, copy=False)
        if _HAS_SKLEARN and isinstance(self._metric, EuclideanDistanceMetric):
            from sklearn.metrics import pairwise_distances
            return pairwise_distances(p32, metric='euclidean')
        metric_dist = self._metric.distance_to_centroids(p32, p32)
        if metric_dist.shape != (p32.shape[0], p32.shape[0]):
            raise ValueError("metric returned an invalid pairwise distance matrix")
        return metric_dist.astype(np.float32, copy=False)

    def _silhouette_precomputed(self, dist: np.ndarray, labels: np.ndarray) -> float:
        """Mean silhouette from a precomputed (n, n) distance matrix."""
        unique = np.unique(labels)
        if unique.size < 2:
            return 0.0

        if _HAS_SKLEARN:
            try:
                return float(_sklearn_silhouette(dist, labels, metric='precomputed'))
            except Exception:
                pass

        # Vectorised NumPy fallback — dist already built, no reallocation.
        n = dist.shape[0]
        a = np.zeros(n, dtype=float)
        b = np.full(n, np.inf)

        for c in unique:
            mask = labels == c
            idx = np.where(mask)[0]
            size = idx.size

            if size > 1:
                intra_sum = dist[np.ix_(idx, idx)].sum(axis=1)
                a[idx] = intra_sum / (size - 1)

            not_idx = np.where(~mask)[0]
            if not_idx.size > 0 and size > 0:
                inter_mean = dist[np.ix_(not_idx, idx)].mean(axis=1)
                b[not_idx] = np.minimum(b[not_idx], inter_mean)

        b = np.where(np.isinf(b), 0.0, b)
        denom = np.maximum(a, b)
        sil = np.where(denom == 0, 0.0, (b - a) / denom)
        return float(sil.mean())
