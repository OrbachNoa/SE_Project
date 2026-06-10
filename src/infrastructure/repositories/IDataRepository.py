"""Defines the storage interface for the application data cache.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..cache.DataCache import DataCache


class IDataRepository(ABC):
    """Defines the base rules for data storage because we want to allow different saving methods in the future."""

    @abstractmethod
    def save(self, cache: DataCache) -> None:
        """Saves the current data cache for future application runs."""
        raise NotImplementedError

    @abstractmethod
    def load(self) -> DataCache | None:
        """Loads the saved data cache. 
        Returns None when no saved cache exists, so the application can load 
        the data from the original input files instead.
        """
        raise NotImplementedError