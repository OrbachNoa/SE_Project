"""Service for importing course and exam-period files into application state."""
from __future__ import annotations

from typing import Callable, Dict, List

from application.state.InputDataState import InputDataState
from application.ImportMode import ImportMode
from application.ImportResult import ImportResult
from io.parsers.ParserFactory import ParserFactory
from io.validators.ValidatorPipeline import ValidatorPipeline
from io.validators import fileValidator
from infrastructure.repositories.IDataRepository import IDataRepository
from infrastructure.cache.FileChangeDetector import FileChangeDetector


class FileImportService:
    """Loads, validates, and parses input files, then applies them to state."""

    def __init__(
        self,
        repository: IDataRepository,
        detector: FileChangeDetector,
        parser_factory: ParserFactory,
        validators: ValidatorPipeline,
        state: InputDataState,
    ) -> None:
        self._repository = repository
        self._detector = detector
        self._parser_factory = parser_factory
        self._validators = validators
        self._state = state
        # Paths loaded so far, keyed by file_type, so persist hashes the full set
        self._loaded_paths: Dict[str, str] = {}
        # Set when merge changes state, so persist_if_needed writes only when needed
        self._dirty = False

        # Map of import modes to their merge handlers, so merge() can dispatch without if/else or match.
        self._merge_handlers: Dict[ImportMode, Callable[[list], None]] = {
            ImportMode.REPLACE: self._merge_replace,
            ImportMode.UPDATE: self._merge_update,
        }

    def load_file(self, path: str, file_type: str, mode: ImportMode) -> ImportResult:
        """Loads one file and applies it to state, reusing the cache when unchanged."""

        # Validate raw file content first, so a bad path fails cleanly before the
        # detector or parser ever touches it.
        try:
            fileValidator.validate_file_exists(path)
            fileValidator.validate_file_not_empty(path)
            fileValidator.validate_language(path)
        except (FileNotFoundError, ValueError) as e:
            return ImportResult(success=False, loaded_count=0, errors=[str(e)])

        self._loaded_paths[file_type] = path

        # If a cache exists and nothing this service tracks has changed, rebuild
        # from the cache and skip parsing entirely (requirement §5.1).
        cached = self._repository.load()
        if cached is not None and not self._detector.has_changed(
            list(self._loaded_paths.values()), cached.source_hashes
        ):
            self._state.load_cache(cached)
            return ImportResult(success=True, loaded_count=self._loaded_count(file_type))

        # Parse; parser failures also become a result rather than a raise.
        try:
            data = self.parse(path, file_type)
        except (FileNotFoundError, ValueError) as e:
            return ImportResult(success=False, loaded_count=0, errors=[str(e)])

        # Apply the parsed data to the current state
        self.merge(data, mode)

        # Persist to the cache so unchanged sources can skip re-parsing next run
        self.persist_if_needed()

        return ImportResult(success=True, loaded_count=len(data))

    def parse(self, path: str, file_type: str) -> list:
        """Creates the right parser for file_type and parses the file."""
        parser = self._parser_factory.create(file_type)
        return parser.parse(path)

    def merge(self, data: list, mode: ImportMode) -> None:
        """Applies parsed data to state using the handler for the given mode."""
        handler = self._merge_handlers.get(mode)
        if handler is None:
            raise ValueError(f"unsupported import mode: {mode}")
        handler(data)
        self._dirty = True

    def persist_if_needed(self) -> None:
        """Serializes state to a cache and saves it, but only after a change."""
        if not self._dirty:
            return

        # Domain -> dict happens here; stamp the hashes of every loaded source file
        cache = self._state.to_cache()
        cache.source_hashes = self._detector.compute_hashes(list(self._loaded_paths.values()))
        self._repository.save(cache)
        self._dirty = False

    # --- merge handlers ----------------------------------------------------

    def _merge_replace(self, data: list) -> None:
        """REPLACE: overwrite the matching state slice with the new data."""
        if self._is_periods(data):
            self._state.replace_periods(data)
        else:
            self._state.replace_courses(data)

    def _merge_update(self, data: list) -> None:
        """UPDATE: add to existing data without deleting, incoming wins on key."""
        if self._is_periods(data):
            merged = self._merge_periods(self._state.get_periods(), data)
            self._state.replace_periods(merged)
        else:
            merged = self._merge_courses(self._state.get_courses(), data)
            self._state.replace_courses(merged)

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _is_periods(data: list) -> bool:
        """True when the data is exam periods (only periods carry a moed)."""
        return bool(data) and hasattr(data[0], "moed")

    @staticmethod
    def _merge_courses(existing: List, incoming: List) -> List:
        """Merges incoming courses over existing; incoming takes precedence on conflicts."""
        by_id = {c.courseId: c for c in existing}
        for c in incoming:
            by_id[c.courseId] = c
        return list(by_id.values())

    @staticmethod
    def _merge_periods(existing: List, incoming: List) -> List:
        """Merges incoming periods over existing; incoming takes precedence on (semester, moed)."""
        by_key = {(p.semester, p.moed): p for p in existing}
        for p in incoming:
            by_key[(p.semester, p.moed)] = p
        return list(by_key.values())

    def _loaded_count(self, file_type: str) -> int:
        """Count of items in state for the given file type (for cache-hit results)."""
        if file_type == "periods":
            return len(self._state.get_periods())
        return len(self._state.get_courses())