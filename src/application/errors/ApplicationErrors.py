"""Typed application exceptions.

These replace generic ``ValueError`` / ``RuntimeError`` at the critical
application and domain boundaries. Every one of them carries a fully-formed
:class:`AppErrorInfo`, so the code that catches it never has to guess how to
present it — it just reads ``exc.info``.

The hierarchy is intentionally shallow: a single base, :class:`ApplicationError`,
with one subclass per :class:`ErrorCategory`. New failure *kinds* are added by
constructing a different ``AppErrorInfo`` (or by registering a new mapper), not
by deepening this tree — that keeps the catch sites stable (LSP/OCP).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.application.errors.ErrorModel import (
    AppErrorInfo,
    ErrorCategory,
    ErrorSeverity,
)


class ApplicationError(Exception):
    """Base class for every error the application raises on purpose.

    Holds the presentation-ready :class:`AppErrorInfo` and, optionally, the
    lower-level exception that triggered it (``cause``) for logging.
    """

    #: Subclasses set these so the convenience constructor can build the info.
    category: ErrorCategory = ErrorCategory.UNEXPECTED
    default_severity: ErrorSeverity = ErrorSeverity.ERROR
    default_code: str = "APPLICATION_ERROR"
    default_recoverable: bool = True

    def __init__(
        self,
        user_message: str,
        *,
        technical_message: str = "",
        code: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        recoverable: Optional[bool] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        info: Optional[AppErrorInfo] = None,
    ) -> None:
        # Callers may pass a ready-made AppErrorInfo, or the convenience fields
        # from which we build one using the subclass defaults.
        self.info = info or AppErrorInfo(
            code=code or self.default_code,
            category=self.category,
            severity=severity or self.default_severity,
            user_message=user_message,
            technical_message=technical_message or user_message,
            recoverable=self.default_recoverable if recoverable is None else recoverable,
            context=context or {},
        )
        self.cause = cause
        super().__init__(self.info.technical_message)
        # Preserve the exception chain for tracebacks/logging.
        if cause is not None:
            self.__cause__ = cause

    @property
    def user_message(self) -> str:
        """The clean, end-user-facing message (shortcut for ``info.user_message``)."""
        return self.info.user_message


class ValidationApplicationError(ApplicationError):
    """User-supplied input was rejected (e.g. too many programs, bad selection)."""

    category = ErrorCategory.VALIDATION
    default_severity = ErrorSeverity.WARNING
    default_code = "VALIDATION_FAILED"


class InputFileApplicationError(ApplicationError):
    """A course/period/programs file is missing, empty, or unparseable."""

    category = ErrorCategory.INPUT_FILE
    default_severity = ErrorSeverity.ERROR
    default_code = "INPUT_FILE_INVALID"


class SchedulingApplicationError(ApplicationError):
    """The scheduling search failed for a reason other than infeasibility."""

    category = ErrorCategory.SCHEDULING
    default_severity = ErrorSeverity.ERROR
    default_code = "SCHEDULING_FAILED"


class SchedulingInfeasibleError(SchedulingApplicationError):
    """No valid schedule exists for the given input — a clean, expected outcome.

    This is the application-layer wrapper around the domain
    ``InfeasibleScheduleError``; it is recoverable (the user can change input).
    """

    default_severity = ErrorSeverity.WARNING
    default_code = "SCHEDULING_INFEASIBLE"
    default_recoverable = True


class ResourceExhaustedError(ApplicationError):
    """The machine ran out of memory or another bounded resource."""

    category = ErrorCategory.RESOURCE
    default_severity = ErrorSeverity.CRITICAL
    default_code = "RESOURCE_MEMORY_EXHAUSTED"
    default_recoverable = False


class PersistenceApplicationError(ApplicationError):
    """SQLite / disk-cache read or write failed."""

    category = ErrorCategory.PERSISTENCE
    default_severity = ErrorSeverity.ERROR
    default_code = "PERSISTENCE_FAILED"


class ExportApplicationError(ApplicationError):
    """Writing a schedule to TXT / Excel / PDF failed."""

    category = ErrorCategory.EXPORT
    default_severity = ErrorSeverity.ERROR
    default_code = "EXPORT_FAILED"


class InfrastructureApplicationError(ApplicationError):
    """A background process crashed or the IPC channel broke."""

    category = ErrorCategory.INFRASTRUCTURE
    default_severity = ErrorSeverity.CRITICAL
    default_code = "INFRASTRUCTURE_FAILURE"
    default_recoverable = False


class UnexpectedApplicationError(ApplicationError):
    """Catch-all for failures we did not anticipate."""

    category = ErrorCategory.UNEXPECTED
    default_severity = ErrorSeverity.ERROR
    default_code = "UNEXPECTED_ERROR"
