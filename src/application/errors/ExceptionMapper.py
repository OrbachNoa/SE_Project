"""Maps raw exceptions to :class:`AppErrorInfo` at the system boundaries.

This is the one place that knows how to translate a low-level fault
(``MemoryError``, ``PermissionError``, a parser's ``ValueError`` …) into a
user-facing error. Boundaries (GUI, CLI, workers) own *one* registry and call
:meth:`ExceptionMapperRegistry.map`; they never grow their own ``except`` ladder.

OCP: a new failure kind is supported by adding a small mapper to the registry,
not by editing a central handler. ISP: the :class:`ExceptionMapper` interface is
two methods and knows nothing about GUI or CLI.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from src.application.errors.ApplicationErrors import ApplicationError
from src.application.errors.ErrorModel import (
    AppErrorInfo,
    ErrorCategory,
    ErrorSeverity,
)
from src.logic.feasibility.InfeasibleScheduleError import InfeasibleScheduleError


@runtime_checkable
class ExceptionMapper(Protocol):
    """Strategy that recognises one family of exceptions and describes it."""

    def can_handle(self, exc: BaseException) -> bool:
        """True if this mapper knows how to describe ``exc``."""
        ...

    def map(self, exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        """Build an :class:`AppErrorInfo` for ``exc`` (only called if matched)."""
        ...


def _tech(exc: BaseException) -> str:
    """Standard technical string: ``TypeName: message`` for the log."""
    return f"{type(exc).__name__}: {exc}"


# Context keys that steer mapping decisions rather than describing the failure
# itself. Mappers strip these before storing the rest of the context on the
# AppErrorInfo, so a caller-supplied "category" never leaks into the log as
# if it were application data.
_CONTROL_CONTEXT_KEYS = frozenset({"category", "severity", "recoverable", "fallback_code"})


def _strip_control_keys(context: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in context.items() if k not in _CONTROL_CONTEXT_KEYS}


# One safe, generic sentence per category for exceptions no specific mapper
# recognises. Never includes raw exception text — only the log gets that.
_GENERIC_MESSAGE_BY_CATEGORY = {
    ErrorCategory.VALIDATION: "The provided input is not valid. Please check it and try again.",
    ErrorCategory.INPUT_FILE: "The file could not be read. Please check it and try again.",
    ErrorCategory.SCHEDULING: "The scheduling engine failed unexpectedly. Please try again.",
    ErrorCategory.RESOURCE: "The operation ran out of resources. Please try again.",
    ErrorCategory.PERSISTENCE: "Could not read or save the data. Please try again.",
    ErrorCategory.EXPORT: "Could not complete the export. Please try again.",
    ErrorCategory.INFRASTRUCTURE: "A background process failed unexpectedly. Please try again.",
    ErrorCategory.UNEXPECTED: "Something went wrong. Please try again.",
}

# Categories whose unknown failures default to non-recoverable (resource/process
# faults rarely go away just by retrying the same action).
_NON_RECOVERABLE_BY_DEFAULT = frozenset({ErrorCategory.RESOURCE, ErrorCategory.INFRASTRUCTURE})


class ApplicationErrorMapper:
    """Pass-through for errors that already carry their own ``AppErrorInfo``."""

    def can_handle(self, exc: BaseException) -> bool:
        return isinstance(exc, ApplicationError)

    def map(self, exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        assert isinstance(exc, ApplicationError)
        return exc.info


class InfeasibleScheduleMapper:
    """The domain ``InfeasibleScheduleError`` → a clean, recoverable message."""

    def can_handle(self, exc: BaseException) -> bool:
        return isinstance(exc, InfeasibleScheduleError)

    def map(self, exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        reasons = list(getattr(exc, "errors", []) or [])
        user_message = (
            "No valid schedule is possible with the current input.\n"
            + "\n".join(f"• {r}" for r in reasons)
            if reasons
            else "No valid schedule is possible with the current input."
        )
        return AppErrorInfo(
            code="SCHEDULING_INFEASIBLE",
            category=ErrorCategory.SCHEDULING,
            severity=ErrorSeverity.WARNING,
            user_message=user_message,
            technical_message=_tech(exc),
            recoverable=True,
            context={**context, "reasons": reasons},
        )


class MemoryErrorMapper:
    """``MemoryError`` → a non-recoverable RESOURCE failure."""

    def can_handle(self, exc: BaseException) -> bool:
        return isinstance(exc, MemoryError)

    def map(self, exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        return AppErrorInfo(
            code="RESOURCE_MEMORY_EXHAUSTED",
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.CRITICAL,
            user_message=(
                "The operation ran out of memory. Try selecting fewer programs "
                "or tightening the constraints, then run again."
            ),
            technical_message=_tech(exc),
            recoverable=False,
            context=dict(context),
        )


class PermissionErrorMapper:
    """``PermissionError`` → a friendly file-access permission message.

    Defaults to EXPORT (its original, most common caller) but — like
    ``ValueErrorMapper`` — a caller can steer the category via context, since
    a denied file isn't only an export problem (e.g. the disk cache write in
    ``FileImportService`` hits the same exception under PERSISTENCE).
    """

    def can_handle(self, exc: BaseException) -> bool:
        return isinstance(exc, PermissionError)

    def map(self, exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        category = context.get("category", ErrorCategory.EXPORT)
        path = getattr(exc, "filename", None) or context.get("path")
        where = f' "{path}"' if path else ""
        code = "EXPORT_PERMISSION_DENIED" if category is ErrorCategory.EXPORT else f"{category.value}_PERMISSION_DENIED"
        # Loading an input file is a read; everything else here is a write —
        # say the right verb instead of always claiming "written".
        verb = "read" if category is ErrorCategory.INPUT_FILE else "written"
        return AppErrorInfo(
            code=code,
            category=category,
            severity=ErrorSeverity.ERROR,
            user_message=(
                f"The file{where} could not be {verb}. It may be open in another "
                "program or you may not have permission. Close it and try again."
            ),
            technical_message=_tech(exc),
            recoverable=True,
            context=_strip_control_keys(context),
        )


class FileNotFoundMapper:
    """``FileNotFoundError`` → an INPUT_FILE problem."""

    def can_handle(self, exc: BaseException) -> bool:
        return isinstance(exc, FileNotFoundError)

    def map(self, exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        path = getattr(exc, "filename", None) or context.get("path")
        where = f' "{path}"' if path else ""
        return AppErrorInfo(
            code="INPUT_FILE_NOT_FOUND",
            category=ErrorCategory.INPUT_FILE,
            severity=ErrorSeverity.ERROR,
            user_message=f"The file{where} could not be found. Please choose the file again.",
            technical_message=_tech(exc),
            recoverable=True,
            context=dict(context),
        )


class OSErrorMapper:
    """Remaining ``OSError`` faults → PERSISTENCE (disk/IO trouble) by default.

    Registered after the more specific ``PermissionError`` / ``FileNotFoundError``
    mappers, so it only catches the leftovers. Like those, a caller can steer
    the category via context — the same disk fault means something different
    during an export (EXPORT) versus loading an input file (INPUT_FILE).
    """

    def can_handle(self, exc: BaseException) -> bool:
        return isinstance(exc, OSError)

    def map(self, exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        category = context.get("category", ErrorCategory.PERSISTENCE)
        code = "IO_FAILED" if category is ErrorCategory.PERSISTENCE else f"{category.value}_IO_FAILED"
        return AppErrorInfo(
            code=code,
            category=category,
            severity=ErrorSeverity.ERROR,
            # Same per-category wording as the unknown-exception fallback, so a
            # disk fault during an import reads like a read problem and one
            # during an export reads like a write problem, instead of one
            # generic sentence regardless of what the user was doing.
            user_message=_GENERIC_MESSAGE_BY_CATEGORY[category],
            technical_message=_tech(exc),
            recoverable=True,
            context=_strip_control_keys(context),
        )


class ValueErrorMapper:
    """``ValueError`` from parsers/validators → a VALIDATION message.

    The exception's own text is shown to the user, because parsers and
    validators already phrase these for humans (e.g. "Row 3: invalid date").
    """

    def can_handle(self, exc: BaseException) -> bool:
        return isinstance(exc, ValueError)

    def map(self, exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        message = str(exc).strip() or "The provided input is not valid."
        return AppErrorInfo(
            code="INPUT_VALIDATION_FAILED",
            category=context.get("category", ErrorCategory.VALIDATION),
            severity=ErrorSeverity.WARNING,
            user_message=message,
            technical_message=_tech(exc),
            recoverable=True,
            context=_strip_control_keys(context),
        )


class ExceptionMapperRegistry:
    """Ordered collection of mappers with a guaranteed fallback.

    Boundaries depend on *this* abstraction (DIP), inject the mappers they want,
    and get an :class:`AppErrorInfo` for any exception — known or not.
    """

    def __init__(self, mappers: Optional[List[ExceptionMapper]] = None) -> None:
        self._mappers: List[ExceptionMapper] = list(mappers or [])

    def register(self, mapper: ExceptionMapper) -> None:
        """Append a mapper (checked before the unknown-error fallback)."""
        self._mappers.append(mapper)

    def map(
        self, exc: BaseException, context: Optional[Dict[str, Any]] = None
    ) -> AppErrorInfo:
        """Return the first matching mapper's result, else the unknown fallback."""
        ctx = dict(context or {})
        for mapper in self._mappers:
            if mapper.can_handle(exc):
                return mapper.map(exc, ctx)
        return self._unknown(exc, ctx)

    @staticmethod
    def _unknown(exc: BaseException, context: Dict[str, Any]) -> AppErrorInfo:
        """Fallback for exceptions no registered mapper recognises.

        A caller can steer this (without writing a mapper) by passing
        ``category``/``severity``/``recoverable``/``fallback_code`` in the
        context — e.g. a worker that knows "anything unmapped here is a
        SCHEDULING problem" passes ``{"category": ErrorCategory.SCHEDULING}``.
        The message stays generic and safe either way; only category/severity
        change, never the wording leaked from the exception.
        """
        category = context.get("category", ErrorCategory.UNEXPECTED)
        severity = context.get("severity", ErrorSeverity.ERROR)
        recoverable = context.get("recoverable", category not in _NON_RECOVERABLE_BY_DEFAULT)
        default_code = (
            "UNEXPECTED_ERROR"
            if category is ErrorCategory.UNEXPECTED
            else f"{category.value}_UNEXPECTED_ERROR"
        )
        code = context.get("fallback_code") or default_code
        user_message = _GENERIC_MESSAGE_BY_CATEGORY[category]
        if not recoverable:
            # "Try again" is misleading for a failure the operation can't
            # recover from on its own (e.g. a crashed worker process) — point
            # the user at restarting instead.
            user_message = user_message.replace(
                "Please try again.", "Please restart and try again."
            )
        return AppErrorInfo(
            code=code,
            category=category,
            severity=severity,
            user_message=user_message,
            technical_message=_tech(exc),
            recoverable=recoverable,
            context=_strip_control_keys(context),
        )


