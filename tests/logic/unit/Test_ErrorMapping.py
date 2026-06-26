"""Unit tests for the core exception -> AppErrorInfo mapping rules.

These cover the boundary mapping rules from the error-handling architecture:
how individual raw exceptions (MemoryError, PermissionError, parser
ValueError, the domain InfeasibleScheduleError, FileNotFoundError, and
anything unknown) become an AppErrorInfo with the right category / severity /
recoverable flag and a stable code, plus the supporting value-object and
registry mechanics (AppErrorInfo defaults/round-trip, mapper ordering,
registry extensibility).

This file was split from a single, larger error-mapping test file once it
grew past the project's per-file line limit. Context-driven behavior — how a
caller's context dict can steer category/severity/message wording, and
build_process_error_payload — lives in Test_ErrorMappingContext.py.

Conventions:
- Each test carries a unique TC-ERR-NNN identifier in the comment block above
  its definition, numbered sequentially within this file.
- Each test body is split into Arrange / Act / Assert sections.
- The `registry` fixture is local to this file (default_registry()); no
  conftest fixture models the error registry.
"""
import pytest

from src.application.errors import (
    AppErrorInfo,
    ErrorCategory,
    ErrorSeverity,
    ResourceExhaustedError,
    ExportApplicationError,
    default_registry,
)
from src.application.errors.ExceptionMapper import ExceptionMapperRegistry
from src.logic.feasibility.InfeasibleScheduleError import InfeasibleScheduleError


@pytest.fixture
def registry() -> ExceptionMapperRegistry:
    return default_registry()


# ===========================================================================
# TC-ERR-001: MemoryError -> RESOURCE / CRITICAL / non-recoverable.
# ===========================================================================
def test_error_mapping_memory_error_maps_to_resource_critical(registry):
    # Arrange
    error = MemoryError("oom")

    # Act
    info = registry.map(error)

    # Assert
    assert info.category == ErrorCategory.RESOURCE
    assert info.severity == ErrorSeverity.CRITICAL
    assert info.recoverable is False
    assert info.code == "RESOURCE_MEMORY_EXHAUSTED"


# ===========================================================================
# TC-ERR-002: PermissionError -> EXPORT with a friendly, file-aware message.
# ===========================================================================
def test_error_mapping_permission_error_maps_to_export_with_friendly_message(registry):
    # Arrange
    error = PermissionError(13, "denied", "report.xlsx")

    # Act
    info = registry.map(error)

    # Assert
    assert info.category == ErrorCategory.EXPORT
    assert info.code == "EXPORT_PERMISSION_DENIED"
    assert "report.xlsx" in info.user_message
    assert "Traceback" not in info.user_message


# ===========================================================================
# TC-ERR-003: a parser/validator ValueError -> VALIDATION, message preserved.
# ===========================================================================
def test_error_mapping_value_error_from_parser_maps_to_validation(registry):
    # Arrange
    error = ValueError("Row 3: invalid date")

    # Act
    info = registry.map(error)

    # Assert
    assert info.category == ErrorCategory.VALIDATION
    assert info.severity == ErrorSeverity.WARNING
    # The validator already phrases this for humans; keep its text.
    assert info.user_message == "Row 3: invalid date"


# ===========================================================================
# TC-ERR-004: an unknown exception -> the UNEXPECTED fallback (never leaks).
# ===========================================================================
def test_error_mapping_unknown_exception_maps_to_unexpected_fallback(registry):
    # Arrange
    error = KeyError("surprise")

    # Act
    info = registry.map(error)

    # Assert
    assert info.category == ErrorCategory.UNEXPECTED
    assert info.code == "UNEXPECTED_ERROR"
    assert info.user_message  # always something to show the user


