"""
Test suite for ClusteringCoordinator.

Scope   : prepare()'s ValueError guards (empty population, no readable score
          vectors) and its happy path populating is_prepared/flat_criteria;
          cluster()'s RuntimeError when called before prepare(); and
          run_on_schedules()'s ValueError on an empty schedule list plus its
          happy path. The repository collaborator is a duck-typed mock
          (count_scores/read_score_vectors); ClusterConfig/ClusteringService
          run for real, exercising this environment's pure-Python clustering
          fallback (no sklearn required).
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CC-001 .. TC-CC-008
Fixtures: mock_repository (tests/conftest.py)
"""
import numpy as np
import pytest

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.application.services.ClusteringCoordinator import ClusteringCoordinator, ClusteringRun
from src.logic.clustering.ClusterConfig import ClusterConfig
from src.logic.comparators.ScheduleScorer import (
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
    MIN_MANDATORY_GAP,
)


def _make_fixed_config(k=2):
    """A small, deterministic config so cluster() never depends on auto-K."""
    return ClusterConfig(k_mode="fixed", k=k, seed=42)


# TC-CC-001
# prepare() must raise ValueError when the repository reports zero (or
# negative) scored schedules — there is nothing to sample or fit.
def test_prepare_raises_value_error_when_population_is_not_positive(mock_repository):
    # Arrange
    mock_repository.count_scores.return_value = 0
    coordinator = ClusteringCoordinator(mock_repository)

    # Act / Assert
    with pytest.raises(ValueError):
        coordinator.prepare(_make_fixed_config())


# TC-CC-002
# prepare() must raise ValueError when the repository returns an empty
# vector matrix for the sampled ids, even though the population is
# positive — clustering needs at least the rows it asked for.
def test_prepare_raises_value_error_when_no_score_vectors_could_be_read(mock_repository):
    # Arrange
    mock_repository.count_scores.return_value = 10
    mock_repository.read_score_vectors.return_value = ([], np.empty((0, 5)))
    coordinator = ClusteringCoordinator(mock_repository)

    # Act / Assert
    with pytest.raises(ValueError):
        coordinator.prepare(_make_fixed_config())


# TC-CC-003
# A successful prepare() must mark the coordinator as prepared and expose
# flat_criteria — here every column has nonzero variance, so flat_criteria
# must be empty.
def test_prepare_happy_path_marks_prepared_with_no_flat_criteria(mock_repository):
    # Arrange
    mock_repository.count_scores.return_value = 6
    ids = [1, 2, 3, 4, 5, 6]
    vectors = np.array([
        [10.0, 5.0, 0.0, 20.0, -1.0],
        [12.0, 6.0, -1.0, 18.0, -2.0],
        [8.0, 4.0, 0.0, 22.0, -1.0],
        [1.0, 1.0, -5.0, 2.0, -4.0],
        [2.0, 0.5, -4.0, 3.0, -3.0],
        [0.5, 1.5, -6.0, 1.0, -5.0],
    ])
    mock_repository.read_score_vectors.return_value = (ids, vectors)
    coordinator = ClusteringCoordinator(mock_repository)

    # Act
    coordinator.prepare(_make_fixed_config())

    # Assert
    assert coordinator.is_prepared is True
    assert coordinator.flat_criteria == []


# TC-CC-004
# When one criterion column is constant across the sample (near-zero
# variance), prepare() must report it in flat_criteria so the UI can warn
# that this criterion contributes nothing to the partition.
def test_prepare_detects_a_flat_criterion_column(mock_repository):
    # Arrange
    mock_repository.count_scores.return_value = 4
    ids = [1, 2, 3, 4]
    # MIN_MANDATORY_GAP is constant (5.0) across every row -> flat.
    vectors = np.array([
        [5.0, 5.0, 0.0, 20.0, -1.0],
        [5.0, 6.0, -1.0, 18.0, -2.0],
        [5.0, 4.0, 0.0, 22.0, -1.0],
        [5.0, 1.0, -5.0, 2.0, -4.0],
    ])
    mock_repository.read_score_vectors.return_value = (ids, vectors)
    coordinator = ClusteringCoordinator(mock_repository)

    # Act
    coordinator.prepare(_make_fixed_config())

    # Assert
    assert MIN_MANDATORY_GAP in coordinator.flat_criteria


