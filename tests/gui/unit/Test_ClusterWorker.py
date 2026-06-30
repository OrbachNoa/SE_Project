"""
Test suite for ClusterWorker.

Scope   : The background QThread that runs ClusteringCoordinator.prepare()
          and .cluster(k) off the GUI thread. Covers the success path
          (prepare() skipped when already prepared, finished emits the run)
          and the failure path (an exception is mapped to a clean user
          message via the registry, with last_error populated distinctly
          from the raw exception text).
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CW-001 .. TC-CW-005
Fixtures: qapp (tests/conftest.py)

ClusterWorker.run() does `from sklearn.exceptions import ConvergenceWarning`
unconditionally. This environment does not have scikit-learn installed, so
the success-path tests inject a minimal stub module into sys.modules for the
duration of the test (removed in a finally block) — this exercises the real
control flow (prepare/cluster/finished.emit) without requiring the real
dependency to be installed, mirroring how ClusterWorker only needs the one
symbol, ConvergenceWarning, to exist and be a Warning subclass.
"""
import sys
import types
from unittest.mock import MagicMock

import pytest

from src.infrastructure.concurrency.ClusterWorker import ClusterWorker

pytestmark = pytest.mark.usefixtures("qapp")


from unittest.mock import patch

@pytest.fixture
def stub_sklearn_exceptions():
    """Install a minimal sklearn.exceptions module exposing ConvergenceWarning using patch.dict."""
    class ConvergenceWarning(UserWarning):
        pass

    fake_exceptions = MagicMock()
    fake_exceptions.ConvergenceWarning = ConvergenceWarning

    with patch.dict(sys.modules, {
        "sklearn": MagicMock(),
        "sklearn.exceptions": fake_exceptions
    }):
        yield ConvergenceWarning

# TC-CW-001
# When the coordinator is not yet prepared, run() must call prepare() before
# cluster(), and finished must carry exactly the run cluster() returned.
def test_run_calls_prepare_then_cluster_when_not_prepared(qtbot, stub_sklearn_exceptions):
    # Arrange
    coordinator = MagicMock()
    coordinator.is_prepared = False
    fake_run = MagicMock(name="ClusteringRun")
    coordinator.cluster.return_value = fake_run
    worker = ClusterWorker(coordinator, config=None, k=3)

    # Act
    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    # Assert
    coordinator.prepare.assert_called_once_with(None)
    coordinator.cluster.assert_called_once_with(3)
    assert blocker.args == [fake_run]


# TC-CW-002
# When the coordinator is already prepared, run() must skip prepare()
# entirely and go straight to cluster() — re-fitting would waste the
# expensive sampling step for no reason.
def test_run_skips_prepare_when_already_prepared(qtbot, stub_sklearn_exceptions):
    # Arrange
    coordinator = MagicMock()
    coordinator.is_prepared = True
    fake_run = MagicMock(name="ClusteringRun")
    coordinator.cluster.return_value = fake_run
    worker = ClusterWorker(coordinator, config=None, k=None)

    # Act
    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        worker.start()
    worker.wait()

    # Assert
    coordinator.prepare.assert_not_called()
    coordinator.cluster.assert_called_once_with(None)
    assert blocker.args == [fake_run]


# TC-CW-003
# A failure raised from prepare() must be mapped through the exception
# registry into a clean failed.emit() message, and last_error must hold the
# structured AppErrorInfo — distinct from (and not containing) the raw
# exception's technical text.
def test_run_reports_failure_from_prepare_with_clean_message(stub_sklearn_exceptions):
    # Arrange
    coordinator = MagicMock()
    coordinator.is_prepared = False
    coordinator.prepare.side_effect = ValueError("no scored schedules available to cluster")
    worker = ClusterWorker(coordinator, config=None, k=None)
    messages = []
    worker.failed.connect(messages.append)

    # Act — run synchronously, mirroring the established SortWorker pattern.
    worker.run()

    # Assert
    assert len(messages) == 1
    assert messages[0] == "no scored schedules available to cluster"
    assert worker.last_error is not None
    assert worker.last_error.code == "INPUT_VALIDATION_FAILED"
    coordinator.cluster.assert_not_called()


# TC-CW-004
# A failure raised from cluster() (after a successful prepare()) must be
# reported the same way as a prepare() failure — both ultimately funnel
# through the same try/except in run().
def test_run_reports_failure_from_cluster_with_clean_message(stub_sklearn_exceptions):
    # Arrange
    coordinator = MagicMock()
    coordinator.is_prepared = True
    coordinator.cluster.side_effect = RuntimeError("prepare() must be called before cluster()")
    worker = ClusterWorker(coordinator, config=None, k=2)
    messages = []
    worker.failed.connect(messages.append)

    # Act
    worker.run()

    # Assert
    assert len(messages) == 1
    assert "RuntimeError" not in messages[0]
    assert worker.last_error is not None
    assert worker.last_error.category.value == "SCHEDULING"
    assert worker.last_error.technical_message.startswith("RuntimeError:")


# TC-CW-005
# An unexpected, unmapped exception (e.g. MemoryError) must still be caught
# by the broad except clause and surfaced through failed/last_error rather
# than crashing the worker thread silently.
def test_run_reports_memory_error_as_resource_failure(stub_sklearn_exceptions):
    # Arrange
    coordinator = MagicMock()
    coordinator.is_prepared = False
    coordinator.prepare.side_effect = MemoryError("oom during sampling")
    worker = ClusterWorker(coordinator, config=None, k=None)
    messages = []
    worker.failed.connect(messages.append)

    # Act
    worker.run()

    # Assert
    assert len(messages) == 1
    assert "MemoryError" not in messages[0]
    assert worker.last_error.code == "RESOURCE_MEMORY_EXHAUSTED"
