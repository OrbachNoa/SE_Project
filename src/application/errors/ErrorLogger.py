"""A thin logging wrapper around the error model.

Keeps the two audiences separate: the *technical* message and context go to the
log (file + stderr) for developers, while callers keep the short ``user_message``
for the GUI/CLI. Severity maps onto the standard ``logging`` levels so existing
log tooling keeps working.

The logger is deliberately tiny and side-effect-light: configuring handlers is
done once, lazily, and is a no-op if the host application already configured
logging.
"""
from __future__ import annotations

import logging
from typing import Optional

from src.application.errors.ErrorModel import AppErrorInfo, ErrorSeverity

_LEVEL_BY_SEVERITY = {
    ErrorSeverity.INFO: logging.INFO,
    ErrorSeverity.WARNING: logging.WARNING,
    ErrorSeverity.ERROR: logging.ERROR,
    ErrorSeverity.CRITICAL: logging.CRITICAL,
}

_DEFAULT_LOGGER_NAME = "se_project.errors"


class ErrorLogger:
    """Logs :class:`AppErrorInfo` records at the right level with full detail."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or logging.getLogger(_DEFAULT_LOGGER_NAME)

    def log(
        self, info: AppErrorInfo, cause: Optional[BaseException] = None
    ) -> AppErrorInfo:
        """Write ``info`` to the log and return it unchanged (for chaining).

        ``cause``, when given, is attached as exception info so the traceback is
        captured in the log without ever reaching the user-facing message.
        """
        level = _LEVEL_BY_SEVERITY.get(info.severity, logging.ERROR)
        self._logger.log(
            level,
            "[%s/%s] %s | %s%s",
            info.code,
            info.category.value,
            info.technical_message,
            info.user_message,
            f" | context={info.context}" if info.context else "",
            exc_info=cause if cause is not None else None,
        )
        return info


def configure_default_logging(level: int = logging.INFO) -> None:
    """Attach a basic stderr handler once, if logging is otherwise unconfigured.

    Safe to call from any entry point (CLI ``main`` or GUI bootstrap). Does
    nothing if the root logger already has handlers, so it never fights with a
    host that set up its own logging.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
