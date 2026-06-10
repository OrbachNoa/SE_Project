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
        """Return the cached snapshot only when it was built from EXACTLY this
        set of files (same set, all unchanged).

        Requiring set equality — not merely "every path in `paths` is unchanged"
        — is what prevents a snapshot from a previous session (which may carry
        extra UPDATE files) from being returned for a partial set of files
        loaded in the current session. Without this, an UPDATE load could take a
        cache hit and return merged data the user has not actually loaded yet,
        silently skipping the merge.
        """
        cached = self._repository.load()
        if cached is None:
            return None

        # The cached snapshot must describe the same file set we are loading now.
        if set(cached.source_hashes.keys()) != {str(p) for p in paths}:
            return None

        # And every one of those files must be byte-for-byte unchanged.
        if self._detector.has_changed(paths, cached.source_hashes):
            return None

        return cached

    def persist(self, state: InputDataState, paths: List[str]) -> None:
        """Persist the current session's state as a clean, self-contained snapshot.

        `paths` is cumulative within a session — FileImportService tracks every
        file loaded so far — so it already covers the full current state. We
        therefore overwrite the cache outright instead of merging with whatever
        was on disk before.

        The previous implementation merged `source_hashes` with the existing
        cache (`{**existing, **new}`) and carried forward old courses/periods.
        That mixed file sets from different sessions into one snapshot, which let
        a stale UPDATE hit return data that was never loaded this session. A
        clean overwrite keeps the snapshot honest: these files <-> this state.

        Note this is also strictly less work than before: we no longer read and
        unpickle the existing cache from disk on every persist.
        """
        final = state.to_cache()
        final.source_hashes = self._detector.compute_hashes(paths)
        self._repository.save(final)