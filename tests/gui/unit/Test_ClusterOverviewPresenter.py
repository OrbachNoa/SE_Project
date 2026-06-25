"""Unit tests for ClusterOverviewPresenter's background-worker error handling.

ClusterWorker maps its own exceptions and emits `failed` with only the clean
user message (see SortWorker/ClusterWorker docs in
docs/error-handling-architecture-en.md, section 6.6). The presenter must still
route the worker's structured AppErrorInfo (`last_error`) into the controller's
technical log, the same way OutputScreenPresenter does for SortWorker.
"""
from unittest.mock import MagicMock

from src.gui.features.clusters.ClusterOverviewPresenter import ClusterOverviewPresenter


def _presenter():
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    detail_screen = MagicMock()
    compare_screen = MagicMock()
    presenter = ClusterOverviewPresenter(view, controller, router, detail_screen, compare_screen)
    return presenter, view, controller


# ===========================================================================
# TC-COP-001: a ClusterWorker failure's structured AppErrorInfo (last_error)
# reaches the controller's technical log, not just the GUI message.
# ===========================================================================
def test_on_worker_failed_logs_structured_error_via_controller():
    from src.application.errors.ErrorModel import AppErrorInfo, ErrorCategory, ErrorSeverity

    presenter, view, controller = _presenter()
    info = AppErrorInfo(
        code="SCHEDULING_UNEXPECTED_ERROR",
        category=ErrorCategory.SCHEDULING,
        severity=ErrorSeverity.ERROR,
        user_message="Could not compute clusters. Please try again.",
        technical_message="RuntimeError during clustering",
        recoverable=True,
    )
    mock_worker = MagicMock()
    mock_worker.last_error = info
    presenter._worker = mock_worker

    # Act — the worker's `failed` signal already carries only the user message.
    presenter._on_worker_failed("Could not compute clusters. Please try again.")

    # Assert
    assert controller.log_worker_error.call_count == 1
    assert controller.log_worker_error.call_args[0][0] is info
    assert view.show_message.call_count == 1


# ===========================================================================
# TC-COP-002: if no worker reference is held (e.g. failure surfaced before
# _kick_off ever ran), nothing is logged and the GUI message still shows.
# ===========================================================================
def test_on_worker_failed_without_worker_reference_does_not_log():
    presenter, view, controller = _presenter()
    presenter._worker = None

    presenter._on_worker_failed("Could not compute clusters. Please try again.")

    assert controller.log_worker_error.call_count == 0
    assert view.show_message.call_count == 1
