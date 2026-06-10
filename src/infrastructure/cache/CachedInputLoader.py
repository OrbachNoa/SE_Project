from __future__ import annotations
from typing import List, Tuple

from src.models.Course import Course
from src.models.ExamPeriod import ExamPeriod
from src.infrastructure.repositories.IDataRepository import IDataRepository
from src.infrastructure.cache.FileChangeDetector import FileChangeDetector
from src.application.state.InputDataState import InputDataState


class CachedInputLoader:
    """Loads input data from cache when the original files did not change."""

    def __init__(
        self,
        repository: IDataRepository,
        detector: FileChangeDetector,
        course_parser,
        period_parser,
    ) -> None:
        """Creates a loader with cache storage, file change detection, and parsers."""
        self._repository = repository
        self._detector = detector
        self._course_parser = course_parser
        self._period_parser = period_parser

    def load(
        self, courses_path: str, periods_path: str
    ) -> Tuple[List[Course], List[ExamPeriod]]:
        """Loads courses and exam periods from cache or from the original files."""

        # These are the source input files that the cache depends on.
        source_paths = [courses_path, periods_path]
        
        # Try to load previously parsed input data from storage.
        cache = self._repository.load()

        # If a cache exists and the input files are unchanged, 
        # reuse the parsed data instead of parsing the files again.
        if cache is not None and not self._detector.has_changed(source_paths, cache.source_hashes):
            state = InputDataState()
            state.load_cache(cache)
            return state.get_courses(), state.get_periods()

        # If there is no cache, or the files changed, parse the original files again.
        courses = self._course_parser.parse(courses_path)
        periods = self._period_parser.parse(periods_path)

        # Store the newly parsed data in the application state.
        state = InputDataState()
        state.replace_courses(courses)
        state.replace_periods(periods)
        # Create a new cache and save the current file hashes with it. 
        # The hashes let us know next time whether these files changed.
        new_cache = state.to_cache()
        new_cache.source_hashes = self._detector.compute_hashes(source_paths)
        # Save the parsed input data for future runs.
        self._repository.save(new_cache)

        return courses, periods
