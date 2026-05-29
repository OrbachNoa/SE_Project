"""Service for importing course and exam-period files into application state.

The service validates the file, parses it, and applies the results to state per the requested mode (replace or update).,
which includes success.
"""
from __future__ import annotations

from typing import List

from src.application.app_state import AppState
from src.application.import_mode import ImportMode
from src.application.import_result import ImportResult
from src.parsers.courseParser import CoursesFileParser
from src.parsers.dateParser import ExamPeriodsFileParser
from src.validators import fileValidator


class FileImportService:
    """Parses input files and writes the results into the application state."""

    def __init__(
        self,
        course_parser: CoursesFileParser,
        period_parser: ExamPeriodsFileParser,
        app_state: AppState,
    ) -> None:
        self._course_parser = course_parser
        self._period_parser = period_parser
        self._app_state = app_state

    def import_courses(self, path: str, mode: ImportMode) -> ImportResult:
        """Load courses from path and apply them to state per mode."""
        return self._import(path, mode, self._course_parser.parse, self._apply_courses)

    def import_periods(self, path: str, mode: ImportMode) -> ImportResult:
        """Load exam periods from path and apply them to state per mode."""
        return self._import(path, mode, self._period_parser.parse, self._apply_periods)

    def _import(self, path, mode, parse_fn, apply_fn) -> ImportResult:
        """Shared logic for importing courses or periods: validate, parse, apply, and report."""
        try:
            fileValidator.validate_file_exists(path)
            fileValidator.validate_file_not_empty(path)
            fileValidator.validate_language(path)
            parsed = parse_fn(path)
        except (FileNotFoundError, ValueError) as e:
            return ImportResult(success=False, loaded_count=0, errors=[str(e)])

        apply_fn(parsed, mode)
        return ImportResult(success=True, loaded_count=len(parsed))

    def _apply_courses(self, courses: List, mode: ImportMode) -> None:
        """Writes courses into state, replacing or merging with existing per mode."""
        input_state = self._app_state.get_input_state()
        if mode is ImportMode.REPLACE:
            input_state.replace_courses(courses)
        else:
            input_state.replace_courses(self._merge_courses(input_state.get_courses(), courses))

    def _apply_periods(self, periods: List, mode: ImportMode) -> None:
        """Writes exam periods into state, replacing or merging with existing per mode."""
        input_state = self._app_state.get_input_state()
        if mode is ImportMode.REPLACE:
            input_state.replace_periods(periods)
        else:
            input_state.replace_periods(self._merge_periods(input_state.get_periods(), periods))

    @staticmethod
    def _merge_courses(existing: List, incoming: List) -> List:
        """Merge incoming courses over existing, incoming wins on duplicate courseId."""
        by_id = {c.courseId: c for c in existing}
        for c in incoming:
            by_id[c.courseId] = c
        return list(by_id.values())

    @staticmethod
    def _merge_periods(existing: List, incoming: List) -> List:
        """Merge incoming periods over existing, incoming wins on (semester, moed)."""
        by_key = {(p.semester, p.moed): p for p in existing}
        for p in incoming:
            by_key[(p.semester, p.moed)] = p
        return list(by_key.values())