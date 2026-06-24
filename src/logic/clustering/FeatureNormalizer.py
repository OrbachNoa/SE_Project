"""Min-max normalization of feature vectors.

The five scores live on wildly different scales: a mandatory span is tens of days
while max-exams-per-day is a small negated integer. Fed raw into a distance, the
wide-range feature would dominate and the others would barely matter. This
normalizer rescales every dimension to [0, 1] across the population so each
criterion contributes fairly.

The fitted min/range are stored, so a single new vector (e.g. a freshly generated
schedule) can be projected onto the very same scale the clusters were built on.
"""
from __future__ import annotations

from typing import Optional

import numpy as np


class FeatureNormalizer:
    """Fits per-feature min/max and rescales vectors to the [0, 1] range."""

    def __init__(self) -> None:
        self._min: Optional[np.ndarray] = None
        self._range: Optional[np.ndarray] = None

    def fit(self, matrix: np.ndarray) -> "FeatureNormalizer":
        """Learn the per-dimension minimum and range from an (n, d) matrix."""
        if matrix.size == 0:
            raise ValueError("cannot fit a normalizer on an empty matrix")

        matrix = np.asarray(matrix, dtype=float)
        self._min = matrix.min(axis=0)
        span = matrix.max(axis=0) - self._min
        # A constant feature carries no information; keep its range at 1 so it
        # maps to a constant 0 instead of producing div-by-zero.
        span[span == 0] = 1.0
        self._range = span
        return self

    def transform(self, matrix: np.ndarray) -> np.ndarray:
        """Project an (n, d) matrix onto the fitted [0, 1] scale."""
        self._ensure_fitted()
        return (np.asarray(matrix, dtype=float) - self._min) / self._range

    def fit_transform(self, matrix: np.ndarray) -> np.ndarray:
        """Convenience: ``fit`` then ``transform`` on the same population.

        Returns an empty array of the same shape when given an empty matrix
        (0 rows) instead of raising, so callers don't need to guard.
        """
        matrix = np.asarray(matrix, dtype=float)
        if matrix.ndim == 2 and matrix.shape[0] == 0:
            return matrix
        return self.fit(matrix).transform(matrix)

    def transform_one(self, vector: np.ndarray) -> np.ndarray:
        """Project a single (d,) vector onto the fitted scale."""
        self._ensure_fitted()
        return (np.asarray(vector, dtype=float) - self._min) / self._range

    def _ensure_fitted(self) -> None:
        if self._min is None or self._range is None:
            raise RuntimeError("normalizer used before fit() was called")


def normalize_features(vectors: np.ndarray) -> np.ndarray:
    """Min-max normalize an (n, d) matrix to [0, 1] per column.

    Identical-value columns map to 0.0 (not NaN).  Empty input (0 rows)
    returns the same empty array without raising.

    This is a convenience wrapper for callers that want a one-call API
    without constructing a ``FeatureNormalizer`` explicitly.
    """
    return FeatureNormalizer().fit_transform(np.asarray(vectors, dtype=float))
