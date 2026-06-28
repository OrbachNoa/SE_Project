"""Default feature extractor: reuse the five scores the engine already computes.

The scheduling worker scores every schedule on the five sort criteria
(MIN_MANDATORY_GAP, AVG_ALL_COURSES_GAP, ELECTIVE_CONFLICTS, MANDATORY_SPAN,
MAX_EXAMS_PER_DAY) and stores them on the DTO (and in SQLite). Those scores are a
ready-made, meaningful description of a schedule's character — so instead of
re-deriving features from raw exam dates (slow, and redundant with work already
done), clustering operates directly on them.

This is the key adaptation from the original prototype, which recomputed
date-based features. Here the feature vector *is* the score vector, which makes
the engine both faster and consistent with how the rest of the app ranks
schedules. The set of criteria used is configurable, so a future "cluster only by
exam spread" request just selects a subset.
"""
from __future__ import annotations

from typing import Dict, Sequence

import numpy as np

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.logic.clustering.IFeatureExtractor import IFeatureExtractor
from src.logic.clustering.ExtendedFeatureComputer import ALL_EXTENDED_FEATURES
from src.logic.comparators.ScheduleScorer import ALL_CRITERIA

_VALID_CRITERIA = set(ALL_CRITERIA) | set(ALL_EXTENDED_FEATURES)


class ScoreFeatureExtractor(IFeatureExtractor):
    """Builds a feature vector from a schedule's precomputed sort scores."""

    def __init__(self, criteria: Sequence[str] | None = None) -> None:
        self._criteria = tuple(criteria) if criteria is not None else ALL_CRITERIA
        unknown = [c for c in self._criteria if c not in _VALID_CRITERIA]
        if unknown:
            raise ValueError(f"unknown criteria: {unknown}")

    def feature_names(self) -> list:
        return list(self._criteria)

    def extract(self, schedule: ScheduleDTO) -> np.ndarray:
        """Pull the selected scores off the schedule, in a fixed order."""
        return self.extract_from_scores(schedule.scores or {})

    def extract_from_scores(self, scores: Dict[str, float]) -> np.ndarray:
        """Same as ``extract`` but from a bare score map.

        Lets the SQLite path build vectors straight from the ``schedule_scores``
        table without materialising a ScheduleDTO at all.
        """
        return np.array(
            [float(scores.get(cid, 0.0)) for cid in self._criteria],
            dtype=float,
        )

    def extract_many(self, schedules: Sequence[ScheduleDTO]) -> np.ndarray:
        """Stack the feature vectors of many schedules into an (n, d) matrix."""
        if not schedules:
            return np.empty((0, len(self._criteria)), dtype=float)
        matrix = np.empty((len(schedules), len(self._criteria)), dtype=float)
        for row_index, schedule in enumerate(schedules):
            scores = schedule.scores or {}
            matrix[row_index, :] = [
                float(scores.get(criterion, 0.0))
                for criterion in self._criteria
            ]
        return matrix

    def extract_many_from_scores(
        self, score_dicts: Sequence[Dict[str, float]]
    ) -> np.ndarray:
        """Stack feature vectors from raw score dicts into an (n, d) matrix.

        This is the fast path used by the SQLite pipeline: score dicts come
        straight from the ``schedule_scores`` table without materialising DTOs.
        """
        if not score_dicts:
            return np.empty((0, len(self._criteria)), dtype=float)
        matrix = np.empty((len(score_dicts), len(self._criteria)), dtype=float)
        for row_index, scores in enumerate(score_dicts):
            matrix[row_index, :] = [
                float(scores.get(criterion, 0.0))
                for criterion in self._criteria
            ]
        return matrix

