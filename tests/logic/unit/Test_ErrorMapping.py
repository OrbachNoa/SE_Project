"""Unit tests for the layered error model and the ExceptionMapperRegistry.

These cover the boundary mapping rules from the error-handling architecture:
raw exceptions (MemoryError, PermissionError, parser ValueError, the domain
InfeasibleScheduleError, and anything unknown) must each become an AppErrorInfo
with the right category / severity / recoverable flag and a stable code.
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
from src.application.errors.ExceptionMapper import (
    ExceptionMapperRegistry,
    build_process_error_payload,
)
from src.logic.feasibility.InfeasibleScheduleError import InfeasibleScheduleError


@pytest.fixture
def registry() -> ExceptionMapperRegistry:
    return default_registry()


# ===========================================================================
# TC-ERR-001: MemoryError → RESOURCE / CRITICAL / non-recoverable.
# ===========================================================================
def test_memory_error_maps_to_resource_critical(registry):
    info = registry.map(MemoryError("oom"))
    assert info.category == ErrorCategory.RESOURCE
    assert info.severity == ErrorSeverity.CRITICAL
    assert info.recoverable is False
    assert info.code == "RESOURCE_MEMORY_EXHAUSTED"


# ===========================================================================
# TC-ERR-002: PermissionError → EXPORT with a friendly, file-aware message.
# ===========================================================================
def test_permission_error_maps_to_export_with_friendly_message(registry):
    info = registry.map(PermissionError(13, "denied", "report.xlsx"))
    assert info.category == ErrorCategory.EXPORT
    assert info.code == "EXPORT_PERMISSION_DENIED"
    assert "report.xlsx" in info.user_message
    assert "Traceback" not in info.user_message


# ===========================================================================
# TC-ERR-003: a parser/validator ValueError → VALIDATION, message preserved.
# ===========================================================================
def test_value_error_from_parser_maps_to_validation(registry):
    info = registry.map(ValueError("Row 3: invalid date"))
    assert info.category == ErrorCategory.VALIDATION
    assert info.severity == ErrorSeverity.WARNING
    # The validator already phrases this for humans; keep its text.
    assert info.user_message == "Row 3: invalid date"


# ===========================================================================
# TC-ERR-004: context can steer a ValueError's category (input-file imports).
# ===========================================================================
def test_value_error_category_can_be_overridden_by_context(registry):
    info = registry.map(
        ValueError("bad header"),
        {"category": ErrorCategory.INPUT_FILE, "path": "courses.txt"},
    )
    assert info.category == ErrorCategory.INPUT_FILE


# ===========================================================================
# TC-ERR-005: an unknown exception → the UNEXPECTED fallback (never leaks).
# ===========================================================================
def test_unknown_exception_maps_to_unexpected_fallback(registry):
    info = registry.map(KeyError("surprise"))
    assert info.category == ErrorCategory.UNEXPECTED
    assert info.code == "UNEXPECTED_ERROR"
    assert info.user_message  # always something to show the user


# ===========================================================================
# TC-ERR-006: the domain InfeasibleScheduleError → a clean, recoverable message.
# ===========================================================================
def test_infeasible_schedule_maps_to_clean_recoverable_message(registry):
    info = registry.map(InfeasibleScheduleError(["too many exams in June"]))
    assert info.category == ErrorCategory.SCHEDULING
    assert info.severity == ErrorSeverity.WARNING
    assert info.recoverable is True
    assert "too many exams in June" in info.user_message
    assert "Traceback" not in info.user_message


# ===========================================================================
# TC-ERR-007: an ApplicationError passes its own info through unchanged (LSP).
# ===========================================================================
def test_application_error_passes_through_its_info(registry):
    raised = ResourceExhaustedError("custom", code="RESOURCE_MEMORY_EXHAUSTED")
    info = registry.map(raised)
    assert info is raised.info
    assert info.recoverable is False


# ===========================================================================
# TC-ERR-008: ordering — PermissionError is EXPORT, not the generic OSError path.
# ===========================================================================
def test_permission_error_beats_generic_oserror(registry):
    # PermissionError is an OSError subclass; the specific mapper must win.
    info = registry.map(PermissionError("locked"))
    assert info.code == "EXPORT_PERMISSION_DENIED"


# ===========================================================================
# TC-ERR-009: AppErrorInfo survives a serialise/deserialise round-trip (IPC).
# ===========================================================================
def test_app_error_info_payload_round_trip():
    info = AppErrorInfo(
        code="X",
        category=ErrorCategory.SCHEDULING,
        severity=ErrorSeverity.ERROR,
        user_message="u",
        technical_message="t",
        recoverable=False,
        context={"k": 1},
    )
    restored = AppErrorInfo.from_payload(info.to_payload())
    assert restored == info


# ===========================================================================
# TC-ERR-010: technical_message defaults to the user message when omitted.
# ===========================================================================
def test_technical_message_defaults_to_user_message():
    info = AppErrorInfo(
        code="X",
        category=ErrorCategory.EXPORT,
        severity=ErrorSeverity.ERROR,
        user_message="please retry",
    )
    assert info.technical_message == "please retry"


# ===========================================================================
# TC-ERR-011: a custom mapper extends the registry without editing it (OCP).
# ===========================================================================
def test_registry_is_extensible_with_a_custom_mapper():
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

    registry = ExceptionMapperRegistry()
    registry.register(_ZeroDivMapper())
    info = registry.map(ZeroDivisionError("x/0"))
    assert info.code == "MATH"


# ===========================================================================
# TC-ERR-012: ExportApplicationError carries its category by default.
# ===========================================================================
def test_export_application_error_defaults():
    err = ExportApplicationError("could not write file")
    assert err.info.category == ErrorCategory.EXPORT
    assert err.user_message == "could not write file"


# ===========================================================================
# TC-ERR-013: a caller can steer the unknown-exception fallback's category
# (e.g. "anything unmapped here is a SCHEDULING problem") without writing a
# mapper — message stays generic and safe either way.
# ===========================================================================
def test_unknown_exception_category_can_be_overridden_by_context(registry):
    info = registry.map(RuntimeError("backtracking error"), {"category": ErrorCategory.SCHEDULING})
    assert info.category == ErrorCategory.SCHEDULING
    assert info.code == "SCHEDULING_UNEXPECTED_ERROR"
    assert "backtracking error" not in info.user_message
    assert "backtracking error" in info.technical_message


# ===========================================================================
# TC-ERR-014: MemoryError still wins its own RESOURCE mapping even when the
# caller's context tries to steer unknown errors elsewhere — the dedicated
# mapper always runs before the context-driven fallback.
# ===========================================================================
def test_memory_error_beats_category_override(registry):
    info = registry.map(MemoryError("oom"), {"category": ErrorCategory.SCHEDULING})
    assert info.category == ErrorCategory.RESOURCE
    assert info.code == "RESOURCE_MEMORY_EXHAUSTED"


# ===========================================================================
# TC-ERR-015: control keys (category/severity/...) never leak into the
# AppErrorInfo's own context dict — only real data does.
# ===========================================================================
def test_control_context_keys_are_stripped_from_unknown_fallback(registry):
    info = registry.map(
        RuntimeError("x"),
        {"category": ErrorCategory.EXPORT, "severity": ErrorSeverity.CRITICAL, "path": "out.xlsx"},
    )
    assert "category" not in info.context
    assert "severity" not in info.context
    assert info.context == {"path": "out.xlsx"}


# ===========================================================================
# TC-ERR-016: build_process_error_payload — MemoryError during a worker-
# process stage stays RESOURCE_MEMORY_EXHAUSTED, not a generic process error.
# ===========================================================================
def test_build_process_error_payload_memory_error():
    payload = build_process_error_payload(MemoryError("oom"), "scheduling")
    assert payload["code"] == "RESOURCE_MEMORY_EXHAUSTED"
    assert payload["category"] == "RESOURCE"
    assert payload["recoverable"] is False


# ===========================================================================
# TC-ERR-017: build_process_error_payload — any other failure during a
# worker-process stage is a clean INFRASTRUCTURE payload, never str(e).
# ===========================================================================
def test_build_process_error_payload_generic_failure():
    payload = build_process_error_payload(RuntimeError("partition bug"), "work partitioning")
    assert isinstance(payload, dict)
    assert payload["category"] == "INFRASTRUCTURE"
    assert payload["recoverable"] is False
    assert "partition bug" in payload["technical_message"]
    assert "partition bug" not in payload["user_message"]


# ===========================================================================
# TC-ERR-018: PermissionError with context category EXPORT returns the
# export category/code and "written" wording (the default, unchanged).
# ===========================================================================
def test_permission_error_with_export_context(registry):
    info = registry.map(
        PermissionError(13, "denied", "out.xlsx"),
        {"category": ErrorCategory.EXPORT, "path": "out.xlsx"},
    )
    assert info.category == ErrorCategory.EXPORT
    assert info.code == "EXPORT_PERMISSION_DENIED"
    assert "written" in info.user_message
    assert "out.xlsx" in info.user_message


# ===========================================================================
# TC-ERR-019: PermissionError with context category INPUT_FILE returns the
# input-file category/code and "read" wording — it's a load, not an export.
# ===========================================================================
def test_permission_error_with_input_file_context(registry):
    info = registry.map(
        PermissionError(13, "denied", "courses.txt"),
        {"category": ErrorCategory.INPUT_FILE, "path": "courses.txt"},
    )
    assert info.category == ErrorCategory.INPUT_FILE
    assert info.code == "INPUT_FILE_PERMISSION_DENIED"
    assert "read" in info.user_message
    assert "written" not in info.user_message


# ===========================================================================
# TC-ERR-020: OSError with context category EXPORT stays EXPORT — it must
# not silently fall back to the mapper's own PERSISTENCE default.
# ===========================================================================
def test_os_error_with_export_context_does_not_default_to_persistence(registry):
    info = registry.map(OSError("disk error"), {"category": ErrorCategory.EXPORT})
    assert info.category == ErrorCategory.EXPORT
    assert info.code == "EXPORT_IO_FAILED"


# ===========================================================================
# TC-ERR-021: OSError with no context override keeps its original default —
# PERSISTENCE, code IO_FAILED — so existing cache/repository callers are
# unaffected by making the mapper context-aware.
# ===========================================================================
def test_os_error_without_context_defaults_to_persistence(registry):
    info = registry.map(OSError("disk error"))
    assert info.category == ErrorCategory.PERSISTENCE
    assert info.code == "IO_FAILED"


# ===========================================================================
# TC-ERR-022: an OSError's user_message is worded for the operation it
# happened during (import/export/persistence), not one generic sentence —
# a disk fault while importing should read like a read problem, and one
# while exporting should read like a write problem.
# ===========================================================================
def test_os_error_message_differs_by_context_category(registry):
    import_info = registry.map(OSError("disk error"), {"category": ErrorCategory.INPUT_FILE})
    export_info = registry.map(OSError("disk error"), {"category": ErrorCategory.EXPORT})
    persistence_info = registry.map(OSError("disk error"))

    assert "read" in import_info.user_message.lower()
    assert "export" in export_info.user_message.lower()
    assert import_info.user_message != export_info.user_message
    assert import_info.user_message != persistence_info.user_message
    assert "disk error" not in import_info.user_message
    assert "disk error" not in export_info.user_message


# ===========================================================================
# TC-ERR-023: FileNotFoundError's message tells the user what to do next,
# not just what happened.
# ===========================================================================
def test_file_not_found_message_includes_actionable_suggestion(registry):
    info = registry.map(FileNotFoundError(2, "No such file", "courses.txt"))
    assert "could not be found" in info.user_message
    assert "choose the file again" in info.user_message.lower()


# ===========================================================================
# TC-ERR-024: a non-recoverable unknown failure tells the user to restart
# instead of just "try again", which is misleading when retrying the same
# action can't possibly help.
# ===========================================================================
def test_unknown_non_recoverable_failure_suggests_restart(registry):
    info = registry.map(
        RuntimeError("worker died"),
        {"category": ErrorCategory.INFRASTRUCTURE, "recoverable": False},
    )
    assert info.recoverable is False
    assert "restart" in info.user_message.lower()
    assert "worker died" not in info.user_message


# ===========================================================================
# TC-ERR-025: a recoverable unknown failure keeps the plain "try again"
# wording — no restart suggestion when retrying is actually reasonable.
# ===========================================================================
def test_unknown_recoverable_failure_keeps_try_again_wording(registry):
    info = registry.map(RuntimeError("transient glitch"), {"category": ErrorCategory.PERSISTENCE})
    assert info.recoverable is True
    assert "restart" not in info.user_message.lower()
    assert "try again" in info.user_message.lower()
