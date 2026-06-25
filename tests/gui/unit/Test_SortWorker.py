import pytest
from unittest.mock import MagicMock

from src.gui.features.output.workers.SortWorker import SortWorker

pytestmark = pytest.mark.usefixtures("qapp")


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
