"""K-means clustering with k-means++ seeding (the default strategy).

Implemented in-house so the project stays lightweight (no scikit-learn) and the
algorithm is an explicit, swappable Strategy component. A fixed random seed makes
the result deterministic, which keeps the UI stable: the same schedules and the
same K always produce the same families.

The distance metric is injected, so the notion of "nearest centroid" is decided
by whichever ``IDistanceMetric`` the caller chose — plain Euclidean by default,
or the weighted metric when a request emphasises particular criteria.
"""
from __future__ import annotations

import numpy as np

from src.logic.clustering.IClusteringStrategy import (
    ClusteringOutput,
    IClusteringStrategy,
)
from src.logic.clustering.IDistanceMetric import IDistanceMetric
from src.logic.clustering.EuclideanDistanceMetric import EuclideanDistanceMetric


class KMeansClusteringStrategy(IClusteringStrategy):
    """Lloyd's algorithm with k-means++ initialization."""

    def __init__(
        self,
        metric: IDistanceMetric | None = None,
        max_iterations: int = 100,
        seed: int = 42,
    ) -> None:
        # Default to Euclidean, but accept any injected metric (Strategy).
        self._metric = metric or EuclideanDistanceMetric()
        self._max_iterations = max_iterations
        self._seed = seed

    def cluster(self, points: np.ndarray, k: int) -> ClusteringOutput:
        if k <= 0:
            raise ValueError("k must be a positive integer")

        points = np.asarray(points, dtype=float)
        n = points.shape[0]
        if n == 0:
            raise ValueError("cannot cluster an empty set of points")

        # More clusters than points is meaningless: every point is its own cluster.
        effective_k = min(k, n)

        rng = np.random.default_rng(self._seed)
        centroids = self._kmeans_plus_plus_init(points, effective_k, rng)

        labels = np.zeros(n, dtype=int)
        for _ in range(self._max_iterations):
            distances = self._metric.distance_to_centroids(points, centroids)
            new_labels = distances.argmin(axis=1)

            # Converged once no point changes its cluster.
            if np.array_equal(new_labels, labels):
                labels = new_labels
                break
            labels = new_labels

            centroids = self._recompute_centroids(points, labels, centroids, rng)

        return ClusteringOutput(labels=labels, centroids=centroids)

    # ── initialization ───────────────────────────────────────────────────────

    def _kmeans_plus_plus_init(
        self, points: np.ndarray, k: int, rng: np.random.Generator
    ) -> np.ndarray:
        """Pick spread-out initial centroids (k-means++) for a stable result."""
        n = points.shape[0]
        first = rng.integers(n)
        centroids = [points[first]]

        for _ in range(1, k):
            existing = np.array(centroids)
            # Squared distance from every point to its nearest chosen centroid.
            dist = self._metric.distance_to_centroids(points, existing).min(axis=1)
            sq = dist ** 2
            total = sq.sum()
            if total == 0:
                # All remaining points coincide with a centroid; pick any.
                centroids.append(points[rng.integers(n)])
                continue
            # Choose the next centroid proportionally to squared distance.
            probabilities = sq / total
            chosen = rng.choice(n, p=probabilities)
            centroids.append(points[chosen])

        return np.array(centroids)

    # ── update step ──────────────────────────────────────────────────────────

    def _recompute_centroids(
        self,
        points: np.ndarray,
        labels: np.ndarray,
        previous: np.ndarray,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Each centroid becomes the mean of its members; re-seed empty clusters."""
        k = previous.shape[0]
        centroids = previous.copy()
        for c in range(k):
            members = points[labels == c]
            if len(members) > 0:
                centroids[c] = members.mean(axis=0)
            else:
                # Empty cluster: move it to the point farthest from any centroid,
                # so the cluster count requested by the user is preserved.
                dist = self._metric.distance_to_centroids(points, centroids).min(axis=1)
                centroids[c] = points[int(dist.argmax())]
        return centroids
