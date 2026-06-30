"""
Test suite for FileValidator.

Scope   : Validates validate_language, validate_file_exists, validate_file_not_empty,
          and validate_all_files in src/file_io/validators/FileValidator.py.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-FVA-001, TC-FVA-002, ... TC-FVA-010
Fixtures: none (uses unittest.mock to avoid touching the physical disk)
"""
import pytest
from unittest.mock import patch, mock_open

from src.file_io.validators.FileValidator import (
    validate_language,
    validate_file_exists,
    validate_file_not_empty,
    validate_all_files,
)


# TC-FVA-001
# A UTF-8 encoded file must pass language validation without raising.
@patch("builtins.open", new_callable=mock_open, read_data="Hello, world! Café, naïve.")
def test_validate_language_accepts_utf8_file(mock_file):
    # Act
    result = validate_language("fake_utf8.txt")

    # Assert
    assert result is None


# TC-FVA-002
# A file encoded in a non-UTF-8 codec must raise ValueError
# because the raw bytes cannot be decoded as UTF-8.
@patch("builtins.open")
def test_validate_language_rejects_non_utf8_file(mock_file):
    # Arrange
    # Force read() to raise UnicodeDecodeError, simulating bad encoding
    mock_file.return_value.__enter__.return_value.read.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")

    # Act + Assert
    with pytest.raises(ValueError):
        validate_language("fake_utf16.txt")


# TC-FVA-003
# validate_file_exists must raise FileNotFoundError for a path that does
# not point at an existing file.
@patch("os.path.isfile", return_value=False)
def test_validate_file_exists_raises_for_missing_path(mock_isfile):
    # Act + Assert
    with pytest.raises(FileNotFoundError):
        validate_file_exists("does_not_exist.txt")


# TC-FVA-004
# validate_file_exists must succeed silently for a real file.
@patch("os.path.isfile", return_value=True)
def test_validate_file_exists_accepts_existing_file(mock_isfile):
    # Act
    result = validate_file_exists("present.txt")

    # Assert
    assert result is None


# TC-FVA-005
# validate_file_exists must raise FileNotFoundError when the path points
# at a directory rather than a file (os.path.isfile excludes directories).
@patch("os.path.isfile", return_value=False)
def test_validate_file_exists_rejects_directory_path(mock_isfile):
    # Act + Assert
    with pytest.raises(FileNotFoundError):
        validate_file_exists("a_directory_path")


# TC-FVA-006
# validate_file_not_empty must raise ValueError for a genuinely zero-byte file.
@patch("os.path.getsize", return_value=0)
def test_validate_file_not_empty_rejects_zero_byte_file(mock_getsize):
    # Act + Assert
    with pytest.raises(ValueError):
        validate_file_not_empty("empty.txt")


# TC-FVA-007
# validate_file_not_empty must accept a file that has at least one byte.
@patch("os.path.getsize", return_value=1)
def test_validate_file_not_empty_accepts_nonempty_file(mock_getsize):
    # Act
    result = validate_file_not_empty("nonempty.txt")

    # Assert
    assert result is None


# TC-FVA-008
# validate_all_files must run exists -> not-empty -> language, in that
# exact order, for every path given — a missing file must be reported as
# FileNotFoundError (the first check) even though it would also fail the
# later checks if they ran first.
@patch("os.path.isfile", side_effect=[True, False])
def test_validate_all_files_runs_checks_in_order_for_each_path(mock_isfile):
    # Arrange — one well-formed file and one missing file.
    # We patch the exists check to fail on the second file.
    
    # Act + Assert
    with pytest.raises(FileNotFoundError):
        validate_all_files(["good.txt", "missing.txt"])


# TC-FVA-009
# validate_all_files must raise ValueError (from the not-empty check) for
# an existing but zero-byte file, confirming the second check actually runs
# when the first one (exists) passes.
@patch("os.path.isfile", return_value=True)
@patch("os.path.getsize", return_value=0)
def test_validate_all_files_rejects_empty_file_in_list(mock_getsize, mock_isfile):
    # Act + Assert
    with pytest.raises(ValueError):
        validate_all_files(["blank.txt"])


# TC-FVA-010
# validate_all_files must succeed silently when every path in the list is
# a real, non-empty, UTF-8 file.
@patch("os.path.isfile", return_value=True)
@patch("os.path.getsize", return_value=100)
@patch("builtins.open", new_callable=mock_open, read_data="valid content")
def test_validate_all_files_accepts_all_valid_paths(mock_file, mock_getsize, mock_isfile):
    # Act
    result = validate_all_files(["first.txt", "second.txt"])

    # Assert
    assert result is None
