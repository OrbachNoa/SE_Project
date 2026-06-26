"""Unit tests for the clustering feature pipeline: score extraction and normalization.

Covers ScoreFeatureExtractor (building feature vectors from a schedule's
precomputed sort scores, including default criteria, missing-score handling,
batch extraction, and rejection of unknown criteria) and FeatureNormalizer
(min-max rescaling to [0, 1], constant-column safety, projecting new vectors
onto a previously fitted scale, and guarding against use-before-fit or
fitting on empty data).

This file owns TC-CLU-001..010, the first quarter of a single numbered test
family shared across four sibling files that each exercise a different layer
of the clustering subsystem: this file (TC-CLU-001..010, feature extraction
and normalization), Test_ClusteringDistanceMetrics.py (TC-CLU-011..016,
distance metrics), Test_ClusteringAlgorithms.py (TC-CLU-017..027, clustering
algorithms), and Test_ClusteringService.py (TC-CLU-028..032, the clustering
service facade). The shared prefix and continuous numbering let the family be
read as one coherent suite despite living in separate files.

Every test body follows Arrange/Act/Assert. None of the shared factory
fixtures defined in tests/conftest.py apply here: this file's collaborators
(ScheduleDTO, ScoreFeatureExtractor, FeatureNormalizer, numpy arrays) are
plain, cheap-to-construct objects, so each test builds its own inputs
directly in the Arrange section instead of going through a fixture.
"""
import numpy as np
import pytest

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.logic.clustering.ScoreFeatureExtractor import ScoreFeatureExtractor
from src.logic.clustering.FeatureNormalizer import FeatureNormalizer
from src.logic.comparators.ScheduleScorer import (
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
)


# ---------------------------------------------------------------------------
# ScoreFeatureExtractor TC-CLU-001..005
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CLU-001: extract() pulls the configured criteria off a ScheduleDTO, in
# the order the extractor was built with, ignoring any other stored scores.
# ===========================================================================
def test_score_feature_extractor_extracts_scores_in_criteria_order():
    # Arrange
    extractor = ScoreFeatureExtractor([MANDATORY_SPAN, MIN_MANDATORY_GAP])
    schedule = ScheduleDTO(
        scores={MANDATORY_SPAN: 10.0, MIN_MANDATORY_GAP: 5.0, AVG_ALL_COURSES_GAP: 99.0}
    )

    # Act
    vector = extractor.extract(schedule)

    # Assert
    assert vector.tolist() == [10.0, 5.0]


# ===========================================================================
# TC-CLU-002: extract() defaults a criterion missing from the schedule's
# score map to 0.0, rather than raising.
# ===========================================================================
def test_score_feature_extractor_defaults_missing_criterion_to_zero():
    # Arrange
    extractor = ScoreFeatureExtractor([MANDATORY_SPAN, ELECTIVE_CONFLICTS])
    schedule = ScheduleDTO(scores={MANDATORY_SPAN: 7.0})

    # Act
    vector = extractor.extract(schedule)

    # Assert
    assert vector.tolist() == [7.0, 0.0]


# ===========================================================================
# TC-CLU-003: with no criteria given, the extractor defaults to every
# criterion in ScheduleScorer.ALL_CRITERIA, in canonical order.
# ===========================================================================
def test_score_feature_extractor_defaults_to_all_criteria():
    # Arrange
    extractor = ScoreFeatureExtractor()

    # Act
    names = extractor.feature_names()

    # Assert
    assert names == [
        MIN_MANDATORY_GAP,
        AVG_ALL_COURSES_GAP,
        ELECTIVE_CONFLICTS,
        MANDATORY_SPAN,
        MAX_EXAMS_PER_DAY,
    ]


# ===========================================================================
# TC-CLU-004: extract_many() stacks each schedule's vector into an (n, d)
# matrix, preserving the input order.
# ===========================================================================
def test_score_feature_extractor_extract_many_stacks_vectors():
    # Arrange
    extractor = ScoreFeatureExtractor([MANDATORY_SPAN])
    schedules = [
        ScheduleDTO(scores={MANDATORY_SPAN: 1.0}),
        ScheduleDTO(scores={MANDATORY_SPAN: 2.0}),
    ]

    # Act
    matrix = extractor.extract_many(schedules)

    # Assert
    assert matrix.shape == (2, 1)
    assert matrix.tolist() == [[1.0], [2.0]]


# ===========================================================================
# TC-CLU-005: constructing the extractor with an unrecognized criterion id
# raises ValueError instead of silently extracting garbage.
# ===========================================================================
def test_score_feature_extractor_rejects_unknown_criterion():
    # Arrange
    bad_criteria = ["NOT_A_REAL_CRITERION"]

    # Act
    # Assert
    with pytest.raises(ValueError):
        ScoreFeatureExtractor(bad_criteria)


# ---------------------------------------------------------------------------
# FeatureNormalizer TC-CLU-006..010
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-CLU-006: fit_transform() rescales every column to exactly [0, 1] based
# on the population's own min and max.
# ===========================================================================
def test_feature_normalizer_scales_to_zero_one_range():
    # Arrange
    matrix = np.array([[0.0, 10.0], [5.0, 20.0], [10.0, 30.0]])
    normalizer = FeatureNormalizer()

    # Act
    result = normalizer.fit_transform(matrix)

    # Assert
    assert result.tolist() == [[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]]


# ===========================================================================
# TC-CLU-007: a constant column (min == max) maps to a constant 0.0 instead
# of dividing by zero or producing NaN.
# ===========================================================================
def test_feature_normalizer_handles_constant_column_without_division_by_zero():
    # Arrange
    matrix = np.array([[5.0, 1.0], [5.0, 2.0], [5.0, 3.0]])
    normalizer = FeatureNormalizer()

    # Act
    result = normalizer.fit_transform(matrix)

    # Assert
    assert result[:, 0].tolist() == [0.0, 0.0, 0.0]
    assert not np.isnan(result).any()


# ===========================================================================
# TC-CLU-008: transform_one() projects a single new vector onto the scale
# learned by a prior fit(), not a scale fitted on the vector itself.
# ===========================================================================
def test_feature_normalizer_transform_one_uses_the_fitted_scale():
    # Arrange
    matrix = np.array([[0.0], [10.0]])
    normalizer = FeatureNormalizer().fit(matrix)

    # Act
    result = normalizer.transform_one(np.array([5.0]))

    # Assert
    assert result.tolist() == [0.5]


# ===========================================================================
# TC-CLU-009: calling transform() before fit() raises RuntimeError rather
# than operating on an unset scale.
# ===========================================================================
def test_feature_normalizer_raises_when_used_before_fit():
    # Arrange
    normalizer = FeatureNormalizer()

    # Act
    # Assert
    with pytest.raises(RuntimeError):
        normalizer.transform(np.array([[1.0]]))


# ===========================================================================
# TC-CLU-010: fitting on an empty matrix raises ValueError instead of
# producing a normalizer with no usable scale.
# ===========================================================================
def test_feature_normalizer_rejects_an_empty_matrix():
    # Arrange
    normalizer = FeatureNormalizer()
    empty_matrix = np.empty((0, 2))

    # Act
    # Assert
    with pytest.raises(ValueError):
        normalizer.fit(empty_matrix)