# TC-CC-005
# cluster() must raise RuntimeError when called before prepare(), since
# there is no fitted matrix yet to partition.
def test_cluster_raises_runtime_error_when_not_prepared(mock_repository):
    # Arrange
    coordinator = ClusteringCoordinator(mock_repository)

    # Act / Assert
    with pytest.raises(RuntimeError):
        coordinator.cluster(2)


# TC-CC-006
# After a successful prepare(), cluster() must return a ClusteringRun whose
# gidx_by_working_index matches the sampled ids returned by the repository,
# so gidx_for() can translate cluster positions back to real schedule ids.
def test_cluster_happy_path_returns_run_with_correct_gidx_mapping(mock_repository):
    # Arrange
    mock_repository.count_scores.return_value = 6
    ids = [101, 102, 103, 104, 105, 106]
    vectors = np.array([
        [10.0, 5.0, 0.0, 20.0, -1.0],
        [12.0, 6.0, -1.0, 18.0, -2.0],
        [8.0, 4.0, 0.0, 22.0, -1.0],
        [1.0, 1.0, -5.0, 2.0, -4.0],
        [2.0, 0.5, -4.0, 3.0, -3.0],
        [0.5, 1.5, -6.0, 1.0, -5.0],
    ])
    mock_repository.read_score_vectors.return_value = (ids, vectors)
    coordinator = ClusteringCoordinator(mock_repository)
    coordinator.prepare(_make_fixed_config(k=2))

    # Act
    run = coordinator.cluster(2)

    # Assert
    assert isinstance(run, ClusteringRun)
    assert run.gidx_by_working_index == ids
    assert run.result.k == 2
    total_members = sum(c.size for c in run.result.clusters)
    assert total_members == 6
    # Every member position maps back to one of the real schedule ids.
    all_positions = [w for c in run.result.clusters for w in c.member_indices]
    assert set(run.gidx_for(all_positions)) <= set(ids)


# TC-CC-007
# run_on_schedules() must raise ValueError for an empty schedule list —
# there is nothing in memory to cluster.
def test_run_on_schedules_raises_value_error_for_empty_list(mock_repository):
    # Arrange
    coordinator = ClusteringCoordinator(mock_repository)

    # Act / Assert
    with pytest.raises(ValueError):
        coordinator.run_on_schedules([])


# TC-CC-008
# run_on_schedules() must cluster an in-memory list of ScheduleDTOs without
# touching the repository at all, and return a run whose gidx_by_working_index
# are valid positions into the original list.
def test_run_on_schedules_happy_path_clusters_in_memory_schedules(mock_repository):
    # Arrange
    coordinator = ClusteringCoordinator(mock_repository)
    schedules = [
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: 20.0, AVG_ALL_COURSES_GAP: 15.0,
            ELECTIVE_CONFLICTS: 0.0, MANDATORY_SPAN: 30.0, MAX_EXAMS_PER_DAY: -1.0,
        }),
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: 18.0, AVG_ALL_COURSES_GAP: 14.0,
            ELECTIVE_CONFLICTS: 0.0, MANDATORY_SPAN: 28.0, MAX_EXAMS_PER_DAY: -1.0,
        }),
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: 1.0, AVG_ALL_COURSES_GAP: 1.0,
            ELECTIVE_CONFLICTS: -5.0, MANDATORY_SPAN: 2.0, MAX_EXAMS_PER_DAY: -4.0,
        }),
        ScheduleDTO(scores={
            MIN_MANDATORY_GAP: 0.5, AVG_ALL_COURSES_GAP: 1.5,
            ELECTIVE_CONFLICTS: -6.0, MANDATORY_SPAN: 1.0, MAX_EXAMS_PER_DAY: -5.0,
        }),
    ]

    # Act
    run = coordinator.run_on_schedules(schedules, config=_make_fixed_config(k=2))

    # Assert
    mock_repository.count_scores.assert_not_called()
    mock_repository.read_score_vectors.assert_not_called()
    assert run.result.k == 2
    assert set(run.gidx_by_working_index) <= {0, 1, 2, 3}
    assert sum(c.size for c in run.result.clusters) == 4
