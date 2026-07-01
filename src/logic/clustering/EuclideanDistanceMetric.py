"""Euclidean distance on normalized feature vectors (the default metric)."""
from __future__ import annotations

import numpy as np

from src.logic.clustering.IDistanceMetric import IDistanceMetric


class EuclideanDistanceMetric(IDistanceMetric):
    """Straight-line distance in normalized feature space."""

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm(a - b))

    def distance_to_centroids(self, points: np.ndarray, centroids: np.ndarray) -> np.ndarray:
        # (n, 1, d) - (1, k, d) -> (n, k, d), then norm over the last axis -> (n, k).
        diff = points[:, np.newaxis, :] - centroids[np.newaxis, :, :]
        return np.linalg.norm(diff, axis=2)