# ===========================================================================
# TC-ERR-005: the domain InfeasibleScheduleError -> a clean, recoverable message.
# ===========================================================================
def test_error_mapping_infeasible_schedule_maps_to_clean_recoverable_message(registry):
    # Arrange
    error = InfeasibleScheduleError(["too many exams in June"])

    # Act
    info = registry.map(error)

    # Assert
    assert info.category == ErrorCategory.SCHEDULING
    assert info.severity == ErrorSeverity.WARNING
    assert info.recoverable is True
    assert "too many exams in June" in info.user_message
    assert "Traceback" not in info.user_message


# ===========================================================================
# TC-ERR-006: an ApplicationError passes its own info through unchanged (LSP).
# ===========================================================================
def test_error_mapping_application_error_passes_through_its_info(registry):
    # Arrange
    raised = ResourceExhaustedError("custom", code="RESOURCE_MEMORY_EXHAUSTED")

    # Act
    info = registry.map(raised)

    # Assert
    assert info is raised.info
    assert info.recoverable is False


# ===========================================================================
# TC-ERR-007: ordering — PermissionError is EXPORT, not the generic OSError path.
# ===========================================================================
def test_error_mapping_permission_error_beats_generic_oserror(registry):
    # Arrange
    # PermissionError is an OSError subclass; the specific mapper must win.
    error = PermissionError("locked")

    # Act
    info = registry.map(error)

    # Assert
    assert info.code == "EXPORT_PERMISSION_DENIED"


# ===========================================================================
# TC-ERR-008: AppErrorInfo survives a serialise/deserialise round-trip (IPC).
# ===========================================================================
def test_error_mapping_app_error_info_payload_round_trip():
    # Arrange
    info = AppErrorInfo(
        code="X",
        category=ErrorCategory.SCHEDULING,
        severity=ErrorSeverity.ERROR,
        user_message="u",
        technical_message="t",
        recoverable=False,
        context={"k": 1},
    )

    # Act
    restored = AppErrorInfo.from_payload(info.to_payload())

    # Assert
    assert restored == info


# ===========================================================================
# TC-ERR-009: technical_message defaults to the user message when omitted.
# ===========================================================================
def test_error_mapping_technical_message_defaults_to_user_message():
    # Arrange

    # Act
    info = AppErrorInfo(
        code="X",
        category=ErrorCategory.EXPORT,
        severity=ErrorSeverity.ERROR,
        user_message="please retry",
    )

    # Assert
    assert info.technical_message == "please retry"


# ===========================================================================
# TC-ERR-010: a custom mapper extends the registry without editing it (OCP).
# ===========================================================================
def test_error_mapping_registry_is_extensible_with_a_custom_mapper():
    # Arrange
    class _ZeroDivMapper:
        def can_handle(self, exc):
            return isinstance(exc, ZeroDivisionError)

        def map(self, exc, context):
            return AppErrorInfo(
                code="MATH",
                category=ErrorCategory.UNEXPECTED,
                severity=ErrorSeverity.ERROR,
                user_message="math broke",
            )

    custom_registry = ExceptionMapperRegistry()
    custom_registry.register(_ZeroDivMapper())

    # Act
    info = custom_registry.map(ZeroDivisionError("x/0"))

    # Assert
    assert info.code == "MATH"


# ===========================================================================
# TC-ERR-011: ExportApplicationError carries its category by default.
# ===========================================================================
def test_error_mapping_export_application_error_defaults():
    # Arrange

    # Act
    err = ExportApplicationError("could not write file")

    # Assert
    assert err.info.category == ErrorCategory.EXPORT
    assert err.user_message == "could not write file"


# ===========================================================================
# TC-ERR-012: FileNotFoundError's message tells the user what to do next,
# not just what happened.
# ===========================================================================
def test_error_mapping_file_not_found_message_includes_actionable_suggestion(registry):
    # Arrange
    error = FileNotFoundError(2, "No such file", "courses.txt")

    # Act
    info = registry.map(error)

    # Assert
    assert "could not be found" in info.user_message
    assert "choose the file again" in info.user_message.lower()
