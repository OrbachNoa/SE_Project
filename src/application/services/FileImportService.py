"""Service for importing course and exam-period files into application state."""
from __future__ import annotations

from typing import Dict

from src.application.state.InputDataState import InputDataState
from src.application.ImportBoundary import ImportMode, ImportResult
from src.file_io.parsers.ParserFactory import ParserFactory
from src.file_io.validators import FileValidator as file_validator
from src.application.services.InputCacheService import InputCacheService
from src.application.services.InputDataMerger import InputDataMerger

class FileImportService:
    """Orchestrates import process: validate → cache? → parse → merge → persist."""

    def __init__(
        self,
        cache_service: InputCacheService,
        parser_factory: ParserFactory,
        merger: InputDataMerger,
        state: InputDataState,
    ) -> None:
        # Cache service for storing merged state across UPDATE sessions.
        self._cache = cache_service
        # Factory for creating file parsers.
        self._parser_factory = parser_factory
        # Merger for combining new parsed data with existing state according to import mode.
        self._merger = merger
        # Application state to be updated with imported data.
        self._state = state
        # Tracks loaded file paths by type for caching and validation purposes.
        self._loaded_paths: Dict[str, str] = {}

    def load_file(self, path: str, file_type: str, mode: ImportMode) -> ImportResult:
        """Main entry point for loading a file. Validates, checks cache, parses, merges, and persists."""
        try:
            file_validator.validate_file_exists(path)
            file_validator.validate_file_not_empty(path)
            file_validator.validate_language(path)
        except (FileNotFoundError, ValueError) as e:
            return ImportResult(success=False, loaded_count=0, errors=[str(e)])

        # Update loaded paths for this file type. This is used for cache lookup and persistence.
        self._loaded_paths[file_type] = path
        paths = list(self._loaded_paths.values())

        # Cache is only used for UPDATE mode.
        # REPLACE must always parse fresh: the cache stores a merged state that
        # may include data from previous UPDATE sessions, so a cache hit would
        # silently return stale merged data instead of only the new file's data.
        if mode == ImportMode.UPDATE:
            cached = self._cache.try_load(paths)
            if cached is not None:
                self._state.load_cache(cached)
                return ImportResult(success=True, loaded_count=self._loaded_count(file_type))

        try:
            data = self._parser_factory.create(file_type).parse(path)
        except (FileNotFoundError, ValueError) as e:
            # Parsing failed, return error result without modifying state or cache.
            return ImportResult(success=False, loaded_count=0, errors=[str(e)])

        self._merger.merge(data, mode, file_type)
        # Persist updated state to cache so future UPDATE loads can skip re-parsing.
        self._cache.persist(self._state, paths)

        return ImportResult(success=True, loaded_count=len(data))

    def _loaded_count(self, file_type: str) -> int:
        """Helper to get count of items by type."""
        if file_type == "periods":
            return len(self._state.get_periods())
        # For any other file type, return the course count.
        return len(self._state.get_courses())