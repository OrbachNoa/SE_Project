"""Layered error model for the scheduler.

A single, framework-agnostic way to describe failures and present them
consistently at every boundary (GUI, CLI, IPC):

* :class:`AppErrorInfo` — the value object every failure becomes.
* ``ApplicationError`` + typed subclasses — exceptions raised on purpose in the
  application/domain layers, each carrying its own ``AppErrorInfo``.
* :class:`ExceptionMapperRegistry` — converts any raw exception (``MemoryError``,
  ``PermissionError``, parser ``ValueError`` …) into an ``AppErrorInfo`` at the
  boundary, extensible by adding a mapper (OCP) rather than editing a handler.
* :class:`ErrorLogger` — logs the technical detail while the boundary keeps the
  short user message.
"""
from src.application.errors.ErrorModel import (
    AppErrorInfo,
    ErrorCategory,
    ErrorSeverity,
    make_unexpected,
)
from src.application.errors.ApplicationErrors import (
    ApplicationError,
    ValidationApplicationError,
    InputFileApplicationError,
    SchedulingApplicationError,
    SchedulingInfeasibleError,
    ResourceExhaustedError,
    PersistenceApplicationError,
    ExportApplicationError,
    InfrastructureApplicationError,
    UnexpectedApplicationError,
)
from src.application.errors.ExceptionMapper import (
    ExceptionMapper,
    ExceptionMapperRegistry,
    default_registry,
    build_process_error_payload,
)
from src.application.errors.ErrorLogger import (
    ErrorLogger,
    configure_default_logging,
)

__all__ = [
    # model
    "AppErrorInfo",
    "ErrorCategory",
    "ErrorSeverity",
    "make_unexpected",
    # exceptions
    "ApplicationError",
    "ValidationApplicationError",
    "InputFileApplicationError",
    "SchedulingApplicationError",
    "SchedulingInfeasibleError",
    "ResourceExhaustedError",
    "PersistenceApplicationError",
    "ExportApplicationError",
    "InfrastructureApplicationError",
    "UnexpectedApplicationError",
    # mapping
    "ExceptionMapper",
    "ExceptionMapperRegistry",
    "default_registry",
    "build_process_error_payload",
    # logging
    "ErrorLogger",
    "configure_default_logging",
]
