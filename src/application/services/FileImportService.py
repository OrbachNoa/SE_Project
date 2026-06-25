"""Service for importing course and exam-period files into application state."""
from __future__ import annotations

from typing import Dict, Optional

from src.application.state.InputDataState import InputDataState
from src.application.ImportBoundary import ImportMode, ImportResult
from src.file_io.parsers.ParserFactory import ParserFactory
from src.file_io.validators import FileValidator as file_validator
from src.application.services.InputCacheService import InputCacheService
from src.application.services.InputDataMerger import InputDataMerger
from src.application.errors.ErrorModel import ErrorCategory
from src.application.errors.ExceptionMapper import (
    ExceptionMapperRegistry,
    default_registry,
)
from src.application.errors.ErrorLogger import ErrorLogger

class FileImportService:
    """Orchestrates import process: validate → cache? → parse → merge → persist."""

    def __init__(
        self,
        cache_service: InputCacheService,
        parser_factory: ParserFactory,
        merger: InputDataMerger,
        state: InputDataState,
        error_registry: Optional[ExceptionMapperRegistry] = None,
        error_logger: Optional[ErrorLogger] = None,
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
        # Turns parser/validator faults into structured AppErrorInfo records.
        self._errors = error_registry or default_registry()
        self._error_logger = error_logger or ErrorLogger()

    def load_file(self, path: str, file_type: str, mode: ImportMode) -> ImportResult:
        """Main entry point for loading a file. Validates, checks cache, parses, merges, and persists."""
        try:
            file_validator.validate_file_exists(path)
            file_validator.validate_file_not_empty(path)
            file_validator.validate_language(path)
        except (FileNotFoundError, ValueError) as e:
            return self._failure(e, path, file_type)

        # Update loaded paths for this file type. This is used for cache lookup and persistence.
        self._loaded_paths[file_type] = path
        paths = list(self._loaded_paths.values())

        # Cache is only used for UPDATE mode.
        # REPLACE must always parse fresh: the cache stores a merged state that
        # may include data from previous UPDATE sessions, so a cache hit would
        # silently return stale merged data instead of only the new file's data.
        if mode == ImportMode.UPDATE:
            # A read failure while checking the cache (e.g. a file became
            # unreadable between validation and here) is treated as a cache
            # miss rather than a load failure — the parse below recovers it.
            try:
                cached = self._cache.try_load(paths)
            except OSError as e:
                info = self._errors.map(
                    e, {"path": path, "file_type": file_type, "category": ErrorCategory.PERSISTENCE}
                )
                self._error_logger.log(info, cause=e)
                cached = None
            if cached is not None:
                self._state.load_cache(cached)
                return ImportResult(success=True, loaded_count=self._loaded_count(file_type))

        try:
            data = self._parser_factory.create(file_type).parse(path)
        except (FileNotFoundError, ValueError, OSError) as e:
            # Parsing failed (including disk/permission errors reading the
            # file), return a mapped error result without modifying state or
            # cache instead of letting it escape unhandled.
            return self._failure(e, path, file_type)

        self._merger.merge(data, mode, file_type)
        # Persist updated state to cache so future UPDATE loads can skip re-parsing.
        # A write failure here (disk full, permission denied, etc.) must not
        # discard data that was already merged into state — log it through the
        # same mapper as every other failure and degrade gracefully: the next
        # load simply re-parses instead of hitting a fast cache, exactly like
        # DiskCacheRepository.load() already does for a broken cache file.
        try:
            self._cache.persist(self._state, paths)
        except OSError as e:
            info = self._errors.map(
                e, {"path": path, "file_type": file_type, "category": ErrorCategory.PERSISTENCE}
            )
            self._error_logger.log(info, cause=e)

        return ImportResult(success=True, loaded_count=len(data))

    def _failure(self, exc: Exception, path: str, file_type: str) -> ImportResult:
        """Map a load failure to a structured ImportResult (errors stay strings)."""
        info = self._errors.map(
            exc,
            {"path": path, "file_type": file_type, "category": ErrorCategory.INPUT_FILE},
        )
        self._error_logger.log(info, cause=exc)
        return ImportResult.failure(info)

    def _loaded_count(self, file_type: str) -> int:
        """Helper to get count of items by type."""
        if file_type == "periods":
            return len(self._state.get_periods())
        # For any other file type, return the course count.
        return len(self._state.get_courses())