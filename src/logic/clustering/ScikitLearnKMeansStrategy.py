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
    ) -> None:
        self._n_init = n_init
        self._max_iter = max_iter
        self._random_state = random_state

    def cluster(self, points: np.ndarray, k: int) -> ClusteringOutput:
        if k <= 0:
            raise ValueError("k must be a positive integer")

        points = np.asarray(points, dtype=float)
        n = points.shape[0]
        if n == 0:
            raise ValueError("cannot cluster an empty set of points")

        effective_k = min(k, n)
        km = KMeans(
            n_clusters=effective_k,
            n_init=self._n_init,
            max_iter=self._max_iter,
            random_state=self._random_state,
        )
        labels = km.fit_predict(points)
        return ClusteringOutput(
            labels=labels.astype(int),
            centroids=km.cluster_centers_,
        )
