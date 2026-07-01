"""
Test suite for ErrorLogger.

Scope   : ErrorLogger message formatting, severity mapping, and default configuration logic.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-EL-001, TC-EL-002, TC-EL-003
Fixtures: caplog
"""
import logging

from src.application.errors.ErrorLogger import ErrorLogger, configure_default_logging
from src.application.errors.ErrorModel import AppErrorInfo, ErrorCategory, ErrorSeverity


# TC-EL-001
# Verifies that log() maps severity correctly, formats the message including context, and returns the info object.
def test_error_logger_log_emits_correctly_formatted_message(caplog):
    # Arrange
    logger = ErrorLogger()
    info = AppErrorInfo(
        code="ERR01",
        category=ErrorCategory.PERSISTENCE,
        severity=ErrorSeverity.WARNING,
        technical_message="Tech message",
        user_message="User message",
        context={"file": "test.txt"},
        recoverable=True
    )

    # Act
    with caplog.at_level(logging.WARNING):
        result = logger.log(info)

    # Assert
    assert result is info
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.WARNING
    assert "ERR01" in record.message
    assert "PERSISTENCE" in record.message
    assert "Tech message" in record.message
    assert "User message" in record.message
    assert "context={'file': 'test.txt'}" in record.message


# TC-EL-002
# Verifies that configure_default_logging() does nothing if handlers are already present, avoiding duplicate logs.
def test_configure_default_logging_no_op_when_handlers_exist():
    # Arrange
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    test_handler = logging.NullHandler()
    root.addHandler(test_handler)

    try:
        handler_count_before = len(root.handlers)

        # Act
        configure_default_logging()

        # Assert
        assert len(root.handlers) == handler_count_before
        assert test_handler in root.handlers
    finally:
        # Cleanup
        root.removeHandler(test_handler)
        root.handlers = original_handlers


# TC-EL-003
# Verifies that configure_default_logging() successfully attaches a handler when starting from scratch.
def test_configure_default_logging_sets_up_when_no_handlers_exist():
    # Arrange
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    root.handlers = []  # Clear to simulate an unconfigured state

    try:
        # Act
        configure_default_logging(level=logging.DEBUG)

        # Assert
        assert len(root.handlers) > 0
        assert root.level == logging.DEBUG
    finally:
        # Cleanup — restore BOTH handlers and level. configure_default_logging()
        # calls logging.basicConfig(), which mutates the root logger's level to
        # DEBUG; without restoring it the root logger would stay at DEBUG and
        # leak that verbosity into every later test in the session.
        root.handlers = original_handlers
        root.setLevel(original_level)
