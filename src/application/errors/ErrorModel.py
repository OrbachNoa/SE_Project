"""The shared, framework-agnostic error model.

Every failure that crosses an application boundary (GUI, CLI, IPC) is described
by a single value object, :class:`AppErrorInfo`. It separates the three concerns
that boundaries actually care about:

* a *category* (which subsystem failed),
* a *severity* (how loud the failure is), and
* two messages — a clean ``user_message`` for the UI and a verbose
  ``technical_message`` for the log.

The model has no dependency on PyQt, logging, or any concrete subsystem, so it
can be raised in ``logic``/``infrastructure`` and rendered in ``gui``/``main``
without coupling those layers together.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """How serious a failure is, independent of which subsystem produced it."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """Which area of the system a failure belongs to.

    Categories drive presentation (icon, wording) and triage, not control flow:
    the GUI shows the same dialog for every category, only the text differs.
    """

    VALIDATION = "VALIDATION"          # User input rejected by a validator.
    INPUT_FILE = "INPUT_FILE"          # A course/period/programs file is bad.
    SCHEDULING = "SCHEDULING"          # The scheduling search itself failed.
    TRANSLATION = "TRANSLATION"        # Free-text → config translation (e.g. LLM) failed.
    RESOURCE = "RESOURCE"              # Out of memory / out of CPU budget.
    PERSISTENCE = "PERSISTENCE"        # SQLite / disk cache problems.
    EXPORT = "EXPORT"                  # Writing TXT / Excel / PDF output.
    INFRASTRUCTURE = "INFRASTRUCTURE"  # Process crash, IPC, OS-level faults.
    UNEXPECTED = "UNEXPECTED"          # Anything we did not anticipate.


@dataclass(frozen=True)
class AppErrorInfo:
    """A complete, serialisable description of a single failure.

    Instances are immutable so they can be passed across threads and (after
    :meth:`to_payload`) across process boundaries without aliasing surprises.
    """

    code: str
    category: ErrorCategory
    severity: ErrorSeverity
    user_message: str
    technical_message: str = ""
    recoverable: bool = True
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # The technical message defaults to the user message when none is given,
        # so the log is never emptier than the dialog.
        if not self.technical_message:
            object.__setattr__(self, "technical_message", self.user_message)

    # ------------------------------------------------------------------
    # Serialisation — lets workers send an error across the IPC/Qt boundary
    # as a plain dict and reconstruct it on the other side.
    # ------------------------------------------------------------------

    def to_payload(self) -> Dict[str, Any]:
        """Return a plain-dict form safe to send over a multiprocessing queue."""
        return {
            "code": self.code,
            "category": self.category.value,
            "severity": self.severity.value,
            "user_message": self.user_message,
            "technical_message": self.technical_message,
            "recoverable": self.recoverable,
            "context": dict(self.context),
        }

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "AppErrorInfo":
        """Rebuild an :class:`AppErrorInfo` from :meth:`to_payload` output."""
        return cls(
            code=payload["code"],
            category=ErrorCategory(payload["category"]),
            severity=ErrorSeverity(payload["severity"]),
            user_message=payload["user_message"],
            technical_message=payload.get("technical_message", ""),
            recoverable=payload.get("recoverable", True),
            context=dict(payload.get("context", {})),
        )


def make_unexpected(
    technical_message: str,
    *,
    code: str = "UNEXPECTED_ERROR",
    context: Optional[Dict[str, Any]] = None,
) -> AppErrorInfo:
    """Build the catch-all error used when nothing more specific applies."""
    return AppErrorInfo(
        code=code,
        category=ErrorCategory.UNEXPECTED,
        severity=ErrorSeverity.ERROR,
        user_message="Something went wrong. Please try again.",
        technical_message=technical_message,
        recoverable=True,
        context=context or {},
    )
