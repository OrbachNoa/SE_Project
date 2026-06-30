"""Unit tests for ClusteringService, the orchestrator that wires feature
extraction, normalization, K selection, and the clustering strategy into a
single fit()/cluster() pipeline and reports the outcome as a ClusterResult.

This file owns TC-CLU-028 through TC-CLU-033. The "CLU" prefix is shared
across four sibling files that each cover one layer of the clustering
subsystem as a single numbered family:
  - Test_ClusteringFeatures.py          TC-CLU-001..010 (feature extraction)
  - Test_ClusteringDistanceMetrics.py    TC-CLU-011..016 (distance metrics)
  - Test_ClusteringAlgorithms.py         TC-CLU-017..027 (clustering strategies)
  - Test_ClusteringService.py (this file) TC-CLU-028..032 (end-to-end orchestration)

Every test body follows the Arrange/Act/Assert structure, with each section
marked by its own exact comment so the setup, the call under test, and the
outcome checks stay visually distinct.

Fixture policy: this file does not draw on any shared fixtures from
tests/conftest.py. Those fixtures build domain objects (Course, ExamPeriod,
ExamAssignment, etc.) for the scheduling engine, whereas these tests only
need bare ScheduleDTO score dictionaries and ClusteringService/ClusterConfig
instances, which are cheaper and clearer to construct inline per test.
"""
import numpy as np
import pytest

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.logic.clustering.ClusteringService import ClusteringService
from src.logic.clustering.ClusterConfig import ClusterConfig
from src.logic.comparators.ScheduleScorer import (
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
)


# ===========================================================================
# TC-CLU-028: fitting on six schedules that form two clearly distinct
# behavioural groups (spacious vs. cramped) and clustering with a fixed
# k=2 produces two coherent, non-empty clusters that each keep their own
# group's members together.
# ===========================================================================
def test_clustering_service_groups_schedules_with_similar_scores_together():
    # Arrange
    spacious = [
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: 20.0, AVG_ALL_COURSES_GAP: 15.0,
            ELECTIVE_CONFLICTS: 0.0, MANDATORY_SPAN: 30.0, MAX_EXAMS_PER_DAY: -1.0,
        })
        for _ in range(3)
    ]
    cramped = [
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: 1.0, AVG_ALL_COURSES_GAP: 1.0,
            ELECTIVE_CONFLICTS: -5.0, MANDATORY_SPAN: 2.0, MAX_EXAMS_PER_DAY: -4.0,
        })
        for _ in range(3)
    ]
    schedules = spacious + cramped
    service = ClusteringService(ClusterConfig(k_mode="fixed", k=2, seed=42))
    service.fit(schedules)

    # Act
    result = service.cluster()

    # Assert
    assert result.k == 2
    assert len(result.clusters) == 2
    member_sets = [set(c.member_indices) for c in result.clusters]
    assert {0, 1, 2} in member_sets
    assert {3, 4, 5} in member_sets
    for cluster in result.clusters:
        assert cluster.size == 3
        assert cluster.representative_index in cluster.member_indices
        assert cluster.description != ""
        assert set(cluster.summary.keys()) == {
            MIN_MANDATORY_GAP, AVG_ALL_COURSES_GAP,
            ELECTIVE_CONFLICTS, MANDATORY_SPAN, MAX_EXAMS_PER_DAY,
        }


# ===========================================================================
# TC-CLU-029: calling cluster() before fit() raises RuntimeError, since
# there is no normalized matrix yet to partition.
# ===========================================================================
def test_clustering_service_cluster_before_fit_raises():
    # Arrange
    service = ClusteringService(ClusterConfig(k_mode="fixed", k=2))

    # Act
    act = lambda: service.cluster()

    # Assert
    with pytest.raises(RuntimeError):
        act()


# ===========================================================================
# TC-CLU-030: fitting on an empty list of schedules raises ValueError
# instead of silently producing an unusable service.
# ===========================================================================
def test_clustering_service_fit_on_empty_schedules_raises():
    # Arrange
    service = ClusteringService(ClusterConfig(k_mode="fixed", k=2))

    # Act
    act = lambda: service.fit([])

    # Assert
    with pytest.raises(ValueError):
        act()


# ===========================================================================
# TC-CLU-031: when fit() is given a population_size larger than the
# working set, the result is marked sampled and a cluster's estimated
# population size is scaled up accordingly.
# ===========================================================================
def test_clustering_service_scales_estimated_size_when_sampled():
    # Arrange
    schedules = [
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: 5.0, AVG_ALL_COURSES_GAP: 5.0,
            ELECTIVE_CONFLICTS: 0.0, MANDATORY_SPAN: 5.0, MAX_EXAMS_PER_DAY: -1.0,
        })
        for _ in range(3)
    ]
    service = ClusteringService(ClusterConfig(k_mode="fixed", k=1, seed=42))
    service.fit(schedules, population_size=30)

    # Act
    result = service.cluster()

    # Assert
    assert result.sampled is True
    assert result.population_size == 30
    assert result.working_set_size == 3
    cluster = result.clusters[0]
    assert cluster.size == 3
    assert cluster.estimated_population_size == 30


# ===========================================================================
# TC-CLU-032: when the config selects only one criterion, the result
# reports just that criterion, end to end through extraction and summary.
# ===========================================================================
def test_clustering_service_result_reports_only_the_configured_criteria():
    # Arrange
    schedules = [
        ScheduleDTO(scores={MANDATORY_SPAN: 5.0, MIN_MANDATORY_GAP: 99.0}),
        ScheduleDTO(scores={MANDATORY_SPAN: 6.0, MIN_MANDATORY_GAP: 1.0}),
    ]
    config = ClusterConfig(criteria=(MANDATORY_SPAN,), k_mode="fixed", k=1, seed=42)
    service = ClusteringService(config)
    service.fit(schedules)

    # Act
    result = service.cluster()

    # Assert
    assert result.criteria == [MANDATORY_SPAN]
    assert set(result.clusters[0].summary.keys()) == {MANDATORY_SPAN}


# ===========================================================================
# TC-CLU-033: weighted criteria affect the sklearn-backed cluster assignment,
# not only the later representative-picking step.
# ===========================================================================
def test_clustering_service_applies_config_weights_to_cluster_assignment():
    # Arrange
    raw_vectors = np.array([
        [0.0, 0.0],
        [0.0, 10.0],
        [1.0, 0.0],
        [1.0, 10.0],
    ])
    config = ClusterConfig(
        criteria=(MIN_MANDATORY_GAP, MANDATORY_SPAN),
        weights={MIN_MANDATORY_GAP: 400.0},
        normalizer="minmax",
        k_mode="fixed",
        k=2,
        seed=42,
    )
    service = ClusteringService(config)
    service.fit_vectors(raw_vectors)

    # Act
    result = service.cluster()

    # Assert
    member_sets = [set(cluster.member_indices) for cluster in result.clusters]
    assert {0, 1} in member_sets
    assert {2, 3} in member_sets
