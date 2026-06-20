"""Strategy interface for the distance between two normalized feature vectors.

Distance is always measured on normalized vectors, so it expresses how similar
two schedules are regardless of original units. Hiding it behind an interface
lets the clustering algorithm stay agnostic to *which* notion of similarity is in
use (plain Euclidean, weighted, Manhattan, ...). The weighted variant is what a
future "group mostly by X" request will lean on.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class IDistanceMetric(ABC):
    """Measures how far apart two normalized feature vectors are."""

    @abstractmethod
    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Distance between two (d,) vectors. Smaller means more similar."""
        raise NotImplementedError

    @abstractmethod
    def distance_to_centroids(self, points: np.ndarray, centroids: np.ndarray) -> np.ndarray:
        """Distance from each of ``n`` points to each of ``k`` centroids.

        ``points`` is (n, d), ``centroids`` is (k, d); returns an (n, k) matrix.
        Part of the interface because clustering needs it in bulk and a metric
        can vectorize it far more efficiently than n*k scalar calls.
        """
        raise NotImplementedError
