"""Service for importing course and exam-period files into application state."""
from __future__ import annotations

from typing import Callable, Dict, List

from src.application.state.InputDataState import InputDataState
from src.application.ImportBoundary import ImportMode, ImportResult
from src.file_io.parsers.ParserFactory import ParserFactory
from src.file_io.validators.ValidatorPipeline import ValidatorPipeline
from src.file_io.validators import FileValidator as file_validator
from src.application.services.InputCacheService import InputCacheService
from src.application.services.InputDataMerger import InputDataMerger

class FileImportService:
    """Orchestrates import: validate → cache? → parse → merge → persist."""

    def __init__(
        self,
        cache_service: InputCacheService,
        parser_factory: ParserFactory,
        validators: ValidatorPipeline,
        merger: InputDataMerger,
        state: InputDataState,
    ) -> None:
        self._cache = cache_service
        self._parser_factory = parser_factory
        self._validators = validators
        self._merger = merger
        self._state = state
        self._loaded_paths: Dict[str, str] = {}

    def load_file(self, path: str, file_type: str, mode: ImportMode) -> ImportResult:
        try:
            file_validator.validate_file_exists(path)
            file_validator.validate_file_not_empty(path)
            file_validator.validate_language(path)
        except (FileNotFoundError, ValueError) as e:
            return ImportResult(success=False, loaded_count=0, errors=[str(e)])

        self._loaded_paths[file_type] = path
        paths = list(self._loaded_paths.values())

        cached = self._cache.try_load(paths)
        if cached is not None:
            self._state.load_cache(cached)
            return ImportResult(success=True, loaded_count=self._loaded_count(file_type))

        try:
            data = self._parser_factory.create(file_type).parse(path)
        except (FileNotFoundError, ValueError) as e:
            return ImportResult(success=False, loaded_count=0, errors=[str(e)])

        self._merger.merge(data, mode)
        self._cache.persist(self._state, paths)

        return ImportResult(success=True, loaded_count=len(data))

    def _loaded_count(self, file_type: str) -> int:
        if file_type == "periods":
            return len(self._state.get_periods())
        return len(self._state.get_courses())
