"""Strategy interface for the clustering algorithm itself.

The algorithm receives an already-normalized (n, d) matrix and a target number of
clusters K, and returns, for every point, the index of the cluster it belongs to
together with the cluster centroids. Hiding it behind an interface lets the
in-house K-means be replaced (by scikit-learn's KMeans, k-medoids, hierarchical
clustering, ...) without changing any caller.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class ClusteringOutput:
    """Raw result of a clustering run."""

    # labels[i] = index of the cluster that point i was assigned to (0..k-1).
    labels: np.ndarray
    # centroids[c] = the center of cluster c, in normalized feature space.
    centroids: np.ndarray


class IClusteringStrategy(ABC):
    """Partitions normalized points into K clusters."""

    @abstractmethod
    def cluster(self, points: np.ndarray, k: int) -> ClusteringOutput:
        """Assign each row of ``points`` (n, d) to one of ``k`` clusters."""
        raise NotImplementedError
