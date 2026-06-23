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

    # Assert — a classic 3-4-5 right triangle.
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

    # Assert — sqrt(4 * 1^2 + 1 * 1^2) = sqrt(5), not the unweighted sqrt(2).
    assert result == pytest.approx(5 ** 0.5)


# ===========================================================================
# TC-CLU-015: a negative weight is rejected, since it would invert a
# dimension's contribution to the distance.
# ===========================================================================
def test_weighted_euclidean_distance_rejects_negative_weights():
    # Act + Assert
    with pytest.raises(ValueError):
        WeightedEuclideanDistanceMetric([-1.0, 1.0])


# ===========================================================================
# TC-CLU-016: all-zero weights are rejected, since no dimension would ever
# count toward similarity.
# ===========================================================================
def test_weighted_euclidean_distance_rejects_all_zero_weights():
    # Act + Assert
    with pytest.raises(ValueError):
        WeightedEuclideanDistanceMetric([0.0, 0.0])
