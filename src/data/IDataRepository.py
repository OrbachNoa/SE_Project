"""Defines the interface for saving and loading the DataCache.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .DataCache import DataCache


class IDataRepository(ABC):
    """Defines the base rules for data storage because we want to allow different saving methods in the future."""

    @abstractmethod
    def save(self, cache: DataCache) -> None:
        """Saves the cache to storage because the app needs to remember data for the next run."""
        raise NotImplementedError

    @abstractmethod
    def load(self) -> DataCache | None:
        """Loads the cache from storage because the app needs it to start quickly.

        Returns None if there is no data because the app will just create new data from scratch.
        """
        raise NotImplementedError