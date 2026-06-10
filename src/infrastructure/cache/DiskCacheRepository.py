"""Saves and loads the DataCache to a local disk.

It uses 'pickle' because it is very fast for saving and loading Python objects.
"""
from __future__ import annotations

import pickle
from pathlib import Path

from .DataCache import DataCache
from ..repositories.IDataRepository import IDataRepository


class DiskCacheRepository(IDataRepository):
    """Stores the application input-data cache in a local pickle file."""

    def __init__(self, cache_path: str | Path = ".cache/data_cache.pkl") -> None:
        """Creates a disk cache repository with the given cache file path."""
             
        # The path is injectable so tests can use a temporary cache file.
        self._cache_path = Path(cache_path)

    @property
    def cache_path(self) -> Path:
        """Returns the cache file path."""
        return self._cache_path

    def save(self, cache: DataCache) -> None:
        """Saves the DataCache to disk."""
        
        # Create the cache folder if it does not exist yet.
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to a temporary file first.
        # If the app crashes while writing, only the temporary file is damaged.
        # The old cache file stays valid until the new file is fully written.
        tmp_path = self._cache_path.with_suffix(self._cache_path.suffix + ".tmp")
        with tmp_path.open("wb") as f:
            pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            
        # Replace the old cache file only after the temporary file was written successfully.
        tmp_path.replace(self._cache_path)

    def load(self) -> DataCache | None:
        """ 
        Loads the DataCache from disk. 
        Returns None if the cache file is missing, corrupted, or not a valid DataCache. 
        In that case, the app can parse the original input files again.
        """
        # If the cache file does not exist, there is nothing to load.
        if not self._cache_path.exists():
            return None
            
        try:
            with self._cache_path.open("rb") as f:
                cache = pickle.load(f)
        except (pickle.UnpicklingError, EOFError, OSError, ImportError, AttributeError):
            # Treat a broken cache like a missing cache. 
            # The app can rebuild it by parsing the input files again.
            return None
            
        # Make sure the loaded object is really the expected cache type.
        if not isinstance(cache, DataCache):
            return None
            
        return cache