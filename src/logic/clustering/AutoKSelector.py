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

        scores: dict = {}
        best_k, best_score = lower, -1.0
        for k in range(lower, upper + 1):
            labels = self._strategy.cluster(eval_points, k).labels
            score = self._silhouette(eval_points, labels)
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

    def _silhouette(self, points: np.ndarray, labels: np.ndarray) -> float:
        """Mean silhouette coefficient of a labelling (higher is better).

        For each point: a = mean distance to its own cluster, b = mean distance
        to the nearest other cluster; silhouette = (b - a) / max(a, b). Returns 0
        for degenerate labellings (a single non-empty cluster).
        """
        unique = np.unique(labels)
        if unique.size < 2:
            return 0.0

        # Full pairwise distances on the (capped) evaluation set.
        diff = points[:, np.newaxis, :] - points[np.newaxis, :, :]
        dist = np.linalg.norm(diff, axis=2)

        n = points.shape[0]
        sil = np.zeros(n, dtype=float)
        for i in range(n):
            own = labels[i]
            same = labels == own
            same[i] = False  # exclude self
            same_count = same.sum()
            if same_count == 0:
                sil[i] = 0.0  # lone point in its cluster
                continue
            a = dist[i, same].mean()

            b = np.inf
            for other in unique:
                if other == own:
                    continue
                mask = labels == other
                if mask.any():
                    b = min(b, dist[i, mask].mean())

            sil[i] = 0.0 if max(a, b) == 0 else (b - a) / max(a, b)

        return float(sil.mean())
