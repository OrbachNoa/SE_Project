import pickle
import pytest
from pathlib import Path
from src.data.DataCache import DataCache
from src.data.DiskCacheRepository import DiskCacheRepository
from src.data.FileChangeDetector import FileChangeDetector

# ===========================================================================
# TC-DATA-001 : Test FileChangeDetector computes SHA-256 hash correctly
# ===========================================================================
def test_file_change_detector_compute_hash(tmp_path):
    # Arrange
    file = tmp_path / "test_file.txt"
    file.write_text("hello world", encoding="utf-8")
    detector = FileChangeDetector()
    
    # Act
    h = detector.compute_hash(file)
    
    # Assert
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert h == expected


# ===========================================================================
# TC-DATA-002: Test that has_changed correctly detects file changes across states.
# ===========================================================================
@pytest.mark.parametrize("state, expected_result", [
    ("initial_run", True),
    ("unchanged", False),
    ("modified", True),
])
def test_file_change_detector_has_changed(tmp_path, state, expected_result):
    # Arrange
    f1 = tmp_path / "f1.txt"
    f1.write_text("content 1", encoding="utf-8")
    f2 = tmp_path / "f2.txt"
    f2.write_text("content 2", encoding="utf-8")
    detector = FileChangeDetector()
    
    # Act
    if state == "initial_run":
        stored_hashes = {}
    elif state == "unchanged":
        stored_hashes = detector.compute_hashes([f1, f2])
    elif state == "modified":
        stored_hashes = detector.compute_hashes([f1, f2])
        f1.write_text("modified content", encoding="utf-8")
        
    changed = detector.has_changed([f1, f2], stored_hashes)
    
    # Assert
    assert changed is expected_result


# ===========================================================================
# TC-DATA-003: Test that DiskCacheRepository returns None when the cache file is missing.
# ===========================================================================
def test_disk_cache_repository_load_missing_file(tmp_path):
    # Arrange
    cache_file = tmp_path / "missing_cache.pkl"
    repo = DiskCacheRepository(cache_file)
    
    # Act
    loaded = repo.load()
    
    # Assert
    assert loaded is None


# ===========================================================================
# TC-DATA-004: Test that DiskCacheRepository successfully saves and loads a valid DataCache.
# ===========================================================================
def test_disk_cache_repository_save_and_load(tmp_path, make_data_cache):
    # Arrange
    cache_file = tmp_path / "nested_dir" / "cache.pkl"
    repo = DiskCacheRepository(cache_file)
    cache = make_data_cache(
        courses=[{"courseId": "10101", "name": "Calc 1"}],
        periods=[{"semester": "FALL", "moed": "ALEPH", "startDate": "2026-06-01", "endDate": "2026-06-30", "excludedDates": []}]
    )
    
    # Act
    repo.save(cache)
    loaded = repo.load()
    
    # Assert
    assert cache_file.exists()
    assert loaded is not None
    assert isinstance(loaded, DataCache)
    assert len(loaded.courses) == 1
    assert loaded.courses[0]["courseId"] == "10101"
    assert loaded.courses[0]["name"] == "Calc 1"
    assert len(loaded.periods) == 1
    assert loaded.periods[0]["semester"] == "FALL"


# ===========================================================================
# TC-DATA-005: Test that DiskCacheRepository returns None when loading invalid or corrupted files.
# ===========================================================================
@pytest.mark.parametrize("corrupt_mode, content", [
    ("invalid_pickle", b"not a pickle object"),
    ("wrong_type", pickle.dumps("just a string")),
    ("empty_file", b""),
])
def test_disk_cache_repository_load_corrupted(tmp_path, corrupt_mode, content):
    # Arrange
    cache_file = tmp_path / "bad_cache.pkl"
    repo = DiskCacheRepository(cache_file)
    
    # Act
    cache_file.write_bytes(content)
    loaded = repo.load()
    
    # Assert
    assert loaded is None


