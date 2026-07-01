"""
Test suite for the output-screen sort components.

Consolidates the two sort-related units that previously lived in separate
single-purpose files: SortWorker (the background QThread that scores and
orders a large result set off the GUI thread) and SortLifecyclePresenter
(which starts, tracks, and safely retires that worker). Each component keeps
its own section and its original TC-ID family.

Scope   : SortWorker run/ready/failed behaviour and error mapping, plus
          SortLifecyclePresenter's start/stop/retire lifecycle management.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SW-001..003 (SortWorker), TC-GUI-SLP-001..002 (SortLifecyclePresenter)
Fixtures: qapp (tests/conftest.py)
"""
import pytest
from unittest.mock import MagicMock, patch

from src.gui.features.output.workers.SortWorker import SortWorker
from src.gui.features.output.SortLifecyclePresenter import SortLifecyclePresenter

pytestmark = pytest.mark.usefixtures("qapp")


# ===========================================================================
# SortWorker
#   The background QThread that runs the controller's compute_sort_data()
#   off the GUI thread.
# ===========================================================================

# ===========================================================================
# TC-SW-001: starting the worker runs compute_sort_data on the controller
# in the background and emits `ready` carrying its result.
# ===========================================================================
def test_sort_worker_runs_and_emits_ready_with_results(qtbot):
    # Arrange
    controller = MagicMock()
    controller.compute_sort_data.return_value = {"order": ["10101", "10102"]}
    worker = SortWorker(controller, ["MANDATORY_SPAN"])

    # Act
    with qtbot.waitSignal(worker.ready, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    # Assert
    controller.compute_sort_data.assert_called_once_with(["MANDATORY_SPAN"])
    assert blocker.args == [{"order": ["10101", "10102"]}]


# ===========================================================================
# TC-SW-002: an empty priority list is passed through unchanged and still
# completes successfully, emitting `ready` with whatever the controller
# returns rather than failing on the empty input.
# ===========================================================================
def test_sort_worker_handles_an_empty_priority_list(qtbot):
    # Arrange
    controller = MagicMock()
    controller.compute_sort_data.return_value = {}
    worker = SortWorker(controller, [])

    # Act
    with qtbot.waitSignal(worker.ready, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    # Assert
    controller.compute_sort_data.assert_called_once_with([])
    assert blocker.args == [{}]


# ===========================================================================
# TC-SW-003: a failure during the background sort is reported through `failed`
# as a clean message, and the structured record is recorded with a stable code.
# ===========================================================================
def test_sort_worker_reports_failure_with_structured_error():
    # Arrange
    controller = MagicMock()
    controller.compute_sort_data.side_effect = MemoryError("oom while sorting")
    worker = SortWorker(controller, ["MANDATORY_SPAN"])
    messages = []
    worker.failed.connect(messages.append)

    # Act — run synchronously so the test does not depend on pytest-qt.
    worker.run()

    # Assert — user message is clean (no raw exception text), record is typed.
    assert len(messages) == 1
    assert "memory" in messages[0].lower()
    assert "MemoryError" not in messages[0]
    assert worker.last_error is not None
    assert worker.last_error.code == "RESOURCE_MEMORY_EXHAUSTED"


# ===========================================================================
# SortLifecyclePresenter
#   Starts, tracks, and safely stops the background sort worker.
# ===========================================================================

# TC-GUI-SLP-001
# SortLifecyclePresenter must instantiate and return a SortWorker on start.
@patch("src.gui.features.output.SortLifecyclePresenter.SortWorker")
def test_sort_lifecycle_starts_worker(MockWorker):
    # Arrange
    controller = MagicMock()
    presenter = SortLifecyclePresenter(controller)

    # Act
    worker = presenter.start(["priority1"])

    # Assert
    MockWorker.assert_called_once_with(controller, ["priority1"])
    assert presenter.worker == MockWorker.return_value
    assert worker == MockWorker.return_value


# TC-GUI-SLP-002
# SortLifecyclePresenter must disconnect and retire active workers on stop.
def test_sort_lifecycle_stops_and_retires_worker():
    # Arrange
    controller = MagicMock()
    presenter = SortLifecyclePresenter(controller)

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    presenter.worker = mock_worker

    # Act
    presenter.stop()

    # Assert
    mock_worker.ready.disconnect.assert_called_once()
    mock_worker.failed.disconnect.assert_called_once()
    mock_worker.quit.assert_called_once()
    mock_worker.finished.connect.assert_called_once()

    assert mock_worker in presenter.retired_workers
    assert presenter.worker is None
