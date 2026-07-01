"""Unit tests for context-driven error mapping and process-error payloads.

A caller can pass a context dict to ExceptionMapperRegistry.map() to steer an
exception's resulting category, severity, or recoverable flag, and to get
operation-aware message wording (e.g. an OSError reads differently depending
on whether it happened during an import, an export, or plain persistence).
This file also covers build_process_error_payload, the equivalent boundary
used by worker-process stages.

This file was split out of a single, larger error-mapping test file once it
grew past the project's per-file line limit; the core, context-free mapping
rules for individual exception types stayed in Test_ErrorMapping.py.

Conventions:
- Each test carries a unique TC-EMC-NNN identifier in the comment block above
  its definition, numbered sequentially within this file (independent of the
  numbering in Test_ErrorMapping.py).
- Each test body is split into Arrange / Act / Assert sections.
- The `registry` fixture is local to this file (default_registry()); no
  conftest fixture models the error registry.
"""
import pytest

from src.application.errors import ErrorCategory, ErrorSeverity, default_registry
from src.application.errors.ExceptionMapper import (
    ExceptionMapperRegistry,
    build_process_error_payload,
)


@pytest.fixture
def registry() -> ExceptionMapperRegistry:
    return default_registry()


# ===========================================================================
# TC-EMC-001: context can steer a ValueError's category (input-file imports).
# ===========================================================================
def test_error_mapping_value_error_category_can_be_overridden_by_context(registry):
    # Arrange
    error = ValueError("bad header")
    context = {"category": ErrorCategory.INPUT_FILE, "path": "courses.txt"}

    # Act
    info = registry.map(error, context)

    # Assert
    assert info.category == ErrorCategory.INPUT_FILE


# ===========================================================================
# TC-EMC-002: a caller can steer the unknown-exception fallback's category
# (e.g. "anything unmapped here is a SCHEDULING problem") without writing a
# mapper — message stays generic and safe either way.
# ===========================================================================
def test_error_mapping_unknown_exception_category_can_be_overridden_by_context(registry):
    # Arrange
    error = RuntimeError("backtracking error")
    context = {"category": ErrorCategory.SCHEDULING}

    # Act
    info = registry.map(error, context)

    # Assert
    assert info.category == ErrorCategory.SCHEDULING
    assert info.code == "SCHEDULING_UNEXPECTED_ERROR"
    assert "backtracking error" not in info.user_message
    assert "backtracking error" in info.technical_message


# ===========================================================================
# TC-EMC-003: MemoryError still wins its own RESOURCE mapping even when the
# caller's context tries to steer unknown errors elsewhere — the dedicated
# mapper always runs before the context-driven fallback.
# ===========================================================================
def test_error_mapping_memory_error_beats_category_override(registry):
    # Arrange
    error = MemoryError("oom")
    context = {"category": ErrorCategory.SCHEDULING}

    # Act
    info = registry.map(error, context)

    # Assert
    assert info.category == ErrorCategory.RESOURCE
    assert info.code == "RESOURCE_MEMORY_EXHAUSTED"


# ===========================================================================
# TC-EMC-004: control keys (category/severity/...) never leak into the
# AppErrorInfo's own context dict — only real data does.
# ===========================================================================
def test_error_mapping_control_context_keys_are_stripped_from_unknown_fallback(registry):
    # Arrange
    error = RuntimeError("x")
    context = {"category": ErrorCategory.EXPORT, "severity": ErrorSeverity.CRITICAL, "path": "out.xlsx"}

    # Act
    info = registry.map(error, context)

    # Assert
    assert "category" not in info.context
    assert "severity" not in info.context
    assert info.context == {"path": "out.xlsx"}


# ===========================================================================
# TC-EMC-005: build_process_error_payload — MemoryError during a worker-
# process stage stays RESOURCE_MEMORY_EXHAUSTED, not a generic process error.
# ===========================================================================
def test_error_mapping_build_process_error_payload_memory_error():
    # Arrange
    error = MemoryError("oom")

    # Act
    payload = build_process_error_payload(error, "scheduling")

    # Assert
    assert payload["code"] == "RESOURCE_MEMORY_EXHAUSTED"
    assert payload["category"] == "RESOURCE"
    assert payload["recoverable"] is False


# ===========================================================================
# TC-EMC-006: build_process_error_payload — any other failure during a
# worker-process stage is a clean INFRASTRUCTURE payload, never str(e).
# ===========================================================================
def test_error_mapping_build_process_error_payload_generic_failure():
    # Arrange
    error = RuntimeError("partition bug")

    # Act
    payload = build_process_error_payload(error, "work partitioning")

    # Assert
    assert isinstance(payload, dict)
    assert payload["category"] == "INFRASTRUCTURE"
    assert payload["recoverable"] is False
    assert "partition bug" in payload["technical_message"]
    assert "partition bug" not in payload["user_message"]


