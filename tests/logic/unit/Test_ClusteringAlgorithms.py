import numpy as np
import pytest

from src.logic.clustering.KMeansClusteringStrategy import KMeansClusteringStrategy
from src.logic.clustering.AutoKSelector import AutoKSelector
from src.logic.clustering.ScheduleSampler import ScheduleSampler


# ---------------------------------------------------------------------------
# KMeansClusteringStrategy TC-CLU-017..021
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CLU-017: with two well-separated blobs and k=2, every point of a blob
# ends up under the same label, and the two blobs get different labels.
# ===========================================================================
def test_kmeans_clustering_separates_two_well_separated_blobs():
    # Arrange
    points = np.array([
        [0.0, 0.0], [0.1, 0.1], [0.0, 0.2], [0.2, 0.0],
        [100.0, 100.0], [100.1, 100.1], [100.0, 100.2], [100.2, 100.0],
    ])
    strategy = KMeansClusteringStrategy(seed=42)

    # Act
    output = strategy.cluster(points, k=2)

    # Assert
    assert output.centroids.shape == (2, 2)
    first_blob_labels = set(output.labels[:4].tolist())
    second_blob_labels = set(output.labels[4:].tolist())
    assert len(first_blob_labels) == 1
    assert len(second_blob_labels) == 1
    assert first_blob_labels != second_blob_labels


# ===========================================================================
# TC-CLU-018: with three well-separated blobs and k=3, the algorithm
# produces exactly three non-empty clusters, one per blob.
# ===========================================================================
def test_kmeans_clustering_produces_k_non_empty_clusters_for_three_blobs():
    # Arrange
    points = np.array([
        [0.0, 0.0], [0.1, 0.1], [0.2, 0.0],
        [50.0, 50.0], [50.1, 50.1], [50.2, 50.0],
        [100.0, 0.0], [100.1, 0.1], [100.2, 0.0],
    ])
    strategy = KMeansClusteringStrategy(seed=42)

    # Act
    output = strategy.cluster(points, k=3)

    # Assert — three distinct, non-empty clusters of three members each.
    unique_labels, counts = np.unique(output.labels, return_counts=True)
    assert len(unique_labels) == 3
    assert sorted(counts.tolist()) == [3, 3, 3]


# ===========================================================================
# TC-CLU-019: requesting more clusters than available points caps the
# effective K down to the number of points.
# ===========================================================================
def test_kmeans_clustering_caps_k_to_the_number_of_points():
    # Arrange
    points = np.array([[0.0, 0.0], [1.0, 1.0]])
    strategy = KMeansClusteringStrategy(seed=42)

    # Act
    output = strategy.cluster(points, k=5)

    # Assert
    assert output.centroids.shape[0] == 2


# ===========================================================================
# TC-CLU-020: clustering the same points with the same seed twice produces
# identical labels and centroids (deterministic for a stable UI).
# ===========================================================================
def test_kmeans_clustering_is_deterministic_for_a_fixed_seed():
    # Arrange
    points = np.array([[0.0, 0.0], [0.1, 0.1], [10.0, 10.0], [10.1, 10.1]])
    strategy_one = KMeansClusteringStrategy(seed=42)
    strategy_two = KMeansClusteringStrategy(seed=42)

    # Act
    output_one = strategy_one.cluster(points, k=2)
    output_two = strategy_two.cluster(points, k=2)

    # Assert
    assert output_one.labels.tolist() == output_two.labels.tolist()
    assert output_one.centroids.tolist() == output_two.centroids.tolist()


# ===========================================================================
# TC-CLU-021: clustering an empty set of points raises ValueError instead
# of returning a meaningless empty result.
# ===========================================================================
def test_kmeans_clustering_rejects_an_empty_point_set():
    # Arrange
    strategy = KMeansClusteringStrategy(seed=42)
    empty_points = np.empty((0, 2))

    # Act + Assert
    with pytest.raises(ValueError):
        strategy.cluster(empty_points, k=2)


# ---------------------------------------------------------------------------
# AutoKSelector TC-CLU-022..023
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CLU-022: for three tight, well-separated blobs, silhouette scoring
# picks K=3 over every other candidate in [2, 5].
# ===========================================================================
def test_auto_k_selector_picks_a_reasonable_k_for_three_obvious_blobs():
    # Arrange
    points = np.array([
        [0.0, 0.0], [0.1, 0.1], [0.2, 0.0],
        [50.0, 50.0], [50.1, 50.1], [50.2, 50.0],
        [100.0, 0.0], [100.1, 0.1], [100.2, 0.0],
    ])
    selector = AutoKSelector(seed=42)

    # Act
    selection = selector.choose(points, k_min=2, k_max=5)

    # Assert
    assert selection.k == 3
    assert set(selection.scores.keys()) == {2, 3, 4, 5}
    assert selection.scores[3] == max(selection.scores.values())


# ===========================================================================
# TC-CLU-023: a degenerate population (only as many points as k_min) skips
# silhouette scoring entirely and returns a capped K with no scores.
# ===========================================================================
def test_auto_k_selector_handles_a_degenerate_small_population():
    # Arrange
    points = np.array([[0.0, 0.0], [1.0, 1.0]])
    selector = AutoKSelector(seed=42)

    # Act
    selection = selector.choose(points, k_min=2, k_max=5)

    # Assert
    assert selection.k == 2
    assert selection.scores == {}


# ---------------------------------------------------------------------------
# ScheduleSampler TC-CLU-024..027
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CLU-024: when the population already fits within max_sample, every
# index is returned, in order, with no sampling.
# ===========================================================================
def test_schedule_sampler_returns_every_index_when_population_fits():
    # Arrange
    sampler = ScheduleSampler(max_sample=10, seed=42)

    # Act
    indices = sampler.sample_indices(5)

    # Assert
    assert indices == [0, 1, 2, 3, 4]


# ===========================================================================
# TC-CLU-025: when the population exceeds max_sample, exactly max_sample
# unique, sorted, in-range indices are drawn.
# ===========================================================================
def test_schedule_sampler_samples_exactly_max_sample_unique_sorted_indices():
    # Arrange
    sampler = ScheduleSampler(max_sample=10, seed=42)

    # Act
    indices = sampler.sample_indices(1000)

    # Assert
    assert len(indices) == 10
    assert len(set(indices)) == 10
    assert indices == sorted(indices)
    assert all(0 <= i < 1000 for i in indices)


# ===========================================================================
# TC-CLU-026: sample() returns the sampled items together with the
# original indices they came from, consistently paired.
# ===========================================================================
def test_schedule_sampler_sample_maps_items_to_original_indices():
    # Arrange
    sampler = ScheduleSampler(max_sample=3, seed=42)
    items = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]

    # Act
    sampled_items, indices = sampler.sample(items)

    # Assert
    assert len(sampled_items) == 3
    assert sampled_items == [items[i] for i in indices]


# ===========================================================================
# TC-CLU-027: constructing a sampler with a non-positive max_sample raises
# ValueError instead of producing a sampler that can never sample.
# ===========================================================================
def test_schedule_sampler_rejects_a_non_positive_max_sample():
    # Act + Assert
    with pytest.raises(ValueError):
        ScheduleSampler(max_sample=0)
