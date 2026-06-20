"""Weighted Euclidean distance — emphasise some criteria over others.

Identical to plain Euclidean when all weights are 1. A weight scales how much a
dimension counts toward "similar": a large weight on MANDATORY_SPAN makes two
schedules feel close only when their spans are close. This is the metric a future
custom-clustering request ("group mainly by exam spread") maps onto — the LLM
fills ``ClusterConfig.weights`` and this metric does the rest, with no change to
the clustering algorithm itself.
"""
from __future__ import annotations

import numpy as np

from src.logic.clustering.IDistanceMetric import IDistanceMetric


class WeightedEuclideanDistanceMetric(IDistanceMetric):
    """Euclidean distance after scaling each dimension by sqrt(weight)."""

    def __init__(self, weights) -> None:
        w = np.asarray(weights, dtype=float)
        if np.any(w < 0):
            raise ValueError("weights must be non-negative")
        if w.size == 0 or np.all(w == 0):
            raise ValueError("at least one weight must be positive")
        # Scaling each axis by sqrt(w) makes ordinary Euclidean distance on the
        # scaled space equal to the weighted distance on the original space.
        self._scale = np.sqrt(w)

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm((a - b) * self._scale))

    def distance_to_centroids(self, points: np.ndarray, centroids: np.ndarray) -> np.ndarray:
        diff = (points[:, np.newaxis, :] - centroids[np.newaxis, :, :]) * self._scale
        return np.linalg.norm(diff, axis=2)
