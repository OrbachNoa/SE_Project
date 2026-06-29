"""Unit tests for ClusterRequestWorker import behaviour."""
import importlib
import sys
# ===========================================================================
# TC-CRW-001: Ensure ClusterRequestWorker does not preload heavy sklearn exception modules.
# ===========================================================================
def test_cluster_request_worker_import_does_not_load_sklearn_exceptions():
    # Arrange
    sys.modules.pop("src.infrastructure.concurrency.ClusterRequestWorker", None)
    sys.modules.pop("sklearn.exceptions", None)

    # Act
    importlib.import_module("src.infrastructure.concurrency.ClusterRequestWorker")

    # Assert
    assert "sklearn.exceptions" not in sys.modules
