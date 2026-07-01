"""
Test suite for CachedInputLoader.

Scope   : Input loader's cache-hit and cache-miss/changed logic, confirming
          it parses files only when necessary and updates the cache.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CIL-001, TC-CIL-002, TC-CIL-003
Fixtures: make_course, make_period
"""
from unittest.mock import MagicMock

from src.infrastructure.cache.CachedInputLoader import CachedInputLoader
from src.application.state.InputDataState import InputDataState


# TC-CIL-001
# Verifies that when a cache exists and files are unchanged, the loader returns
# the cached data and does not invoke the parsers.
def test_load_returns_cache_when_files_unchanged(make_course, make_period):
    # Arrange
    course = make_course("10101")
    period = make_period()

    mock_repo = MagicMock()
    state = InputDataState()
    state.replace_courses([course])
    state.replace_periods([period])
    fake_cache = state.to_cache()
    fake_cache.source_hashes = {"courses.txt": "hash1", "periods.txt": "hash2"}
    mock_repo.load.return_value = fake_cache

    mock_detector = MagicMock()
    # has_changed returns False -> cache is valid
    mock_detector.has_changed.return_value = False

    mock_course_parser = MagicMock()
    mock_period_parser = MagicMock()

    loader = CachedInputLoader(
        repository=mock_repo,
        detector=mock_detector,
        course_parser=mock_course_parser,
        period_parser=mock_period_parser
    )

    # Act
    courses, periods = loader.load("courses.txt", "periods.txt")

    # Assert
    assert len(courses) == 1
    assert courses[0].courseId == course.courseId
    assert len(periods) == 1
    assert periods[0].semester == period.semester
    # Parsers must not be called
    mock_course_parser.parse.assert_not_called()
    mock_period_parser.parse.assert_not_called()
    # Cache must not be overwritten
    mock_repo.save.assert_not_called()


# TC-CIL-002
# Verifies that when no cache exists, the loader parses the files, builds a
# new cache with file hashes, and saves it.
def test_load_parses_files_and_saves_cache_when_no_cache_exists(make_course, make_period):
    # Arrange
    course = make_course("10101")
    period = make_period()

    mock_repo = MagicMock()
    mock_repo.load.return_value = None  # No cache exists

    mock_detector = MagicMock()
    mock_detector.compute_hashes.return_value = {"courses.txt": "newhash1", "periods.txt": "newhash2"}

    mock_course_parser = MagicMock()
    mock_course_parser.parse.return_value = [course]

    mock_period_parser = MagicMock()
    mock_period_parser.parse.return_value = [period]

    loader = CachedInputLoader(
        repository=mock_repo,
        detector=mock_detector,
        course_parser=mock_course_parser,
        period_parser=mock_period_parser
    )

    # Act
    courses, periods = loader.load("courses.txt", "periods.txt")

    # Assert
    assert courses == [course]
    assert periods == [period]

    mock_course_parser.parse.assert_called_once_with("courses.txt")
    mock_period_parser.parse.assert_called_once_with("periods.txt")

    # Verify the new cache was saved with the correct hashes
    mock_repo.save.assert_called_once()
    saved_cache = mock_repo.save.call_args[0][0]
    assert saved_cache.courses[0]["courseId"] == course.courseId
    assert saved_cache.periods[0]["semester"] == period.semester.value
    assert saved_cache.source_hashes == {"courses.txt": "newhash1", "periods.txt": "newhash2"}


# TC-CIL-003
# Verifies that when a cache exists but the files HAVE changed, the loader
# discards the cache, parses the files, and saves the updated cache.
def test_load_parses_files_and_saves_cache_when_files_changed(make_course, make_period):
    # Arrange
    old_course = make_course("10101")
    new_course = make_course("10102")
    period = make_period()

    state = InputDataState()
    state.replace_courses([old_course])
    state.replace_periods([])
    fake_cache = state.to_cache()
    fake_cache.source_hashes = {"courses.txt": "oldhash1", "periods.txt": "oldhash2"}
    mock_repo = MagicMock()
    mock_repo.load.return_value = fake_cache

    mock_detector = MagicMock()
    # has_changed returns True -> cache is invalid
    mock_detector.has_changed.return_value = True
    mock_detector.compute_hashes.return_value = {"courses.txt": "newhash1", "periods.txt": "newhash2"}

    mock_course_parser = MagicMock()
    mock_course_parser.parse.return_value = [new_course]

    mock_period_parser = MagicMock()
    mock_period_parser.parse.return_value = [period]

    loader = CachedInputLoader(
        repository=mock_repo,
        detector=mock_detector,
        course_parser=mock_course_parser,
        period_parser=mock_period_parser
    )

    # Act
    courses, periods = loader.load("courses.txt", "periods.txt")

    # Assert
    assert courses == [new_course]
    assert periods == [period]

    mock_course_parser.parse.assert_called_once_with("courses.txt")
    mock_period_parser.parse.assert_called_once_with("periods.txt")

    # Verify the cache was updated
    mock_repo.save.assert_called_once()
    saved_cache = mock_repo.save.call_args[0][0]
    assert saved_cache.courses[0]["courseId"] == new_course.courseId
    assert saved_cache.periods[0]["semester"] == period.semester.value
    assert saved_cache.source_hashes == {"courses.txt": "newhash1", "periods.txt": "newhash2"}
