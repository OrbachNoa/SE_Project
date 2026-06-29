"""
Test suite for InputCacheService.

Scope   : try_load()'s four branches (no cache, mismatched file-set keys,
          detector reports a change, true cache hit) and persist()'s
          serialize-then-save pipeline, including the hashes attached to
          the saved DataCache.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-ICS-001 .. TC-ICS-006
Fixtures: none (collaborators are mocked locally per test)
"""
from unittest.mock import MagicMock

from src.application.services.InputCacheService import InputCacheService
from src.infrastructure.cache.DataCache import DataCache


def _make_service():
    repository = MagicMock()
    detector = MagicMock()
    service = InputCacheService(repository, detector)
    return service, repository, detector


# TC-ICS-001
# try_load() must return None when the repository has no saved cache at all
# — there is nothing to validate or return.
def test_try_load_returns_none_when_repository_has_no_cache():
    # Arrange
    service, repository, detector = _make_service()
    repository.load.return_value = None

    # Act
    result = service.try_load(["courses.xlsx", "periods.xlsx"])

    # Assert
    assert result is None
    detector.has_changed.assert_not_called()


# TC-ICS-002
# try_load() must return None when the cached file-set keys do not exactly
# match the requested paths — a different set of input files invalidates the
# whole cache rather than allowing a partial match.
def test_try_load_returns_none_when_file_set_keys_do_not_match():
    # Arrange
    service, repository, detector = _make_service()
    cached = DataCache(source_hashes={"courses.xlsx": "abc123"})
    repository.load.return_value = cached

    # Act
    result = service.try_load(["courses.xlsx", "periods.xlsx"])

    # Assert
    assert result is None
    detector.has_changed.assert_not_called()


# TC-ICS-003
# try_load() must return None when the detector reports that file content
# has changed since the cache was created, even though the file-set keys
# match exactly.
def test_try_load_returns_none_when_detector_reports_change():
    # Arrange
    service, repository, detector = _make_service()
    cached = DataCache(source_hashes={"courses.xlsx": "abc123", "periods.xlsx": "def456"})
    repository.load.return_value = cached
    detector.has_changed.return_value = True

    # Act
    result = service.try_load(["courses.xlsx", "periods.xlsx"])

    # Assert
    assert result is None
    detector.has_changed.assert_called_once_with(
        ["courses.xlsx", "periods.xlsx"], cached.source_hashes
    )


# TC-ICS-004
# try_load() must return the cached DataCache itself on a true hit: matching
# file-set keys and no detected content change.
def test_try_load_returns_cache_on_true_hit():
    # Arrange
    service, repository, detector = _make_service()
    cached = DataCache(source_hashes={"courses.xlsx": "abc123", "periods.xlsx": "def456"})
    repository.load.return_value = cached
    detector.has_changed.return_value = False

    # Act
    result = service.try_load(["courses.xlsx", "periods.xlsx"])

    # Assert
    assert result is cached


# TC-ICS-005
# try_load() must compare file-set keys using string-normalized paths, so a
# Path object or a plain string requesting the same file still matches the
# cached (string) keys.
def test_try_load_normalizes_path_like_objects_to_strings():
    # Arrange
    from pathlib import Path
    service, repository, detector = _make_service()
    cached = DataCache(source_hashes={"courses.xlsx": "abc123"})
    repository.load.return_value = cached
    detector.has_changed.return_value = False

    # Act
    result = service.try_load([Path("courses.xlsx")])

    # Assert
    assert result is cached


# TC-ICS-006
# persist() must serialize the state via to_cache(), attach the hashes
# computed by the detector for the given paths, and save exactly that
# DataCache through the repository.
def test_persist_serializes_state_and_saves_with_computed_hashes():
    # Arrange
    service, repository, detector = _make_service()
    state = MagicMock()
    serialized = DataCache(courses=[{"courseId": "10101"}], periods=[])
    state.to_cache.return_value = serialized
    detector.compute_hashes.return_value = {"courses.xlsx": "hash-1", "periods.xlsx": "hash-2"}

    # Act
    service.persist(state, ["courses.xlsx", "periods.xlsx"])

    # Assert
    detector.compute_hashes.assert_called_once_with(["courses.xlsx", "periods.xlsx"])
    repository.save.assert_called_once()
    saved_cache = repository.save.call_args[0][0]
    assert saved_cache is serialized
    assert saved_cache.source_hashes == {"courses.xlsx": "hash-1", "periods.xlsx": "hash-2"}
    assert saved_cache.courses == [{"courseId": "10101"}]
