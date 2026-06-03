from __future__ import annotations
from typing import List, Tuple

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from infrastructure.repositories.IDataRepository import IDataRepository
from infrastructure.cache.FileChangeDetector import FileChangeDetector
from application.state.input_data_state import InputDataState


class CachedInputLoader:
    """Loads courses and periods, utilizing a cache to avoid redundant parsing when files are unchanged."""

    def __init__(
        self,
        repository: IDataRepository,
        detector: FileChangeDetector,
        course_parser,
        period_parser,
    ) -> None:
        """Initializes the loader with a storage repository, change detection, and file parsers."""
        self._repository = repository
        self._detector = detector
        self._course_parser = course_parser
        self._period_parser = period_parser

    def load(
        self, courses_path: str, periods_path: str
    ) -> Tuple[List[Course], List[ExamPeriod]]:
        """Returns parsed courses and periods, either from cache or by parsing the source files."""

        source_paths = [courses_path, periods_path]
        
        # Attempt to load existing cache from the repository
        cache = self._repository.load()

        # If cache exists and source files haven't changed, rebuild domain objects and skip parsing
        if cache is not None and not self._detector.has_changed(source_paths, cache.source_hashes):
            state = InputDataState()
            state.load_cache(cache)
            return state.get_courses(), state.get_periods()

        # If cache is missing or files are stale, parse the files normally
        courses = self._course_parser.parse(courses_path)
        periods = self._period_parser.parse(periods_path)

        # Update the cache with the newly parsed data and current file hashes for future runs
        state = InputDataState()
        state.replace_courses(courses)
        state.replace_periods(periods)
        new_cache = state.to_cache()
        new_cache.source_hashes = self._detector.compute_hashes(source_paths)
        self._repository.save(new_cache)

        return courses, periods