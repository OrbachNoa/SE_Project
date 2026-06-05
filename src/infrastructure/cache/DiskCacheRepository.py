"""Saves and loads the DataCache to a local disk.

It uses 'pickle' because it is very fast for saving and loading Python objects.
"""
from __future__ import annotations

import pickle
from pathlib import Path

from .DataCache import DataCache
from ..repositories.IDataRepository import IDataRepository


class DiskCacheRepository(IDataRepository):
    """Manages the cache file because the system needs a way to store data on the local disk."""

    def __init__(self, cache_path: str | Path = ".cache/data_cache.pkl") -> None:
        """Sets up the repository.
        """
             
        # The file path. We pass it as an argument because it makes testing easier.
        self._cache_path = Path(cache_path)

    @property
    def cache_path(self) -> Path:
        """Returns the file path because other parts of the system might need to know it."""
        return self._cache_path

    def save(self, cache: DataCache) -> None:
        """Saves the cache to a file because we want to keep the data for the next run."""
        
        # Creates parent folders first because the folder path might not exist yet.
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Writes to a temporary file first because we want to prevent a corrupted file 
        # if the app crashes in the middle of writing.
        tmp_path = self._cache_path.with_suffix(self._cache_path.suffix + ".tmp")
        with tmp_path.open("wb") as f:
            pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            
        # Replaces the old file with the new one safely.
        tmp_path.replace(self._cache_path)

    def load(self) -> DataCache | None:
        """Loads the cache from the file because we want to start the app quickly.

        Returns None if the file is missing or bad, because the app should just 
        build new data instead of crashing.
        """
        # Returns None early because there is nothing to load if the file doesn't exist.
        if not self._cache_path.exists():
            return None
            
        try:
            with self._cache_path.open("rb") as f:
                cache = pickle.load(f)
        except (pickle.UnpicklingError, EOFError, OSError, ImportError, AttributeError):
            # Catches errors and returns None because a broken file is exactly like having no file.
            return None
            
        # Checks the type because we want to be 100% sure the loaded data is a real DataCache object.
        if not isinstance(cache, DataCache):
            return None
            
        return cache