# ===========================================================================
# TC-EMC-007: PermissionError with context category EXPORT returns the
# export category/code and "written" wording (the default, unchanged).
# ===========================================================================
def test_error_mapping_permission_error_with_export_context(registry):
    # Arrange
    error = PermissionError(13, "denied", "out.xlsx")
    context = {"category": ErrorCategory.EXPORT, "path": "out.xlsx"}

    # Act
    info = registry.map(error, context)

    # Assert
    assert info.category == ErrorCategory.EXPORT
    assert info.code == "EXPORT_PERMISSION_DENIED"
    assert "written" in info.user_message
    assert "out.xlsx" in info.user_message


# ===========================================================================
# TC-EMC-008: PermissionError with context category INPUT_FILE returns the
# input-file category/code and "read" wording — it's a load, not an export.
# ===========================================================================
def test_error_mapping_permission_error_with_input_file_context(registry):
    # Arrange
    error = PermissionError(13, "denied", "courses.txt")
    context = {"category": ErrorCategory.INPUT_FILE, "path": "courses.txt"}

    # Act
    info = registry.map(error, context)

    # Assert
    assert info.category == ErrorCategory.INPUT_FILE
    assert info.code == "INPUT_FILE_PERMISSION_DENIED"
    assert "read" in info.user_message
    assert "written" not in info.user_message


# ===========================================================================
# TC-EMC-009: OSError with context category EXPORT stays EXPORT — it must
# not silently fall back to the mapper's own PERSISTENCE default.
# ===========================================================================
def test_error_mapping_os_error_with_export_context_does_not_default_to_persistence(registry):
    # Arrange
    error = OSError("disk error")
    context = {"category": ErrorCategory.EXPORT}

    # Act
    info = registry.map(error, context)

    # Assert
    assert info.category == ErrorCategory.EXPORT
    assert info.code == "EXPORT_IO_FAILED"


# ===========================================================================
# TC-EMC-010: OSError with no context override keeps its original default —
# PERSISTENCE, code IO_FAILED — so existing cache/repository callers are
# unaffected by making the mapper context-aware.
# ===========================================================================
def test_error_mapping_os_error_without_context_defaults_to_persistence(registry):
    # Arrange
    error = OSError("disk error")

    # Act
    info = registry.map(error)

    # Assert
    assert info.category == ErrorCategory.PERSISTENCE
    assert info.code == "IO_FAILED"


# ===========================================================================
# TC-EMC-011: an OSError's user_message is worded for the operation it
# happened during (import/export/persistence), not one generic sentence —
# a disk fault while importing should read like a read problem, and one
# while exporting should read like a write problem.
# ===========================================================================
def test_error_mapping_os_error_message_differs_by_context_category(registry):
    # Arrange
    error = OSError("disk error")

    # Act
    import_info = registry.map(error, {"category": ErrorCategory.INPUT_FILE})
    export_info = registry.map(error, {"category": ErrorCategory.EXPORT})
    persistence_info = registry.map(error)

    # Assert
    assert "read" in import_info.user_message.lower()
    assert "export" in export_info.user_message.lower()
    assert import_info.user_message != export_info.user_message
    assert import_info.user_message != persistence_info.user_message
    assert "disk error" not in import_info.user_message
    assert "disk error" not in export_info.user_message


# ===========================================================================
# TC-EMC-012: a non-recoverable unknown failure tells the user to restart
# instead of just "try again", which is misleading when retrying the same
# action can't possibly help.
# ===========================================================================
def test_error_mapping_unknown_non_recoverable_failure_suggests_restart(registry):
    # Arrange
    error = RuntimeError("worker died")
    context = {"category": ErrorCategory.INFRASTRUCTURE, "recoverable": False}

    # Act
    info = registry.map(error, context)

    # Assert
    assert info.recoverable is False
    assert "restart" in info.user_message.lower()
    assert "worker died" not in info.user_message


# ===========================================================================
# TC-EMC-013: a recoverable unknown failure keeps the plain "try again"
# wording — no restart suggestion when retrying is actually reasonable.
# ===========================================================================
def test_error_mapping_unknown_recoverable_failure_keeps_try_again_wording(registry):
    # Arrange
    error = RuntimeError("transient glitch")
    context = {"category": ErrorCategory.PERSISTENCE}

    # Act
    info = registry.map(error, context)

    # Assert
    assert info.recoverable is True
    assert "restart" not in info.user_message.lower()
    assert "try again" in info.user_message.lower()