def build_process_error_payload(
    exc: BaseException, stage: str, registry: Optional[ExceptionMapperRegistry] = None
) -> Dict[str, Any]:
    """Describe a worker-process failure as a serialisable AppErrorInfo payload.

    Used by code that runs inside a multiprocessing worker (SchedulingService's
    child-process functions, SchedulerProcessRunner) where only plain, picklable
    data can cross back to the main process. ``MemoryError`` still wins its own
    RESOURCE mapping (the dedicated mapper runs first); anything else not
    otherwise recognised is filed as INFRASTRUCTURE, since a process-level
    failure during ``stage`` is exactly that.
    """
    reg = registry or default_registry()
    info = reg.map(exc, {"stage": stage, "category": ErrorCategory.INFRASTRUCTURE})
    return info.to_payload()


def default_registry() -> ExceptionMapperRegistry:
    """The standard registry wired for the whole application.

    Order matters: most specific first. ``ApplicationError`` (already mapped)
    leads; the broad ``ValueError`` / ``OSError`` mappers come last so they only
    catch what the specific ones missed.
    """
    return ExceptionMapperRegistry(
        [
            ApplicationErrorMapper(),
            InfeasibleScheduleMapper(),
            MemoryErrorMapper(),
            PermissionErrorMapper(),
            FileNotFoundMapper(),
            ValueErrorMapper(),
            OSErrorMapper(),
        ]
    )
