from typing import List, Optional

from src.application.state.InputDataState import InputDataState
from src.infrastructure.repositories.IDataRepository import IDataRepository
from src.infrastructure.cache.FileChangeDetector import FileChangeDetector
from src.infrastructure.cache.DataCache import DataCache


class InputCacheService:
    """Manages input data cache and determines when re-parsing is needed."""

    def __init__(self, repository: IDataRepository, detector: FileChangeDetector) -> None:
        self._repository = repository
        self._detector = detector

    def try_load(self, paths: List[str]) -> Optional[DataCache]:
        """Loads cache only if it matches the current file set and files haven't changed."""
        cached = self._repository.load()
        if cached is None:
            return None

        # Verify the cached file set matches the current file set exactly
        if set(cached.source_hashes.keys()) != {str(p) for p in paths}:
            return None

        # Check if any file content has changed since cache creation
        if self._detector.has_changed(paths, cached.source_hashes):
            return None

        return cached

    def persist(self, state: InputDataState, paths: List[str]) -> None:
        """Saves the current state as a complete cache snapshot for the loaded files."""
        final = state.to_cache()

        # Compute and store current file hashes for future change detection
        final.source_hashes = self._detector.compute_hashes(paths)

        self._repository.save(final)