from typing import List, Optional
from src.application.state.InputDataState import InputDataState
from src.infrastructure.repositories.IDataRepository import IDataRepository
from src.infrastructure.cache.FileChangeDetector import FileChangeDetector
from src.infrastructure.cache.DataCache import DataCache


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
        """Serializes state to cache, merging with any previously cached data.

        When the user loads files one at a time, the state only contains the data
        loaded so far. A naive overwrite would erase cached data for files not yet
        loaded in this session. Instead we:
          1. Merge source_hashes: existing entries are kept, new ones override.
          2. Preserve courses/periods from the existing cache when the current
             state does not yet have them (i.e. that file type has not been loaded
             this session). Note: file validators reject empty files before persist
             is ever called, so an empty list in state genuinely means "not loaded".
        """
        existing = self._repository.load()
        new_hashes = self._detector.compute_hashes(paths)

        final = state.to_cache()

        if existing is not None:
            # Keep all previously stored hashes; overwrite only the ones just updated.
            final.source_hashes = {**existing.source_hashes, **new_hashes}

            # Carry forward cached courses/periods that are absent from the current state.
            if not final.courses and existing.courses:
                final.courses = existing.courses
            if not final.periods and existing.periods:
                final.periods = existing.periods
        else:
            final.source_hashes = new_hashes

        self._repository.save(final)