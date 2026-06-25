"""Unit tests for FileImportService's error reporting.

ImportResult keeps `errors: List[str]` for backward compatibility, but every
failure should now also populate `error_details: List[AppErrorInfo]` with the
correct category (INPUT_FILE), via the shared ExceptionMapperRegistry — not a
locally formatted string.
"""
import pytest
from unittest.mock import MagicMock

from src.application.services.FileImportService import FileImportService
from src.application.ImportBoundary import ImportMode
from src.application.errors.ErrorModel import ErrorCategory


@pytest.fixture
def service():
    return FileImportService(
        cache_service=MagicMock(),
        parser_factory=MagicMock(),
        merger=MagicMock(),
        state=MagicMock(),
    )


# ===========================================================================
# TC-FIS-001: a missing file populates error_details with an INPUT_FILE
# AppErrorInfo (FileNotFoundError), alongside the legacy errors string.
# ===========================================================================
def test_missing_file_populates_error_details(service, tmp_path):
    missing = tmp_path / "does_not_exist.txt"

    result = service.load_file(str(missing), "courses", ImportMode.REPLACE)

    assert result.success is False
    assert result.has_errors()
    assert len(result.error_details) == 1
    info = result.error_details[0]
    assert info.category == ErrorCategory.INPUT_FILE
    assert info.code == "INPUT_FILE_NOT_FOUND"
    assert result.errors == [info.user_message]


# ===========================================================================
# TC-FIS-002: an empty file populates error_details with an INPUT_FILE
# AppErrorInfo built from the validator's ValueError, context-steered to
# INPUT_FILE rather than the generic VALIDATION category.
# ===========================================================================
def test_empty_file_populates_error_details_as_input_file(service, tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")

    result = service.load_file(str(empty), "courses", ImportMode.REPLACE)

    assert result.success is False
    info = result.error_details[0]
    assert info.category == ErrorCategory.INPUT_FILE
    assert "empty" in info.user_message.lower()
    assert "Traceback" not in info.user_message


# ===========================================================================
# TC-FIS-003: a parser failure (after validation passes) also populates
# error_details, with the path/file_type recorded in context.
# ===========================================================================
def test_parser_failure_populates_error_details_with_context(service, tmp_path):
    valid_file = tmp_path / "courses.txt"
    valid_file.write_text("some content", encoding="utf-8")
    service._parser_factory.create.return_value.parse.side_effect = ValueError("bad row 3")

    result = service.load_file(str(valid_file), "courses", ImportMode.REPLACE)

    assert result.success is False
    info = result.error_details[0]
    assert info.category == ErrorCategory.INPUT_FILE
    assert info.context["path"] == str(valid_file)
    assert info.context["file_type"] == "courses"


# ===========================================================================
# TC-FIS-004: a successful load leaves error_details empty.
# ===========================================================================
def test_successful_load_has_no_error_details(service, tmp_path):
    valid_file = tmp_path / "courses.txt"
    valid_file.write_text("some content", encoding="utf-8")
    service._parser_factory.create.return_value.parse.return_value = [1, 2, 3]

    result = service.load_file(str(valid_file), "courses", ImportMode.REPLACE)

    assert result.success is True
    assert result.error_details == []
    assert result.errors == []


# ===========================================================================
# TC-FIS-005: a cache-write failure (OSError from persist) must not discard
# data already merged into state — the load still reports success, the
# failure is only logged (graceful degradation, like a broken cache file).
# ===========================================================================
def test_cache_persist_failure_does_not_fail_the_load(service, tmp_path):
    valid_file = tmp_path / "courses.txt"
    valid_file.write_text("some content", encoding="utf-8")
    service._parser_factory.create.return_value.parse.return_value = [1, 2, 3]
    service._cache.persist.side_effect = PermissionError("disk full")
    logged = []
    service._error_logger.log = lambda info, cause=None: logged.append(info)

    result = service.load_file(str(valid_file), "courses", ImportMode.REPLACE)

    assert result.success is True
    assert result.loaded_count == 3
    assert len(logged) == 1
    assert logged[0].category == ErrorCategory.PERSISTENCE


# ===========================================================================
# TC-FIS-006: a cache-read failure (OSError from try_load, e.g. a file
# becoming unreadable mid-check) is treated as a cache miss — the service
# falls through to parsing instead of propagating a raw OSError.
# ===========================================================================
def test_cache_try_load_failure_falls_back_to_parsing(service, tmp_path):
    valid_file = tmp_path / "courses.txt"
    valid_file.write_text("some content", encoding="utf-8")
    service._cache.try_load.side_effect = OSError("file vanished")
    service._parser_factory.create.return_value.parse.return_value = [1, 2]
    logged = []
    service._error_logger.log = lambda info, cause=None: logged.append(info)

    result = service.load_file(str(valid_file), "courses", ImportMode.UPDATE)

    assert result.success is True
    assert result.loaded_count == 2
    assert len(logged) == 1
    assert logged[0].category == ErrorCategory.PERSISTENCE
    service._merger.merge.assert_called_once()


# ===========================================================================
# TC-FIS-007: a PermissionError raised by the parser itself (disk/permission
# fault while reading the file, distinct from a parse-content ValueError)
# is mapped instead of escaping unhandled — success is False, category is
# INPUT_FILE (a read failure, not export), and the message stays clean.
# ===========================================================================
def test_parser_permission_error_populates_error_details_as_input_file(service, tmp_path):
    valid_file = tmp_path / "courses.txt"
    valid_file.write_text("some content", encoding="utf-8")
    service._parser_factory.create.return_value.parse.side_effect = PermissionError(
        13, "denied", str(valid_file)
    )

    result = service.load_file(str(valid_file), "courses", ImportMode.REPLACE)

    assert result.success is False
    assert len(result.error_details) == 1
    info = result.error_details[0]
    assert info.category == ErrorCategory.INPUT_FILE
    assert info.code == "INPUT_FILE_PERMISSION_DENIED"
    assert "Traceback" not in info.user_message
    assert "PermissionError" not in info.user_message
    # It's a read failure, not a write — the message should say so.
    assert "read" in info.user_message.lower()
    assert result.errors == [info.user_message]
