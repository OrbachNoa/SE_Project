"""
Test suite for SortLifecyclePresenter.

Scope   : Verifies starting, tracking, and safely stopping the background sort worker.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-SLP-001..002
"""
from unittest.mock import MagicMock, patch
from src.gui.features.output.SortLifecyclePresenter import SortLifecyclePresenter

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
