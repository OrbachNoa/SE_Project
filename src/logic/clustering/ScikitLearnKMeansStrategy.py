"""K-means via scikit-learn (the fast, production-grade path).

scikit-learn's KMeans is implemented in optimised C/Cython, supports multiple
restarts (``n_init``) to escape bad initialisations, and is an order of
magnitude faster than a pure-Python Lloyd's loop on the 5-dimensional,
10K-point working sets the application uses.

The custom ``KMeansClusteringStrategy`` is kept as a dependency-free fallback
(useful in constrained environments and for unit tests that run offline), but
this is the default strategy in ``ClusteringService``.
"""
from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

from src.logic.clustering.IClusteringStrategy import (
    ClusteringOutput,
    IClusteringStrategy,
)


class ScikitLearnKMeansStrategy(IClusteringStrategy):
    """Wraps ``sklearn.cluster.KMeans`` behind the ``IClusteringStrategy`` interface."""

    def __init__(
        self,
        n_init: int = 10,
        max_iter: int = 300,
        random_state: int = 42,
        weights=None,
    ) -> None:
        self._n_init = n_init
        self._max_iter = max_iter
        self._random_state = random_state
        self._scale = self._build_scale(weights)

    def cluster(self, points: np.ndarray, k: int) -> ClusteringOutput:
        if k <= 0:
            raise ValueError("k must be a positive integer")

        points = np.asarray(points, dtype=float)
        n = points.shape[0]
        if n == 0:
            raise ValueError("cannot cluster an empty set of points")

        effective_k = min(k, n)
        fit_points = self._scale_points(points)
        km = KMeans(
            n_clusters=effective_k,
            n_init=self._n_init,
            max_iter=self._max_iter,
            random_state=self._random_state,
        )
        labels = km.fit_predict(fit_points)
        return ClusteringOutput(
            labels=labels.astype(int),
            centroids=self._centroids_in_original_space(points, labels, effective_k, km.cluster_centers_),
        )

    @staticmethod
    def _build_scale(weights):
        if weights is None:
            return None
        w = np.asarray(weights, dtype=float)
        if np.any(w < 0):
            raise ValueError("weights must be non-negative")
        if w.size == 0 or np.all(w == 0):
            raise ValueError("at least one weight must be positive")
        if np.allclose(w, 1.0):
            return None
        return np.sqrt(w)

    def _scale_points(self, points: np.ndarray) -> np.ndarray:
        if self._scale is None:
            return points
        if points.shape[1] != self._scale.shape[0]:
            raise ValueError("weights length must match point dimensionality")
        return points * self._scale

    def _centroids_in_original_space(
        self,
        points: np.ndarray,
        labels: np.ndarray,
        k: int,
        fitted_centers: np.ndarray,
    ) -> np.ndarray:
        if self._scale is None:
            return fitted_centers
        centroids = np.empty((k, points.shape[1]), dtype=float)
        for cluster_id in range(k):
            members = points[labels == cluster_id]
            if len(members) > 0:
                centroids[cluster_id] = members.mean(axis=0)
            else:
                centroids[cluster_id] = 0.0
        return centroids