# ===========================================================================
# TC-DATA-006: Test that DiskCacheRepository returns None when file read raises OSError.
# ===========================================================================
def test_disk_cache_repository_load_os_error(tmp_path):
    # Arrange - Create a folder with the same name as the cache file to trigger OSError on read
    cache_path = tmp_path / "cache_dir"
    cache_path.mkdir()
    repo = DiskCacheRepository(cache_path)
    
    # Act
    loaded = repo.load()
    
    # Assert
    assert loaded is None


# ===========================================================================
# TC-DATA-007: Test that DiskCacheRepository defaults to the correct cache path.
# ===========================================================================
def test_disk_cache_repository_default_path():
    # Act
    repo = DiskCacheRepository()
    
    # Assert
    assert repo.cache_path == Path(".cache/data_cache.pkl")


# ===========================================================================
# TC-DATA-008: Test that FileChangeDetector correctly hashes a file larger than the chunk size (64 KB).
# ===========================================================================
def test_file_change_detector_chunked_hashing(tmp_path):
    # Arrange
    file_path = tmp_path / "large_file.bin"
    # Write 70 KB of data (larger than 64 KB chunk size)
    data = b"A" * (70 * 1024)
    file_path.write_bytes(data)
    
    import hashlib
    expected_hash = hashlib.sha256(data).hexdigest()
    
    detector = FileChangeDetector()
    
    # Act
    h = detector.compute_hash(file_path)
    
    # Assert
    assert h == expected_hash


# ===========================================================================
# TC-DATA-009: Test that has_changed detects changes when file lists mismatch.
# ===========================================================================
def test_file_change_detector_has_changed_mismatched_keys(tmp_path):
    # Arrange
    f1 = tmp_path / "f1.txt"
    f1.write_text("content 1", encoding="utf-8")
    f2 = tmp_path / "f2.txt"
    f2.write_text("content 2", encoding="utf-8")
    
    detector = FileChangeDetector()
    stored_hashes = detector.compute_hashes([f1])
    
    # Act (Check when a new file f2 is added to current paths)
    changed_added = detector.has_changed([f1, f2], stored_hashes)
    
    # Act (Check when a file is removed/missing from current paths relative to stored hashes)
    stored_hashes_both = detector.compute_hashes([f1, f2])
    changed_removed = detector.has_changed([f1], stored_hashes_both)
    
    # Assert
    assert changed_added is True
    assert changed_removed is True


# ===========================================================================
# TC-DATA-010: Test that DataCache default fields are correctly initialized.
# ===========================================================================
def test_data_cache_default_values():
    # Act
    cache = DataCache()
    
    # Assert
    assert cache.courses == []
    assert cache.periods == []
    assert cache.source_hashes == {}
    assert isinstance(cache.saved_at, str)
    assert "T" in cache.saved_at
    assert ":" in cache.saved_at
    assert cache.schema_version == 1


# ===========================================================================
# TC-DATA-011: Test that FileChangeDetector raises FileNotFoundError for missing files.
# ===========================================================================
def test_file_change_detector_missing_file(tmp_path):
    # Arrange
    missing_file = tmp_path / "does_not_exist.txt"
    detector = FileChangeDetector()
    
    # Act & Assert
    with pytest.raises(FileNotFoundError):
        detector.compute_hash(missing_file)


# ===========================================================================
# TC-DATA-012: Test that DiskCacheRepository.save raises OSError when writing fails.
# ===========================================================================
def test_disk_cache_repository_save_os_error(tmp_path, make_data_cache):
    # Arrange - Set cache path to a directory itself, which makes file replacement fail
    cache_path = tmp_path / "cache_dir"
    cache_path.mkdir()
    
    repo = DiskCacheRepository(cache_path)
    cache = make_data_cache()
    
    # Act & Assert
    with pytest.raises(OSError):
        repo.save(cache)


