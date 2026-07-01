"""Strategy interface for turning a schedule into a numeric feature vector.

Keeping extraction behind an interface means *where the comparable numbers come
from* can change without touching the normalizer, the distance metric, or the
clustering algorithm. The default implementation reuses the five sort scores the
engine already computes for every schedule, but an alternative extractor (raw
dates, a learned embedding, ...) could be dropped in here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.application.dto.ScheduleDTO import ScheduleDTO


class IFeatureExtractor(ABC):
    """Turns one schedule into a comparable feature vector."""

    @abstractmethod
    def extract(self, schedule: ScheduleDTO) -> np.ndarray:
        """Return the feature vector of ``schedule`` as a 1-D float array."""
        raise NotImplementedError

    @abstractmethod
    def feature_names(self) -> list:
        """The names of the produced dimensions, in vector order."""
        raise NotImplementedError
