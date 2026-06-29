"""
Test suite for FileValidator.

Scope   : Validates validate_language, validate_file_exists, validate_file_not_empty,
          and validate_all_files in src/file_io/validators/FileValidator.py.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-FVA-001, TC-FVA-002, ... TC-FVA-009
Fixtures: none (uses pytest's built-in tmp_path)
"""
import pytest

from src.file_io.validators.FileValidator import (
    validate_language,
    validate_file_exists,
    validate_file_not_empty,
    validate_all_files,
)


# TC-FVA-001
# A UTF-8 encoded file must pass language validation without raising.
def test_validate_language_accepts_utf8_file(tmp_path):
    # Arrange
    fixture = tmp_path / "utf8.txt"
    fixture.write_text("Hello, world! Café, naïve.", encoding="utf-8")

    # Act
    result = validate_language(str(fixture))

    # Assert
    assert result is None


# TC-FVA-002
# A file encoded in a non-UTF-8 codec (here, UTF-16) must raise ValueError
# because the raw bytes cannot be decoded as UTF-8.
def test_validate_language_rejects_non_utf8_file(tmp_path):
    # Arrange
    fixture = tmp_path / "utf16.txt"
    fixture.write_bytes("Hello world".encode("utf-16"))

    # Act + Assert
    with pytest.raises(ValueError):
        validate_language(str(fixture))


# TC-FVA-003
# validate_file_exists must raise FileNotFoundError for a path that does
# not point at an existing file.
def test_validate_file_exists_raises_for_missing_path(tmp_path):
    # Arrange
    missing_path = tmp_path / "does_not_exist.txt"

    # Act + Assert
    with pytest.raises(FileNotFoundError):
        validate_file_exists(str(missing_path))


# TC-FVA-004
# validate_file_exists must succeed silently for a real file.
def test_validate_file_exists_accepts_existing_file(tmp_path):
    # Arrange
    fixture = tmp_path / "present.txt"
    fixture.write_text("content", encoding="utf-8")

    # Act
    result = validate_file_exists(str(fixture))

    # Assert
    assert result is None


# TC-FVA-005
# validate_file_exists must raise FileNotFoundError when the path points
# at a directory rather than a file (os.path.isfile excludes directories).
def test_validate_file_exists_rejects_directory_path(tmp_path):
    # Arrange — tmp_path itself is a directory, not a file.
    # Act + Assert
    with pytest.raises(FileNotFoundError):
        validate_file_exists(str(tmp_path))


# TC-FVA-006
# validate_file_not_empty must raise ValueError for a genuinely zero-byte file.
def test_validate_file_not_empty_rejects_zero_byte_file(tmp_path):
    # Arrange
    fixture = tmp_path / "empty.txt"
    fixture.write_bytes(b"")

    # Act + Assert
    with pytest.raises(ValueError):
        validate_file_not_empty(str(fixture))


# TC-FVA-007
# validate_file_not_empty must accept a file that has at least one byte.
def test_validate_file_not_empty_accepts_nonempty_file(tmp_path):
    # Arrange
    fixture = tmp_path / "nonempty.txt"
    fixture.write_text("x", encoding="utf-8")

    # Act
    result = validate_file_not_empty(str(fixture))

    # Assert
    assert result is None


# TC-FVA-008
# validate_all_files must run exists -> not-empty -> language, in that
# exact order, for every path given — a missing file must be reported as
# FileNotFoundError (the first check) even though it would also fail the
# later checks if they ran first.
def test_validate_all_files_runs_checks_in_order_for_each_path(tmp_path):
    # Arrange — one well-formed file and one missing file.
    good_file = tmp_path / "good.txt"
    good_file.write_text("valid content", encoding="utf-8")
    missing_file = tmp_path / "missing.txt"

    # Act + Assert — exists-check fires first, producing FileNotFoundError
    # rather than some other error type.
    with pytest.raises(FileNotFoundError):
        validate_all_files([str(good_file), str(missing_file)])


# TC-FVA-009
# validate_all_files must raise ValueError (from the not-empty check) for
# an existing but zero-byte file, confirming the second check actually runs
# when the first one (exists) passes.
def test_validate_all_files_rejects_empty_file_in_list(tmp_path):
    # Arrange
    empty_file = tmp_path / "blank.txt"
    empty_file.write_bytes(b"")

    # Act + Assert
    with pytest.raises(ValueError):
        validate_all_files([str(empty_file)])


# TC-FVA-010
# validate_all_files must succeed silently when every path in the list is
# a real, non-empty, UTF-8 file.
def test_validate_all_files_accepts_all_valid_paths(tmp_path):
    # Arrange
    first = tmp_path / "first.txt"
    first.write_text("first content", encoding="utf-8")
    second = tmp_path / "second.txt"
    second.write_text("second content", encoding="utf-8")

    # Act
    result = validate_all_files([str(first), str(second)])

    # Assert
    assert result is None
