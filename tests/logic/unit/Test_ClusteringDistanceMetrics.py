"""Unit tests for the clustering subsystem's distance metrics.

Covers EuclideanDistanceMetric and WeightedEuclideanDistanceMetric: plain
straight-line distance, the batched point-to-centroid distance matrix used
by the clustering algorithms, and weighted distance behaviour (matching
plain Euclidean at unit weights, scaling a dimension's contribution, and
rejecting invalid weight vectors).

This file is one of four sibling files that share the "CLU" TC-ID prefix,
each covering a different layer of the clustering subsystem as one
continuous numbered family:
  - Test_ClusteringFeatures.py     TC-CLU-001..010 (feature extraction/normalization)
  - Test_ClusteringDistanceMetrics.py (this file)  TC-CLU-011..016 (distance metrics)
  - Test_ClusteringAlgorithms.py   TC-CLU-017..027 (clustering algorithms/sampling)
  - Test_ClusteringService.py      TC-CLU-028..032 (clustering service)
The numbering is intentionally continuous across the four files and must
not be restarted within any single file.

Test bodies follow the Arrange/Act/Assert structure, marked with explicit
``# Arrange`` / ``# Act`` / ``# Assert`` comments.

Fixture policy: none of the shared fixtures defined in tests/conftest.py
apply here. Those fixtures build scheduling domain objects (courses, exam
periods, assignments, DTOs); this file tests pure distance-metric math on
small NumPy arrays, so each test constructs its own minimal vectors inline
instead.
"""
import numpy as np
import pytest

from src.logic.clustering.EuclideanDistanceMetric import EuclideanDistanceMetric
from src.logic.clustering.WeightedEuclideanDistanceMetric import WeightedEuclideanDistanceMetric


# ---------------------------------------------------------------------------
# EuclideanDistanceMetric TC-CLU-011..012
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CLU-011: distance() returns the plain straight-line (Euclidean) norm
# of the difference between two vectors.
# ===========================================================================
def test_euclidean_distance_metric_computes_straight_line_distance():
    # Arrange
    metric = EuclideanDistanceMetric()
    a = np.array([0.0, 0.0])
    b = np.array([3.0, 4.0])

    # Act
    result = metric.distance(a, b)

    # Assert
    # 3-4-5 right triangle, so the straight-line distance is exactly 5.
    assert result == 5.0


# ===========================================================================
# TC-CLU-012: distance_to_centroids() returns the full (n, k) matrix of
# distances from every point to every centroid.
# ===========================================================================
def test_euclidean_distance_metric_distance_to_centroids_matrix():
    # Arrange
    metric = EuclideanDistanceMetric()
    points = np.array([[0.0, 0.0], [3.0, 4.0]])
    centroids = np.array([[0.0, 0.0], [0.0, 4.0]])

    # Act
    result = metric.distance_to_centroids(points, centroids)

    # Assert
    assert result.shape == (2, 2)
    assert result.tolist() == [[0.0, 4.0], [5.0, 3.0]]


# ---------------------------------------------------------------------------
# WeightedEuclideanDistanceMetric TC-CLU-013..016
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CLU-013: with every weight equal to 1, the weighted metric matches
# plain Euclidean distance exactly.
# ===========================================================================
def test_weighted_euclidean_distance_matches_plain_euclidean_when_weights_are_one():
    # Arrange
    weighted = WeightedEuclideanDistanceMetric([1.0, 1.0])
    plain = EuclideanDistanceMetric()
    a = np.array([0.0, 0.0])
    b = np.array([3.0, 4.0])

    # Act
    weighted_result = weighted.distance(a, b)
    plain_result = plain.distance(a, b)

    # Assert
    assert weighted_result == plain_result


# ===========================================================================
# TC-CLU-014: a larger weight on a dimension increases that dimension's
# contribution to the overall distance.
# ===========================================================================
def test_weighted_euclidean_distance_applies_the_weight():
    # Arrange — weight 4.0 on the first dimension, 1.0 on the second.
    metric = WeightedEuclideanDistanceMetric([4.0, 1.0])
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 1.0])

    # Act
    result = metric.distance(a, b)

    # Assert
    # sqrt(4 * 1^2 + 1 * 1^2) = sqrt(5), not the unweighted sqrt(2).
    assert result == pytest.approx(5 ** 0.5)


# ===========================================================================
# TC-CLU-015: a negative weight is rejected, since it would invert a
# dimension's contribution to the distance.
# ===========================================================================
def test_weighted_euclidean_distance_rejects_negative_weights():
    # Arrange

    # Act
    # Assert
    # Validation happens inside the constructor, so the call and the
    # expected outcome are captured together by the context manager.
    with pytest.raises(ValueError):
        WeightedEuclideanDistanceMetric([-1.0, 1.0])


# ===========================================================================
# TC-CLU-016: all-zero weights are rejected, since no dimension would ever
# count toward similarity.
# ===========================================================================
def test_weighted_euclidean_distance_rejects_all_zero_weights():
    # Arrange

    # Act
    # Assert
    # Validation happens inside the constructor, so the call and the
    # expected outcome are captured together by the context manager.
    with pytest.raises(ValueError):
        WeightedEuclideanDistanceMetric([0.0, 0.0])
