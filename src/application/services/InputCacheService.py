from typing import List, Optional
from application.state.InputDataState import InputDataState
from infrastructure.repositories.IDataRepository import IDataRepository
from infrastructure.cache.FileChangeDetector import FileChangeDetector
from infrastructure.cache.DataCache import DataCache


class InputCacheService:
    """Loads and saves the on-disk cache; decides when a re-parse is needed."""

    def __init__(self, repository: IDataRepository, detector: FileChangeDetector) -> None:
        self._repository = repository
        self._detector = detector

    def try_load(self, paths: List[str]) -> Optional[DataCache]:
        """Returns cached DataCache if source files are unchanged, otherwise None."""
        cached = self._repository.load()
        if cached is not None and not self._detector.has_changed(paths, cached.source_hashes):
            return cached
        return None

    def persist(self, state: InputDataState, paths: List[str]) -> None:
        """Serializes state to cache and stamps current file hashes."""
        cache = state.to_cache()
        cache.source_hashes = self._detector.compute_hashes(paths)
        self._repository.save(cache)